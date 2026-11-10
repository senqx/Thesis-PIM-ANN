#!/usr/bin/env python3
"""Check graph availability, order-only schedules and published-layout adaptation."""

from collections import Counter
import gzip
import json
import random
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from followup_traces import (
    adjacency_addresses,
    emit,
    phase_addresses,
    profile_edges,
    split_phases,
)
from result_validation import cache_valid, query_rows, validate_replay, write_cache
from followup_validation import original_query_rows


class Followup(unittest.TestCase):
    def test_query_service_includes_inter_phase_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "bounded"
            folder.mkdir()
            path = folder / "timing.json"
            path.with_suffix(".queries.csv").write_text(
                "query,reads,first_arrive,last_depart,cycles\n"
                "0,1,10,20,10\n1,2,25,31,6\n2,1,40,50,10\n"
            )
            phases = [{"query": "0"}, {"query": "0"}, {"query": "1"}]
            actual = original_query_rows(path, phases)
            self.assertEqual([r["cycles"] for r in actual], [21, 10])
            self.assertEqual([r["reads"] for r in actual], [3, 1])
            with self.assertRaises(ValueError):
                original_query_rows(path, phases[:-1])

    def setUp(self):
        self.graph = {
            (0, 0): (1, 2),
            (1, 0): (3,),
            (2, 0): (3,),
            (3, 0): (),
            (0, 1): (2,),
        }
        self.trace = [
            (0, 0, "V", 1, 512),
            (0, 0, "A", 1, 8),
            (0, 2, "V", 1, 512),
            (0, 0, "V", 0, 512),
            (0, 0, "A", 0, 12),
            (0, 1, "V", 0, 512),
            (0, 2, "V", 0, 512),
            (0, 1, "A", 0, 8),
            (0, 3, "V", 0, 512),
            (1, 0, "V", 0, 512),
            (1, 0, "A", 0, 12),
            (1, 1, "V", 0, 512),
        ]

    def test_phases_and_profile(self):
        phases = split_phases(self.trace, self.graph)
        self.assertEqual([len(p) for p in phases], [1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1])
        self.assertEqual([r for p in phases for r in p], self.trace)
        self.assertEqual(
            profile_edges(self.trace, self.graph),
            Counter({(0, 1): 2, (0, 2): 1, (1, 3): 1}),
        )
        bad = list(self.trace)
        bad[6] = (0, 3, "V", 0, 512)
        with self.assertRaises(ValueError):
            split_phases(bad, self.graph)
        with self.assertRaises(ValueError):
            profile_edges(bad, self.graph)

    def test_schedules_preserve_each_phase_and_emit_expected_addresses(self):
        phases = split_phases(self.trace, self.graph)
        mapping = [2, 3, 0, 1]
        for width in (128, 512):
            adjacency = adjacency_addresses(self.graph, 4, width)
            candidate = phases[5]
            a, b = 0x10000000 + 3 * width, 0x10000000
            expected = [
                address
                for offset in range(0, width, 32)
                for address in (a + offset, b + offset)
            ]
            self.assertEqual(
                phase_addresses(candidate, mapping, adjacency, width, "roundrobin"),
                expected,
            )
            with tempfile.TemporaryDirectory() as tmp:
                proofs = {}
                for mode in ("flat", "bounded", "sorted", "roundrobin"):
                    path = Path(tmp) / mode
                    proofs[mode] = emit(phases, self.graph, mapping, width, mode, path)
                    lines = path.read_text().splitlines()
                    expected_records = []
                    for i, phase in enumerate(phases):
                        marker = phase[0][0] if mode == "flat" else i
                        expected_records += [(marker, phase[0][2])] * (
                            len(phase) * width // 32 if phase[0][2] == "V" else 1
                        )
                    self.assertEqual(
                        [(int(line.split()[2]), line.split()[3]) for line in lines],
                        expected_records,
                    )
                self.assertEqual(
                    len({p["phase_multiset_sha256"] for p in proofs.values()}), 1
                )
                self.assertEqual(len({p["reads"] for p in proofs.values()}), 1)

    def test_lossless_compressed_cache_and_truncation(self):
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
            path = Path(tmp) / "timing.json"
            shutil.copyfile(reference, path)
            sidecar = path.with_suffix(".queries.csv.gz")
            sidecar.write_bytes(
                gzip.compress(
                    reference.with_suffix(".queries.csv").read_bytes(), mtime=0
                )
            )
            self.assertEqual(query_rows(path), query_rows(reference))
            validate_replay(path)
            stamp = path.with_suffix(".cache.json")
            write_cache(stamp, path, signature)
            self.assertTrue(cache_valid(stamp, path, signature))
            sidecar.write_bytes(sidecar.read_bytes()[:20])
            self.assertFalse(cache_valid(stamp, path, signature))

    def test_published_adapter(self):
        executable = ROOT / "bin/published_layouts"
        if not executable.exists():
            self.skipTest("optional published sources not installed")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            graph, profile, result = [
                folder / name for name in ("graph.csv", "profile.csv", "mapping.csv")
            ]
            graph.write_text(
                "node,level,neighbors\n"
                + "".join(f"{i},0,{i + 1 if i < 19 else ''}\n" for i in range(20))
            )
            profile.write_text("source,target,traversals\n0,1,5\n")
            for method in ("rcm", "gorder", "porder"):
                subprocess.run(
                    [executable, graph, profile, method, result],
                    check=True,
                    capture_output=True,
                )
                values = [
                    int(line.split(",")[1])
                    for line in result.read_text().splitlines()[1:]
                ]
                self.assertEqual(sorted(values), list(range(20)))
                if method == "rcm":
                    # Zero-degree node 19 is started first; reversing the resulting
                    # directed BFS places it last. This matches the supplied routine.
                    self.assertEqual(values[-1], 19)
            profile.write_text("source,target,traversals\n0,19,5\n")
            p = subprocess.run(
                [executable, graph, profile, "porder", result], capture_output=True
            )
            self.assertNotEqual(p.returncode, 0)

    def test_weighted_queue_preserves_published_ordering(self):
        reference = ROOT / ".toolchain/coleman/reference_layouts"
        if not reference.exists():
            self.skipTest("optional published reference not installed")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            rng = random.Random(71)
            for trial in range(30):
                n = 20 + trial * 17
                graph, profile = folder / "graph.csv", folder / "profile.csv"
                edges = [
                    rng.sample(
                        [j for j in range(n) if i != j], rng.randrange(min(n, 33))
                    )
                    for i in range(n)
                ]
                graph.write_text(
                    "node,level,neighbors\n"
                    + "".join(
                        f"{i},0," + " ".join(map(str, neighbors)) + "\n"
                        for i, neighbors in enumerate(edges)
                    )
                )
                profile.write_text(
                    "source,target,traversals\n"
                    + "".join(
                        f"{i},{j},{rng.randrange(1, 501)}\n"
                        for i, neighbors in enumerate(edges)
                        for j in neighbors
                    )
                )
                for method in ("rcm", "gorder", "porder"):
                    outputs = [folder / "reference.csv", folder / "adapted.csv"]
                    for executable, output in zip(
                        (reference, ROOT / "bin/published_layouts"), outputs
                    ):
                        subprocess.run(
                            [executable, graph, profile, method, output],
                            check=True,
                            capture_output=True,
                        )
                    self.assertEqual(
                        outputs[0].read_bytes(),
                        outputs[1].read_bytes(),
                        (trial, method),
                    )


if __name__ == "__main__":
    unittest.main()
