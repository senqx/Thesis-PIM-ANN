#!/usr/bin/env python3
"""Recovery tests: corrupt/missing cached evidence must never look complete."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import experiments
from trace_diagnostics import offered_bank_diversity
from result_validation import cache_valid, write_cache


class Recovery(unittest.TestCase):
    def test_bank_windows_respect_query_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "banks.trace"
            trace.write_text("LD 0 0 V\n" * 64 + "LD 1024 1 V\n" * 64)
            result = offered_bank_diversity(trace)
            self.assertEqual(result["windows"], 2)
            self.assertEqual(result["mean_distinct_banks"], 1)
            trace.write_text("LD 0\nLD 1024\n" * 32)
            self.assertEqual(offered_bank_diversity(trace)["mean_distinct_banks"], 2)
            trace.write_text("LD 0\n" * 63)
            with self.assertRaises(ValueError):
                offered_bank_diversity(trace)

    def test_cache_requires_valid_complete_unchanged_artifacts(self):
        reference = ROOT / "results/sift/seed1/timing/bfs_128.json"
        raw = json.loads(reference.read_text())
        signature = dict(
            trace=raw["trace_sha256"],
            library=raw["library_sha256"],
            frontend=raw["frontend_sha256"],
            runner="test",
            parameters={},
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run.json"
            queries = output.with_suffix(".queries.csv")
            stamp = output.with_suffix(".cache.json")
            for damage in (
                "missing_queries",
                "truncated_json",
                "wrong_count",
                "wrong_trace",
                "wrong_mean",
                "valid_but_changed",
                "truncated_stamp",
            ):
                shutil.copyfile(reference, output)
                shutil.copyfile(reference.with_suffix(".queries.csv"), queries)
                write_cache(stamp, output, signature)
                self.assertTrue(cache_valid(stamp, output, signature))
                if damage == "missing_queries":
                    queries.unlink()
                elif damage == "truncated_json":
                    output.write_text('{"checks":')
                elif damage == "truncated_stamp":
                    stamp.write_text("{")
                else:
                    data = json.loads(output.read_text())
                    if damage == "wrong_count":
                        data["checks"]["served"] -= 1
                    elif damage == "wrong_trace":
                        data["trace_sha256"] = "wrong"
                    elif damage == "wrong_mean":
                        data["mean_query_cycles"] += 1
                    else:
                        data["trace_file"] = "unexpected.trace"
                    output.write_text(json.dumps(data))
                self.assertFalse(cache_valid(stamp, output, signature), damage)

    def test_missing_or_partial_sensitivity_inputs_fail_before_any_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with (
                patch.object(experiments, "WORK", work),
                patch.object(experiments, "replay") as replay,
            ):
                with self.assertRaisesRegex(RuntimeError, "prerequisite"):
                    experiments.real_sensitivity()
                folder = work / "sift/seed1"
                folder.mkdir(parents=True)
                (folder / "bfs_128.trace").write_text("LD 0 0 V\n")
                with self.assertRaisesRegex(RuntimeError, "prerequisite"):
                    experiments.real_sensitivity()
                replay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
