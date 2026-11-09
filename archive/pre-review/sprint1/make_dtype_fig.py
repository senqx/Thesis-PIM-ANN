#!/usr/bin/env python3
# Capstone figure: real SIFT1M inter-vector row-hit at float32 vs int8, four
# layouts. (a) byte-budget law holds on real data (all rise with int8); (b) the
# bigger budget does NOT rescue query-aware: BFS stays best, lead GROWS.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "legend.fontsize": 7.6, "xtick.labelsize": 8.5, "ytick.labelsize": 8,
    "font.family": "serif", "axes.grid": True, "grid.alpha": 0.25,
    "axes.axisbelow": True,
})
COL = {"random": "#9A3B2E", "community": "#B08A00",
       "bfs": "#1F6F8B", "query_aware": "#2E7D46"}
LABEL = {"random": "Random", "community": "Community",
         "query_aware": "Query-aware (proposed)", "bfs": "BFS (traversal order)"}
layouts = ["random", "community", "query_aware", "bfs"]

data = {
    "float32": {"random": 0.004, "community": 0.129,
                "query_aware": 1.005, "bfs": 1.365},
    "int8":    {"random": 0.020, "community": 0.609,
                "query_aware": 1.151, "bfs": 2.103},
}
dtypes = ["float32", "int8"]
dtype_label = {"float32": "float32\n(4 vectors / row)",
               "int8": "int8 / PQ\n(16 vectors / row)"}

fig, ax = plt.subplots(figsize=(4.4, 3.0))
x = np.arange(len(dtypes)); w = 0.2
for i, lay in enumerate(layouts):
    vals = [data[dt][lay] for dt in dtypes]
    bars = ax.bar(x + (i - 1.5) * w, vals, w, color=COL[lay],
                  label=LABEL[lay], edgecolor="white", linewidth=0.4)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.04, "%.2f" % v,
                ha="center", va="bottom", fontsize=6.6, color="#333")

# Clean "BFS lead" brackets above each group (no diagonal arrows, no overlap).
for xi, dt in zip(x, dtypes):
    q = data[dt]["query_aware"]; b = data[dt]["bfs"]
    x_q = xi + 0.5 * w; x_b = xi + 1.5 * w; y = b + 0.34
    ax.plot([x_q, x_q, x_b, x_b], [b + 0.20, y, y, b + 0.20],
            color="#444", lw=0.9)
    ax.text((x_q + x_b) / 2, y + 0.02, "BFS lead +%.2f" % (b - q),
            ha="center", va="bottom", fontsize=7, color="#444")

ax.set_xticks(x)
ax.set_xticklabels([dtype_label[dt] for dt in dtypes])
ax.set_ylabel("inter-vector row-hit rate (%)")
ax.set_title("Real SIFT1M: a bigger byte budget widens BFS's lead\n"
             "- it does not rescue the learned layout")
ax.set_ylim(0, 2.9)
ax.legend(loc="upper left", framealpha=0.95, ncol=1, handlelength=1.3,
          borderpad=0.5, labelspacing=0.35)
ax.margins(x=0.08)
fig.tight_layout()
fig.savefig("fig_dtype_byte_budget.pdf", bbox_inches="tight")
fig.savefig("fig_dtype_byte_budget.png", dpi=150, bbox_inches="tight")
print("wrote fig_dtype_byte_budget")
