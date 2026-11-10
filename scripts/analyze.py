#!/usr/bin/env python3
"""Derive every current figure/table from raw results, using paired split-level intervals."""

import csv
import hashlib
import io
import json
import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "work/matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "doc/generated"
LAYOUTS = ["identity", "random", "bfs", "community", "query_aware"]
LABELS = {
    "identity": "Identity",
    "random": "Random",
    "bfs": "BFS",
    "community": "Community",
    "query_aware": "Query-aware",
}


def rows(path):
    return list(csv.DictReader(io.StringIO(path.read_text())))


def raw(path):
    return json.loads(path.read_text())


def writecsv(path, records):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def interval(values):
    x = np.asarray(values, dtype=float)
    if len(x) < 2:
        raise ValueError("at least two paired observations required")
    mean = float(x.mean())
    half = float(t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)))
    return mean, mean - half, mean + half


def table(name, headers, records, columns=None):
    if any(len(row) != len(headers) for row in records):
        raise ValueError(f"{name}: inconsistent table width")
    columns = columns or ("l" + "r" * (len(headers) - 1))
    if set(columns) <= set("lcr") and len(columns) != len(headers):
        raise ValueError(f"{name}: alignment does not match table width")
    text = (
        "\\begin{tabular}{"
        + columns
        + "}\n\\toprule\n"
        + " & ".join(headers)
        + " \\\\\n\\midrule\n"
    )
    text += "\n".join(
        " & ".join(str(x) for x in record) + " \\\\" for record in records
    )
    text += "\n\\bottomrule\n\\end{tabular}\n"
    (OUT / name).write_text(text)


def savefig(name):
    plt.tight_layout()
    plt.savefig(OUT / name, bbox_inches="tight")
    plt.close()


def write_provenance():
    inputs = sorted(
        p for p in RESULTS.rglob("*") if p.is_file() and ".cache." not in p.name
    )
    manifest = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in inputs
    }
    (OUT / "provenance.json").write_text(
        json.dumps(
            {
                "profiled_fetch_generator_sha256": hashlib.sha256(
                    (ROOT / "scripts/analyze_profiled_fetch.py").read_bytes()
                ).hexdigest(),
                "scheduling_generator_sha256": hashlib.sha256(
                    (ROOT / "scripts/analyze_scheduling.py").read_bytes()
                ).hexdigest(),
                "followup_generator_sha256": hashlib.sha256(
                    (ROOT / "scripts/analyze_followup.py").read_bytes()
                ).hexdigest(),
                "extension_generator_sha256": hashlib.sha256(
                    (ROOT / "scripts/analyze_strengthening.py").read_bytes()
                ).hexdigest(),
                "generator_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "inputs": manifest,
            },
            indent=2,
        )
        + "\n"
    )


def main():
    # Fail before replacing any figure or table when the evidence is incomplete.
    from check_results import check

    check()
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 11.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
        }
    )
    real = []
    meta = []
    for seed in range(1, 11):
        path = RESULTS / "sift" / f"seed{seed}"
        metadata = rows(path / "metadata.csv")[0]
        meta.append(metadata)
        layouts = {
            (r["layout"], int(r["vector_bytes"])): r for r in rows(path / "layouts.csv")
        }
        for width in [128, 512]:
            for layout in LAYOUTS:
                j = raw(path / "timing" / f"{layout}_{width}.json")
                p = layouts[(layout, width)]
                if len(set(j["checks"].values())) != 1:
                    raise ValueError("invalid request accounting")
                real.append(
                    dict(
                        seed=seed,
                        layout=layout,
                        vector_bytes=width,
                        cycles=j["cycles"],
                        row_hit_pct=j["row_hit_pct"],
                        same_block_pct=float(p["consecutive_vector_same_block_pct"]),
                        reads=j["checks"]["trace_reads"],
                        layout_seconds=float(p["layout_seconds"]),
                        mean_query_cycles=j["mean_query_cycles"],
                        recall=float(metadata["recall"]),
                    )
                )
    writecsv(RESULTS / "real_summary.csv", real)
    paired = []
    real_table = []
    for width in [512, 128]:
        baseline = {
            r["seed"]: r["cycles"]
            for r in real
            if r["vector_bytes"] == width and r["layout"] == "bfs"
        }
        for layout in LAYOUTS:
            data = [
                r for r in real if r["vector_bytes"] == width and r["layout"] == layout
            ]
            delta = [100 * (r["cycles"] / baseline[r["seed"]] - 1) for r in data]
            mean, lo, hi = interval(delta)
            record = dict(
                vector_bytes=width,
                layout=layout,
                n=len(delta),
                mean_delta_pct=mean,
                ci_low=lo,
                ci_high=hi,
                mean_cycles=np.mean([r["cycles"] for r in data]),
                mean_row_hit_pct=np.mean([r["row_hit_pct"] for r in data]),
                mean_same_block_pct=np.mean([r["same_block_pct"] for r in data]),
                mean_layout_seconds=np.mean([r["layout_seconds"] for r in data]),
            )
            paired.append(record)
            real_table.append(
                [
                    width,
                    LABELS[layout],
                    f"{record['mean_cycles'] / 1e6:.4f}",
                    f"{record['mean_row_hit_pct']:.2f}",
                    f"{record['mean_same_block_pct']:.2f}",
                    f"{mean:+.2f} [{lo:+.2f}, {hi:+.2f}]",
                ]
            )
    writecsv(RESULTS / "paired_summary.csv", paired)
    table(
        "real_table.tex",
        [
            "Bytes",
            "Layout",
            "Cycles ($10^6$)",
            "Hit (\\%)",
            "Block (\\%)",
            "$\\Delta$ vs. BFS (\\%)",
        ],
        real_table,
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.4), sharey=True)
    for ax, width in zip(axes, [512, 128]):
        data = [
            r for r in paired if r["vector_bytes"] == width and r["layout"] != "bfs"
        ]
        y = np.arange(len(data))
        v = np.array([r["mean_delta_pct"] for r in data])
        lo = np.array([r["ci_low"] for r in data])
        hi = np.array([r["ci_high"] for r in data])
        ax.errorbar(v, y, xerr=[v - lo, hi - v], fmt="o", capsize=4, color="#006c80")
        ax.axvline(0, color="gray", lw=1)
        ax.set_yticks(y, [LABELS[r["layout"]] for r in data])
        ax.set_title(f"{width} bytes / vector")
        ax.set_xlabel("Cycle difference vs BFS (%)")
        ax.grid(axis="x", alpha=0.2)
    savefig("real_paired.pdf")
    order = [
        raw(RESULTS / "micro/order" / f"{name}.json")
        for name in ["sequential", "random"]
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for ax, key, label in zip(
        axes,
        ["cycles", "row_hit_pct"],
        ["Completed-stream cycles", "Classified row hits (%)"],
    ):
        ax.bar(
            ["Sequential", "Permuted"],
            [j[key] for j in order],
            color=["#006c80", "#cf704b"],
        )
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
    savefig("micro_order.pdf")
    reorder = []
    for window in [1, 16, 64, 256, 1024, 4096, 16384]:
        j = raw(RESULTS / "micro/reorder" / f"w{window}.json")
        reorder.append([window, j["cycles"], f"{j['row_hit_pct']:.2f}"])
    table("reorder_table.tex", ["Window (requests)", "Cycles", "Hit (\\%)"], reorder)
    runs = []
    threshold = []
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8))
    for width in [96, 128, 192, 256, 384, 512]:
        vals = []
        for count in [1, 2, 4, 8, 16, 32, 64]:
            j = raw(RESULTS / "micro/runs" / f"width{width}_offset0_run{count}.json")
            vals.append(j["row_hit_pct"])
        axes[0].plot(
            np.array([1, 2, 4, 8, 16, 32, 64]) * width,
            vals,
            marker=".",
            label=f"{width} B",
        )
        for offset in [0, 32, 480]:
            points = [
                raw(
                    RESULTS
                    / "micro/runs"
                    / f"width{width}_offset{offset}_run{count}.json"
                )
                for count in [1, 2, 4, 8, 16, 32, 64]
            ]
            hits = np.array([j["row_hit_pct"] for j in points])
            best = max(hits)
            first = next(i for i in range(7) if np.all(hits[i:] >= best - 1))
            count = [1, 2, 4, 8, 16, 32, 64][first]
            threshold.append(
                dict(
                    vector_bytes=width,
                    offset=offset,
                    run_vectors=count,
                    run_bytes=count * width,
                    grid_best_hit_pct=best,
                )
            )
            for c, j in zip([1, 2, 4, 8, 16, 32, 64], points):
                runs.append(
                    dict(
                        vector_bytes=width,
                        offset=offset,
                        run_vectors=c,
                        cycles=j["cycles"],
                        row_hit_pct=j["row_hit_pct"],
                    )
                )
    axes[0].set_xscale("log", base=2)
    axes[0].set_xlabel("Contiguous run bytes (aligned base)")
    axes[0].set_ylabel("Row hits (%)")
    axes[0].legend(ncol=2, fontsize=10.5)
    for offset in [0, 32, 480]:
        points = [r for r in runs if r["vector_bytes"] == 128 and r["offset"] == offset]
        axes[1].plot(
            [r["run_vectors"] for r in points],
            [r["cycles"] for r in points],
            marker=".",
            label=f"Offset {offset} B",
        )
    axes[1].set_xscale("log", base=2)
    axes[1].set_xlabel("Run length (128-byte vectors)")
    axes[1].set_ylabel("Completed-stream cycles")
    axes[1].legend(fontsize=10.5)
    savefig("run_sensitivity.pdf")
    writecsv(RESULTS / "runs_summary.csv", runs)
    writecsv(RESULTS / "thresholds.csv", threshold)
    table(
        "threshold_table.tex",
        ["Vector bytes", "Offset 0", "Offset 32", "Offset 480"],
        [
            [w]
            + [
                next(
                    r["run_bytes"]
                    for r in threshold
                    if r["vector_bytes"] == w and r["offset"] == o
                )
                for o in [0, 32, 480]
            ]
            for w in [96, 128, 192, 256, 384, 512]
        ],
    )
    quality = []
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for q in [0, 25, 50, 75, 90, 100]:
        j = raw(RESULTS / "micro/quality" / f"q{q}.json")
        quality.append([q, j["cycles"], j["row_hit_pct"]])
    a = np.array(quality)
    axes[0].plot(a[:, 0], a[:, 1], "-o", color="#006c80")
    axes[0].set_ylabel("Completed-stream cycles")
    axes[1].plot(a[:, 0], a[:, 2], "-o", color="#cf704b")
    axes[1].set_ylabel("Row hits (%)")
    for ax in axes:
        ax.set_xlabel("Requested fixed-slot fraction (%)")
        ax.grid(alpha=0.2)
    savefig("quality.pdf")
    table(
        "quality_table.tex",
        ["Fixed slots (\\%)", "Cycles", "Hit (\\%)"],
        [[q, c, f"{h:.2f}"] for q, c, h in quality],
    )
    sensitivity = []
    conditions = [
        "default",
        "inflight1",
        "inflight16",
        "queue8",
        "issue4",
        "cap1",
        "cap4",
        "rowhit",
        "alternate_mapping",
    ]
    fig, axes = plt.subplots(2, 1, figsize=(7.5, 8.5))
    for ax, width in zip(axes, [512, 128]):
        matrix = []
        for condition in conditions:
            path = (
                RESULTS / "sift/seed1/timing"
                if condition == "default"
                else RESULTS / "sensitivity" / condition
            )
            js = {layout: raw(path / f"{layout}_{width}.json") for layout in LAYOUTS}
            matrix.append(
                [100 * (js[l]["cycles"] / js["bfs"]["cycles"] - 1) for l in LAYOUTS]
            )
            for l in LAYOUTS:
                sensitivity.append(
                    dict(
                        condition=condition,
                        vector_bytes=width,
                        layout=l,
                        cycles=js[l]["cycles"],
                        row_hit_pct=js[l]["row_hit_pct"],
                        delta_bfs_pct=100 * (js[l]["cycles"] / js["bfs"]["cycles"] - 1),
                    )
                )
        limit = 20
        ax.imshow(matrix, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
        for y, row in enumerate(matrix):
            for x, v in enumerate(row):
                ax.text(
                    x,
                    y,
                    f"{v:+.1f}",
                    ha="center",
                    va="center",
                    fontsize=11.5,
                    color="white" if abs(v) > 12 else "black",
                )
        ax.set_xticks(range(5), [LABELS[l] for l in LAYOUTS], rotation=40, ha="right")
        ax.set_yticks(
            range(len(conditions)),
            [
                "Default",
                "Outstanding: 1",
                "Outstanding: 16",
                "Read queue: 8",
                "Issue interval: 4",
                "ClosedCAP: 1",
                "ClosedCAP: 4",
                "Row-hit priority",
                "Alternate mapping",
            ],
        )
        ax.set_title(f"{width} bytes: cycle difference vs. BFS (%)")
    savefig("sensitivity.pdf")
    writecsv(RESULTS / "sensitivity_summary.csv", sensitivity)
    ablations = []
    for name in ["train100", "train1000", "window4", "window64", "block2048"]:
        metadata = rows(RESULTS / "ablations" / name / "metadata.csv")[0]
        for width in [512, 128]:
            path = RESULTS / "ablations" / name / "timing"
            b = raw(path / f"bfs_{width}.json")
            q = raw(path / f"query_aware_{width}.json")
            ablations.append(
                [
                    name.replace("_", "-"),
                    width,
                    f"{100 * (q['cycles'] / b['cycles'] - 1):+.2f}",
                    f"{100 * float(metadata['test_access_coverage']):.1f}",
                    f"{float(metadata['model_seconds']):.3f}",
                ]
            )
    table(
        "ablation_table.tex",
        ["Condition", "Bytes", "$\\Delta$ QA/BFS (\\%)", "Coverage (\\%)", "Model (s)"],
        ablations,
    )
    cost = []
    for layout in LAYOUTS:
        values = [
            r["layout_seconds"]
            for r in real
            if r["layout"] == layout and r["vector_bytes"] == 512
        ]
        cost.append([LABELS[layout], f"{np.mean(values):.4f}"])
    table("cost_table.tex", ["Layout", "Mean construction (s), 512 B"], cost)
    recall = interval([100 * float(m["recall"]) for m in meta])
    values = {
        "SiftRecall": f"{recall[0]:.2f}",
        "SiftRecallLow": f"{recall[1]:.2f}",
        "SiftRecallHigh": f"{recall[2]:.2f}",
        "SequentialCycles": str(order[0]["cycles"]),
        "RandomCycles": str(order[1]["cycles"]),
        "SequentialHit": f"{order[0]['row_hit_pct']:.2f}",
        "RandomHit": f"{order[1]['row_hit_pct']:.2f}",
        "MeanCoverage": f"{np.mean([float(m['test_access_coverage']) * 100 for m in meta]):.1f}",
        "MeanIndexSeconds": f"{np.mean([float(m['index_seconds']) for m in meta]):.2f}",
        "MeanTrainingSeconds": f"{np.mean([float(m['training_seconds']) for m in meta]):.2f}",
        "MeanModelSeconds": f"{np.mean([float(m['model_seconds']) for m in meta]):.2f}",
        "UpperFraction": f"{100 * np.mean([int(m['upper_records']) / (int(m['vector_reads']) + int(m['adjacency_reads'])) for m in meta]):.2f}",
    }
    for width in [512, 128]:
        r = next(
            r
            for r in paired
            if r["layout"] == "query_aware" and r["vector_bytes"] == width
        )
        suffix = "Float" if width == 512 else "Compact"
        values["QADelta" + suffix] = f"{r['mean_delta_pct']:+.2f}"
        values["QALow" + suffix] = f"{r['ci_low']:+.2f}"
        values["QAHigh" + suffix] = f"{r['ci_high']:+.2f}"
    (OUT / "values.tex").write_text(
        "".join("\\newcommand{\\" + k + "}{" + v + "}\n" for k, v in values.items())
    )
    from analyze_strengthening import generate

    generate()
    from analyze_followup import generate as generate_followup

    generate_followup()
    from analyze_scheduling import generate as generate_scheduling

    generate_scheduling()
    from analyze_profiled_fetch import generate as generate_profiled_fetch

    generate_profiled_fetch()
    write_provenance()
    print(
        "Generated tables and figures from 10 paired SIFT splits and the completed sensitivity matrix."
    )
    print(json.dumps(values, indent=2))


if __name__ == "__main__":
    main()
