#!/usr/bin/env python3
"""Replay a read-only stream, retain raw stats, and enforce complete accounting."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PIN = "7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da"
sys.path.insert(0, str(ROOT / "ramulator2/python"))


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def run(
    trace,
    output,
    *,
    inflight=64,
    policy="Open",
    cap=4,
    scheduler="FRFCFS",
    mapper="RoBaRaCoCh",
    queue=32,
    issue=1,
    commands=0,
):
    import ramulator

    trace, output = Path(trace).resolve(), Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    query_path = output.with_suffix(".queries.csv")
    output.with_suffix(".queries.csv.gz").unlink(missing_ok=True)
    frontend = {
        "impl": "LoadStoreTrace",
        "clock_ratio": 1,
        "path": str(trace),
        "max_inflight": inflight,
        "query_output": str(query_path),
    }
    row_policy = {"impl": policy}
    if policy == "ClosedCAP":
        row_policy["cap"] = cap
    memory = {
        "impl": "GenericDRAM",
        "clock_ratio": issue,
        "channel_mapper": {"impl": "CacheLineInterleave"},
        "controllers": [
            {
                "impl": "GenericDDR",
                "read_buffer_size": queue,
                "dram": {
                    "impl": "HBM2",
                    "org": {"preset": "HBM2_8Gb"},
                    "timing": {"preset": "HBM2_2000Mbps"},
                },
                "scheduler": {
                    "impl": "FRFCFS-RowHit"
                    if scheduler == "FRFCFSRowHit"
                    else scheduler
                },
                "refresh_manager": {"impl": "AllBank"},
                "row_policy": row_policy,
                "addr_mapper": {"impl": mapper},
            }
        ],
    }
    # Use generated component serialization for the DRAM preset keys.
    memory["controllers"][0]["dram"] = ramulator.dram.HBM2(
        org_preset="HBM2_8Gb", timing_preset="HBM2_2000Mbps"
    ).to_config()
    command_path = output.with_suffix(".commands.csv")
    if commands:
        memory["controllers"][0]["controller_plugins"] = [
            {
                "impl": "CommandCounter",
                "commands_to_count": [
                    "ACT",
                    "PREpb",
                    "PREab",
                    "RD",
                    "RDA",
                    "WR",
                    "WRA",
                    "REFab",
                    "REFpb",
                ],
                "path": str(command_path),
            }
        ]
        if commands == 2:
            memory["controllers"][0]["controller_plugins"].append(
                {
                    "impl": "CmdTraceRecorder",
                    "path": str(output.with_suffix(".command_trace.csv")),
                }
            )
    sim = ramulator.Simulation(frontend, memory)
    sim.run()
    sim.finalize()
    stats = sim.stats
    controller = stats["memory_system"]["controller"]
    if isinstance(controller, list):
        controller = controller[0]
    queries = list(csv.DictReader(query_path.open()))
    expected = sum(int(r["reads"]) for r in queries)
    with trace.open() as f:
        lines = sum(1 for _ in f)
    classified = sum(
        controller[k]
        for k in ["read_row_hits", "read_row_misses", "read_row_conflicts"]
    )
    served = controller["num_read_reqs_served"]
    submitted = controller["num_read_reqs"]
    if not (lines == expected == classified == served == submitted):
        raise RuntimeError(
            f"request accounting mismatch: {lines, expected, classified, served, submitted}"
        )
    result = {
        "ramulator_commit": PIN,
        "trace_sha256": sha256(trace),
        "trace_file": trace.name,
        "frontend_sha256": sha256(ROOT / "simulator/thesis_trace.cpp"),
        "library_sha256": sha256(ROOT / "ramulator2/libramulator.so"),
        "parameters": dict(
            inflight=inflight,
            policy=policy,
            cap=cap,
            scheduler=scheduler,
            mapper=mapper,
            queue=queue,
            issue=issue,
        ),
        "config": {"frontend": frontend, "memory_system": memory},
        "stats": stats,
        "checks": {
            "trace_reads": lines,
            "completed_callbacks": expected,
            "submitted": submitted,
            "served": served,
            "classified": classified,
        },
        "cycles": controller["cycles"],
        "row_hit_pct": 100 * controller["read_row_hits"] / classified,
        "mean_query_cycles": sum(int(r["cycles"]) for r in queries) / len(queries),
    }
    if commands:
        with command_path.open() as stream:
            result["command_counts"] = {r[0]: int(r[1]) for r in csv.reader(stream)}
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(output)
    from result_validation import validate_replay

    validate_replay(output)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("--output", type=Path, default=ROOT / "work/replay.json")
    p.add_argument("--commands", type=int, choices=[0, 1, 2], default=0)
    for flag, default in [("inflight", 64), ("cap", 4), ("queue", 32), ("issue", 1)]:
        p.add_argument("--" + flag, type=int, default=default)
    p.add_argument("--policy", choices=["Open", "ClosedCAP"], default="Open")
    p.add_argument("--scheduler", choices=["FRFCFS", "FRFCFSRowHit"], default="FRFCFS")
    p.add_argument(
        "--mapper", choices=["RoBaRaCoCh", "ChRaBaRoCo"], default="RoBaRaCoCh"
    )
    p.add_argument("--csv", action="store_true")
    a = p.parse_args()
    if min(a.inflight, a.cap, a.queue, a.issue) <= 0:
        p.error("numeric parameters must be positive")
    result = run(
        a.trace,
        a.output,
        inflight=a.inflight,
        policy=a.policy,
        cap=a.cap,
        scheduler=a.scheduler,
        mapper=a.mapper,
        queue=a.queue,
        issue=a.issue,
        commands=a.commands,
    )
    if a.csv:
        print(f"{result['cycles']},{result['row_hit_pct']:.8f}")
    else:
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in ["cycles", "row_hit_pct", "mean_query_cycles", "checks"]
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
