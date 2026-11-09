# Multi-seed confidence intervals on REAL SIFT1M

Addresses the reviewer's statistical-validity point: the single-seed real-data
layout margins are small, so we report mean / stddev / 95% CI across seeds.

## What varies per seed
On a fixed real corpus the base vectors cannot change, so each seed re-shuffles
the **train/test query split** (which queries train the co-visitation model vs.
which are held out for scoring) and re-seeds the Random and Community layouts.
BFS and QueryAware are deterministic given the split, so their per-seed spread
reflects **generalisation variance** -- exactly the quantity in question.

## Run (on the VM, with SIFT1M downloaded to sprint1/data/)
```bash
cd sprint1
make run_sift_multiseed
./scripts/multiseed_sift.sh data/sift_base.fvecs data/sift_query.fvecs \
    20 100000 500 200 64
#    ^NSEEDS ^maxBase ^trainQ ^testQ ^ef
```
This writes `multiseed_sift_results.csv` (one row per seed) and prints the
aggregate table. Use NSEEDS=20-30 for a stable 95% CI.

## Reading the result
If the BFS and query_aware 95% CIs **do not overlap**, their ordering is
statistically distinguishable -- that is the claim you can then make in the
paper. If they overlap, the honest statement is "indistinguishable on aggregate;
BFS leads on the point estimate." Either way you are now reporting uncertainty,
not a bare single-seed number.

## Paste into the thesis (replace the X.xxx placeholders with your output)
LaTeX table template -- drop into Section "Validating the layout idea...":

\begin{table}[h]
\centering
\renewcommand{\arraystretch}{1.2}
\begin{tabular}{lrrr}
\toprule
\textbf{Layout} & \textbf{mean} & \textbf{sd} & \textbf{95\% CI} \\
\midrule
Random                 & X.xxx & X.xxx & [X.xxx, X.xxx] \\
Community              & X.xxx & X.xxx & [X.xxx, X.xxx] \\
Query-aware (proposed) & X.xxx & X.xxx & [X.xxx, X.xxx] \\
\textbf{BFS}           & \textbf{X.xxx} & X.xxx & [X.xxx, X.xxx] \\
\bottomrule
\end{tabular}
\caption{Inter-vector row-hit (\%) on real SIFT1M across $N$ seeds (each a fresh
train/test query split). BFS leads query-aware; CIs quantify the margin.}
\label{tab:ci}
\end{table}
