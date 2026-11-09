#!/usr/bin/env python3
"""Regression tests for scientific invariants, separate from performance claims."""

from collections import Counter
import csv
import io
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def command(*args, ok=True):
    result = subprocess.run(
        [str(x) for x in args], cwd=ROOT, text=True, capture_output=True
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr)
    if not ok and not result.returncode:
        raise AssertionError("invalid input accepted")
    return result.stdout


class Pipeline(unittest.TestCase):
    def test_numeric_rejection(self):
        for tool in ["gen_trace", "gen_layout"]:
            for bad in ["-1", "123junk", "18446744073709551616"]:
                command(ROOT / "bin" / tool, "--dim", bad, ok=False)
        for bad in ["-1", "18446744073709551616"]:
            command(ROOT / "bin/reorder", bad, ok=False)

    def test_quality_is_bijection_and_fixed_trace(self):
        reference = command(
            ROOT / "bin/gen_layout", "--cluster", 16, "--quality", 100, "--burst", 32
        ).splitlines()
        for quality in [0, 25, 50, 75, 90, 100]:
            lines = command(
                ROOT / "bin/gen_layout",
                "--cluster",
                16,
                "--quality",
                quality,
                "--burst",
                32,
            ).splitlines()
            self.assertEqual(Counter(lines), Counter(reference))
            slots = [int(line.split()[1], 0) for line in lines[::4]]
            original = [int(line.split()[1], 0) for line in reference[::4]]
            self.assertEqual(len(set(slots)), 4096)
            self.assertEqual(
                sum(x == y for x, y in zip(slots, original)), 4096 * quality // 100
            )

    def test_partial_aligned_bursts(self):
        lines = command(
            ROOT / "bin/gen_trace",
            "--num_vectors",
            3,
            "--dim",
            65,
            "--base",
            31,
            "--burst",
            32,
        ).splitlines()
        addresses = [int(x.split()[1], 0) for x in lines]
        expected = []
        for v in range(3):
            start = 31 + 65 * v
            expected.extend(range(start // 32 * 32, start + 65, 32))
        self.assertEqual(addresses, expected)

    def test_small_pipeline_and_short_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "study"
            command(
                ROOT / "sprint1/run_study",
                "--max-base",
                100,
                "--train",
                10,
                "--test",
                5,
                "--output",
                dest,
            )
            split = list(csv.DictReader(io.StringIO((dest / "split.csv").read_text())))
            train = {r["source_query"] for r in split if r["partition"] == "train"}
            test = {r["source_query"] for r in split if r["partition"] == "test"}
            self.assertFalse(train & test)
            summaries = list(
                csv.DictReader(io.StringIO((dest / "layouts.csv").read_text()))
            )
            self.assertEqual(len(summaries), 10)
            for width in ["128", "512"]:
                self.assertEqual(
                    len({r["reads"] for r in summaries if r["vector_bytes"] == width}),
                    1,
                )
            for mapping in dest.glob("*.mapping.csv"):
                rows = list(csv.DictReader(io.StringIO(mapping.read_text())))
                self.assertEqual(sorted(int(r["slot"]) for r in rows), list(range(100)))
            f = Path(tmp) / "short.fvecs"
            f.write_bytes(struct.pack("<iff", 2, 1, 2))
            command(
                ROOT / "sprint1/run_study",
                "--base",
                f,
                "--queries",
                f,
                "--max-base",
                100,
                "--output",
                dest,
                ok=False,
            )
            f.write_bytes(struct.pack("<if", 1, float("nan")))
            command(
                ROOT / "sprint1/run_study",
                "--base",
                f,
                "--queries",
                f,
                "--max-base",
                10,
                "--output",
                dest,
                ok=False,
            )


if __name__ == "__main__":
    unittest.main()
