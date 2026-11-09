#!/usr/bin/env python3
"""Checked experiment matrix. Large traces stay in work/; auditable results go to results/."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("PIMANN_WORK", str(ROOT / "work")))
sys.path.insert(0, str(ROOT / "scripts"))
from run_ann_ramulator import sha256
from result_validation import cache_valid, write_cache

LAYOUTS = ("identity", "random", "bfs", "community", "query_aware")
WIDTHS = (128, 512)


def study_traces(directory):
    paths = [
        directory / f"{layout}_{width}.trace" for width in WIDTHS for layout in LAYOUTS
    ]
    missing = [str(p) for p in paths if not p.is_file() or not p.stat().st_size]
    if missing:
        raise RuntimeError(
            "Missing prerequisite traces; run the sift stage first: "
            + ", ".join(missing)
        )
    return paths


def execute(cmd, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        subprocess.run(
            [str(x) for x in cmd],
            cwd=ROOT,
            stdout=f,
            stderr=subprocess.STDOUT,
            check=True,
        )


def fingerprint(paths):
    return {
        (str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)): sha256(p)
        for p in sorted(paths)
    }


def study(
    label,
    *,
    seed=1,
    train=500,
    test=200,
    window=16,
    block=1024,
    n=100000,
    synthetic=False,
    index_seed=100,
    insertion_seed=0,
):
    dest = WORK / label
    dest.mkdir(parents=True, exist_ok=True)
    command = [
        ROOT / "sprint1/run_study",
        "--max-base",
        n,
        "--train",
        train,
        "--test",
        test,
        "--seed",
        seed,
        "--index-seed",
        index_seed,
        "--insertion-seed",
        insertion_seed,
        "--window",
        window,
        "--block-bytes",
        block,
        "--output",
        dest,
    ]
    if not synthetic:
        command += [
            "--base",
            ROOT / "data/sift_base.fvecs",
            "--queries",
            ROOT / "data/sift_query.fvecs",
        ]
    signature = {
        "command": [str(x) for x in command],
        "binary": sha256(ROOT / "sprint1/run_study"),
    }
    if not synthetic:
        signature["data"] = fingerprint(
            [ROOT / "data/sift_base.fvecs", ROOT / "data/sift_query.fvecs"]
        )
    stamp = dest / "run.json"
    required = [
        dest / f"{l}_{w}.{ext}"
        for w in WIDTHS
        for l in LAYOUTS
        for ext in ("trace", "mapping.csv")
    ]
    required += [
        dest / name
        for name in (
            "split.csv",
            "recall.csv",
            "metadata.csv",
            "layouts.csv",
            "logical.csv",
            "insertion.csv",
            "graph.csv",
        )
    ]
    complete = all(p.is_file() and p.stat().st_size for p in required)
    try:
        cached = json.loads(stamp.read_text()) == signature
    except (OSError, ValueError):
        cached = False
    if not complete or not cached:
        print("STUDY", label, flush=True)
        # An interrupted regeneration must not retain an older completion marker.
        stamp.unlink(missing_ok=True)
        execute(command, dest / "run.log")
        stamp.write_text(json.dumps(signature, indent=2) + "\n")
    result = ROOT / "results" / label
    result.mkdir(parents=True, exist_ok=True)
    for name in ["split.csv", "recall.csv", "metadata.csv", "layouts.csv", "run.json"]:
        shutil.copyfile(dest / name, result / name)
    mappings = fingerprint(list(dest.glob("*.mapping.csv")) + [dest / "logical.csv"])
    (result / "mapping_hashes.json").write_text(json.dumps(mappings, indent=2) + "\n")
    (result / "graph_hashes.json").write_text(
        json.dumps(
            {name: sha256(dest / name) for name in ("graph.csv", "insertion.csv")},
            indent=2,
        )
        + "\n"
    )
    return dest


def replay(trace, label, **parameters):
    output = ROOT / "results" / label
    output = output.with_suffix(".json")
    signature = {
        "trace": sha256(trace),
        "library": sha256(ROOT / "ramulator2/libramulator.so"),
        "runner": sha256(ROOT / "scripts/run_ann_ramulator.py"),
        "frontend": sha256(ROOT / "simulator/thesis_trace.cpp"),
        "parameters": parameters,
    }
    stamp = output.with_suffix(".cache.json")
    if cache_valid(stamp, output, signature):
        return
    command = [
        sys.executable,
        ROOT / "scripts/run_ann_ramulator.py",
        trace,
        "--output",
        output,
    ]
    for k, v in parameters.items():
        command += ["--" + k, str(v)]
    print("REPLAY", label, flush=True)
    execute(command, WORK / "logs" / (label.replace("/", "_") + ".log"))
    write_cache(stamp, output, signature)


def sift_seed(seed):
    directory = study(f"sift/seed{seed}", seed=seed)
    for trace in sorted(directory.glob("*.trace")):
        replay(trace, f"sift/seed{seed}/timing/{trace.stem}")
    # Keep split one for controller sensitivities; other transaction streams are
    # regenerable and large. Their hashes, mappings, logical traces and raw results remain.
    if seed != 1:
        for trace in directory.glob("*.trace"):
            trace.unlink()


def real_sensitivity():
    directory = WORK / "sift/seed1"
    traces = study_traces(directory)
    conditions = {
        "inflight1": {"inflight": 1},
        "inflight16": {"inflight": 16},
        "queue8": {"queue": 8},
        "issue4": {"issue": 4},
        "cap1": {"policy": "ClosedCAP", "cap": 1},
        "cap4": {"policy": "ClosedCAP", "cap": 4},
        "rowhit": {"scheduler": "FRFCFSRowHit"},
        "alternate_mapping": {"mapper": "ChRaBaRoCo"},
    }
    for name, params in conditions.items():
        for trace in traces:
            replay(trace, f"sensitivity/{name}/{trace.stem}", **params)
    for name, params in {
        "train100": {"train": 100},
        "train1000": {"train": 1000},
        "window4": {"window": 4},
        "window64": {"window": 64},
        "block2048": {"block": 2048},
    }.items():
        directory = study("ablations/" + name, **params)
        for trace in sorted(directory.glob("*.trace")):
            if trace.name.startswith(("bfs_", "query_aware_")):
                replay(trace, f"ablations/{name}/timing/{trace.stem}")
        for trace in directory.glob("*.trace"):
            trace.unlink()


def generate(tool, filename, **params):
    dest = WORK / "micro" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [ROOT / "bin" / tool, "--burst", 32]
    for k, v in params.items():
        command += ["--" + k, str(v)]
    with dest.open("w") as f:
        subprocess.run(
            [str(x) for x in command],
            cwd=ROOT,
            stdout=f,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    return dest


def micro():
    seq = generate("gen_trace", "seq.trace", pattern="seq")
    rand = generate("gen_trace", "rand.trace", pattern="rand")
    for name, trace in [("sequential", seq), ("random", rand)]:
        replay(trace, "micro/order/" + name)
    for w in [1, 16, 64, 256, 1024, 4096, 16384]:
        dest = WORK / "micro" / f"reorder{w}.trace"
        with rand.open() as f, dest.open("w") as g:
            subprocess.run(
                [ROOT / "bin/reorder", str(w)], stdin=f, stdout=g, check=True
            )
        if w == 16384 and dest.read_bytes() != seq.read_bytes():
            raise RuntimeError("full reorder != sequential")
        replay(dest, f"micro/reorder/w{w}")
        if w in [1, 256, 16384]:
            replay(dest, f"micro/reorder_rowhit/w{w}", scheduler="FRFCFSRowHit")
            replay(dest, f"micro/reorder_inflight1/w{w}", inflight=1)
    for width in [96, 128, 192, 256, 384, 512]:
        for offset in [0, 32, 480]:
            for run in [1, 2, 4, 8, 16, 32, 64]:
                trace = generate(
                    "gen_layout",
                    f"run_{width}_{offset}_{run}.trace",
                    dim=width,
                    base=0x100000 + offset,
                    cluster=run,
                )
                replay(trace, f"micro/runs/width{width}_offset{offset}_run{run}")
        for run in [1, 4, 16, 64]:
            trace = WORK / "micro" / f"run_{width}_0_{run}.trace"
            replay(
                trace,
                f"micro/runs_alternate/width{width}_run{run}",
                mapper="ChRaBaRoCo",
            )
    for quality in [0, 25, 50, 75, 90, 100]:
        trace = generate(
            "gen_layout", f"quality{quality}.trace", cluster=16, quality=quality
        )
        replay(trace, f"micro/quality/q{quality}")
    for cap in [1, 4]:
        for name, trace in [("sequential", seq), ("random", rand)]:
            replay(trace, f"micro/cap{cap}/{name}", policy="ClosedCAP", cap=cap)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "stage", choices=["micro", "sift", "sensitivity", "synthetic", "all"]
    )
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--jobs", type=int, default=2)
    a = p.parse_args()
    if a.seeds < 1 or a.jobs < 1:
        p.error("positive seeds/jobs required")
    if a.stage in ["micro", "all"]:
        micro()
    if a.stage in ["sift", "all"]:
        with ThreadPoolExecutor(max_workers=a.jobs) as pool:
            list(pool.map(sift_seed, range(1, a.seeds + 1)))
        shutil.copyfile(ROOT / "data/manifest.json", ROOT / "results/sift/dataset.json")
    if a.stage in ["sensitivity", "all"]:
        real_sensitivity()
    if a.stage in ["synthetic", "all"]:
        dest = study("synthetic", n=8000, train=300, test=150, synthetic=True)
        for trace in sorted(dest.glob("*.trace")):
            replay(trace, "synthetic/timing/" + trace.stem)
    provenance = {
        "sources": fingerprint(
            list((ROOT / "src").glob("*.*"))
            + list((ROOT / "sprint1/src").rglob("*.cpp"))
            + list((ROOT / "sprint1/src").rglob("*.h"))
            + list((ROOT / "simulator").glob("*.cpp"))
        ),
        "compiler": subprocess.check_output(
            ["c++", "--version"], text=True
        ).splitlines()[0],
        "cmake": subprocess.check_output(
            ["cmake", "--version"], text=True
        ).splitlines()[0],
        "python": sys.version,
        "platform": sys.platform,
        "stage": a.stage,
        "seeds": a.seeds,
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (ROOT / "results" / ("provenance_" + a.stage + ".json")).write_text(
        json.dumps(provenance, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
