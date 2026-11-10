"""Compare fresh simulator evidence with a separate retained result tree."""

import argparse
import copy
import gzip
import json
from pathlib import Path

from experiment_matrix import expected_replays
from result_validation import query_rows, validate_replay


def compare_inputs(reference, candidate):
    """Compare retained scientific inputs while excluding host timings and build paths."""
    names = {
        "dataset.json",
        "split.csv",
        "recall.csv",
        "selected_queries.csv",
        "emissions.json",
        "selection.json",
        "graph_hashes.json",
        "mapping_hashes.json",
    }
    comparisons = {}
    for path in sorted(reference.rglob("*")):
        if not path.is_file() or not (
            path.name in names
            or path.name.endswith(".csv.gz")
            and ".queries." not in path.name
        ):
            continue
        name = str(path.relative_to(reference))

        def content(p):
            if p.name == "mapping_hashes.json":
                data = json.loads(p.read_text())
                normalized = {Path(k).name: v for k, v in data.items()}
                if len(normalized) != len(data):
                    raise ValueError("ambiguous mapping-hash filenames")
                return normalized
            if p.suffix == ".json":
                return json.loads(p.read_text())
            return (
                gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
            )

        try:
            comparisons[name] = dict(matched=content(path) == content(candidate / name))
        except (OSError, ValueError) as error:
            comparisons[name] = dict(matched=False, error=str(error))
    return comparisons


def model_config(result):
    config = copy.deepcopy(result["config"])
    for field in ("path", "query_output"):
        config["frontend"].pop(field, None)
    for controller in config["memory_system"]["controllers"]:
        for plugin in controller.get("controller_plugins", []):
            plugin.pop("path", None)
    return config


def compare_replays(reference, candidate):
    before, after = validate_replay(reference), validate_replay(candidate)
    fields = (
        "ramulator_commit",
        "frontend_sha256",
        "trace_sha256",
        "parameters",
        "checks",
        "cycles",
        "row_hit_pct",
        "mean_query_cycles",
        "stats",
    )
    differences = [field for field in fields if before[field] != after[field]]
    if model_config(before) != model_config(after):
        differences.append("model_configuration")
    if query_rows(reference) != query_rows(candidate):
        differences.append("per_query_or_phase_service")
    if before.get("command_counts") != after.get("command_counts"):
        differences.append("command_counts")
    return dict(
        matched=not differences,
        differences=differences,
        reference_cycles=before["cycles"],
        candidate_cycles=after["cycles"],
        reference_library_sha256=before["library_sha256"],
        candidate_library_sha256=after["library_sha256"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference", type=Path, required=True, help="Retained results directory"
    )
    parser.add_argument(
        "--candidate", type=Path, required=True, help="Fresh results directory"
    )
    parser.add_argument(
        "--result",
        action="append",
        help="Optional path relative to results; repeat to select cases",
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.reference.resolve() == args.candidate.resolve():
        parser.error("reference and candidate must be separate result trees")
    expected = expected_replays()
    paths = set(args.result) if args.result else expected
    if not paths or not paths <= expected:
        parser.error("select only named results from the retained experiment matrix")
    report = {}
    for name in sorted(paths):
        try:
            report[name] = compare_replays(args.reference / name, args.candidate / name)
        except (OSError, ValueError, KeyError, AssertionError) as error:
            report[name] = dict(matched=False, error=str(error))
    inputs = compare_inputs(args.reference, args.candidate) if paths == expected else {}
    success = all(r["matched"] for r in report.values()) and all(
        r["matched"] for r in inputs.values()
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            dict(
                full_matrix=paths == expected,
                compared=len(paths),
                matched=success,
                reference=str(args.reference.resolve()),
                candidate=str(args.candidate.resolve()),
                comparisons=report,
                scientific_inputs=inputs,
                interpretation="Exact simulator outputs and query/phase service are compared. Filesystem paths and rebuilt-library byte identity are reported separately from scientific equality. Shared-host preprocessing seconds are not asserted equal.",
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"{'MATCH' if success else 'MISMATCH'}: {len(paths)} replay comparisons; report: {args.report}"
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
