"""Ensure fresh-evidence comparison ignores paths but rejects scientific differences."""

import csv
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_reproduction import compare_inputs, compare_replays
from result_validation import query_rows


class ReproductionComparison(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reference = ROOT / "results/micro/order/sequential.json"
        self.candidate = Path(self.temp.name) / "fresh.json"
        self.data = json.loads(self.reference.read_text())
        shutil.copyfile(
            self.reference.with_suffix(".queries.csv"),
            self.candidate.with_suffix(".queries.csv"),
        )

    def write(self):
        self.candidate.write_text(json.dumps(self.data))

    def test_paths_and_rebuilt_library_do_not_mask_numerical_equality(self):
        self.data["library_sha256"] = "0" * 64
        self.data["config"]["frontend"]["path"] = "/new/location/trace"
        self.data["config"]["frontend"]["query_output"] = "/new/location/timings"
        self.write()
        result = compare_replays(self.reference, self.candidate)
        self.assertTrue(result["matched"])
        self.assertNotEqual(
            result["reference_library_sha256"], result["candidate_library_sha256"]
        )

    def test_diagnostic_changes_are_detected(self):
        self.data["stats"]["memory_system"]["controller"]["avg_read_latency"] += 0.1
        self.write()
        self.assertIn(
            "stats", compare_replays(self.reference, self.candidate)["differences"]
        )

    def test_service_intervals_are_checked_beyond_total_cycles(self):
        rows = query_rows(self.reference)
        rows[0]["first_arrive"] = str(int(rows[0]["first_arrive"]) + 1)
        rows[0]["cycles"] = str(int(rows[0]["cycles"]) - 1)
        self.data["mean_query_cycles"] = sum(int(r["cycles"]) for r in rows) / len(rows)
        with self.candidate.with_suffix(".queries.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        self.write()
        result = compare_replays(self.reference, self.candidate)
        self.assertFalse(result["matched"])
        self.assertEqual(result["reference_cycles"], result["candidate_cycles"])
        self.assertIn("per_query_or_phase_service", result["differences"])

    def test_input_identity_ignores_paths_and_compression_headers(self):
        before, after = Path(self.temp.name) / "before", Path(self.temp.name) / "after"
        before.mkdir()
        after.mkdir()
        for directory, prefix, timestamp in ((before, "/old", 1), (after, "/new", 2)):
            (directory / "mapping_hashes.json").write_text(
                json.dumps({prefix + "/bfs.mapping.csv": "same-hash"})
            )
            (directory / "phases.csv.gz").write_bytes(
                gzip.compress(b"phase,query\n0,0\n", mtime=timestamp)
            )
            (directory / "split.csv").write_text("source_query,partition\n1,test\n")
        self.assertTrue(
            all(r["matched"] for r in compare_inputs(before, after).values())
        )
        (after / "split.csv").write_text("source_query,partition\n2,test\n")
        result = compare_inputs(before, after)
        self.assertFalse(result["split.csv"]["matched"])
        self.assertTrue(result["mapping_hashes.json"]["matched"])


if __name__ == "__main__":
    unittest.main()
