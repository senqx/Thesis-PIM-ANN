"""Paired scheduling sensitivity, stronger-baseline comparison and model diagrams."""

from analyze import OUT, RESULTS, interval, raw, rows, savefig, table, writecsv
from followup_validation import compressed_rows, original_query_rows
from scheduling import CONDITIONS, ORDERS
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

LABELS = {
    "default": "Default (64 outstanding)",
    "inflight16": "16 outstanding",
    "inflight32": "32 outstanding",
    "inflight128": "128 outstanding",
    "batch2": "Candidate batches of 2",
    "batch8": "Candidate batches of 8",
    "alternate_mapping": "Alternative address mapping",
}
TEX_KEYS = {
    "default": "Default",
    "inflight16": "InflightSixteen",
    "inflight32": "InflightThirtyTwo",
    "inflight128": "InflightOneTwentyEight",
    "batch2": "BatchTwo",
    "batch8": "BatchEight",
    "alternate_mapping": "AlternateMapping",
}


def measurements():
    output, queries = [], {}
    for seed in range(1, 11):
        old = RESULTS / f"followup/reference/seed{seed}"
        folder = RESULTS / f"scheduling/seed{seed}"
        phase_maps = {
            cap: compressed_rows(folder / f"phases_batch{cap}.csv.gz")
            for cap in (0, 2, 8)
        }
        for condition, (cap, _) in {"default": (0, {}), **CONDITIONS}.items():
            for width in (512, 128):
                for order in ORDERS:
                    path = (
                        old / order / f"bfs_{width}.json"
                        if condition == "default"
                        else folder / condition / f"{order}_{width}.json"
                    )
                    result = raw(path)
                    original = original_query_rows(path, phase_maps[cap])
                    times = np.array([int(r["cycles"]) for r in original])
                    queries[seed, condition, width, order] = times
                    output.append(
                        dict(
                            seed=seed,
                            condition=condition,
                            vector_bytes=width,
                            order=order,
                            cycles=result["cycles"],
                            mean_original_query_cycles=times.mean(),
                            p95_original_query_cycles=np.percentile(times, 95),
                            row_hit_pct=result["row_hit_pct"],
                            peak_inflight=result["stats"]["frontend"]["peak_inflight"],
                            reads=result["checks"]["trace_reads"],
                        )
                    )
    return output, queries


def generate():
    measured, queries = measurements()
    writecsv(RESULTS / "scheduling_measurements.csv", measured)
    lookup = {
        (r["seed"], r["condition"], r["vector_bytes"], r["order"]): r for r in measured
    }
    pairs = []
    for r in measured:
        if r["order"] == "bounded":
            continue
        seed, condition, width, order = [
            r[k] for k in ("seed", "condition", "vector_bytes", "order")
        ]
        base = lookup[seed, condition, width, "bounded"]
        before, after = (
            queries[seed, condition, width, "bounded"],
            queries[seed, condition, width, order],
        )
        pairs.append(
            dict(
                seed=seed,
                condition=condition,
                vector_bytes=width,
                order=order,
                delta_pct=100 * (r["cycles"] / base["cycles"] - 1),
                saved_cycles_per_query=float((before - after).mean()),
                queries_faster_pct=100 * float((after < before).mean()),
                queries_slower_pct=100 * float((after > before).mean()),
                p95_service_delta_pct=100
                * (np.percentile(after, 95) / np.percentile(before, 95) - 1),
            )
        )
    writecsv(RESULTS / "scheduling_pairs.csv", pairs)
    summary = []
    for condition in LABELS:
        for width in (512, 128):
            for order in ("sorted", "roundrobin"):
                items = [
                    r
                    for r in pairs
                    if (r["condition"], r["vector_bytes"], r["order"])
                    == (condition, width, order)
                ]
                mean, low, high = interval([r["delta_pct"] for r in items])
                summary.append(
                    dict(
                        condition=condition,
                        vector_bytes=width,
                        order=order,
                        n=len(items),
                        mean_delta_pct=mean,
                        ci_low=low,
                        ci_high=high,
                        min_delta_pct=min(r["delta_pct"] for r in items),
                        max_delta_pct=max(r["delta_pct"] for r in items),
                        mean_saved_cycles_per_query=np.mean(
                            [r["saved_cycles_per_query"] for r in items]
                        ),
                        min_queries_faster_pct=min(
                            r["queries_faster_pct"] for r in items
                        ),
                        max_queries_faster_pct=max(
                            r["queries_faster_pct"] for r in items
                        ),
                        min_p95_service_delta_pct=min(
                            r["p95_service_delta_pct"] for r in items
                        ),
                        max_p95_service_delta_pct=max(
                            r["p95_service_delta_pct"] for r in items
                        ),
                    )
                )
    writecsv(RESULTS / "scheduling_summary.csv", summary)
    index = {(r["condition"], r["vector_bytes"], r["order"]): r for r in summary}

    def cell(condition, width, order):
        r = index[condition, width, order]
        return f"{r['mean_delta_pct']:+.2f} [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]"

    table(
        "scheduling_table.tex",
        ["Condition", "Bytes", "Sorted", "Round-robin"],
        [
            [LABELS[c], w, cell(c, w, "sorted"), cell(c, w, "roundrobin")]
            for c in LABELS
            for w in (512, 128)
        ],
    )
    table(
        "scheduling_paper_table.tex",
        ["Condition", "512 bytes", "128 bytes"],
        [
            [
                LABELS[c]
                .replace("Candidate batches of", "Batch")
                .replace("Alternative address mapping", "Alt. mapper")
                .replace("Default (64 outstanding)", "Default 64"),
                cell(c, 512, "roundrobin"),
                cell(c, 128, "roundrobin"),
            ]
            for c in LABELS
        ],
    )
    table(
        "scheduling_query_table.tex",
        [
            "Condition",
            "Bytes",
            "Saved cycles/query",
            "Faster queries (\\%)",
            "p95 change (\\%)",
        ],
        [
            [
                LABELS[r["condition"]],
                r["vector_bytes"],
                f"{r['mean_saved_cycles_per_query']:+,.0f}",
                f"{r['min_queries_faster_pct']:.1f}--{r['max_queries_faster_pct']:.1f}",
                f"{r['min_p95_service_delta_pct']:+.2f} to {r['max_p95_service_delta_pct']:+.2f}",
            ]
            for r in summary
            if r["order"] == "roundrobin"
        ],
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.5), sharey=True, sharex=True)
    for ax, width in zip(axes, (512, 128)):
        for order, offset, color, marker in (
            ("sorted", -0.15, "#cf704b", "s"),
            ("roundrobin", 0.15, "#006c80", "o"),
        ):
            for y, condition in enumerate(LABELS):
                r = index[condition, width, order]
                values = [
                    p["delta_pct"]
                    for p in pairs
                    if (p["condition"], p["vector_bytes"], p["order"])
                    == (condition, width, order)
                ]
                ax.scatter(
                    values, [y + offset] * len(values), s=11, color=color, alpha=0.35
                )
                ax.errorbar(
                    r["mean_delta_pct"],
                    y + offset,
                    xerr=[
                        [r["mean_delta_pct"] - r["ci_low"]],
                        [r["ci_high"] - r["mean_delta_pct"]],
                    ],
                    fmt=marker,
                    ms=4,
                    color=color,
                    capsize=3,
                    label=order if y == 0 else None,
                )
        ax.set_yticks(range(len(LABELS)), list(LABELS.values()))
        ax.set_xticks([-40, 0, 40, 80, 120])
        ax.axvline(0, color="gray", lw=1)
        ax.grid(axis="x", alpha=0.2)
        ax.set_title(
            "512 bytes (float32)" if width == 512 else "128 bytes (hypothetical)"
        )
    axes[0].invert_yaxis()
    axes[1].legend(
        labels=["Sorted", "Round-robin"],
        handles=axes[1].get_legend_handles_labels()[0],
        loc="best",
        fontsize=9,
    )
    fig.supxlabel("Cycle difference vs matching original order (%)", fontsize=11)
    savefig("scheduling_sensitivity.pdf")
    values = {
        "SchedRaisedLimitEqual": str(
            sum(
                lookup[seed, "default", width, order]["cycles"]
                == lookup[seed, "inflight128", width, order]["cycles"]
                for seed in range(1, 11)
                for width in (512, 128)
                for order in ORDERS
            )
        ),
        "SchedDefaultPeak": str(
            max(r["peak_inflight"] for r in measured if r["condition"] == "default")
        ),
    }
    for condition in LABELS:
        key = TEX_KEYS[condition]
        for width, suffix in ((512, "Float"), (128, "Compact")):
            for order, orderkey in (("sorted", "Sort"), ("roundrobin", "RR")):
                r = index[condition, width, order]
                values["Sched" + key + orderkey + suffix] = (
                    f"{r['mean_delta_pct']:+.2f}"
                )
    old = rows(RESULTS / "followup_measurements.csv")
    stronger = []
    for width, layout, suffix in ((512, "porder", "Float"), (128, "gorder", "Compact")):
        effects = []
        for seed in range(1, 11):
            base = next(
                r
                for r in old
                if (
                    r["graph"],
                    int(r["seed"]),
                    int(r["vector_bytes"]),
                    r["layout"],
                    r["mode"],
                )
                == ("reference", seed, width, layout, "bounded")
            )
            effects.append(
                100
                * (
                    lookup[seed, "default", width, "roundrobin"]["cycles"]
                    / float(base["cycles"])
                    - 1
                )
            )
        mean, lo, hi = interval(effects)
        stronger.append(
            dict(
                vector_bytes=width,
                baseline_layout=layout,
                mean_delta_pct=mean,
                ci_low=lo,
                ci_high=hi,
            )
        )
        values["RRvsPublished" + suffix] = f"{mean:+.2f}"
        values["RRvsPublishedLow" + suffix] = f"{lo:+.2f}"
        values["RRvsPublishedHigh" + suffix] = f"{hi:+.2f}"
    writecsv(RESULTS / "scheduling_published_comparison.csv", stronger)
    (OUT / "scheduling_values.tex").write_text(
        "".join("\\newcommand{\\" + k + "}{" + v + "}\n" for k, v in values.items())
    )
    model_diagram()
    print(
        "Generated all scheduling conditions with paired intervals, query effects and model diagram."
    )


def model_diagram():
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.set_xlim(-0.1, 10.5)
    ax.set_ylim(-0.3, 4.5)
    ax.axis("off")
    labels = ["List", "v1", "v2", "v3", "v4", "Next list"]
    for y, title, cuts, explanation in (
        (
            3.25,
            "Flat replay",
            [],
            "Future trace is known; the outstanding limit controls submission.",
        ),
        (
            1.95,
            "Expansion phases",
            [0, 4],
            "Finish the list, then all its candidate vectors, then the next list.",
        ),
        (
            0.65,
            "Batches of two",
            [0, 2, 4],
            "Finish each candidate batch before offering the next one.",
        ),
    ):
        ax.text(0, y + 0.26, title, fontsize=11, fontweight="bold", va="center")
        for i, label in enumerate(labels):
            x = 2.75 + i * 1.18
            ax.add_patch(
                FancyBboxPatch(
                    (x, y),
                    1.02,
                    0.55,
                    boxstyle="round,pad=0.03",
                    facecolor="#eaf3f4" if label.startswith("v") else "#eeeae7",
                    edgecolor="#006c80",
                )
            )
            ax.text(x + 0.51, y + 0.275, label, ha="center", va="center", fontsize=10)
            if i in cuts:
                ax.plot([x + 1.1] * 2, [y - 0.06, y + 0.61], color="#bd5938", lw=2.5)
        ax.text(2.75, y - 0.28, explanation, fontsize=9)
    ax.text(
        2.75,
        -0.1,
        "Orange divider = wait for every earlier group read to complete",
        fontsize=9,
        color="#994326",
    )
    savefig("replay_models.pdf")
