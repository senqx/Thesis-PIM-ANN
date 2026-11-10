"""Calibrate an optional HNSW vector-fetch order using training queries only."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json

from experiments import ROOT, WORK, fingerprint, replay, sha256
from followup import compress, csv_text, prepare, save_json
from followup_traces import emit, graph_rows, mapping_rows, records, rows, split_phases
from result_validation import validate_replay, write_cache
from scheduling import CONDITIONS, ORDERS, batch_phases

CONFIGURATIONS = {"default": (0, {}), **CONDITIONS}
PROFILE_QUERIES = 50


def expected_calibration():
    return {
        f"calibration/seed{s}/{c}/{order}_{width}.json"
        for s in range(1, 11)
        for c in CONFIGURATIONS
        for order in ORDERS
        for width in (128, 512)
    }


def choose_order(costs):
    if set(costs) != set(ORDERS) or any(
        type(v) is not int or v <= 0 for v in costs.values()
    ):
        raise ValueError("complete positive calibration costs required")
    return min(ORDERS, key=lambda order: costs[order])


def select_training(trace, split):
    selected = sorted(
        (r for r in split if r["partition"] == "train"),
        key=lambda r: int(r["position"]),
    )[:PROFILE_QUERIES]
    if [int(r["position"]) for r in selected] != list(range(PROFILE_QUERIES)):
        raise ValueError("incomplete calibration training prefix")
    ids = {int(r["source_query"]) for r in selected}
    test = {int(r["source_query"]) for r in split if r["partition"] == "test"}
    if len(ids) != PROFILE_QUERIES or ids & test:
        raise ValueError("calibration/test query overlap")
    filtered = [r for r in trace if 0 <= r[0] < PROFILE_QUERIES]
    if {r[0] for r in filtered} != set(range(PROFILE_QUERIES)):
        raise ValueError("incomplete calibration trace")
    return filtered, selected


def run_seed(seed):
    study, _ = prepare("reference", seed)
    old = ROOT / f"results/followup/reference/seed{seed}"
    folder = ROOT / f"results/calibration/seed{seed}"
    work = WORK / f"calibration/seed{seed}"
    folder.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    graph = graph_rows(study / "graph.csv")
    trace, selected = select_training(
        records(study / "training.csv"), rows(old / "split.csv")
    )
    logical = csv_text(
        [dict(zip(("query", "node", "kind", "level", "bytes"), row)) for row in trace]
    )
    (folder / "logical.csv.gz").write_bytes(gzip.compress(logical, mtime=0))
    (folder / "selected_queries.csv").write_bytes(csv_text(selected))
    phases = split_phases(trace, graph)
    proofs, selections = {}, {}
    for cap in (0, 2, 8):
        groups, info = batch_phases(phases, cap)
        (folder / f"phases_batch{cap}.csv.gz").write_bytes(
            gzip.compress(csv_text(info), mtime=0)
        )
        for width in (128, 512):
            mapping = mapping_rows(study / f"bfs_{width}.mapping.csv", 100000)
            path = work / f"batch{cap}_{width}.trace"
            canonical = None
            for order in ORDERS:
                proof = emit(groups, graph, mapping, width, order, path)
                canonical = (
                    proof["phase_multiset_sha256"] if canonical is None else canonical
                )
                assert canonical == proof["phase_multiset_sha256"]
                proofs[f"batch{cap}/{order}_{width}"] = proof
                for condition, (batch, parameters) in CONFIGURATIONS.items():
                    if cap != batch:
                        continue
                    label = f"calibration/seed{seed}/{condition}/{order}_{width}"
                    replay(path, label, **parameters)
                    output = ROOT / "results" / (label + ".json")
                    result = validate_replay(output)
                    assert result["trace_sha256"] == proof["trace_sha256"]
                    if output.with_suffix(".queries.csv").exists():
                        compress(output.with_suffix(".queries.csv"))
                        stamp = output.with_suffix(".cache.json")
                        write_cache(
                            stamp, output, json.loads(stamp.read_text())["signature"]
                        )
            path.unlink()
            for condition, (batch, _) in CONFIGURATIONS.items():
                if cap != batch:
                    continue
                costs = {
                    order: json.loads(
                        (folder / condition / f"{order}_{width}.json").read_text()
                    )["cycles"]
                    for order in ORDERS
                }
                selections[f"{condition}/{width}"] = dict(
                    training_cycles=costs, selected_order=choose_order(costs)
                )
    save_json(folder / "emissions.json", proofs)
    save_json(folder / "selection.json", selections)
    save_json(
        folder / "inputs.json",
        dict(
            source_hashes=fingerprint(
                [old / "inputs.json", old / "split.csv"]
                + [
                    study / n
                    for n in (
                        "graph.csv",
                        "training.csv",
                        "bfs_128.mapping.csv",
                        "bfs_512.mapping.csv",
                    )
                ]
            ),
            retained_hashes=fingerprint(
                list(folder.glob("*.gz"))
                + [
                    folder / n
                    for n in (
                        "selected_queries.csv",
                        "selection.json",
                        "emissions.json",
                    )
                ]
            ),
            generator_sha256=sha256(ROOT / "scripts/profiled_fetch.py"),
            batching_generator_sha256=sha256(ROOT / "scripts/scheduling.py"),
            design_sha256=sha256(ROOT / "doc/PROFILED_FETCH_DESIGN.md"),
            profile_queries=PROFILE_QUERIES,
        ),
    )
    print("COMPLETE calibration", seed, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("jobs must be positive")
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(run_seed, range(1, 11)))


if __name__ == "__main__":
    main()
