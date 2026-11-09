#!/usr/bin/env python3
# Figures for the sprint-1 real-HNSW layout benchmark, from bench.csv.
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "font.family": "serif", "axes.grid": True, "grid.alpha": 0.3,
})
GREY = "#5A5A5A"
COL = {"random": "#9A3B2E", "community": "#B08A00",
       "bfs": "#1F6F8B", "query_aware": "#2E7D46"}
MARK = {"random": "o", "community": "D", "bfs": "s", "query_aware": "^"}
LABEL = {"random": "Random", "community": "Community (label-prop)",
         "bfs": "BFS", "query_aware": "Query-aware (proposed)"}

rows = list(csv.DictReader(open("bench.csv")))
efs = sorted({int(r["ef"]) for r in rows})
layouts = ["random", "community", "bfs", "query_aware"]

def series(layout, field):
    d = {int(r["ef"]): float(r[field]) for r in rows if r["layout"] == layout}
    return [d[e] for e in efs]

# ---- Figure 1: inter-vector row-hit vs efSearch (the headline) ------------
fig, ax = plt.subplots(figsize=(3.6, 2.6))
for lay in layouts:
    ax.plot(efs, series(lay, "interVec"), marker=MARK[lay], color=COL[lay],
            lw=1.7, ms=5, label=LABEL[lay])
ax.set_xscale("log", base=2)
ax.set_xticks(efs)
ax.set_xticklabels(efs)
ax.set_xlabel("efSearch (nodes explored per query)")
ax.set_ylabel("inter-vector row-hit (%)")
ax.set_title("Proposed layout's edge grows with search effort")
ax.legend(loc="upper left", framealpha=0.9)
fig.tight_layout()
fig.savefig("fig_bench_efsweep.pdf")
fig.savefig("fig_bench_efsweep.png", dpi=130)
plt.close(fig)
print("wrote fig_bench_efsweep")

# ---- Figure 2: honest vs misleading metric at ef=256 ----------------------
fig, ax = plt.subplots(figsize=(3.6, 2.6))
ef = 256
allb = [float(next(r["allBurst"] for r in rows
                   if r["layout"] == l and int(r["ef"]) == ef))
        for l in layouts]
inter = [float(next(r["interVec"] for r in rows
                    if r["layout"] == l and int(r["ef"]) == ef))
         for l in layouts]
x = range(len(layouts))
ax.bar([i - 0.2 for i in x], allb, 0.4, color=GREY, alpha=0.5,
       label="all-burst proxy (misleading)")
ax.bar([i + 0.2 for i in x], inter, 0.4,
       color=[COL[l] for l in layouts], label="inter-vector (honest)")
ax.set_xticks(list(x))
ax.set_xticklabels([LABEL[l].split(" (")[0] for l in layouts],
                   rotation=20, ha="right")
ax.set_ylabel("row-hit (%)")
ax.set_title("Why the aggregate proxy misleads (efSearch=256)")
ax.legend(loc="upper center", framealpha=0.9)
fig.tight_layout()
fig.savefig("fig_bench_metric.pdf")
fig.savefig("fig_bench_metric.png", dpi=130)
plt.close(fig)
print("wrote fig_bench_metric")
