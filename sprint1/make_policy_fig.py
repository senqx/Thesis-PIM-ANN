#!/usr/bin/env python3
# Open vs closed page policy. Closed-page auto-precharge erases the sequential
# row-hit advantage. A light dashed guide at the open-page height makes the
# closed-page shortfall visible; the delta is labelled in clear space.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8.5, "ytick.labelsize": 8,
    "font.family": "serif", "axes.grid": True, "grid.alpha": 0.25,
    "axes.axisbelow": True,
})
GREEN = "#2E7D46"; BRICK = "#9A3B2E"; GREY = "#444"

labels = ["Sequential", "Random"]
openv = [93.6, 55.1]
closev = [75.0, 54.7]
x = np.arange(len(labels)); w = 0.36
fig, ax = plt.subplots(figsize=(3.6, 2.7))
b1 = ax.bar(x - w/2, openv, w, color=GREEN, label="Open page",
            edgecolor="white", linewidth=0.4)
b2 = ax.bar(x + w/2, closev, w, color=BRICK, label="Closed page",
            edgecolor="white", linewidth=0.4)
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+1.2,
                "%.1f" % b.get_height(), ha="center", va="bottom", fontsize=7.5)

# Light dashed guide at the Sequential open-page height, spanning just that
# group, so the closed-page shortfall is visible. Delta labelled in clear space.
x0l, x0r = x[0] - w, x[0] + w
ax.plot([x[0] + w/2, x0r + 0.14], [93.6, 93.6], color=GREY, ls="--", lw=0.9)
ax.annotate("", xy=(x0r + 0.08, 93.6), xytext=(x0r + 0.08, 75.0),
            arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.0))
ax.text(x0r + 0.16, 84.3, "-18.6\npts", ha="left", va="center",
        fontsize=7, color=GREY)

ax.set_ylabel("DRAM row-hit rate (%)")
ax.set_title("Row-buffer gain needs an open-page policy")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylim(0, 108); ax.set_xlim(-0.6, 1.9)
ax.legend(loc="upper right", framealpha=0.95)
fig.tight_layout()
fig.savefig("fig_policy.pdf", bbox_inches="tight")
fig.savefig("fig_policy.png", dpi=150, bbox_inches="tight")
print("wrote fig_policy")
