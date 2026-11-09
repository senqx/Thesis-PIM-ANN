#!/usr/bin/env python3
"""Bounded robustness and mechanism campaign; see doc/RESEARCH_CLOSURE.md."""

from concurrent.futures import ThreadPoolExecutor
import argparse
import csv
import json
from pathlib import Path

from experiments import ROOT, WORK, study, study_traces, replay, sha256

CONDITIONS = {
    "inflight1": {"inflight": 1},
    "cap4": {"policy": "ClosedCAP", "cap": 4},
    "alternate_mapping": {"mapper": "ChRaBaRoCo"},
}
GRAPHS = {"index101": (101, 0), "index102": (102, 0), "order17": (100, 17)}


def records(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def controller_seed(seed):
    label = f"robustness/reference/seed{seed}"
    directory = study(label, seed=seed)
    original = ROOT / "results/sift" / f"seed{seed}"
    # A changed generator must reproduce the old logical experiment before
    # the retained default timings can be reused as the comparison reference.
    for name in ("split.csv", "recall.csv"):
        if (directory / name).read_bytes() != (original / name).read_bytes():
            raise RuntimeError(f"primary query/results changed: seed {seed}, {name}")
    old_hashes = json.loads((original / "mapping_hashes.json").read_text())
    for name in ["logical.csv"] + [
        f"{p.stem}.mapping.csv" for p in study_traces(directory)
    ]:
        expected = next(v for k, v in old_hashes.items() if Path(k).name == name)
        if sha256(directory / name) != expected:
            raise RuntimeError(f"primary logical/mapping mismatch: {seed} {name}")
    verified = {}
    for trace in study_traces(directory):
        old = json.loads((original / "timing" / f"{trace.stem}.json").read_text())
        digest = sha256(trace)
        if digest != old["trace_sha256"]:
            raise RuntimeError(f"primary trace mismatch: {seed} {trace.name}")
        verified[trace.name] = digest
        for condition, params in CONDITIONS.items():
            replay(
                trace,
                f"robustness/controllers/{condition}/seed{seed}/{trace.stem}",
                **params,
            )
    result = ROOT / "results" / label
    (result / "primary_equivalence.json").write_text(
        json.dumps(
            {
                "binary_sha256": sha256(ROOT / "sprint1/run_study"),
                "split_recall_logical_mappings_identical": True,
                "trace_hashes": verified,
            },
            indent=2,
        )
        + "\n"
    )
    if seed != 1:
        for trace in study_traces(directory):
            trace.unlink()


def graph_seed(item):
    name, seed = item
    index, insertion = GRAPHS[name]
    label = f"robustness/graphs/{name}/seed{seed}"
    directory = study(label, seed=seed, index_seed=index, insertion_seed=insertion)
    reference = ROOT / "results/sift" / f"seed{seed}/split.csv"
    if (directory / "split.csv").read_bytes() != reference.read_bytes():
        raise RuntimeError("graph study changed query IDs")
    for trace in study_traces(directory):
        replay(trace, f"{label}/timing/{trace.stem}")
    for trace in study_traces(directory):
        trace.unlink()


def mechanism():
    directory = WORK / "robustness/reference/seed1"
    study_traces(directory)
    from trace_diagnostics import record_offered_banks

    record_offered_banks(ROOT, WORK)
    dest = WORK / "mechanism"
    dest.mkdir(parents=True, exist_ok=True)
    for layout in ("bfs", "query_aware"):
        trace = directory / f"{layout}_128.trace"
        for component, kind in (("mixed", None), ("vectors", "V"), ("adjacency", "A")):
            filtered = trace
            if kind:
                filtered = dest / f"{layout}_{component}.trace"
                with trace.open() as source, filtered.open("w") as target:
                    for line in source:
                        if line.split()[-1] == kind:
                            target.write(line)
            for inflight in (1, 64):
                replay(
                    filtered,
                    f"mechanism/sift/{layout}_{component}_inflight{inflight}",
                    inflight=inflight,
                    commands=1,
                )
    for layout, filename in (("sequential", "seq.trace"), ("random", "rand.trace")):
        trace = WORK / "micro" / filename
        if not trace.is_file():
            raise RuntimeError("run the micro stage before the mechanism stage")
        for inflight in (1, 64):
            replay(
                trace,
                f"mechanism/micro/{layout}_inflight{inflight}",
                inflight=inflight,
                commands=2,
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("controllers", "graphs", "mechanism", "all"))
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("jobs must be positive")
    if args.stage in ("controllers", "all"):
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(controller_seed, range(1, 11)))
    if args.stage in ("graphs", "all"):
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(graph_seed, [(g, s) for g in GRAPHS for s in range(1, 4)]))
    if args.stage in ("mechanism", "all"):
        mechanism()


if __name__ == "__main__":
    main()
