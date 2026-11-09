#!/usr/bin/env python3
# The headline sprint-1 figure: the synthetic -> real reversal. On synthetic
# clustered data the proposed query-aware layout led; on real SIFT1M it does
# not, and BFS is best. Two panels, same four layouts, honest inter-vector
# row-hit metric. Data is hard-coded from the two cycle-accurate runs.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "font.family": "serif", "axes.grid": True, "grid.alpha": 0.3,
})

layouts = ["random", "community", "bfs", "query_aware"]
labels = ["Random", "Community", "BFS", "Query-aware\n(proposed)"]
COL = {"random": "#9A3B2E", "community": "#B08A00",
       "bfs": "#1F6F8B", "query_aware": "#2E7D46"}
cols = [COL[l] for l in layouts]

# inter-vector row-hit (%), the honest metric
synth = {"random": 0.052, "community": 0.821, "bfs": 5.062, "query_aware": 7.740}
real = {"random": 0.004, "community": 0.129, "bfs": 1.365, "query_aware": 1.005}

fig, (axS, axR) = plt.subplots(1, 2, figsize=(6.6, 2.7), sharey=False)

for ax, data, title in [
    (axS, synth, "Synthetic clustered data"),
    (axR, real, "Real SIFT1M (100k)"),
]:
    vals = [data[l] for l in layouts]
    bars = ax.bar(range(len(layouts)), vals, color=cols, width=0.65)
    best = int(np.argmax(vals))
    bars[best].set_edgecolor("black")
    bars[best].set_linewidth(1.6)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.02, f"{v:.2f}", ha="center",
                va="bottom", fontsize=7)
    ax.set_xticks(range(len(layouts)))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_title(title)
    ax.set_ylim(0, max(vals) * 1.18)

axS.set_ylabel("inter-vector row-hit (%)")
axS.annotate("proposed\nleads", xy=(3, 7.74), xytext=(1.4, 6.2),
             fontsize=7.5, color="#2E7D46",
             arrowprops=dict(arrowstyle="->", color="#2E7D46", lw=1))
axR.annotate("BFS leads;\nproposed does not\ntransfer", xy=(2, 1.365),
             xytext=(0.1, 0.95), fontsize=7.5, color="#1F6F8B",
             arrowprops=dict(arrowstyle="->", color="#1F6F8B", lw=1))

fig.suptitle("Query-aware layout's synthetic advantage does not survive real data",
             fontsize=9.5, y=1.02)
fig.tight_layout()
fig.savefig("fig_synth_vs_real.pdf", bbox_inches="tight")
fig.savefig("fig_synth_vs_real.png", dpi=130, bbox_inches="tight")
print("wrote fig_synth_vs_real")
