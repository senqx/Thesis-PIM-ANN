#!/usr/bin/env python3
# Capstone figure: real SIFT1M inter-vector row-hit at float32 vs int8, four
# layouts. Shows (a) the byte-budget law holds on real data - everything rises
# with int8's bigger budget - and (b) the bigger budget does NOT rescue the
# proposed query-aware layout: BFS stays best and its lead over query-aware
# GROWS. Data hard-coded from results_dtype_real.csv.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "font.family": "serif", "axes.grid": True, "grid.alpha": 0.3,
})
COL = {"random": "#9A3B2E", "community": "#B08A00",
       "bfs": "#1F6F8B", "query_aware": "#2E7D46"}
LABEL = {"random": "Random", "community": "Community",
         "bfs": "BFS", "query_aware": "Query-aware (proposed)"}
layouts = ["random", "community", "query_aware", "bfs"]

# inter-vector row-hit %, real SIFT1M
data = {
    "float32": {"random": 0.004, "community": 0.129,
                "query_aware": 1.005, "bfs": 1.365},
    "int8":    {"random": 0.020, "community": 0.609,
                "query_aware": 1.151, "bfs": 2.103},
}
dtypes = ["float32", "int8"]
dtype_label = {"float32": "float32\n(4 vec/row)", "int8": "int8\n(16 vec/row)"}

fig, ax = plt.subplots(figsize=(4.2, 2.9))
x = np.arange(len(dtypes))
w = 0.2
for i, lay in enumerate(layouts):
    vals = [data[dt][lay] for dt in dtypes]
    bars = ax.bar(x + (i - 1.5) * w, vals, w, color=COL[lay], label=LABEL[lay])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.03, f"{v:.2f}",
                ha="center", va="bottom", fontsize=6.5)

ax.set_xticks(x)
ax.set_xticklabels([dtype_label[dt] for dt in dtypes])
ax.set_ylabel("inter-vector row-hit (%)")
ax.set_title("Real SIFT1M: bigger budget widens BFS's lead,\n"
             "it does not rescue the learned layout")
ax.set_ylim(0, 2.5)
ax.legend(loc="upper left", framealpha=0.9, ncol=1)
# annotate the growing gap
ax.annotate("", xy=(1 + 1.5 * w, 2.103), xytext=(1 + 0.5 * w, 1.151),
            arrowprops=dict(arrowstyle="<->", color="#555", lw=0.8))
ax.text(1 + w, 1.63, "gap\ngrows", fontsize=6.5, color="#555", ha="center")
fig.tight_layout()
fig.savefig("fig_dtype_byte_budget.pdf", bbox_inches="tight")
fig.savefig("fig_dtype_byte_budget.png", dpi=130, bbox_inches="tight")
print("wrote fig_dtype_byte_budget")
