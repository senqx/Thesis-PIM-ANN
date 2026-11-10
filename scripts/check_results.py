#!/usr/bin/env python3
"""Validate the retained experiment matrix independently of plotting code."""

import csv
import io
import json
from result_validation import validate_replay, query_rows
from experiment_matrix import expected_replays
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def rows(p):
    return list(csv.DictReader(io.StringIO(p.read_text())))


def check():
    timing = []
    for path in R.rglob("*.json"):
        if ".cache." in path.name:
            continue
        data = json.loads(path.read_text())
        if "checks" not in data:
            continue
        validate_replay(path)
        timing.append(path)
        checks = data["checks"]
        assert len(set(checks.values())) == 1, (path, checks)
        frontend = data["stats"]["frontend"]
        assert (
            frontend["submitted"] == frontend["completed"] == checks["trace_reads"]
        ), path
        assert 0 < frontend["peak_inflight"] <= data["parameters"]["inflight"], path
        query = query_rows(path)
        assert sum(int(q["reads"]) for q in query) == checks["trace_reads"], path
        assert all(
            int(q["cycles"]) == int(q["last_depart"]) - int(q["first_arrive"]) > 0
            for q in query
        ), path
        assert len({q["query"] for q in query}) == len(query), path
    actual = {str(path.relative_to(R)) for path in timing}
    expected = expected_replays()
    assert actual == expected, (
        "experiment matrix mismatch",
        "missing",
        sorted(expected - actual),
        "unexpected",
        sorted(actual - expected),
    )
    hashes = {json.loads(p.read_text())["library_sha256"] for p in timing}
    assert len(hashes) == 1, hashes
    for seed in range(1, 11):
        folder = R / "sift" / f"seed{seed}"
        split = rows(folder / "split.csv")
        train = {r["source_query"] for r in split if r["partition"] == "train"}
        test = {r["source_query"] for r in split if r["partition"] == "test"}
        assert len(train) == 500 and len(test) == 200 and not train & test
        recalls = rows(folder / "recall.csv")
        assert len(recalls) == 200
        for r in recalls:
            found = r["returned"].split()
            truth = r["truth"].split()
            assert len(found) == len(set(found)) == len(truth) == 10
            assert all(0 <= int(v) < 100000 for v in found + truth)
            assert abs(float(r["recall"]) - len(set(found) & set(truth)) / 10) < 1e-10
        meta = rows(folder / "metadata.csv")[0]
        assert (
            abs(float(meta["recall"]) - sum(float(r["recall"]) for r in recalls) / 200)
            < 1e-10
        )
        layouts = rows(folder / "layouts.csv")
        assert len(layouts) == 10
        for width in [128, 512]:
            subset = [r for r in layouts if int(r["vector_bytes"]) == width]
            assert len({r["reads"] for r in subset}) == 1
            for r in subset:
                data = json.loads(
                    (folder / "timing" / f"{r['layout']}_{width}.json").read_text()
                )
                assert int(r["reads"]) == data["checks"]["trace_reads"]
    reference = {
        r["source_query"]
        for r in rows(R / "sift/seed1/split.csv")
        if r["partition"] == "test"
    }
    for name in ["train100", "train1000", "window4", "window64", "block2048"]:
        split = rows(R / "ablations" / name / "split.csv")
        assert {
            r["source_query"] for r in split if r["partition"] == "test"
        } == reference
        assert (
            not {r["source_query"] for r in split if r["partition"] == "train"}
            & reference
        )
    original = json.loads((R / "micro/order/sequential.json").read_text())
    reordered = json.loads((R / "micro/reorder/w16384.json").read_text())
    assert original["trace_sha256"] == reordered["trace_sha256"]
    assert original["cycles"] == reordered["cycles"]
    validate_extension()
    from followup_validation import validate_followup, validate_mechanism

    validate_followup()
    validate_mechanism()
    print(
        f"Validated all {len(timing)} named replays, read accounting, primary equivalence, "
        "graph/split identity, recall, component streams and command conservation."
    )


def validate_extension():
    from strengthen import CONDITIONS, GRAPHS

    reference_graph = set()
    reference_order = set()
    for seed in range(1, 11):
        source = R / f"sift/seed{seed}"
        reference = R / f"robustness/reference/seed{seed}"
        assert (source / "split.csv").read_bytes() == (
            reference / "split.csv"
        ).read_bytes()
        assert (source / "recall.csv").read_bytes() == (
            reference / "recall.csv"
        ).read_bytes()
        proof = json.loads((reference / "primary_equivalence.json").read_text())
        assert proof["split_recall_logical_mappings_identical"] is True
        assert len(proof["trace_hashes"]) == 10
        hashes = json.loads((reference / "graph_hashes.json").read_text())
        reference_graph.add(hashes["graph.csv"])
        reference_order.add(hashes["insertion.csv"])
        for width in (128, 512):
            for layout in ("identity", "random", "bfs", "community", "query_aware"):
                stem = f"{layout}_{width}"
                base = validate_replay(source / f"timing/{stem}.json")
                assert proof["trace_hashes"][stem + ".trace"] == base["trace_sha256"]
                for condition, params in CONDITIONS.items():
                    item = validate_replay(
                        R / f"robustness/controllers/{condition}/seed{seed}/{stem}.json"
                    )
                    assert item["trace_sha256"] == base["trace_sha256"]
                    assert item["checks"] == base["checks"]
                    assert item["parameters"] == {**base["parameters"], **params}
                    if seed == 1:
                        prior = validate_replay(
                            R / f"sensitivity/{condition}/{stem}.json"
                        )
                        assert item["cycles"] == prior["cycles"]
                        assert item["row_hit_pct"] == prior["row_hit_pct"]
    offered = json.loads((R / "mechanism/offered_banks.json").read_text())
    for name, record in offered.items():
        base_path = (
            R / f"mechanism/micro/{name}_inflight64.json"
            if name in ("sequential", "random")
            else R / f"mechanism/sift/{name}_mixed_inflight64.json"
        )
        base = validate_replay(base_path)
        queries = rows(base_path.with_suffix(".queries.csv"))
        assert record["trace_sha256"] == base["trace_sha256"]
        assert record["windows"] == sum(max(0, int(q["reads"]) - 63) for q in queries)
        assert 1 <= record["mean_distinct_banks"] <= 64
        assert (
            abs(
                record["mean_distinct_banks"]
                - record["bank_count_sum"] / record["windows"]
            )
            < 1e-12
        )
    assert len(reference_graph) == len(reference_order) == 1
    graph_hashes = set(reference_graph)
    for name, (index, insertion) in GRAPHS.items():
        constructed = set()
        for seed in range(1, 4):
            folder = R / f"robustness/graphs/{name}/seed{seed}"
            meta = rows(folder / "metadata.csv")[0]
            assert (
                int(meta["index_seed"]) == index
                and int(meta["insertion_seed"]) == insertion
            )
            assert int(meta["seed"]) == seed
            assert (folder / "split.csv").read_bytes() == (
                R / f"sift/seed{seed}/split.csv"
            ).read_bytes()
            hashes = json.loads((folder / "graph_hashes.json").read_text())
            constructed.add(hashes["graph.csv"])
            assert (hashes["insertion.csv"] in reference_order) == (insertion == 0)
            recalls = rows(folder / "recall.csv")
            assert len(recalls) == 200
            for row in recalls:
                found, truth = row["returned"].split(), row["truth"].split()
                assert (
                    len(found) == len(set(found)) == len(truth) == len(set(truth)) == 10
                )
                assert all(0 <= int(v) < 100000 for v in found + truth)
                assert (
                    abs(float(row["recall"]) - len(set(found) & set(truth)) / 10)
                    < 1e-10
                )
            primary = rows(R / f"sift/seed{seed}/recall.csv")
            assert [(r["source_query"], r["truth"]) for r in recalls] == [
                (r["source_query"], r["truth"]) for r in primary
            ]
            assert (
                abs(
                    float(meta["recall"])
                    - sum(float(r["recall"]) for r in recalls) / 200
                )
                < 1e-10
            )
            layouts = rows(folder / "layouts.csv")
            assert len(layouts) == 10
            for width in (128, 512):
                reads = set()
                for row in layouts:
                    if int(row["vector_bytes"]) == width:
                        item = validate_replay(
                            folder / f"timing/{row['layout']}_{width}.json"
                        )
                        assert item["checks"]["trace_reads"] == int(row["reads"])
                        reads.add(row["reads"])
                assert len(reads) == 1
        assert len(constructed) == 1
        graph_hashes.update(constructed)
    assert len(graph_hashes) == 4, "graph variations must actually change topology"
    for inflight in (1, 64):
        for layout in ("bfs", "query_aware"):
            folder = R / "mechanism/sift"
            mixed = validate_replay(folder / f"{layout}_mixed_inflight{inflight}.json")
            vectors = validate_replay(
                folder / f"{layout}_vectors_inflight{inflight}.json"
            )
            adjacency = validate_replay(
                folder / f"{layout}_adjacency_inflight{inflight}.json"
            )
            assert (
                mixed["checks"]["trace_reads"]
                == vectors["checks"]["trace_reads"] + adjacency["checks"]["trace_reads"]
            )
            primary = (
                R / f"sift/seed1/timing/{layout}_128.json"
                if inflight == 64
                else R / f"sensitivity/inflight1/{layout}_128.json"
            )
            base = validate_replay(primary)
            assert mixed["trace_sha256"] == base["trace_sha256"]
            assert (
                mixed["cycles"] == base["cycles"]
                and mixed["row_hit_pct"] == base["row_hit_pct"]
            )
        b = validate_replay(R / f"mechanism/sift/bfs_adjacency_inflight{inflight}.json")
        q = validate_replay(
            R / f"mechanism/sift/query_aware_adjacency_inflight{inflight}.json"
        )
        assert b["trace_sha256"] == q["trace_sha256"] and b["cycles"] == q["cycles"]
        for layout in ("sequential", "random"):
            item = validate_replay(
                R / f"mechanism/micro/{layout}_inflight{inflight}.json"
            )
            prior = (
                R / f"micro/order/{layout}.json"
                if inflight == 64
                else R
                / f"micro/reorder_inflight1/w{16384 if layout == 'sequential' else 1}.json"
            )
            base = validate_replay(prior)
            assert (
                item["cycles"] == base["cycles"]
                and item["trace_sha256"] == base["trace_sha256"]
            )


if __name__ == "__main__":
    check()
