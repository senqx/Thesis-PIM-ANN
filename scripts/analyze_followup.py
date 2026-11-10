"""Describe all fixed follow-up comparisons without selecting winning methods."""

from analyze import OUT, RESULTS, interval, raw, rows, savefig, table, writecsv
from followup import LAYOUTS, PUBLISHED, cases, modes, original_directory
from followup_validation import compressed_rows, original_query_rows
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

NAMES = dict(
    identity="Identity",
    bfs="BFS",
    query_aware="Query-aware",
    rcm="RCM",
    gorder="Gorder",
    porder="Porder",
)
GRAPHS = dict(
    reference="Reference",
    index101="Seed 101",
    index102="Seed 102",
    order17="Shuffled 17",
)


def effect(a, b):
    return 100 * (a / b - 1)


def ci_text(values):
    m, lo, hi = interval(values)
    return f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]"


def generate():
    from analyze_strengthening import command_row

    diagnostic = []
    offered = raw(RESULTS / "followup/mechanism/offered_banks.json")
    for width in (512, 128):
        for mode in ("bounded", "roundrobin"):
            name = f"{mode}_{width}"
            diagnostic.append(
                dict(
                    vector_bytes=width,
                    mode=mode,
                    **command_row(RESULTS / f"followup/mechanism/{name}.json"),
                    mean_offered_banks=offered[name]["mean_distinct_banks"],
                )
            )
    writecsv(RESULTS / "followup_mechanism_summary.csv", diagnostic)
    table(
        "followup_mechanism_table.tex",
        ["Bytes", "Order", "Cycles", "ACT", "PRE", "No command", "Banks"],
        [
            [
                r["vector_bytes"],
                "Original" if r["mode"] == "bounded" else "Round-robin",
                r["cycles"],
                r["activate"],
                r["precharge"],
                r["no_command_cycles"],
                f"{r['mean_offered_banks']:.2f}",
            ]
            for r in diagnostic
        ],
    )
    measurements, phase_stats, costs = [], [], []
    lookup = {}
    query_cycles = {}
    for graph, seed in cases():
        folder = RESULTS / f"followup/{graph}/seed{seed}"
        phases = compressed_rows(folder / "phases.csv.gz")
        vector_phases = [int(p["vector_records"]) for p in phases if p["kind"] == "V"]
        phase_stats.append(
            dict(
                graph=graph,
                seed=seed,
                phases=len(phases),
                queries=200,
                mean_phases_per_query=len(phases) / 200,
                mean_vectors_per_vector_phase=np.mean(vector_phases),
                single_vector_phase_pct=100
                * sum(n == 1 for n in vector_phases)
                / len(vector_phases),
            )
        )
        for r in rows(folder / "layout_costs.csv"):
            costs.append(
                dict(
                    graph=graph,
                    seed=seed,
                    layout=r["layout"],
                    layout_seconds=float(r["layout_seconds"]),
                )
            )
        for width in (512, 128):
            for layout in LAYOUTS:
                for mode in dict.fromkeys(("flat",) + modes(layout)):
                    path = (
                        original_directory(graph, seed)
                        / f"timing/{layout}_{width}.json"
                        if mode == "flat" and layout not in PUBLISHED
                        else folder / f"{mode}/{layout}_{width}.json"
                    )
                    j = raw(path)
                    query = (
                        original_query_rows(path, phases)
                        if path.parent.name != "timing"
                        else rows(path.with_suffix(".queries.csv"))
                    )
                    durations = np.array([int(q["cycles"]) for q in query])
                    r = dict(
                        graph=graph,
                        seed=seed,
                        vector_bytes=width,
                        layout=layout,
                        mode=mode,
                        cycles=j["cycles"],
                        mean_original_query_cycles=np.mean(durations),
                        p95_original_query_cycles=np.percentile(durations, 95),
                        row_hit_pct=j["row_hit_pct"],
                        reads=j["checks"]["trace_reads"],
                    )
                    measurements.append(r)
                    lookup[graph, seed, width, layout, mode] = r
                    query_cycles[graph, seed, width, layout, mode] = durations
    comparisons = []
    for r in measurements:
        graph, seed, width, layout, mode = [
            r[k] for k in ("graph", "seed", "vector_bytes", "layout", "mode")
        ]
        baselines = (
            [("bfs", mode), ("identity", mode)]
            if mode in ("flat", "bounded")
            else [(layout, "bounded")]
        )
        if mode == "bounded":
            baselines.append((layout, "flat"))
        for baseline_layout, baseline_mode in baselines:
            b = lookup[graph, seed, width, baseline_layout, baseline_mode]
            actual_queries = query_cycles[graph, seed, width, layout, mode]
            baseline_queries = query_cycles[
                graph, seed, width, baseline_layout, baseline_mode
            ]
            query_delta = 100 * (actual_queries / baseline_queries - 1)
            comparisons.append(
                dict(
                    graph=graph,
                    seed=seed,
                    vector_bytes=width,
                    layout=layout,
                    mode=mode,
                    baseline_layout=baseline_layout,
                    baseline_mode=baseline_mode,
                    delta_pct=effect(r["cycles"], b["cycles"]),
                    saved_cycles_per_query=b["mean_original_query_cycles"]
                    - r["mean_original_query_cycles"],
                    queries_faster_pct=100 * np.mean(actual_queries < baseline_queries),
                    min_query_delta_pct=float(query_delta.min()),
                    max_query_delta_pct=float(query_delta.max()),
                    p95_service_delta_pct=effect(
                        r["p95_original_query_cycles"], b["p95_original_query_cycles"]
                    ),
                )
            )
    summaries = []
    groups = {}
    for r in comparisons:
        key = tuple(
            r[k]
            for k in (
                "graph",
                "vector_bytes",
                "layout",
                "mode",
                "baseline_layout",
                "baseline_mode",
            )
        )
        groups.setdefault(key, []).append(r)
    for key, data in groups.items():
        vals = [r["delta_pct"] for r in data]
        mean, low, high = interval(vals)
        summaries.append(
            dict(
                zip(
                    (
                        "graph",
                        "vector_bytes",
                        "layout",
                        "mode",
                        "baseline_layout",
                        "baseline_mode",
                    ),
                    key,
                ),
                n=len(data),
                mean_delta_pct=mean,
                ci_low=low if key[0] == "reference" else "",
                ci_high=high if key[0] == "reference" else "",
                min_delta_pct=min(vals),
                max_delta_pct=max(vals),
                mean_saved_cycles_per_query=np.mean(
                    [r["saved_cycles_per_query"] for r in data]
                ),
                mean_queries_faster_pct=np.mean(
                    [r["queries_faster_pct"] for r in data]
                ),
                min_queries_faster_pct=min(r["queries_faster_pct"] for r in data),
                max_queries_faster_pct=max(r["queries_faster_pct"] for r in data),
                min_p95_service_delta_pct=min(r["p95_service_delta_pct"] for r in data),
                max_p95_service_delta_pct=max(r["p95_service_delta_pct"] for r in data),
            )
        )
    writecsv(RESULTS / "followup_measurements.csv", measurements)
    writecsv(RESULTS / "followup_comparisons.csv", comparisons)
    writecsv(RESULTS / "followup_summary.csv", summaries)
    writecsv(RESULTS / "followup_phases.csv", phase_stats)
    writecsv(RESULTS / "followup_costs.csv", costs)

    def selected(
        width, layout, mode, baseline="bfs", baseline_mode=None, graph="reference"
    ):
        return [
            r
            for r in comparisons
            if (
                r["graph"],
                r["vector_bytes"],
                r["layout"],
                r["mode"],
                r["baseline_layout"],
                r["baseline_mode"],
            )
            == (graph, width, layout, mode, baseline, baseline_mode or mode)
        ]

    layout_table = []
    for width in (512, 128):
        for layout in LAYOUTS:
            layout_table.append(
                [width, NAMES[layout]]
                + [
                    ci_text(
                        [
                            r["delta_pct"]
                            for r in selected(width, layout, mode, baseline)
                        ]
                    )
                    for mode, baseline in (
                        ("flat", "bfs"),
                        ("bounded", "bfs"),
                        ("bounded", "identity"),
                    )
                ]
            )
    table(
        "followup_layout_table.tex",
        [
            "Bytes",
            "Layout",
            "Flat / BFS (\\%)",
            "Bounded / BFS (\\%)",
            "Bounded / identity (\\%)",
        ],
        layout_table,
    )
    table(
        "followup_paper_layout_table.tex",
        ["Bytes", "Layout", "$\\Delta$ vs. BFS (\\%)"],
        [
            [
                width,
                NAMES[layout],
                ci_text([r["delta_pct"] for r in selected(width, layout, "bounded")]),
            ]
            for width in (512, 128)
            for layout in PUBLISHED
        ],
    )
    table(
        "followup_paper_schedule_table.tex",
        ["Bytes", "Schedule", "$\\Delta$ vs. original (\\%)"],
        [
            [
                width,
                "Sorted" if mode == "sorted" else "Round-robin",
                ci_text(
                    [
                        r["delta_pct"]
                        for r in selected(width, "bfs", mode, "bfs", "bounded")
                    ]
                ),
            ]
            for width in (512, 128)
            for mode in ("sorted", "roundrobin")
        ],
    )
    schedule_table = []
    for width in (512, 128):
        for layout in ("bfs", "query_aware"):
            for mode in ("sorted", "roundrobin"):
                data = selected(width, layout, mode, layout, "bounded")
                schedule_table.append(
                    [
                        width,
                        NAMES[layout],
                        "Sorted" if mode == "sorted" else "Round-robin",
                        ci_text([r["delta_pct"] for r in data]),
                        f"{np.mean([r['saved_cycles_per_query'] for r in data]):+.1f}",
                    ]
                )
    table(
        "followup_schedule_table.tex",
        ["Bytes", "Layout", "Schedule", "$\\Delta$ cycles (\\%)", "Saved cycles/query"],
        schedule_table,
    )
    graph_table = []
    for graph in GRAPHS:
        for width in (512, 128):
            graph_table.append(
                [GRAPHS[graph], width]
                + [
                    f"{np.mean(v):+.2f} [{min(v):+.2f}, {max(v):+.2f}]"
                    for layout in ("query_aware", "rcm", "gorder", "porder")
                    for v in [
                        [
                            r["delta_pct"]
                            for r in selected(width, layout, "bounded", graph=graph)
                            if r["seed"] <= 3
                        ]
                    ]
                ]
            )
    table(
        "followup_graph_table.tex",
        ["Graph", "Bytes", "Query-aware", "RCM", "Gorder", "Porder"],
        graph_table,
    )
    schedule_graph = []
    for graph in GRAPHS:
        for width in (512, 128):
            schedule_graph.append(
                [GRAPHS[graph], width]
                + [
                    f"{np.mean(v):+.2f} [{min(v):+.2f}, {max(v):+.2f}]"
                    for layout in ("bfs", "query_aware")
                    for mode in ("sorted", "roundrobin")
                    for v in [
                        [
                            r["delta_pct"]
                            for r in selected(
                                width, layout, mode, layout, "bounded", graph
                            )
                            if r["seed"] <= 3
                        ]
                    ]
                ]
            )
    table(
        "followup_schedule_graph_table.tex",
        [
            "Graph",
            "Bytes",
            "BFS sorted",
            "BFS round-robin",
            "QA sorted",
            "QA round-robin",
        ],
        schedule_graph,
    )
    barriers = []
    for width in (512, 128):
        for layout in ("identity", "bfs", "query_aware"):
            vals = [
                np.mean(
                    [
                        r["mean_original_query_cycles"]
                        for r in measurements
                        if r["graph"] == "reference"
                        and r["vector_bytes"] == width
                        and r["layout"] == layout
                        and r["mode"] == mode
                    ]
                )
                for mode in ("flat", "bounded")
            ]
            barriers.append(
                [
                    width,
                    NAMES[layout],
                    *[f"{v:,.0f}" for v in vals],
                    ci_text(
                        [
                            r["delta_pct"]
                            for r in selected(width, layout, "bounded", layout, "flat")
                        ]
                    ),
                ]
            )
    table(
        "followup_barrier_table.tex",
        [
            "Bytes",
            "Layout",
            "Flat cycles/query",
            "Bounded cycles/query",
            "$\\Delta$ stream (\\%)",
        ],
        barriers,
    )
    table(
        "followup_cost_table.tex",
        ["Layout", "Mean (s)", "Observed range (s)"],
        [
            [NAMES[l], f"{np.mean(v):.3f}", f"{min(v):.3f}--{max(v):.3f}"]
            for l in PUBLISHED
            for v in [[r["layout_seconds"] for r in costs if r["layout"] == l]]
        ],
    )

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8), sharey=True)
    layouts = [l for l in LAYOUTS if l != "bfs"]
    for ax, width in zip(axes, (512, 128)):
        for mode, offset, color in (
            ("flat", -0.12, "#006c80"),
            ("bounded", 0.12, "#cf704b"),
        ):
            vals = np.array(
                [
                    interval([r["delta_pct"] for r in selected(width, l, mode)])
                    for l in layouts
                ]
            )
            ax.errorbar(
                vals[:, 0],
                np.arange(len(layouts)) + offset,
                xerr=[vals[:, 0] - vals[:, 1], vals[:, 2] - vals[:, 0]],
                fmt="o",
                capsize=3,
                label=mode.capitalize(),
                color=color,
            )
        ax.set_yticks(range(len(layouts)), [NAMES[l] for l in layouts])
        ax.axvline(0, color="gray", lw=1)
        ax.grid(axis="x", alpha=0.2)
        ax.set_title(f"{width} bytes / vector")
        ax.set_xlabel("Cycle difference vs matching BFS (%)")
        ax.legend(fontsize=9)
    savefig("followup_layouts.pdf")

    schedule_keys = [
        (layout, mode)
        for layout in ("bfs", "query_aware")
        for mode in ("sorted", "roundrobin")
    ]
    schedule_intervals = {
        width: np.array(
            [
                interval(
                    [
                        r["delta_pct"]
                        for r in selected(width, layout, mode, layout, "bounded")
                    ]
                )
                for layout, mode in schedule_keys
            ]
        )
        for width in (512, 128)
    }
    left = min(v[:, 1].min() for v in schedule_intervals.values()) - 1
    right = max(v[:, 2].max() for v in schedule_intervals.values()) + 1
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.6), sharey=True, sharex=True)
    for ax, width in zip(axes, (512, 128)):
        v = schedule_intervals[width]
        ax.errorbar(
            v[:, 0],
            np.arange(4),
            xerr=[v[:, 0] - v[:, 1], v[:, 2] - v[:, 0]],
            fmt="o",
            capsize=4,
            color="#006c80",
        )
        ax.set_yticks(
            range(4),
            [
                NAMES[layout]
                + " / "
                + ("sorted" if mode == "sorted" else "round-robin")
                for layout, mode in schedule_keys
            ],
        )
        ax.axvline(0, color="gray", lw=1)
        ax.set_xlim(left, right)
        ax.grid(axis="x", alpha=0.2)
        ax.set_title(f"{width} bytes / vector")
    fig.supxlabel("Cycle difference vs original order (%)", fontsize=11)
    savefig("followup_schedules.pdf")

    fig, ax = plt.subplots(figsize=(8, 3.3))
    ax.set_xlim(-0.1, 10.1)
    ax.set_ylim(0, 4)
    ax.axis("off")
    boxes = [
        (0, 2.35, 2.6, "Read list of node 17\nReveals candidates 4, 29"),
        (3.3, 2.35, 3.1, "Read vectors 4 and 29\nOnly this group's reads overlap"),
        (7.1, 2.35, 2.8, "Read next expansion\nAfter vector group completes"),
    ]
    for x, y, w, label in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                1.05,
                boxstyle="round,pad=0.03",
                facecolor="#eaf3f4",
                edgecolor="#006c80",
            )
        )
        ax.text(x + w / 2, y + 0.52, label, ha="center", va="center", fontsize=10)
    for start, end in ((2.65, 3.25), (6.45, 7.05)):
        ax.annotate(
            "",
            xy=(end, 2.9),
            xytext=(start, 2.9),
            arrowprops=dict(arrowstyle="->", color="#006c80", lw=1.5),
        )
        ax.text((start + end) / 2, 2.15, "drain", ha="center", fontsize=9)
    ax.text(
        0,
        1.6,
        "Example with two transactions per vector:",
        fontsize=11,
        fontweight="bold",
    )
    ax.text(
        0.15,
        0.9,
        "Original:  4a  4b  29a  29b\nRound-robin:  4a  29a  4b  29b",
        fontsize=10,
        linespacing=1.8,
    )
    ax.text(
        5.5,
        0.9,
        "Address sorting orders this same group.\nNo read moves across a drain boundary.",
        fontsize=10,
        linespacing=1.8,
    )
    savefig("followup_phases.pdf")
    values = {
        "MeanPhasesPerQuery": f"{np.mean([r['mean_phases_per_query'] for r in phase_stats if r['graph'] == 'reference']):.1f}",
        "MeanVectorsPerPhase": f"{np.mean([r['mean_vectors_per_vector_phase'] for r in phase_stats if r['graph'] == 'reference']):.2f}",
    }
    for width, suffix in ((512, "Float"), (128, "Compact")):
        before, after = [
            next(
                r
                for r in diagnostic
                if r["vector_bytes"] == width and r["mode"] == mode
            )
            for mode in ("bounded", "roundrobin")
        ]
        values["RRCmdExtra" + suffix] = (
            f"{after['command_cycles'] - before['command_cycles']:,}"
        )
        values["RRNoCmdDelta" + suffix] = (
            f"{abs(after['no_command_cycles'] - before['no_command_cycles']):,}"
        )
        values["RRStreamDelta" + suffix] = (
            f"{abs(after['cycles'] - before['cycles']):,}"
        )
        for r, tag in ((before, "Before"), (after, "After")):
            values["RRBanks" + tag + suffix] = f"{r['mean_offered_banks']:.2f}"
            values["RRHit" + tag + suffix] = f"{r['row_hit_pct']:.2f}"
        for layout, name in (
            ("query_aware", "QA"),
            ("porder", "Porder"),
            ("gorder", "Gorder"),
            ("rcm", "RCM"),
        ):
            values[name + "Bounded" + suffix] = ci_text(
                [r["delta_pct"] for r in selected(width, layout, "bounded")]
            )
        for mode, name in (("sorted", "Sorted"), ("roundrobin", "RoundRobin")):
            data = selected(width, "bfs", mode, "bfs", "bounded")
            values[name + "BFS" + suffix] = ci_text([r["delta_pct"] for r in data])
            values[name + "BFSMean" + suffix] = (
                f"{np.mean([r['delta_pct'] for r in data]):+.2f}"
            )
            values[name + "BFSSaved" + suffix] = (
                f"{np.mean([r['saved_cycles_per_query'] for r in data]):,.0f}"
            )
        rr = [
            r
            for r in comparisons
            if r["vector_bytes"] == width
            and r["layout"] == "bfs"
            and r["mode"] == "roundrobin"
        ]
        lower = min(r["queries_faster_pct"] for r in rr)
        upper = max(r["queries_faster_pct"] for r in rr)
        values["RRFasterQueries" + suffix] = (
            f"{lower:.1f}" if lower == upper else f"{lower:.1f}--{upper:.1f}"
        )
        values["RRPtailRange" + suffix] = (
            f"{min(r['p95_service_delta_pct'] for r in rr):+.2f} to {max(r['p95_service_delta_pct'] for r in rr):+.2f}"
        )
    (OUT / "followup_values.tex").write_text(
        "".join("\\newcommand{\\" + k + "}{" + v + "}\n" for k, v in values.items())
    )
    print(
        "Generated complete follow-up comparisons, including original-query aggregation."
    )
