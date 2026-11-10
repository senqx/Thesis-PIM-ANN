"""Evaluate frozen training choices using their existing held-out request streams."""

from collections import Counter

from analyze import OUT, RESULTS, interval, raw, rows, savefig, table, writecsv
from analyze_scheduling import LABELS, TEX_KEYS
from profiled_fetch import CONFIGURATIONS, PROFILE_QUERIES, choose_order
from scheduling import ORDERS
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np


def generate():
    timing = rows(RESULTS / "scheduling_measurements.csv")
    lookup = {
        (int(r["seed"]), r["condition"], int(r["vector_bytes"]), r["order"]): r
        for r in timing
    }
    query_effects = {
        (int(r["seed"]), r["condition"], int(r["vector_bytes"]), r["order"]): r
        for r in rows(RESULTS / "scheduling_pairs.csv")
    }
    earlier = rows(RESULTS / "followup_measurements.csv")
    published = {
        (int(r["seed"]), int(r["vector_bytes"]), r["layout"]): r
        for r in earlier
        if r["graph"] == "reference" and r["mode"] == "bounded"
    }
    selected, comparisons = [], []
    for seed in range(1, 11):
        folder = RESULTS / f"calibration/seed{seed}"
        choices = raw(folder / "selection.json")
        for condition in CONFIGURATIONS:
            for width in (512, 128):
                choice = choices[f"{condition}/{width}"]
                # The choice is determined exclusively by calibration costs.
                order = choose_order(choice["training_cycles"])
                assert order == choice["selected_order"]
                result = lookup[seed, condition, width, order]
                base = lookup[seed, condition, width, "bounded"]
                cycle = float(result["cycles"])
                query_effect = (
                    dict(queries_slower_pct=0, p95_service_delta_pct=0)
                    if order == "bounded"
                    else query_effects[seed, condition, width, order]
                )
                oracle = min(
                    float(lookup[seed, condition, width, o]["cycles"]) for o in ORDERS
                )
                selected.append(
                    dict(
                        seed=seed,
                        condition=condition,
                        vector_bytes=width,
                        selected_order=order,
                        calibration_queries=PROFILE_QUERIES,
                        calibration_total_cycles=sum(
                            choice["training_cycles"].values()
                        ),
                        calibration_selected_cycles=choice["training_cycles"][order],
                        heldout_cycles=int(cycle),
                        original_cycles_per_query=float(
                            base["mean_original_query_cycles"]
                        ),
                        selected_cycles_per_query=float(
                            result["mean_original_query_cycles"]
                        ),
                        delta_vs_original_pct=100 * (cycle / float(base["cycles"]) - 1),
                        saved_cycles_per_query=float(base["mean_original_query_cycles"])
                        - float(result["mean_original_query_cycles"]),
                        oracle_regret_pct=100 * (cycle / oracle - 1),
                        queries_slower_pct=float(query_effect["queries_slower_pct"]),
                        p95_service_delta_pct=float(
                            query_effect["p95_service_delta_pct"]
                        ),
                    )
                )
                targets = {
                    o: float(lookup[seed, condition, width, o]["cycles"])
                    for o in ORDERS
                }
                targets["oracle"] = oracle
                if condition == "default":
                    targets.update(
                        {
                            layout: float(published[seed, width, layout]["cycles"])
                            for layout in ("rcm", "gorder", "porder")
                        }
                    )
                for comparator, cost in targets.items():
                    comparisons.append(
                        dict(
                            seed=seed,
                            condition=condition,
                            vector_bytes=width,
                            selected_order=order,
                            comparator=comparator,
                            delta_pct=100 * (cycle / cost - 1),
                        )
                    )
    writecsv(RESULTS / "profiled_fetch_selections.csv", selected)
    writecsv(RESULTS / "profiled_fetch_pairs.csv", comparisons)
    summary = []
    for c in CONFIGURATIONS:
        for w in (512, 128):
            subset = [
                r for r in selected if (r["condition"], r["vector_bytes"]) == (c, w)
            ]
            counts = Counter(r["selected_order"] for r in subset)
            for comparator in ("bounded", "sorted", "roundrobin", "oracle") + (
                ("rcm", "gorder", "porder") if c == "default" else ()
            ):
                pairs = [
                    r["delta_pct"]
                    for r in comparisons
                    if (r["condition"], r["vector_bytes"], r["comparator"])
                    == (c, w, comparator)
                ]
                mean, low, high = interval(pairs)
                summary.append(
                    dict(
                        condition=c,
                        vector_bytes=w,
                        comparator=comparator,
                        n=len(pairs),
                        mean_delta_pct=mean,
                        ci_low=low,
                        ci_high=high,
                        min_delta_pct=min(pairs),
                        max_delta_pct=max(pairs),
                        chosen_original=counts["bounded"],
                        chosen_sorted=counts["sorted"],
                        chosen_roundrobin=counts["roundrobin"],
                        mean_calibration_cycles=np.mean(
                            [r["calibration_total_cycles"] for r in subset]
                        ),
                        mean_saved_cycles_per_query=np.mean(
                            [r["saved_cycles_per_query"] for r in subset]
                        ),
                    )
                )
    writecsv(RESULTS / "profiled_fetch_summary.csv", summary)
    primary = [r for r in summary if r["comparator"] == "bounded"]
    oracle = {
        (r["condition"], r["vector_bytes"]): r
        for r in summary
        if r["comparator"] == "oracle"
    }

    def effect(r):
        return f"{r['mean_delta_pct']:+.2f} [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]"

    table(
        "profiled_fetch_table.tex",
        [
            "Condition",
            "Bytes",
            "Choices O/S/R",
            "vs original (\\%)",
            "Oracle gap (\\%)",
        ],
        [
            [
                LABELS[r["condition"]],
                r["vector_bytes"],
                f"{r['chosen_original']}/{r['chosen_sorted']}/{r['chosen_roundrobin']}",
                effect(r),
                f"{oracle[r['condition'], r['vector_bytes']]['mean_delta_pct']:.3f}",
            ]
            for r in primary
        ],
    )
    index = {(r["condition"], r["vector_bytes"]): r for r in primary}
    table(
        "profiled_fetch_paper_table.tex",
        ["Condition", "512 bytes", "128 bytes"],
        [
            [
                LABELS[c]
                .replace("Candidate batches of", "Batch")
                .replace("Alternative address mapping", "Alt. mapper")
                .replace("Default (64 outstanding)", "Default 64"),
                effect(index[c, 512]),
                effect(index[c, 128]),
            ]
            for c in CONFIGURATIONS
        ],
    )
    names = dict(
        bounded="Original",
        sorted="Sorted",
        roundrobin="Round-robin",
        oracle="Oracle",
        rcm="RCM",
        gorder="Gorder",
        porder="Porder",
    )
    table(
        "profiled_fetch_baselines.tex",
        ["Bytes", "Comparator", "Profiled path difference (\\%)"],
        [
            [r["vector_bytes"], names[r["comparator"]], effect(r)]
            for r in summary
            if r["condition"] == "default"
        ],
    )
    table(
        "profiled_fetch_costs.tex",
        ["Condition", "Bytes", "Calibration cycles", "Saved cycles/query"],
        [
            [
                LABELS[r["condition"]],
                r["vector_bytes"],
                f"{r['mean_calibration_cycles']:,.0f}",
                f"{r['mean_saved_cycles_per_query']:+,.0f}",
            ]
            for r in primary
        ],
    )
    table(
        "profiled_fetch_service_table.tex",
        ["Condition", "Bytes", "Original cycles/query", "Selected cycles/query"],
        [
            [
                LABELS[c],
                w,
                f"{np.mean([r['original_cycles_per_query'] for r in selected if (r['condition'], r['vector_bytes']) == (c, w)]):,.0f}",
                f"{np.mean([r['selected_cycles_per_query'] for r in selected if (r['condition'], r['vector_bytes']) == (c, w)]):,.0f}",
            ]
            for c in CONFIGURATIONS
            for w in (512, 128)
        ],
    )
    table(
        "profiled_fetch_query_table.tex",
        ["Condition", "Bytes", "Slower queries (\\%)", "p95 change (\\%)"],
        [
            [
                LABELS[c],
                w,
                f"{min(r['queries_slower_pct'] for r in group):.1f}--{max(r['queries_slower_pct'] for r in group):.1f}",
                f"{min(r['p95_service_delta_pct'] for r in group):+.2f} to {max(r['p95_service_delta_pct'] for r in group):+.2f}",
            ]
            for c in CONFIGURATIONS
            for w in (512, 128)
            for group in [
                [r for r in selected if (r["condition"], r["vector_bytes"]) == (c, w)]
            ]
        ],
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.3), sharex=True, sharey=True)
    for ax, w in zip(axes, (512, 128)):
        for y, c in enumerate(CONFIGURATIONS):
            r = index[c, w]
            pts = [
                p["delta_vs_original_pct"]
                for p in selected
                if (p["condition"], p["vector_bytes"]) == (c, w)
            ]
            ax.scatter(pts, [y] * len(pts), s=13, color="#006c80", alpha=0.35)
            ax.errorbar(
                r["mean_delta_pct"],
                y,
                xerr=[
                    [r["mean_delta_pct"] - r["ci_low"]],
                    [r["ci_high"] - r["mean_delta_pct"]],
                ],
                fmt="D",
                ms=4,
                color="#bd5938",
                capsize=3,
            )
        ax.set_yticks(range(len(CONFIGURATIONS)), list(LABELS.values()))
        ax.axvline(0, color="gray", lw=1)
        ax.grid(axis="x", alpha=0.2)
        ax.set_title("512 bytes (float32)" if w == 512 else "128 bytes (hypothetical)")
    axes[0].invert_yaxis()
    fig.supxlabel("Profile-selected vs original-order service cycles (%)", fontsize=11)
    savefig("profiled_fetch.pdf")
    values = {
        "ProfileMaxMeanRegret": f"{max(r['mean_delta_pct'] for r in oracle.values()):.3f}",
        "ProfileMaxSplitRegret": f"{max(r['oracle_regret_pct'] for r in selected):.3f}",
        "ProfileWorstOriginal": f"{max(r['delta_vs_original_pct'] for r in selected):+.3f}",
        "ProfileOracleMatches": str(sum(r["oracle_regret_pct"] == 0 for r in selected)),
        "ProfileOriginalRegressions": str(
            sum(r["delta_vs_original_pct"] > 0 for r in selected)
        ),
        "ProfileOriginalChoices": str(
            sum(r["selected_order"] == "bounded" for r in selected)
        ),
        "ProfileSortedChoices": str(
            sum(r["selected_order"] == "sorted" for r in selected)
        ),
        "ProfileRRChoices": str(
            sum(r["selected_order"] == "roundrobin" for r in selected)
        ),
    }
    for w, suffix in ((512, "Float"), (128, "Compact")):
        for c in CONFIGURATIONS:
            key = TEX_KEYS[c]
            r = index[c, w]
            values["Profile" + key + suffix] = f"{r['mean_delta_pct']:+.2f}"
        for layout in ("rcm", "gorder", "porder"):
            r = next(
                r
                for r in summary
                if (r["condition"], r["vector_bytes"], r["comparator"])
                == ("default", w, layout)
            )
            values["ProfileVs" + layout.capitalize() + suffix] = effect(r)
    (OUT / "profiled_fetch_values.tex").write_text(
        "".join("\\newcommand{\\" + k + "}{" + v + "}\n" for k, v in values.items())
    )
    print(
        "Evaluated 140 frozen training choices on existing held-out replays; all fixed-order and matching published baselines retained."
    )
    execution_diagram()


def execution_diagram():
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    def box(x, y, width, label, colour="#eef0f2", edge="#687682"):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                0.85,
                boxstyle="round,pad=0.04",
                facecolor=colour,
                edgecolor=edge,
                linewidth=1.3,
            )
        )
        ax.text(x + width / 2, y + 0.425, label, ha="center", va="center", fontsize=10)

    def arrow(start, end, dashed=False):
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(
                arrowstyle="->",
                color="#687682",
                lw=1.4,
                linestyle="--" if dashed else "-",
            ),
        )

    ax.text(
        0.2, 4.7, "Once per configuration: training only", fontsize=12, weight="bold"
    )
    for x, label in (
        (0.2, "50 training queries"),
        (3.55, "Time all three orders"),
        (6.9, "Store minimum-cost order"),
    ):
        box(x, 3.45, 2.85, label, "#f9eee7", "#bd5938")
    arrow((3.05, 3.875), (3.5, 3.875))
    arrow((6.4, 3.875), (6.85, 3.875))
    ax.text(
        0.2,
        2.9,
        "For each expansion: proposed execution boundary",
        fontsize=12,
        weight="bold",
    )
    for x, label in (
        (0.2, "HNSW control:\nrequest neighbour list"),
        (2.7, "Select candidates;\nresolve addresses"),
        (7.7, "Distance compute;\nordered state updates"),
    ):
        box(x, 1.4, 2.05, label)
    box(5.2, 1.4, 2.05, "Fetch vector batch\nusing stored order", "#def1f2", "#006c80")
    for x in (2.25, 4.75, 7.25):
        arrow((x, 1.825), (x + 0.4, 1.825))
    arrow((8.325, 3.4), (6.23, 2.3), dashed=True)
    ax.text(
        0.2,
        0.72,
        "Teal: reorderable vector service. Replay also includes neighbour-list DRAM reads.",
        fontsize=10,
    )
    ax.text(
        0.2,
        0.22,
        "Control, compute and integration costs are unmeasured; search order stays fixed.",
        fontsize=10,
    )
    savefig("profiled_fetch_execution.pdf")
