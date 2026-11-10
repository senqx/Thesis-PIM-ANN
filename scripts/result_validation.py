"""Validate complete replay artifacts before analysis or cache reuse."""

import csv
import gzip
import hashlib
import json
import math
from pathlib import Path


DEFAULTS = dict(
    inflight=64,
    policy="Open",
    cap=4,
    scheduler="FRFCFS",
    mapper="RoBaRaCoCh",
    queue=32,
    issue=1,
)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def query_path(path):
    plain = Path(path).with_suffix(".queries.csv")
    compressed = Path(str(plain) + ".gz")
    require(not (plain.exists() and compressed.exists()), "ambiguous query sidecars")
    return compressed if compressed.exists() else plain


def query_rows(path):
    path = query_path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_replay(path, signature=None):
    """Raise on incomplete/malformed evidence, including missing sidecar files."""
    path = Path(path)
    data = json.loads(path.read_text())
    checks = data["checks"]
    expected = {
        "trace_reads",
        "completed_callbacks",
        "submitted",
        "served",
        "classified",
    }
    require(set(checks) == expected, f"{path}: missing accounting fields")
    require(
        all(type(v) is int and v > 0 for v in checks.values()), "invalid read count"
    )
    count = checks["trace_reads"]
    require(set(checks.values()) == {count}, f"{path}: inconsistent read accounting")
    front = data["stats"]["frontend"]
    ctrl = data["stats"]["memory_system"]["controller"]
    if isinstance(ctrl, list):
        require(len(ctrl) == 1, "expected one controller")
        ctrl = ctrl[0]
    require(
        front["submitted"] == front["completed"] == count, "frontend count mismatch"
    )
    require(
        ctrl["num_read_reqs"] == ctrl["num_read_reqs_served"] == count,
        "controller count mismatch",
    )
    classified = sum(
        ctrl[k] for k in ("read_row_hits", "read_row_misses", "read_row_conflicts")
    )
    require(classified == count, "row classification count mismatch")
    require(
        0 < front["peak_inflight"] <= data["parameters"]["inflight"],
        "inflight violation",
    )
    require(
        type(data["cycles"]) is int
        and data["cycles"] > 0
        and data["cycles"] == ctrl["cycles"],
        "invalid cycles",
    )
    hit = data["row_hit_pct"]
    require(
        math.isfinite(hit) and abs(hit - 100 * ctrl["read_row_hits"] / count) < 1e-9,
        "invalid row-hit percentage",
    )
    queries = query_rows(path)
    require(bool(queries), "empty query timing file")
    ids = [int(q["query"]) for q in queries]
    require(ids == sorted(set(ids)) and ids[0] >= 0, "invalid query sequence")
    require(sum(int(q["reads"]) for q in queries) == count, "query read count mismatch")
    previous = -1
    for q in queries:
        first, last, cycles = (
            int(q[k]) for k in ("first_arrive", "last_depart", "cycles")
        )
        require(
            int(q["reads"]) > 0 and last - first == cycles > 0,
            "invalid query service interval",
        )
        require(first >= previous and last <= data["cycles"], "queries do not drain")
        previous = last
    mean = sum(int(q["cycles"]) for q in queries) / len(queries)
    require(
        math.isfinite(data["mean_query_cycles"])
        and abs(data["mean_query_cycles"] - mean) < 1e-8,
        "query mean mismatch",
    )
    if signature is not None:
        for key, field in (
            ("trace", "trace_sha256"),
            ("library", "library_sha256"),
            ("frontend", "frontend_sha256"),
        ):
            require(data[field] == signature[key], f"{field} does not match inputs")
        requested = signature["parameters"]
        require(
            data["parameters"]
            == {**DEFAULTS, **{k: v for k, v in requested.items() if k != "commands"}},
            "replay configuration does not match inputs",
        )
        require(
            bool(data.get("command_counts")) == bool(requested.get("commands", 0)),
            "command diagnostics missing or unexpected",
        )
    if "command_counts" in data:
        counts = data["command_counts"]
        require(counts["RD"] + counts.get("RDA", 0) == count, "command read mismatch")
        require(
            sum(counts.values()) <= data["cycles"], "too many commands for GenericDDR"
        )
        sidecar = path.with_suffix(".commands.csv")
        with sidecar.open() as stream:
            recorded = {r[0]: int(r[1]) for r in csv.reader(stream)}
        require(recorded == counts, "command sidecar mismatch")
        plugins = data["config"]["memory_system"]["controllers"][0].get(
            "controller_plugins", []
        )
        if any(p["impl"] == "CmdTraceRecorder" for p in plugins):
            trace = path.with_suffix(".command_trace.csv.ch0")
            from collections import Counter

            observed = Counter()
            previous = 0
            with trace.open() as stream:
                for row in csv.DictReader(stream):
                    cycle = int(row["clock"])
                    require(previous < cycle <= data["cycles"], "invalid command clock")
                    previous = cycle
                    observed[row["command"]] += 1
            require(
                all(observed[k] == v for k, v in counts.items())
                and not set(observed) - set(counts),
                "command trace mismatch",
            )
    return data


def cache_valid(stamp, output, signature):
    try:
        saved = json.loads(Path(stamp).read_text())
        if saved["signature"] != signature:
            return False
        validate_replay(output, signature)
        artifacts = [Path(output), query_path(output)]
        if signature["parameters"].get("commands", 0):
            artifacts.append(Path(output).with_suffix(".commands.csv"))
        if signature["parameters"].get("commands", 0) == 2:
            artifacts.append(Path(output).with_suffix(".command_trace.csv.ch0"))
        return saved["artifacts"] == {p.name: sha256(p) for p in artifacts}
    except (OSError, EOFError, ValueError, KeyError, TypeError, OverflowError):
        return False


def write_cache(stamp, output, signature):
    validate_replay(output, signature)
    artifacts = [Path(output), query_path(output)]
    if signature["parameters"].get("commands", 0):
        artifacts.append(Path(output).with_suffix(".commands.csv"))
    if signature["parameters"].get("commands", 0) == 2:
        artifacts.append(Path(output).with_suffix(".command_trace.csv.ch0"))
    record = dict(signature=signature, artifacts={p.name: sha256(p) for p in artifacts})
    temporary = Path(stamp).with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    temporary.replace(stamp)
