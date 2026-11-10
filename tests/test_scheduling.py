"""Check batching boundaries and order identities independently of performance."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from followup_traces import emit, phase_rows
from scheduling import batch_phases, expected_scheduling
from scheduling_validation import check_phase_rows


class Scheduling(unittest.TestCase):
    def setUp(self):
        self.phases = [
            [(0, 0, "A", 0, 16)],
            [(0, n, "V", 0, 512) for n in (1, 2, 3)],
            [(1, 0, "V", 0, 512)],
        ]
        self.graph = {(0, 0): (1, 2, 3), (1, 0): (), (2, 0): (), (3, 0): ()}
        self.mapping = [2, 3, 0, 1]

    def test_batch_membership_and_rejection(self):
        groups, info = batch_phases(self.phases, 2)
        self.assertEqual([[r[1] for r in p] for p in groups], [[0], [1, 2], [3], [0]])
        self.assertEqual([r["parent_phase"] for r in info], [0, 1, 1, 2])
        self.assertEqual([r["query"] for r in info], [0, 0, 0, 1])
        check_phase_rows(info, phase_rows(self.phases), 2)
        for field, index in (("parent_phase", 2), ("query", 1), ("vector_records", 2)):
            broken = deepcopy(info)
            broken[index][field] += 1
            with self.assertRaises(ValueError):
                check_phase_rows(broken, phase_rows(self.phases), 2)
        with self.assertRaises(ValueError):
            batch_phases(self.phases, -1)

    def test_single_vector_order_identity_and_flat_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.trace"
            for width in (128, 512):
                flat = emit(self.phases, self.graph, self.mapping, width, "flat", path)
                for cap in (0, 1, 2, 8):
                    groups, _ = batch_phases(self.phases, cap)
                    actual = emit(groups, self.graph, self.mapping, width, "flat", path)
                    self.assertEqual(actual["trace_sha256"], flat["trace_sha256"])
                    proofs = [
                        emit(groups, self.graph, self.mapping, width, mode, path)
                        for mode in ("bounded", "sorted", "roundrobin")
                    ]
                    self.assertEqual(
                        len({p["phase_multiset_sha256"] for p in proofs}), 1
                    )
                    if cap == 1:
                        self.assertEqual(len({p["trace_sha256"] for p in proofs}), 1)
                    if cap == 0:
                        self.assertEqual(groups, self.phases)

    def test_fixed_matrix(self):
        names = expected_scheduling()
        self.assertEqual(len(names), 360)
        self.assertIn("scheduling/seed10/batch8/roundrobin_512.json", names)
        self.assertNotIn("scheduling/seed1/default/bounded_128.json", names)


if __name__ == "__main__":
    unittest.main()
