#!/usr/bin/env python3
"""Small synthetic DPU feasibility matrix; reproduce with --compile then --run.

All seeds are exploratory. Graph hints use full input topology, not future
timing or a test-trained policy. This kernel has 64 destination vertices, 128
source vertices, eight neighbors/destination and 64-byte immutable features.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import time
import zipfile
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from wram_platform import ROOT, BUILD, bytefile, compile_sources, invoke

POLICIES = {"stream128": (0, 128), "stream2048": (0, 2048),
            "history": (1, 128), "degree": (2, 128), "static": (3, 128),
            "block4": (4, 128), "cluster16": (5, 128), "adaptive": (6, 128)}
CASES = ("community", "shuffled", "uniform", "hubs", "phase")


def pack(values):
    return struct.pack(f"<{len(values)}I", *values)


def workload(case, seed):
    start = time.perf_counter()
    rng = random.Random(seed)
    # Construct one bipartite neighbor list. Community/shuffled share the graph.
    rows = []
    for dst in range(64):
        src = []
        for _ in range(8):
            if case in ("community", "shuffled") or (case == "phase" and dst < 32):
                value = ((dst // 8) * 16 + rng.randrange(16)) if rng.random() < .90 else rng.randrange(128)
            elif case == "hubs":
                value = rng.randrange(8) if rng.random() < .65 else rng.randrange(128)
            else:
                value = rng.randrange(128)
            src.append(value)
        rows.append(src)
    if case == "shuffled":
        rng.shuffle(rows)  # only destination processing order changes
    refs = [v for row in rows for v in row]
    degree = [refs.count(i) for i in range(128)]
    top = sorted(range(128), key=lambda v: (-degree[v], v))[:32]
    mapping = [top.index(v) if v in top else 0xffffffff for v in range(128)]
    features = [[(v * 17 + f * 13 + 3) % 251 for f in range(16)] for v in range(128)]
    expected = [sum(features[v][f] for v in row) for row in rows for f in range(16)]
    return refs, features, degree, mapping, expected, time.perf_counter() - start


def expected_traffic(refs, degree, mapping, policy, tasklets):
    """Independent behavioral model, checked against simulator byte counters."""
    fetched = 0
    unused = 0
    for tid in range(tasklets):
        part = refs[tid * len(refs)//tasklets:(tid+1) * len(refs)//tasklets]
        tags = [-1] * 32
        used = [set() for _ in tags]
        group = 4 if policy == "block4" else 16 if policy == "cluster16" else 1
        slots = 32 // group
        # Count rows fetched into a slot but never consumed before eviction/end.
        def discard(slot):
            return (group - len(used[slot])) * 64 if tags[slot] != -1 else 0
        retain, hits = True, 0
        if policy == "static":
            fetched += 32 * 64
        for pos, v in enumerate(part):
            if policy == "adaptive":
                if pos % 256 == 0:
                    if not retain:
                        tags = [-1] * 32
                    retain, hits = True, 0
                elif pos % 256 == 32:
                    retain = hits >= 4
            if policy.startswith("stream") or (policy == "adaptive" and not retain):
                fetched += 64
                continue
            if policy == "static":
                fetched += 64 if mapping[v] == 0xffffffff else 0
                continue
            block, offset = divmod(v, group)
            slot = block % slots
            if tags[slot] == block:
                hits += 1
                used[slot].add(offset)
                continue
            admit = policy != "degree" or tags[slot] == -1 or degree[v] >= degree[tags[slot]]
            if admit:
                unused += discard(slot)
                tags[slot], used[slot] = block, {offset}
            fetched += group * 64
        unused += sum(discard(s) for s in range(slots))
    metadata = 512 * tasklets if policy in ("degree", "static") else 0
    return {"read_bytes": fetched + len(refs) * 4 + metadata,
            "write_bytes": len(refs)//8 * 64, "feature_read_bytes": fetched,
            "metadata_read_bytes": metadata,
            "unused_group_bytes": unused if group > 1 else 0}


def compile_all(tasklets):
    for t in tasklets:
        for index, (name, (policy, size)) in enumerate(POLICIES.items()):
            compile_sources(SimpleNamespace(tasklets=t, sdk=index == 0,
                benchmark=name, source=ROOT / "experiments/wram/task.c",
                define=[f"-DPOLICY={policy}", f"-DINDEX_BYTES={size}"]))


def run_one(case, seed, policy, tasklets, template, run_directory):
    directory = run_directory / f"{case}-s{seed}-{policy}-t{tasklets}"
    if directory.exists():
        raise FileExistsError(f"Preserve prior output; choose a clean runs directory: {directory}")
    shutil.copytree(template, directory)
    refs, features, degree, mapping, expected, prep = workload(case, seed)
    data = pack(refs) + pack([x for row in features for x in row])
    feature_offset = len(refs)*4
    metadata_offset = len(data)
    data += pack(mapping if policy == "static" else degree)
    output_offset = len(data)
    bytefile(directory / "input_DPU_INPUT_ARGUMENTS_0_0.bin", pack([len(refs), feature_offset, metadata_offset, output_offset]))
    bytefile(directory / "input_dpu_mram_heap_pointer_name_0_0_0.bin", data)
    bytefile(directory / f"output_dpu_mram_heap_pointer_name_{output_offset}_0_0.bin", pack(expected))
    (directory / "num_executions.txt").write_text("1\n")
    elapsed = invoke("simulate", directory, policy, tasklets)
    stats = dict(line.split(": ") for line in (directory / "log.txt").read_text().splitlines())
    traffic = expected_traffic(refs, degree, mapping, policy, tasklets)
    for metric in ("read_bytes", "write_bytes"):
        assert int(stats[f"RowBuffer[0_0_0]_{metric}"]) == traffic[metric], (case, policy, metric, stats, traffic)
    values = dict(line.split(": ") for line in (directory / "values.txt").read_text().splitlines())
    allocated = int(values["__sys_heap_pointer_reset"])
    assert allocated <= 65536, allocated
    result = {"case": case, "seed": seed, "policy": policy, "tasklets": tasklets,
              "references": len(refs), "cycles": int(stats["Logic[0_0_0]_logic_cycle"]),
              "instructions": int(stats["Logic[0_0_0]_num_instructions"]), **traffic,
              "wram_static_and_reserved_stack_bytes": allocated,
              "workspace_bytes_per_tasklet": 3328,
              "output_check": "passed", "traffic_check": "passed",
              "simulator_wall_seconds": round(elapsed, 3), "host_generation_seconds": round(prep, 6),
              "input_sha256": hashlib.sha256(data).hexdigest(),
              "expected_sha256": hashlib.sha256(pack(expected)).hexdigest(),
              "iram_sha256": hashlib.sha256((directory / "iram.bin").read_bytes()).hexdigest()}
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{case} seed={seed} {policy} t={tasklets}: {result['cycles']} cycles, {traffic['read_bytes']} read bytes", flush=True)
    return result


def run_all(args):
    jobs = []
    for t in args.tasklets:
        for p in args.policies:
            template = BUILD / f"linked-{p}-t{t}"
            template.mkdir(parents=True, exist_ok=True)
            if args.frozen:
                # Never extract arbitrary paths from an archive.
                with zipfile.ZipFile(ROOT / "experiments/wram/linked-images.zip") as archive:
                    for name in ("addresses.txt", "values.txt", "atomic.bin", "iram.bin", "wram.bin", "mram.bin"):
                        (template / name).write_bytes(archive.read(f"{p}-t{t}/{name}"))
            else:
                invoke("link", template, p, t)
            for seed in args.seeds:
                for case in args.cases:
                    jobs.append((case, seed, p, t, template, args.run_directory))
    # Independent simulations; each uses one simulator worker and its own files.
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda job: run_one(*job), jobs))
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"Wrote {len(results)} checked records to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("compile", "run"))
    parser.add_argument("--tasklets", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 23])
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--policies", nargs="+", choices=POLICIES, default=list(POLICIES))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--frozen", action="store_true", help="replay retained linked images without rebuilding/linking DPU code")
    parser.add_argument("--run-directory", type=Path, default=ROOT / "runs/wram")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/wram/results.csv")
    args = parser.parse_args()
    if args.action == "compile":
        compile_all(args.tasklets)
    else:
        run_all(args)
