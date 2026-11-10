# Revision priorities and their disposition

This revision keeps the thesis centred on fixed-work HNSW memory service. The
new PIM-oriented proposal is an optional, training-selected vector-fetch path.
It selects among established schedules and does not claim a new HNSW algorithm
or measured end-to-end PIM acceleration.

| Requested revision | Change and evidence location |
| --- | --- |
| Align README, abstract and conclusion with the latest results | All now distinguish the default result from scheduling sensitivity and training-selected execution. The full result sources are `scheduling_summary.csv` and `profiled_fetch_summary.csv`. |
| Distinguish simulated DRAM service from PIM performance | The title-page scope, abstracts, model, captions, interpretation and conclusion identify the measured quantity. The execution sketch lists the missing compute, buffering, mapping and communication costs. |
| Explain flat and phase-constrained replay | The model and new replay-boundary diagram distinguish early future work, expansion phases and candidate batches. Batches add drains; they are not rolling residency limits. Original-query intervals include the gaps. |
| Strengthen literature-based novelty | The related-work comparison identifies published Porder, the different execution layers of cache-aware layouts and PIM systems, and PIMCQG's stated SC26 acceptance. Profiling and schedule selection are explicitly established engineering ideas. |
| Explain bank parallelism versus row locality | A worked explanation connects avoided row operations with overlapping bank waits. Command accounting supports the observed mechanism; offered bank diversity is distinguished from ready controller work. |
| Present paired comparisons prominently | New tables and plots show every configuration, ten split effects and paired 95% intervals. The selected path is compared with all fixed orders and matching published placements; oracle regret and regressions remain visible. |
| Explain the hypothetical 128-byte footprint consistently | The search remains float32. The smaller allocation changes emitted traffic and grouping capacity. It supplies no quantised-index accuracy or kernel-speed result. |
| Improve methodology diagrams | A new diagram shows identical logical work under flat, expansion and batch availability. Captions distinguish order from elapsed time and name completion barriers. |
| Remove redundant explanations | Detailed run/alignment experiments and adapter internals move to a supporting appendix; main chapters keep the findings needed for the argument. Earlier figures and measurements are retained. |
| Improve captions and references | New captions name the baseline, unit, repetition and sign convention. The document build checks unresolved citations/references and horizontal overflow; visual inspection checks layout. |
| Check bibliography | A shared bibliography serves both documents. The Ramulator paper's issue year is corrected to 2024 and its DOI added; the pinned implementation is identified separately as 2.1. UpANNS's publication DOI is included. |
| Check university formatting | The author requested the current thesis format plus IEEE, with no supplied institutional constraints. Both are retained; author is **Artashes Atanesyan**. Supervisor details are intentionally left for the author. No claim of compliance with an unspecified university template is made. |
| Add a justified PIM-oriented recommendation | The fixed 50-query training rule, complete comparison matrix, calibration cost, execution pseudocode and target-interface requirements make the recommendation reviewable. Full accelerator evaluation is identified as the next directly related implementation step. |
| Make every experiment reproducible | The full source-to-result workflow, pinned inputs, claim-to-data map, uncached spot-check command and full-tree comparison are documented in `REPRODUCIBILITY.md`. Fresh outputs are compared at every query/phase interval, not just headline means. Three uncached reconstruction/replay checks retain their raw evidence under `reproduction/`. |
| Preserve previous work | All 1,289 prior replays stay in place. All 57 documents at `94d3f1d` are archived byte for byte, alongside the earlier `71ce10b` archive. |

The [validation record](VALIDATION.md) states which checks were actually run.
The [research-position note](RESEARCH_POSITION.md) explains the remaining limits:
one real corpus prefix, a fixed search operating point, selected graph variation,
an exploratory selector evaluation and no integrated PIM execution. These limit
the claims; they are not silently treated as completed accelerator experiments.
