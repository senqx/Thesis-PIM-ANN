"""Validate training-only schedule choices and their calibration evidence."""

import json
from pathlib import Path

from experiments import ROOT, sha256
from followup_traces import phase_rows
from followup_validation import compressed_rows, original_query_rows
from profiled_fetch import CONFIGURATIONS, PROFILE_QUERIES, choose_order
from result_validation import query_rows, validate_replay
from scheduling import ORDERS
from scheduling_validation import check_phase_rows


def logical_phases(records):
    phases = []
    parent_level = query = None
    vector_group = False
    for r in records:
        q, kind, level = int(r["query"]), r["kind"], int(r["level"])
        item = (q, int(r["node"]), kind, level, int(r["bytes"]))
        assert 0 <= item[1] < 100000 and kind in ("A", "V")
        if q != query:
            assert query is None or q > query
            query, parent_level, vector_group = q, None, False
        if kind == "A":
            assert item[4] >= 4 and item[4] % 4 == 0
            phases.append([item])
            parent_level, vector_group = level, False
        else:
            assert item[4] == 512
            candidate = parent_level == level
            if candidate and vector_group:
                phases[-1].append(item)
            else:
                phases.append([item])
            vector_group = candidate
    return phases


def validate_calibration(seeds=range(1, 11)):
    seeds = list(seeds)
    for seed in seeds:
        folder = ROOT / f"results/calibration/seed{seed}"
        old = ROOT / f"results/followup/reference/seed{seed}"
        inputs = json.loads((folder / "inputs.json").read_text())
        prior = json.loads((old / "inputs.json").read_text())
        source = {Path(p).name: h for p, h in prior["input_hashes"].items()}
        assert len(inputs["source_hashes"]) == 6
        assert {Path(p).name for p in inputs["source_hashes"]} == {
            "inputs.json",
            "split.csv",
            "graph.csv",
            "training.csv",
            "bfs_128.mapping.csv",
            "bfs_512.mapping.csv",
        }
        for p, h in inputs["source_hashes"].items():
            assert h == (
                sha256(ROOT / p) if p.startswith("results/") else source[Path(p).name]
            )
        assert len(inputs["retained_hashes"]) == 7
        assert {Path(p).name for p in inputs["retained_hashes"]} == {
            "logical.csv.gz",
            "phases_batch0.csv.gz",
            "phases_batch2.csv.gz",
            "phases_batch8.csv.gz",
            "selected_queries.csv",
            "selection.json",
            "emissions.json",
        }
        for p, h in inputs["retained_hashes"].items():
            assert h == sha256(ROOT / p)
        assert inputs["generator_sha256"] == sha256(ROOT / "scripts/profiled_fetch.py")
        assert inputs["batching_generator_sha256"] == sha256(
            ROOT / "scripts/scheduling.py"
        )
        assert inputs["design_sha256"] == sha256(ROOT / "doc/PROFILED_FETCH_DESIGN.md")
        assert inputs["profile_queries"] == PROFILE_QUERIES
        from followup_traces import rows

        split = rows(old / "split.csv")
        selected = rows(folder / "selected_queries.csv")
        expected = sorted(
            (r for r in split if r["partition"] == "train"),
            key=lambda r: int(r["position"]),
        )[:PROFILE_QUERIES]
        assert selected == expected
        assert not {r["source_query"] for r in selected} & {
            r["source_query"] for r in split if r["partition"] == "test"
        }
        logical = compressed_rows(folder / "logical.csv.gz")
        assert {int(r["query"]) for r in logical} == set(range(PROFILE_QUERIES))
        original_phases = logical_phases(logical)
        phases = {}
        emissions = json.loads((folder / "emissions.json").read_text())
        choices = json.loads((folder / "selection.json").read_text())
        assert set(emissions) == {
            f"batch{b}/{o}_{w}" for b in (0, 2, 8) for o in ORDERS for w in (128, 512)
        }
        assert set(choices) == {f"{c}/{w}" for c in CONFIGURATIONS for w in (128, 512)}
        for cap in (0, 2, 8):
            phases[cap] = compressed_rows(folder / f"phases_batch{cap}.csv.gz")
            check_phase_rows(phases[cap], phase_rows(original_phases), cap)
        for width in (128, 512):
            reads = [
                sum(
                    width // 32 if r["kind"] == "V" else (int(r["bytes"]) + 31) // 32
                    for r in logical
                    if int(r["query"]) == q
                )
                for q in range(PROFILE_QUERIES)
            ]
            for c, (cap, parameters) in CONFIGURATIONS.items():
                costs = {}
                test = (
                    old / f"bounded/bfs_{width}.json"
                    if c == "default"
                    else ROOT
                    / f"results/scheduling/seed{seed}/{c}/bounded_{width}.json"
                )
                reference = validate_replay(test)
                expected_reads = [
                    int(p["vector_records"]) * width // 32
                    + int(p["adjacency_transactions"])
                    for p in phases[cap]
                ]
                fingerprints = set()
                for order in ORDERS:
                    p = folder / c / f"{order}_{width}.json"
                    r = validate_replay(p)
                    proof = emissions[f"batch{cap}/{order}_{width}"]
                    assert r["trace_sha256"] == proof["trace_sha256"]
                    assert r["checks"]["trace_reads"] == proof["reads"] == sum(reads)
                    assert r["parameters"] == reference["parameters"]
                    for key in (
                        "library_sha256",
                        "frontend_sha256",
                        "ramulator_commit",
                    ):
                        assert r[key] == reference[key]
                    timings = query_rows(p)
                    assert [int(t["query"]) for t in timings] == list(
                        range(len(phases[cap]))
                    )
                    assert [int(t["reads"]) for t in timings] == expected_reads
                    original = original_query_rows(p, phases[cap])
                    assert [t["query"] for t in original] == list(
                        range(PROFILE_QUERIES)
                    )
                    assert [t["reads"] for t in original] == reads
                    fingerprints.add(proof["phase_multiset_sha256"])
                    costs[order] = r["cycles"]
                assert len(fingerprints) == 1
                assert choices[f"{c}/{width}"] == dict(
                    training_cycles=costs, selected_order=choose_order(costs)
                )
    print(
        f"Validated {42 * len(seeds)} calibration replays, disjoint training IDs, fixed choices and original-query accounting."
    )


if __name__ == "__main__":
    validate_calibration()
