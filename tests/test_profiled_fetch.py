"""Guard training-only dispatch, deterministic ties and malformed profiles."""

from pathlib import Path
import csv
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from profiled_fetch import choose_order, select_training
from profiled_fetch_validation import logical_phases
from profiled_fetch import CONFIGURATIONS


class ProfiledEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "generated"
        self.out.mkdir()
        timing, queries, published = [], [], []
        for seed in range(1, 11):
            folder = self.root / f"calibration/seed{seed}"
            folder.mkdir(parents=True)
            choices = {}
            for c in CONFIGURATIONS:
                for w in (512, 128):
                    # Training favours sorting; held-out work favours round-robin.
                    choices[f"{c}/{w}"] = dict(
                        training_cycles=dict(bounded=300, sorted=100, roundrobin=200),
                        selected_order="sorted",
                    )
                    for order, cost in (
                        ("bounded", 1000),
                        ("sorted", 1100),
                        ("roundrobin", 900),
                    ):
                        timing.append(
                            dict(
                                seed=seed,
                                condition=c,
                                vector_bytes=w,
                                order=order,
                                cycles=cost,
                                mean_original_query_cycles=cost / 200,
                            )
                        )
                        if order != "bounded":
                            queries.append(
                                dict(
                                    seed=seed,
                                    condition=c,
                                    vector_bytes=w,
                                    order=order,
                                    queries_slower_pct=60 if order == "sorted" else 20,
                                    p95_service_delta_pct=12
                                    if order == "sorted"
                                    else -10,
                                )
                            )
            (folder / "selection.json").write_text(json.dumps(choices))
            for w in (512, 128):
                for layout in ("rcm", "gorder", "porder"):
                    published.append(
                        dict(
                            seed=seed,
                            vector_bytes=w,
                            graph="reference",
                            mode="bounded",
                            layout=layout,
                            cycles=1250,
                        )
                    )
        for name, data in (
            ("scheduling_measurements.csv", timing),
            ("scheduling_pairs.csv", queries),
            ("followup_measurements.csv", published),
        ):
            with (self.root / name).open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(data[0]))
                writer.writeheader()
                writer.writerows(data)

    def run_analysis(self):
        import analyze
        import analyze_profiled_fetch as module
        import matplotlib.pyplot as plt

        with (
            patch.object(module, "RESULTS", self.root),
            patch.object(module, "OUT", self.out),
            patch.object(analyze, "OUT", self.out),
            patch.object(module, "savefig", lambda _: plt.close()),
        ):
            module.generate()

    def test_test_oracle_cannot_change_training_choice(self):
        self.run_analysis()
        with (self.root / "profiled_fetch_selections.csv").open() as f:
            selected = list(csv.DictReader(f))
        self.assertEqual(len(selected), 140)
        for r in selected:
            self.assertEqual(r["selected_order"], "sorted")
            self.assertAlmostEqual(float(r["delta_vs_original_pct"]), 10)
            self.assertAlmostEqual(
                float(r["oracle_regret_pct"]), 100 * (1100 / 900 - 1)
            )
            self.assertEqual(float(r["calibration_total_cycles"]), 600)
            self.assertEqual(float(r["saved_cycles_per_query"]), -0.5)
            self.assertEqual(float(r["queries_slower_pct"]), 60)
        with (self.root / "profiled_fetch_pairs.csv").open() as f:
            pairs = list(csv.DictReader(f))
        self.assertEqual(len(pairs), 620)
        for r in pairs:
            if r["comparator"] in ("rcm", "gorder", "porder"):
                self.assertEqual(r["condition"], "default")
                self.assertAlmostEqual(float(r["delta_pct"]), -12)

    def test_missing_query_effects_are_rejected(self):
        path = self.root / "scheduling_pairs.csv"
        lines = path.read_text().splitlines()
        path.write_text("\n".join([lines[0]] + lines[2:]) + "\n")
        with self.assertRaises(KeyError):
            self.run_analysis()


class ProfiledFetch(unittest.TestCase):
    def test_choice_uses_only_training_and_handles_ties(self):
        self.assertEqual(
            choose_order(dict(bounded=100, sorted=100, roundrobin=100)), "bounded"
        )
        self.assertEqual(
            choose_order(dict(bounded=100, sorted=105, roundrobin=80)), "roundrobin"
        )
        self.assertEqual(
            choose_order(dict(bounded=100, sorted=79, roundrobin=80)), "sorted"
        )
        for costs in (
            {"bounded": 100},
            {"bounded": 100, "sorted": 0, "roundrobin": 80},
            {"bounded": 100, "sorted": float("nan"), "roundrobin": 80},
        ):
            with self.assertRaises(ValueError):
                choose_order(costs)

    def test_training_prefix_and_overlap_rejection(self):
        split = [
            dict(partition="train", position=str(i), source_query=str(100 + i))
            for i in range(50)
        ]
        split.append(dict(partition="test", position="0", source_query="1000"))
        trace = [(i, i, "V", 0, 512) for i in range(55)]
        selected, _ = select_training(trace, split)
        self.assertEqual([r[0] for r in selected], list(range(50)))
        with self.assertRaises(ValueError):
            select_training(trace[:49], split)
        split[-1]["source_query"] = "100"
        with self.assertRaises(ValueError):
            select_training(trace, split)

    def test_level_entry_and_query_boundaries(self):
        records = [
            dict(query=0, node=0, kind="A", level=1, bytes=8),
            dict(query=0, node=1, kind="V", level=1, bytes=512),
            dict(query=0, node=0, kind="V", level=0, bytes=512),
            dict(query=1, node=0, kind="V", level=0, bytes=512),
        ]
        phases = logical_phases(records)
        self.assertEqual(len(phases), 4)
        self.assertEqual([p[0][0] for p in phases], [0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()
