"""Cross-check new layout and phase evidence against the original experiments."""

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

from experiments import ROOT
from followup import (
    LAYOUTS,
    PUBLISHED,
    cases,
    modes,
    original_directory,
    reference_directory,
)
from result_validation import query_rows, validate_replay
from setup_published import ARCHIVE_SHA, URL


def compressed_rows(path):
    return list(
        csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode()))
    )


def original_query_rows(result_path, phases):
    recorded = query_rows(result_path)
    if result_path.parent.name == "flat":
        return recorded
    groups = {}
    for item, phase in zip(recorded, phases, strict=True):
        q = int(phase["query"])
        if q not in groups:
            groups[q] = dict(query=q, reads=0, first_arrive=int(item["first_arrive"]))
        groups[q]["reads"] += int(item["reads"])
        groups[q]["last_depart"] = int(item["last_depart"])
    for item in groups.values():
        item["cycles"] = item["last_depart"] - item["first_arrive"]
    return list(groups.values())


def validate_followup(selected_cases=None):
    source = json.loads((ROOT / "results/followup/published_source.json").read_text())
    assert source["url"] == URL and source["archive_sha256"] == ARCHIVE_SHA
    assert (
        source["wrapper_sha256"]
        == hashlib.sha256((ROOT / "src/published_layouts.cpp").read_bytes()).hexdigest()
    )
    assert (
        source["priority_queue_sha256"]
        == hashlib.sha256(
            (ROOT / "src/published_priority_queue.h").read_bytes()
        ).hexdigest()
    )
    selected_cases = cases() if selected_cases is None else selected_cases
    static_mappings = {}
    for graph, seed in selected_cases:
        folder = ROOT / f"results/followup/{graph}/seed{seed}"
        ref = reference_directory(graph, seed)
        old = original_directory(graph, seed)
        for name in ("split.csv", "recall.csv"):
            assert (folder / name).read_bytes() == (ref / name).read_bytes()
        inputs = json.loads((folder / "inputs.json").read_text())
        assert inputs["original_equivalence"] is True
        assert inputs["published_executable_sha256"] == source["executable_sha256"]
        expected_hashes = {
            Path(k).name: v
            for k, v in json.loads((ref / "mapping_hashes.json").read_text()).items()
        }
        expected_hashes.update(json.loads((ref / "graph_hashes.json").read_text()))
        hashes = {Path(k).name: v for k, v in inputs["input_hashes"].items()}
        assert all(hashes[k] == v for k, v in expected_hashes.items())
        profile_path = folder / "profile.csv.gz"
        assert (
            hashlib.sha256(gzip.decompress(profile_path.read_bytes())).hexdigest()
            == hashes["profile.csv"]
        )
        profile = compressed_rows(profile_path)
        assert len(profile) == inputs["profile_edge_count"]
        assert (
            sum(int(r["traversals"]) for r in profile) == inputs["profile_traversals"]
        )
        assert all(
            0 <= int(r["source"]) < 100000
            and 0 <= int(r["target"]) < 100000
            and 0 < int(r["traversals"]) <= 500
            for r in profile
        )
        for layout in PUBLISHED:
            path = folder / f"{layout}.mapping.csv.gz"
            assert (
                hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()
                == hashes[f"{layout}.mapping.csv"]
            )
            mapping = compressed_rows(path)
            assert [int(r["logicalId"]) for r in mapping] == list(range(100000))
            assert sorted(int(r["slot"]) for r in mapping) == list(range(100000))
            if layout in ("rcm", "gorder"):
                static_mappings.setdefault((graph, layout), set()).add(
                    hashes[f"{layout}.mapping.csv"]
                )
        phases = compressed_rows(folder / "phases.csv.gz")
        assert (
            inputs["phases_sha256"]
            == hashlib.sha256((folder / "phases.csv.gz").read_bytes()).hexdigest()
        )
        assert (
            inputs["phase_generator_sha256"]
            == hashlib.sha256(
                (ROOT / "scripts/followup_traces.py").read_bytes()
            ).hexdigest()
        )
        assert [int(p["phase"]) for p in phases] == list(range(len(phases)))
        queries = [int(p["query"]) for p in phases]
        assert queries == sorted(queries) and set(queries) == set(range(200))
        assert all(int(p["logical_records"]) > 0 for p in phases)
        assert all(
            (
                int(p["vector_records"]) == int(p["logical_records"])
                and int(p["adjacency_transactions"]) == 0
            )
            if p["kind"] == "V"
            else (
                p["kind"] == "A"
                and int(p["logical_records"]) == 1
                and int(p["vector_records"]) == 0
                and int(p["adjacency_transactions"]) > 0
            )
            for p in phases
        )
        emissions = json.loads((folder / "emissions.json").read_text())
        wanted = {
            f"{mode}/{layout}_{width}"
            for layout in LAYOUTS
            for width in (128, 512)
            for mode in set(modes(layout)) | {"flat"}
        }
        assert set(emissions) == wanted
        for width in (128, 512):
            baseline = validate_replay(old / f"timing/bfs_{width}.json")
            reads_per_phase = [
                int(p["vector_records"]) * width // 32
                + int(p["adjacency_transactions"])
                for p in phases
            ]
            assert sum(reads_per_phase) == baseline["checks"]["trace_reads"]
            for layout in LAYOUTS:
                flat = emissions[f"flat/{layout}_{width}"]
                if layout not in PUBLISHED:
                    assert (
                        flat["trace_sha256"]
                        == validate_replay(old / f"timing/{layout}_{width}.json")[
                            "trace_sha256"
                        ]
                    )
                for mode in modes(layout):
                    name = f"{mode}/{layout}_{width}"
                    proof = emissions[name]
                    path = folder / (name + ".json")
                    result = validate_replay(path)
                    assert result["trace_sha256"] == proof["trace_sha256"]
                    assert result["parameters"] == baseline["parameters"]
                    assert result["library_sha256"] == baseline["library_sha256"]
                    assert (
                        proof["reads"]
                        == baseline["checks"]["trace_reads"]
                        == result["checks"]["trace_reads"]
                    )
                    assert (
                        proof["phase_multiset_sha256"] == flat["phase_multiset_sha256"]
                    )
                    timing = query_rows(path)
                    if mode != "flat":
                        assert [int(r["query"]) for r in timing] == list(
                            range(len(phases))
                        )
                        assert [int(r["reads"]) for r in timing] == reads_per_phase
                    original = original_query_rows(path, phases)
                    assert [int(r["query"]) for r in original] == list(range(200))
                    assert [int(r["reads"]) for r in original] == [
                        int(r["reads"])
                        for r in query_rows(old / f"timing/bfs_{width}.json")
                    ]
    assert all(len(hashes) == 1 for hashes in static_mappings.values()), (
        "Static placement changed with query split"
    )
    print(
        f"Validated {26 * len(selected_cases)} follow-up replays, published mappings, primary equivalence, phase conservation and original-query accounting."
    )


def validate_mechanism():
    folder = ROOT / "results/followup/mechanism"
    offered = json.loads((folder / "offered_banks.json").read_text())
    assert set(offered) == {
        f"{mode}_{width}" for mode in ("bounded", "roundrobin") for width in (128, 512)
    }
    for width in (128, 512):
        for mode in ("bounded", "roundrobin"):
            name = f"{mode}_{width}"
            path = folder / (name + ".json")
            result = validate_replay(path)
            base_path = (
                ROOT / f"results/followup/reference/seed1/{mode}/bfs_{width}.json"
            )
            base = validate_replay(base_path)
            for key in (
                "cycles",
                "checks",
                "trace_sha256",
                "row_hit_pct",
                "parameters",
                "library_sha256",
                "frontend_sha256",
            ):
                assert result[key] == base[key], (name, key)
            assert query_rows(path) == query_rows(base_path)
            record = offered[name]
            assert record["trace_sha256"] == result["trace_sha256"]
            assert record["windows"] == sum(
                max(0, int(q["reads"]) - 63) for q in query_rows(path)
            )
            assert 1 <= record["mean_distinct_banks"] <= 64
            assert (
                abs(
                    record["mean_distinct_banks"]
                    - record["bank_count_sum"] / record["windows"]
                )
                < 1e-12
            )
    print(
        "Four scheduling diagnostics preserve cycles, phase timing, and command/read accounting."
    )


if __name__ == "__main__":
    validate_followup()
    validate_mechanism()
