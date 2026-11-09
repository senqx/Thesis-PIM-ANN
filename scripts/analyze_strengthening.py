#!/usr/bin/env python3
"""Derive robustness, command-mechanism and practical-effect evidence."""

import numpy as np
from analyze import (
    RESULTS,
    OUT,
    LAYOUTS,
    LABELS,
    raw,
    rows,
    writecsv,
    interval,
    table,
    savefig,
)
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def command_row(path):
    data = raw(path)
    counts = data["command_counts"]
    ctrl = data["stats"]["memory_system"]["controller"]
    if isinstance(ctrl, list):
        ctrl = ctrl[0]
    return dict(
        cycles=data["cycles"],
        row_hit_pct=data["row_hit_pct"],
        reads=data["checks"]["trace_reads"],
        activate=counts["ACT"],
        precharge=counts["PREpb"] + counts["PREab"],
        refresh=counts["REFab"] + counts["REFpb"],
        command_cycles=sum(counts.values()),
        no_command_cycles=data["cycles"] - sum(counts.values()),
        mean_read_latency=ctrl["avg_read_latency"],
    )


def generate():
    values = {}
    repetitions = []
    summaries = []
    conditions = ["inflight1", "cap4", "alternate_mapping"]
    names = {
        "inflight1": "Outstanding: 1",
        "cap4": "ClosedCAP, cap 4",
        "alternate_mapping": "Alternate mapper",
    }
    for condition in conditions:
        for width in [512, 128]:
            for layout in LAYOUTS:
                delta = []
                for seed in range(1, 11):
                    folder = (
                        RESULTS / "robustness/controllers" / condition / f"seed{seed}"
                    )
                    base = raw(folder / f"bfs_{width}.json")
                    item = raw(folder / f"{layout}_{width}.json")
                    change = 100 * (item["cycles"] / base["cycles"] - 1)
                    delta.append(change)
                    repetitions.append(
                        dict(
                            condition=condition,
                            vector_bytes=width,
                            layout=layout,
                            seed=seed,
                            cycles=item["cycles"],
                            delta_bfs_pct=change,
                            row_hit_pct=item["row_hit_pct"],
                        )
                    )
                mean, low, high = interval(delta)
                summaries.append(
                    dict(
                        condition=condition,
                        vector_bytes=width,
                        layout=layout,
                        n=10,
                        mean_delta_pct=mean,
                        ci_low=low,
                        ci_high=high,
                        min_delta_pct=min(delta),
                        max_delta_pct=max(delta),
                    )
                )
    writecsv(RESULTS / "robustness/controller_repetitions.csv", repetitions)
    writecsv(RESULTS / "robustness/controller_summary.csv", summaries)
    qa = [r for r in summaries if r["layout"] == "query_aware"]
    table(
        "robust_controller_table.tex",
        ["Setting", "Bytes", r"$\Delta$ QA/BFS (\%)", r"95\% interval"],
        [
            [
                names[r["condition"]],
                r["vector_bytes"],
                f"{r['mean_delta_pct']:+.2f}",
                f"[{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]",
            ]
            for r in qa
        ],
        columns="lrrr",
    )
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.2))
    for ax, width in zip(axes, [512, 128]):
        data = [r for r in qa if r["vector_bytes"] == width]
        for i, r in enumerate(data):
            points = [
                v["delta_bfs_pct"]
                for v in repetitions
                if v["condition"] == r["condition"]
                and v["vector_bytes"] == width
                and v["layout"] == "query_aware"
            ]
            ax.scatter(
                points,
                np.full(10, i) + np.linspace(-0.12, 0.12, 10),
                s=13,
                alpha=0.45,
                color="#006c80",
            )
            ax.errorbar(
                r["mean_delta_pct"],
                i,
                xerr=[
                    [r["mean_delta_pct"] - r["ci_low"]],
                    [r["ci_high"] - r["mean_delta_pct"]],
                ],
                fmt="D",
                capsize=4,
                color="#a04320",
            )
        ax.axvline(0, color="gray", lw=1)
        ax.set_yticks(range(3), [names[r["condition"]] for r in data])
        ax.set_title(f"{width} bytes per vector: ten matched query splits")
        ax.set_xlabel("Query-aware cycle difference relative to BFS (%)")
        ax.grid(axis="x", alpha=0.2)
    savefig("robust_controllers.pdf")
    graph_rows = []
    graph_raw = []
    for graph in ["reference", "index101", "index102", "order17"]:
        for width in [512, 128]:
            for layout in LAYOUTS:
                changes, recalls = [], []
                for seed in range(1, 4):
                    folder = (
                        RESULTS / f"sift/seed{seed}"
                        if graph == "reference"
                        else RESULTS / f"robustness/graphs/{graph}/seed{seed}"
                    )
                    baseline = raw(folder / f"timing/bfs_{width}.json")
                    item = raw(folder / f"timing/{layout}_{width}.json")
                    recall = 100 * float(rows(folder / "metadata.csv")[0]["recall"])
                    change = 100 * (item["cycles"] / baseline["cycles"] - 1)
                    changes.append(change)
                    recalls.append(recall)
                    graph_raw.append(
                        dict(
                            graph=graph,
                            vector_bytes=width,
                            layout=layout,
                            seed=seed,
                            cycles=item["cycles"],
                            delta_bfs_pct=change,
                            recall_pct=recall,
                        )
                    )
                graph_rows.append(
                    dict(
                        graph=graph,
                        vector_bytes=width,
                        layout=layout,
                        n=3,
                        mean_delta_pct=np.mean(changes),
                        min_delta_pct=min(changes),
                        max_delta_pct=max(changes),
                        mean_recall_pct=np.mean(recalls),
                    )
                )
    writecsv(RESULTS / "robustness/graph_repetitions.csv", graph_raw)
    writecsv(RESULTS / "robustness/graph_summary.csv", graph_rows)
    paper_graph_rows = []
    for graph, title in [
        ("reference", "Seed 100, corpus order"),
        ("index101", "Seed 101, corpus order"),
        ("index102", "Seed 102, corpus order"),
        ("order17", "Seed 100, shuffled order"),
    ]:
        row = [title]
        for width in [512, 128]:
            r = next(
                r
                for r in graph_rows
                if r["graph"] == graph
                and r["vector_bytes"] == width
                and r["layout"] == "query_aware"
            )
            row.append(
                f"{r['mean_delta_pct']:+.3f} [{r['min_delta_pct']:+.3f}, {r['max_delta_pct']:+.3f}]"
            )
        paper_graph_rows.append(row)
    table(
        "graph_paper_table.tex",
        ["Construction", "512 bytes (\\%)", "128 bytes (\\%)"],
        paper_graph_rows,
    )
    primary = rows(RESULTS / "paired_summary.csv")
    table(
        "paper_results_table.tex",
        ["Layout", "512 bytes (\\%)", "128 bytes (\\%)"],
        [
            [LABELS[l]]
            + [
                next(
                    f"{float(r['mean_delta_pct']):+.2f} [{float(r['ci_low']):+.2f}, {float(r['ci_high']):+.2f}]"
                    for r in primary
                    if r["layout"] == l and int(r["vector_bytes"]) == w
                )
                for w in [512, 128]
            ]
            for l in LAYOUTS
        ],
    )

    graph_names = {
        "reference": "Seed 100, corpus order",
        "index101": "Seed 101, corpus order",
        "index102": "Seed 102, corpus order",
        "order17": "Seed 100, shuffled order",
    }
    table(
        "graph_robustness_table.tex",
        ["Graph construction", "Bytes", r"Mean $\Delta$ (\%)", r"Observed range (\%)"],
        [
            [
                graph_names[r["graph"]],
                r["vector_bytes"],
                f"{r['mean_delta_pct']:+.3f}",
                f"[{r['min_delta_pct']:+.3f}, {r['max_delta_pct']:+.3f}]",
            ]
            for r in graph_rows
            if r["layout"] == "query_aware"
        ],
        columns="lrrr",
    )

    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.7), sharey=True)
    names = ["reference", "index101", "index102", "order17"]
    labels = ["Seed 100", "Seed 101", "Seed 102", "Seed 100, shuffled"]
    for ax, width in zip(axes, [512, 128]):
        for i, graph in enumerate(names):
            points = [
                r["delta_bfs_pct"]
                for r in graph_raw
                if r["graph"] == graph
                and r["vector_bytes"] == width
                and r["layout"] == "query_aware"
            ]
            ax.plot([min(points), max(points)], [i, i], color="#7c8992", lw=1.4)
            ax.scatter(
                points,
                np.full(3, i) + np.linspace(-0.09, 0.09, 3),
                s=22,
                color="#006c80",
            )
            ax.scatter(np.mean(points), i, marker="D", s=30, color="#a04320", zorder=4)
        ax.axvline(0, color="gray", lw=1)
        ax.set_yticks(range(4), labels)
        ax.set_title(f"{width} bytes / vector")
        ax.set_xlabel("Cycle difference vs BFS (%)")
        ax.grid(axis="x", alpha=0.18)
    savefig("graph_robustness.pdf")
    for graph, macro in [
        ("reference", "GraphRefCompact"),
        ("index101", "GraphOneCompact"),
        ("index102", "GraphTwoCompact"),
        ("order17", "GraphShuffleCompact"),
    ]:
        item = next(
            r
            for r in graph_rows
            if r["graph"] == graph
            and r["vector_bytes"] == 128
            and r["layout"] == "query_aware"
        )
        values[macro] = f"{item['mean_delta_pct']:+.3f}"
    values["GraphRecallMin"] = f"{min(r['recall_pct'] for r in graph_raw):.2f}"
    values["GraphRecallMax"] = f"{max(r['recall_pct'] for r in graph_raw):.2f}"
    micro = []
    for inflight in [64, 1]:
        for layout in ["sequential", "random"]:
            path = RESULTS / f"mechanism/micro/{layout}_inflight{inflight}.json"
            entry = dict(layout=layout, inflight=inflight, **command_row(path))
            # Diversity is a property of the offered order, not a measured queue occupancy.
            # The retained summary was calculated during the campaign from the trace.
            entry["mean_offered_banks_64"] = raw(
                RESULTS / "mechanism/offered_banks.json"
            )[layout]["mean_distinct_banks"]
            micro.append(entry)
    writecsv(RESULTS / "mechanism/micro_summary.csv", micro)
    table(
        "mechanism_micro_table.tex",
        ["Limit", "Order", "Cycles", "ACT", "PRE", "No command"],
        [
            [
                r["inflight"],
                "Sequential" if r["layout"] == "sequential" else "Permuted",
                r["cycles"],
                r["activate"],
                r["precharge"],
                r["no_command_cycles"],
            ]
            for r in micro
        ],
        columns="rlrrrr",
    )
    values["SequentialBanks"] = f"{micro[0]['mean_offered_banks_64']:.2f}"
    values["RandomBanks"] = f"{micro[1]['mean_offered_banks_64']:.2f}"
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True, sharey=True)
    for ax, layout in zip(axes, ["sequential", "random"]):
        path = RESULTS / f"mechanism/micro/{layout}_inflight64.command_trace.csv.ch0"
        commands = [
            r for r in rows(path) if r["command"] == "RD" and int(r["clock"]) <= 256
        ]
        banks = [
            int(r["PseudoChannel"])
            + 2 * int(r["Sid"])
            + 4 * int(r["BankGroup"])
            + 16 * int(r["Bank"])
            for r in commands
        ]
        ax.scatter([int(r["clock"]) for r in commands], banks, s=15, color="#006c80")
        ax.set_title("Sequential input" if layout == "sequential" else "Permuted input")
        ax.set_ylabel("Bank instance ID")
        ax.set_ylim(-2, 65)
        ax.grid(alpha=0.18)
    axes[-1].set_xlabel(
        "Controller cycle (first 256 cycles, 64 outstanding reads allowed)"
    )
    savefig("command_timeline.pdf")
    sift = []
    for inflight in [64, 1]:
        for component in ["mixed", "vectors", "adjacency"]:
            for layout in ["bfs", "query_aware"]:
                sift.append(
                    dict(
                        inflight=inflight,
                        component=component,
                        layout=layout,
                        **command_row(
                            RESULTS
                            / f"mechanism/sift/{layout}_{component}_inflight{inflight}.json"
                        ),
                    )
                )
    writecsv(RESULTS / "mechanism/sift_summary.csv", sift)
    comparison = []
    for inflight in [64, 1]:
        for component in ["mixed", "vectors", "adjacency"]:
            b, q = [
                r
                for r in sift
                if r["inflight"] == inflight and r["component"] == component
            ]
            comparison.append(
                dict(
                    inflight=inflight,
                    component=component,
                    delta_bfs_pct=100 * (q["cycles"] / b["cycles"] - 1),
                    delta_cycles=q["cycles"] - b["cycles"],
                    delta_activate=q["activate"] - b["activate"],
                    delta_commands=q["command_cycles"] - b["command_cycles"],
                    delta_no_command=q["no_command_cycles"] - b["no_command_cycles"],
                )
            )
    writecsv(RESULTS / "mechanism/sift_differences.csv", comparison)
    table(
        "mechanism_sift_table.tex",
        [
            "Limit",
            "Stream",
            r"$\Delta$ cycles",
            r"$\Delta$ ACT",
            r"$\Delta$ commands",
            r"$\Delta$ no cmd.",
        ],
        [
            [
                r["inflight"],
                r["component"].capitalize(),
                f"{r['delta_cycles']:+d}",
                f"{r['delta_activate']:+d}",
                f"{r['delta_commands']:+d}",
                f"{r['delta_no_command']:+d}",
            ]
            for r in comparison
        ],
        columns="rlrrrr",
    )
    main = rows(RESULTS / "paired_summary.csv")
    b = next(r for r in main if r["vector_bytes"] == "512" and r["layout"] == "bfs")
    q = next(
        r for r in main if r["vector_bytes"] == "512" and r["layout"] == "query_aware"
    )
    saving = (float(b["mean_cycles"]) - float(q["mean_cycles"])) / 200
    values["SavedCyclesPerQuery"] = f"{saving:.1f}"
    mixed = comparison[0]
    values["MixedDeltaCycles"] = f"{mixed['delta_cycles']:,}"
    values["MixedSavedCommands"] = f"{-mixed['delta_commands']:,}"
    values["MixedExtraNoCommand"] = f"{mixed['delta_no_command']:,}"
    values["MixedSavedACT"] = f"{-mixed['delta_activate']:,}"
    offered = raw(RESULTS / "mechanism/offered_banks.json")
    values["BfsOfferedBanks"] = f"{offered['bfs']['mean_distinct_banks']:.2f}"
    values["QAOfferedBanks"] = f"{offered['query_aware']['mean_distinct_banks']:.2f}"
    traffic = []
    for width in [512, 128]:
        for seed in range(1, 11):
            meta = rows(RESULTS / f"sift/seed{seed}/metadata.csv")[0]
            count = raw(RESULTS / f"sift/seed{seed}/timing/bfs_{width}.json")["checks"][
                "trace_reads"
            ]
            vectors = int(meta["vector_reads"])
            chunks = width // 32
            traffic.append(
                dict(
                    vector_bytes=width,
                    seed=seed,
                    vector_records=vectors,
                    vector_transactions=vectors * chunks,
                    adjacency_transactions=count - vectors * chunks,
                    vector_traffic_pct=100 * vectors * chunks / count,
                    within_vector_followup_pct=100 * vectors * (chunks - 1) / count,
                )
            )
    writecsv(RESULTS / "mechanism/traffic_summary.csv", traffic)
    table(
        "traffic_table.tex",
        [
            "Vector bytes",
            "Reads/vector",
            "Vector traffic (\\%)",
            "Within-vector follow-ups (\\%)",
        ],
        [
            [
                w,
                w // 32,
                f"{np.mean([r['vector_traffic_pct'] for r in traffic if r['vector_bytes'] == w]):.2f}",
                f"{np.mean([r['within_vector_followup_pct'] for r in traffic if r['vector_bytes'] == w]):.2f}",
            ]
            for w in [512, 128]
        ],
        columns="rrrr",
    )

    values["MappingMiB"] = f"{16 * 100000 / 1024**2:.2f}"
    (OUT / "strengthening_values.tex").write_text(
        "".join("\\newcommand{\\" + k + "}{" + v + "}\n" for k, v in values.items())
    )
    draw_pipeline()
    draw_layout_example()
    return values


def draw_pipeline():
    # Conceptual diagram: explicitly illustrative values, not another measured run.
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.set(xlim=(0, 9), ylim=(0, 3.6))
    ax.axis("off")
    boxes = [
        (
            0.1,
            2,
            "1. Search discovers nodes",
            "Read vector 17; expand list 17;\nthen read candidate vectors.",
        ),
        (
            4.65,
            2,
            "2. Layout assigns slots",
            "Example: node 17 → slot 2.\nAt 512 B: address = base + 1,024.",
        ),
        (
            0.1,
            0.15,
            "3. Emit memory requests",
            "One 512-byte vector → 16 reads\nof 32 bytes each, plus list reads.",
        ),
        (
            4.65,
            0.15,
            "4. Controller services reads",
            "Banks and rows + timing rules\n→ completed cycles and row hits.",
        ),
    ]
    for x, y, title, detail in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                4.2,
                1.4,
                boxstyle="round,pad=.07",
                facecolor="#eef5f6",
                edgecolor="#006c80",
            )
        )
        ax.text(x + 0.15, y + 1.06, title, fontsize=11.5, weight="bold", va="center")
        ax.text(x + 0.15, y + 0.52, detail, fontsize=10.5, va="center", linespacing=1.5)
    for start, end in [
        ((4.32, 2.7), (4.55, 2.7)),
        ((6.7, 1.91), (2.2, 1.68)),
        ((4.32, 0.75), (4.55, 0.75)),
    ]:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle="->", color="#444", lw=1.6),
        )
    savefig("study_pipeline.pdf")


def draw_layout_example():
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.set(xlim=(-1.7, 8.2), ylim=(-0.35, 2.65))
    ax.axis("off")
    for y, label, nodes in [
        (1.35, "Layout A", [4, 9, 17, 6, 29, 8, 3, 12]),
        (0.05, "Layout B", [4, 9, 17, 29, 6, 8, 3, 12]),
    ]:
        ax.text(
            -0.2, y + 0.42, label, ha="right", va="center", fontsize=11.5, weight="bold"
        )
        for slot, node in enumerate(nodes):
            color = "#006c80" if node in [17, 29] else "#edf1f3"
            ax.add_patch(
                FancyBboxPatch(
                    (slot + 0.04, y),
                    0.90,
                    0.82,
                    boxstyle="round,pad=.02",
                    facecolor=color,
                    edgecolor="white",
                )
            )
            ax.text(
                slot + 0.49,
                y + 0.42,
                str(node),
                ha="center",
                va="center",
                fontsize=12,
                color="white" if node in [17, 29] else "#243542",
                weight="bold",
            )
        for block in range(4):
            left = 2 * block
            ax.plot(
                [left + 0.02, left + 0.02, left + 1.97, left + 1.97],
                [y + 0.87, y + 0.97, y + 0.97, y + 0.87],
                color="#536974",
                lw=1,
            )
            if y > 1:
                ax.text(left + 1, y + 1.05, "1 KiB block", ha="center", fontsize=10.5)
    ax.text(
        4,
        -0.27,
        "Numbers are node IDs; highlighted vectors 17 and 29 are needed together.",
        ha="center",
        fontsize=10.5,
    )
    savefig("layout_example.pdf")


if __name__ == "__main__":
    from check_results import check

    check()
    generate()
