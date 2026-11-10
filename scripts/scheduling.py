"""Fixed scheduling sensitivity matrix; preserve all earlier replay evidence."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json

from experiments import ROOT, WORK, fingerprint, replay, sha256
from followup import compress, csv_text, prepare, save_json
from followup_traces import (
    emit,
    graph_rows,
    mapping_rows,
    phase_rows,
    records,
    split_phases,
)
from result_validation import validate_replay, write_cache

ORDERS = ("bounded", "sorted", "roundrobin")
CONDITIONS = {
    "inflight16": (0, {"inflight": 16}),
    "inflight32": (0, {"inflight": 32}),
    "inflight128": (0, {"inflight": 128}),
    "batch2": (2, {}),
    "batch8": (8, {}),
    "alternate_mapping": (0, {"mapper": "ChRaBaRoCo"}),
}


def expected_scheduling():
    return {
        f"scheduling/seed{s}/{c}/{order}_{width}.json"
        for s in range(1, 11)
        for c in CONDITIONS
        for order in ORDERS
        for width in (128, 512)
    }


def batch_phases(phases, cap):
    if cap < 0:
        raise ValueError("negative vector batch size")
    groups, parents = [], []
    for parent, phase in enumerate(phases):
        size = cap if cap and phase[0][2] == "V" else len(phase)
        for start in range(0, len(phase), size):
            groups.append(phase[start : start + size])
            parents.append(parent)
    if [r for p in groups for r in p] != [r for p in phases for r in p]:
        raise ValueError("batching changed logical work")
    info = phase_rows(groups)
    for row, parent in zip(info, parents, strict=True):
        row["parent_phase"] = parent
    return groups, info


def run_seed(seed):
    study, _ = prepare("reference", seed)
    old = ROOT / f"results/followup/reference/seed{seed}"
    out = ROOT / f"results/scheduling/seed{seed}"
    work = WORK / f"scheduling/seed{seed}"
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    graph = graph_rows(study / "graph.csv")
    phases = split_phases(records(study / "logical.csv"), graph)
    if gzip.decompress((old / "phases.csv.gz").read_bytes()) != csv_text(
        phase_rows(phases)
    ):
        raise ValueError("previous phase membership changed")
    old_emissions = json.loads((old / "emissions.json").read_text())
    proofs = {}
    for cap in (0, 2, 8):
        groups, info = batch_phases(phases, cap)
        sidecar = out / f"phases_batch{cap}.csv.gz"
        sidecar.write_bytes(gzip.compress(csv_text(info), mtime=0))
        for width in (128, 512):
            mapping = mapping_rows(study / f"bfs_{width}.mapping.csv", 100000)
            path = work / f"batch{cap}_{width}.trace"
            flat = emit(groups, graph, mapping, width, "flat", path)
            if (
                flat["trace_sha256"]
                != old_emissions[f"flat/bfs_{width}"]["trace_sha256"]
            ):
                raise ValueError("batching changed original flat trace")
            proofs[f"batch{cap}/flat_{width}"] = flat
            for order in ORDERS:
                proof = emit(groups, graph, mapping, width, order, path)
                if proof["phase_multiset_sha256"] != flat["phase_multiset_sha256"]:
                    raise ValueError("schedule changed batch transaction multiset")
                if not cap and proof != old_emissions[f"{order}/bfs_{width}"]:
                    raise ValueError("previous bounded request stream changed")
                proofs[f"batch{cap}/{order}_{width}"] = proof
                for condition, (batch, parameters) in CONDITIONS.items():
                    if batch != cap:
                        continue
                    label = f"scheduling/seed{seed}/{condition}/{order}_{width}"
                    replay(path, label, **parameters)
                    result = ROOT / "results" / (label + ".json")
                    measured = validate_replay(result)
                    assert measured["trace_sha256"] == proof["trace_sha256"]
                    plain = result.with_suffix(".queries.csv")
                    if plain.exists():
                        compress(plain)
                        stamp = result.with_suffix(".cache.json")
                        write_cache(
                            stamp, result, json.loads(stamp.read_text())["signature"]
                        )
            path.unlink()
    save_json(out / "emissions.json", proofs)
    sources = [
        old / n
        for n in (
            "inputs.json",
            "phases.csv.gz",
            "emissions.json",
            "split.csv",
            "recall.csv",
        )
    ]
    sources += [
        study / n
        for n in (
            "graph.csv",
            "logical.csv",
            "bfs_128.mapping.csv",
            "bfs_512.mapping.csv",
        )
    ]
    save_json(
        out / "inputs.json",
        dict(
            source_hashes=fingerprint(sources),
            phase_hashes={
                p.name: sha256(p) for p in sorted(out.glob("phases_*.csv.gz"))
            },
            generator_sha256=sha256(ROOT / "scripts/scheduling.py"),
            design_sha256=sha256(ROOT / "doc/SCHEDULING_DESIGN.md"),
            emissions_sha256=sha256(out / "emissions.json"),
        ),
    )
    print("COMPLETE scheduling", seed, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("jobs must be positive")
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(run_seed, [1] if args.pilot else range(1, 11)))


if __name__ == "__main__":
    main()
