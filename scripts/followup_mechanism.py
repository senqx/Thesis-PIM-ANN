"""Four non-perturbing diagnostic repeats of the scheduling pilot."""

import json
from experiments import ROOT, WORK, replay
from followup import compress, save_json
from followup_traces import emit, graph_rows, mapping_rows, records, split_phases
from result_validation import query_rows, validate_replay, write_cache
from trace_diagnostics import offered_bank_diversity


def expected_mechanism():
    return {
        f"followup/mechanism/{mode}_{width}.json"
        for mode in ("bounded", "roundrobin")
        for width in (128, 512)
    }


def run():
    study = WORK / "followup/reference/seed1/study"
    graph = graph_rows(study / "graph.csv")
    phases = split_phases(records(study / "logical.csv"), graph)
    directory = WORK / "followup/mechanism"
    directory.mkdir(parents=True, exist_ok=True)
    offered = {}
    for width in (128, 512):
        mapping = mapping_rows(study / f"bfs_{width}.mapping.csv", 100000)
        for mode in ("bounded", "roundrobin"):
            name = f"{mode}_{width}"
            path = directory / (name + ".trace")
            proof = emit(phases, graph, mapping, width, mode, path)
            baseline_path = (
                ROOT / f"results/followup/reference/seed1/{mode}/bfs_{width}.json"
            )
            baseline = validate_replay(baseline_path)
            assert proof["trace_sha256"] == baseline["trace_sha256"]
            offered[name] = offered_bank_diversity(path)
            label = f"followup/mechanism/{name}"
            replay(path, label, commands=1)
            result_path = ROOT / "results" / (label + ".json")
            measured = validate_replay(result_path)
            assert measured["cycles"] == baseline["cycles"]
            assert measured["row_hit_pct"] == baseline["row_hit_pct"]
            assert query_rows(result_path) == query_rows(baseline_path)
            plain = result_path.with_suffix(".queries.csv")
            if plain.exists():
                compress(plain)
                stamp = result_path.with_suffix(".cache.json")
                write_cache(
                    stamp, result_path, json.loads(stamp.read_text())["signature"]
                )
            path.unlink()
    save_json(ROOT / "results/followup/mechanism/offered_banks.json", offered)
    print("Four scheduling diagnostic repeats match the original timings exactly.")


if __name__ == "__main__":
    run()
