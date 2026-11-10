#!/usr/bin/env python3
"""Run the fixed, directly related campaign in doc/FOLLOWUP_DESIGN.md."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
import json
from pathlib import Path
import shutil
import subprocess

from experiments import ROOT, WORK, fingerprint, replay, sha256
from result_validation import validate_replay, write_cache
from followup_traces import (
    records,
    graph_rows,
    mapping_rows,
    profile_edges,
    split_phases,
    phase_rows,
    emit,
)

PUBLISHED = ("rcm", "gorder", "porder")
LAYOUTS = ("identity", "bfs", "query_aware") + PUBLISHED
GRAPH_SETTINGS = {
    "reference": (100, 0),
    "index101": (101, 0),
    "index102": (102, 0),
    "order17": (100, 17),
}


def cases():
    return [
        (graph, seed)
        for graph in GRAPH_SETTINGS
        for seed in (range(1, 11) if graph == "reference" else range(1, 4))
    ]


def modes(layout):
    return (
        (("flat",) if layout in PUBLISHED else ())
        + ("bounded",)
        + (("sorted", "roundrobin") if layout in ("bfs", "query_aware") else ())
    )


def expected_followup():
    return {
        f"followup/{g}/seed{s}/{mode}/{layout}_{w}.json"
        for g, s in cases()
        for w in (128, 512)
        for layout in LAYOUTS
        for mode in modes(layout)
    }


def original_directory(graph, seed):
    return (
        ROOT
        / "results"
        / (
            f"sift/seed{seed}"
            if graph == "reference"
            else f"robustness/graphs/{graph}/seed{seed}"
        )
    )


def reference_directory(graph, seed):
    return (
        ROOT / f"results/robustness/reference/seed{seed}"
        if graph == "reference"
        else original_directory(graph, seed)
    )


def save_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def csv_text(data):
    import io

    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(data[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    return out.getvalue().encode()


def compress(path):
    compressed = Path(str(path) + ".gz")
    temporary = Path(str(compressed) + ".tmp")
    with path.open("rb") as src, temporary.open("wb") as dst:
        with gzip.GzipFile(filename="", fileobj=dst, mode="wb", mtime=0) as target:
            shutil.copyfileobj(src, target)
    temporary.replace(compressed)
    path.unlink()
    return compressed


def prepare(graph, seed):
    directory = WORK / f"followup/{graph}/seed{seed}/study"
    directory.mkdir(parents=True, exist_ok=True)
    index, insertion = GRAPH_SETTINGS[graph]
    command = [
        str(ROOT / "sprint1/run_study"),
        "--base",
        str(ROOT / "data/sift_base.fvecs"),
        "--queries",
        str(ROOT / "data/sift_query.fvecs"),
        "--max-base",
        "100000",
        "--train",
        "500",
        "--test",
        "200",
        "--seed",
        str(seed),
        "--index-seed",
        str(index),
        "--insertion-seed",
        str(insertion),
        "--no-traces",
        "--export-training",
        "--output",
        str(directory),
    ]
    signature = dict(
        command=command,
        binary=sha256(ROOT / "sprint1/run_study"),
        data=fingerprint(
            [ROOT / "data/sift_base.fvecs", ROOT / "data/sift_query.fvecs"]
        ),
    )
    stamp = directory / "prepared.json"
    required = [
        directory / p
        for p in (
            "graph.csv",
            "logical.csv",
            "training.csv",
            "insertion.csv",
            "split.csv",
            "recall.csv",
        )
    ] + [
        directory / f"{l}_{w}.mapping.csv"
        for l in ("identity", "random", "bfs", "community", "query_aware")
        for w in (128, 512)
    ]
    try:
        cached = json.loads(stamp.read_text()) == dict(
            signature=signature, files=fingerprint(required)
        )
    except (OSError, ValueError):
        cached = False
    if not cached:
        stamp.unlink(missing_ok=True)
        print("PROFILE", graph, seed, flush=True)
        with (directory / "study.log").open("w") as log:
            subprocess.run(
                command, stdout=log, stderr=subprocess.STDOUT, check=True, cwd=ROOT
            )
        save_json(stamp, dict(signature=signature, files=fingerprint(required)))
    ref = reference_directory(graph, seed)
    for name in ("split.csv", "recall.csv"):
        if (directory / name).read_bytes() != (ref / name).read_bytes():
            raise RuntimeError("query/result identity changed: " + name)
    hashes = {
        Path(k).name: v
        for k, v in json.loads((ref / "mapping_hashes.json").read_text()).items()
    }
    hashes.update(json.loads((ref / "graph_hashes.json").read_text()))
    for name, expected in hashes.items():
        if sha256(directory / name) != expected:
            raise RuntimeError("prior experiment changed: " + name)
    return directory, signature


def run_case(case):
    graph_name, seed = case
    directory, signature = prepare(graph_name, seed)
    result = ROOT / f"results/followup/{graph_name}/seed{seed}"
    result.mkdir(parents=True, exist_ok=True)
    graph = graph_rows(directory / "graph.csv")
    trace = records(directory / "logical.csv")
    training = records(directory / "training.csv")
    profile = profile_edges(training, graph)
    profile_path = directory / "profile.csv"
    profile_path.write_bytes(
        csv_text(
            [
                dict(source=a, target=b, traversals=c)
                for (a, b), c in sorted(profile.items())
            ]
        )
    )
    phases = split_phases(trace, graph)
    (result / "phases.csv.gz").write_bytes(
        gzip.compress(csv_text(phase_rows(phases)), mtime=0)
    )
    (result / "profile.csv.gz").write_bytes(
        gzip.compress(profile_path.read_bytes(), mtime=0)
    )
    for name in ("split.csv", "recall.csv"):
        shutil.copyfile(directory / name, result / name)
    costs = []
    for method in PUBLISHED:
        output = directory / f"{method}.mapping.csv"
        command = [
            str(ROOT / "bin/published_layouts"),
            str(directory / "graph.csv"),
            str(profile_path),
            method,
            str(output),
        ]
        print("LAYOUT", graph_name, seed, method, flush=True)
        measured = json.loads(subprocess.check_output(command, text=True, cwd=ROOT))
        mapping_rows(output, 100000)
        costs.append(dict(layout=method, **measured))
        (result / f"{method}.mapping.csv.gz").write_bytes(
            gzip.compress(output.read_bytes(), mtime=0)
        )
    (result / "layout_costs.csv").write_bytes(csv_text(costs))
    inputs = fingerprint(
        [
            directory / n
            for n in (
                "graph.csv",
                "logical.csv",
                "training.csv",
                "profile.csv",
                "insertion.csv",
                "split.csv",
                "recall.csv",
            )
        ]
        + list(directory.glob("*.mapping.csv"))
    )
    save_json(
        result / "inputs.json",
        dict(
            study=signature,
            input_hashes=inputs,
            original_equivalence=True,
            profile_edge_count=len(profile),
            profile_traversals=sum(profile.values()),
            phases_sha256=sha256(result / "phases.csv.gz"),
            phase_generator_sha256=sha256(ROOT / "scripts/followup_traces.py"),
            published_executable_sha256=sha256(ROOT / "bin/published_layouts"),
        ),
    )
    emissions = {}
    for width in (128, 512):
        for layout in LAYOUTS:
            map_path = directory / (
                f"{layout}.mapping.csv"
                if layout in PUBLISHED
                else f"{layout}_{width}.mapping.csv"
            )
            mapping = mapping_rows(map_path, 100000)
            canonical = None
            # Independent emission must reproduce retained flat traces before reuse.
            flat_path = directory / f"{layout}_{width}.trace"
            proof = emit(phases, graph, mapping, width, "flat", flat_path)
            emissions[f"flat/{layout}_{width}"] = proof
            canonical = proof["phase_multiset_sha256"]
            if layout not in PUBLISHED:
                old = json.loads(
                    (
                        original_directory(graph_name, seed)
                        / f"timing/{layout}_{width}.json"
                    ).read_text()
                )
                if proof["trace_sha256"] != old["trace_sha256"]:
                    raise RuntimeError("independent emitter changed original trace")
            for mode in modes(layout):
                path = (
                    flat_path
                    if mode == "flat"
                    else directory / f"{mode}_{layout}_{width}.trace"
                )
                if mode != "flat":
                    proof = emit(phases, graph, mapping, width, mode, path)
                    if proof["phase_multiset_sha256"] != canonical:
                        raise RuntimeError("schedule changed a phase's work")
                    emissions[f"{mode}/{layout}_{width}"] = proof
                label = f"followup/{graph_name}/seed{seed}/{mode}/{layout}_{width}"
                replay(path, label)
                output = ROOT / "results" / (label + ".json")
                sidecar = output.with_suffix(".queries.csv")
                if mode != "flat" and sidecar.exists():
                    compress(sidecar)
                    stamp = output.with_suffix(".cache.json")
                    saved = json.loads(stamp.read_text())
                    write_cache(stamp, output, saved["signature"])
                validate_replay(output)
                save_json(result / "emissions.json", emissions)
                if path != flat_path:
                    path.unlink()
            flat_path.unlink()
    print("COMPLETE", graph_name, seed, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("jobs must be positive")
    source = ROOT / ".toolchain/coleman/build.json"
    if not source.exists():
        raise SystemExit("Run python3 scripts/setup_published.py first")
    target = ROOT / "results/followup"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target / "published_source.json")
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(run_case, cases()[:1] if args.pilot else cases()))
    if not args.pilot:
        from followup_mechanism import run as run_mechanism

        run_mechanism()


if __name__ == "__main__":
    main()
