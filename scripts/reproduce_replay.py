"""Rebuild HNSW demands and freshly simulate one vector-fetch comparison, without replay caches."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from compare_reproduction import compare_replays
from experiments import ROOT, WORK, sha256
from followup_traces import emit, graph_rows, mapping_rows, records, rows, split_phases
from profiled_fetch import CONFIGURATIONS, select_training
from result_validation import validate_replay
from scheduling import batch_phases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "result",
        type=Path,
        help="A scheduling/calibration record, or reference-graph BFS follow-up record",
    )
    parser.add_argument(
        "--output-directory", type=Path, help="New directory; must not already exist"
    )
    args = parser.parse_args()
    reference = args.result.resolve()
    try:
        name = str(reference.relative_to(ROOT / "results"))
    except ValueError:
        parser.error("result must be inside this checkout's results directory")
    match = re.fullmatch(
        r"(scheduling|calibration)/seed(\d+)/([^/]+)/(bounded|sorted|roundrobin)_(128|512)\.json",
        name,
    )
    if match:
        family, seed, condition, order, width = match.groups()
    else:
        match = re.fullmatch(
            r"followup/reference/seed(\d+)/(flat|bounded|sorted|roundrobin)/bfs_(128|512)\.json",
            name,
        )
        if not match:
            parser.error(
                "use a scheduling/calibration record or reference BFS follow-up record; the complete reproduction procedure covers the other families"
            )
        seed, order, width = match.groups()
        family, condition = "followup", "default"
    if condition not in CONFIGURATIONS or not 1 <= int(seed) <= 10:
        parser.error("unknown seed or configuration")
    baseline = validate_replay(reference)
    if args.output_directory:
        destination = args.output_directory.resolve()
        if destination.is_relative_to(ROOT / "results") or destination.is_relative_to(
            ROOT / "archive"
        ):
            parser.error("fresh output must be outside results and archives")
        destination.mkdir(parents=True, exist_ok=False)
    else:
        (WORK / "reproductions").mkdir(parents=True, exist_ok=True)
        destination = Path(
            tempfile.mkdtemp(prefix="fresh-", dir=WORK / "reproductions")
        )
    study = destination / "study"
    inputs = json.loads(
        (ROOT / f"results/followup/reference/seed{seed}/inputs.json").read_text()
    )
    data_hashes = {name: sha256(ROOT / name) for name in inputs["study"]["data"]}
    if data_hashes != inputs["study"]["data"]:
        raise ValueError("dataset bytes differ from the retained experiment")
    command = list(inputs["study"]["command"])
    command[0] = str(ROOT / "sprint1/run_study")
    for flag, value in (
        ("--base", ROOT / "data/sift_base.fvecs"),
        ("--queries", ROOT / "data/sift_query.fvecs"),
        ("--output", study),
    ):
        command[command.index(flag) + 1] = str(value)
    print(f"Fresh graph/search reconstruction: {name}", flush=True)
    with (destination / "search.log").open("w") as log:
        subprocess.run(
            command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True
        )
    verified = {}
    for path, expected in inputs["input_hashes"].items():
        fresh = study / Path(path).name
        if fresh.exists():
            observed = sha256(fresh)
            if observed != expected:
                raise ValueError(f"reconstructed input differs: {fresh.name}")
            verified[fresh.name] = observed
    required = {
        "graph.csv",
        "logical.csv",
        "training.csv",
        "split.csv",
        "recall.csv",
        "insertion.csv",
        f"bfs_{width}.mapping.csv",
    }
    if not required <= verified.keys():
        raise ValueError("missing search/placement reconstruction evidence")
    graph = graph_rows(study / "graph.csv")
    logical = records(
        study / ("training.csv" if family == "calibration" else "logical.csv")
    )
    if family == "calibration":
        logical, _ = select_training(logical, rows(study / "split.csv"))
    groups, _ = batch_phases(split_phases(logical, graph), CONFIGURATIONS[condition][0])
    trace = destination / "fresh.trace"
    proof = emit(
        groups,
        graph,
        mapping_rows(study / f"bfs_{width}.mapping.csv", 100000),
        int(width),
        order,
        trace,
    )
    if proof["trace_sha256"] != baseline["trace_sha256"]:
        raise ValueError("freshly emitted trace differs from retained evidence")
    output = destination / "fresh.json"
    command = [
        sys.executable,
        str(ROOT / "scripts/run_ann_ramulator.py"),
        str(trace),
        "--output",
        str(output),
    ]
    for key, value in baseline["parameters"].items():
        command.extend(["--" + key, str(value)])
    print("Fresh simulator invocation (replay cache bypassed)", flush=True)
    with (destination / "replay.log").open("w") as log:
        subprocess.run(
            command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True
        )
    comparison = compare_replays(reference, output)
    report = dict(
        reference=name,
        fresh_output=str(output),
        search_reconstructed=True,
        replay_cache_used=False,
        reconstructed_inputs=verified,
        data_hashes=data_hashes,
        comparison=comparison,
    )
    (destination / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"{'MATCH' if comparison['matched'] else 'MISMATCH'}: {destination / 'comparison.json'}",
        flush=True,
    )
    raise SystemExit(0 if comparison["matched"] else 1)


if __name__ == "__main__":
    main()
