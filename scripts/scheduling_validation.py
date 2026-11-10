"""Validate the fixed scheduling matrix and its original-query/batch identities."""

import json
from pathlib import Path

from experiments import ROOT, sha256
from followup_validation import compressed_rows, original_query_rows
from result_validation import query_rows, validate_replay
from scheduling import CONDITIONS, ORDERS


def expected_batch_rows(original, cap):
    output = []
    for parent, row in enumerate(original):
        count = int(row["logical_records"])
        step = cap if cap and row["kind"] == "V" else count
        for start in range(0, count, step):
            size = min(step, count - start)
            output.append(
                dict(
                    phase=len(output),
                    query=int(row["query"]),
                    kind=row["kind"],
                    logical_records=size,
                    vector_records=size if row["kind"] == "V" else 0,
                    adjacency_transactions=int(row["adjacency_transactions"]),
                    parent_phase=parent,
                )
            )
    return output


def check_phase_rows(actual, original, cap):
    expected = expected_batch_rows(original, cap)
    normalized = [
        {key: value if key == "kind" else int(value) for key, value in row.items()}
        for row in actual
    ]
    if normalized != expected:
        raise ValueError("batch map changed query, parent membership or logical work")


def validate_scheduling(seeds=range(1, 11)):
    seeds = list(seeds)
    for seed in seeds:
        old = ROOT / f"results/followup/reference/seed{seed}"
        directory = ROOT / f"results/scheduling/seed{seed}"
        inputs = json.loads((directory / "inputs.json").read_text())
        prior = json.loads((old / "inputs.json").read_text())
        assert len(inputs["source_hashes"]) == 9
        assert {Path(p).name for p in inputs["source_hashes"]} == {
            "inputs.json",
            "phases.csv.gz",
            "emissions.json",
            "split.csv",
            "recall.csv",
            "graph.csv",
            "logical.csv",
            "bfs_128.mapping.csv",
            "bfs_512.mapping.csv",
        }
        hashes = {Path(p).name: value for p, value in prior["input_hashes"].items()}
        for name, value in inputs["source_hashes"].items():
            if name.startswith("results/"):
                assert value == sha256(ROOT / name), name
            else:
                assert value == hashes[Path(name).name], name
        assert inputs["generator_sha256"] == sha256(ROOT / "scripts/scheduling.py")
        assert inputs["design_sha256"] == sha256(ROOT / "doc/SCHEDULING_DESIGN.md")
        assert inputs["emissions_sha256"] == sha256(directory / "emissions.json")
        assert set(inputs["phase_hashes"]) == {
            f"phases_batch{b}.csv.gz" for b in (0, 2, 8)
        }
        old_phases = compressed_rows(old / "phases.csv.gz")
        old_emissions = json.loads((old / "emissions.json").read_text())
        emissions = json.loads((directory / "emissions.json").read_text())
        assert set(emissions) == {
            f"batch{b}/{order}_{w}"
            for b in (0, 2, 8)
            for order in ("flat",) + ORDERS
            for w in (128, 512)
        }
        phases = {}
        for cap in (0, 2, 8):
            name = f"phases_batch{cap}.csv.gz"
            assert inputs["phase_hashes"][name] == sha256(directory / name)
            phases[cap] = compressed_rows(directory / name)
            check_phase_rows(phases[cap], old_phases, cap)
            for width in (128, 512):
                flat = emissions[f"batch{cap}/flat_{width}"]
                assert (
                    flat["trace_sha256"]
                    == old_emissions[f"flat/bfs_{width}"]["trace_sha256"]
                )
                for order in ORDERS:
                    proof = emissions[f"batch{cap}/{order}_{width}"]
                    assert (
                        proof["phase_multiset_sha256"] == flat["phase_multiset_sha256"]
                    )
                    assert proof["reads"] == flat["reads"]
                    if cap == 0:
                        assert proof == old_emissions[f"{order}/bfs_{width}"]
        for width in (128, 512):
            baseline_path = old / f"bounded/bfs_{width}.json"
            baseline = validate_replay(baseline_path)
            old_queries = original_query_rows(baseline_path, old_phases)
            for condition, (cap, parameters) in CONDITIONS.items():
                expected_reads = [
                    int(p["vector_records"]) * width // 32
                    + int(p["adjacency_transactions"])
                    for p in phases[cap]
                ]
                for order in ORDERS:
                    path = directory / condition / f"{order}_{width}.json"
                    result = validate_replay(path)
                    proof = emissions[f"batch{cap}/{order}_{width}"]
                    assert result["trace_sha256"] == proof["trace_sha256"]
                    assert result["checks"] == baseline["checks"]
                    assert proof["reads"] == result["checks"]["trace_reads"]
                    assert result["parameters"] == {
                        **baseline["parameters"],
                        **parameters,
                    }
                    for key in (
                        "library_sha256",
                        "frontend_sha256",
                        "ramulator_commit",
                    ):
                        assert result[key] == baseline[key]
                    timing = query_rows(path)
                    assert [int(r["query"]) for r in timing] == list(
                        range(len(phases[cap]))
                    )
                    assert [int(r["reads"]) for r in timing] == expected_reads
                    original = original_query_rows(path, phases[cap])
                    assert [r["query"] for r in original] == list(range(200))
                    assert [r["reads"] for r in original] == [
                        r["reads"] for r in old_queries
                    ]
    print(
        f"Validated {36 * len(seeds)} scheduling replays, unchanged source traces, batch membership, configuration and original-query accounting."
    )


if __name__ == "__main__":
    validate_scheduling()
