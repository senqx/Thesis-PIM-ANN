# Project overview

The thesis evaluates how request order and vector placement affect a specified
HBM2 DRAM service model during graph ANN. It separates logical HNSW traversal,
vector-address layout, and controller service so comparisons can hold the search
fixed. It does not evaluate a complete PIM accelerator.

The corrected artifact has one experiment driver (`sprint1/run_study`), one pinned
simulator setup, one replay runner, and one data-driven analysis path. The main
study uses SIFT100k, exact subset Recall@10, ten disjoint-within-split train/test
partitions, five vector layouts, and two modelled footprints. A smaller footprint
changes placement capacity and traffic, while retaining float32 search.

Under flat replay on the primary graph, query-aware placement improves cycles relative to BFS
slightly at 512 bytes and loses slightly at 128 bytes. Additional graph
constructions reverse the 128-byte ranking; the 512-byte advantage persists in
the tested flat-replay cases. These results are conditional on the graph and memory model. The baseline
microbenchmark also shows that sequential access can have more row hits and more
cycles when concurrency exposes different banks. Neither BFS optimality nor a
universal byte-budget law follows. The controller and heuristic sensitivities are
reported in the thesis and retained as raw evidence.

Read [README.md](../../README.md) for commands, [the thesis](../../doc/pim_ann_thesis.pdf) for
methods and interpretation, and [the remediation record](REVIEW_FIXES.md) for
the correction history. `archive/pre-review` is explicitly superseded material.

The final research pass adds ten-split comparisons for three controller settings,
three additional graph constructions on matching query splits, and command-level
analysis of the locality/timing reversal. It preserves the original primary traces
and distinguishes within-vector traffic from locality between different vectors.
That checkpoint retains 791 replay records; these are not 791 independent statistical
replications. Read the [research design](../../doc/RESEARCH_CLOSURE.md) for the comparison
units and the [reading guide](../../doc/READING_GUIDE.md) for the narrative path.

The 10 November follow-up adds 494 comparisons and four scheduling diagnostics,
bringing that checkpoint to 1,289 replays. It tests published RCM/Gorder/Porder placements and limits
future memory work at graph-expansion boundaries. Within those boundaries,
round-robin improves the reference 512-byte BFS service time by 14.58% but worsens
the hypothetical 128-byte case by 3.43%. Sorting is slower on average at both
widths under those default settings. All selected graph constructions and the smaller placement gains remain
in the complete comparison, with explicit overhead and model limits.

[Research position](../../doc/RESEARCH_POSITION.md) states the current RQs and existing
prior art. [Preservation](../../doc/RESULTS_PRESERVATION.md) links the previous validated
PDFs, source text and graphics. The added evidence does not discard earlier work.

The current extension adds 360 scheduling sensitivity replays and 420 training
calibration replays, for 2,069 total. It tests outstanding limits, candidate batch
boundaries and address mapping separately. The results motivate a configuration-
specific vector-fetch path: compare three established schedules on 50 training
queries, freeze the choice and evaluate 200 held-out queries. This preserves HNSW
search decisions and targets an execution frontend that exposes native requests.
The thesis compares the selected path with fixed orders and published placements,
and reports calibration cost and held-out regret. The training choice matches
the best fixed held-out order in all 140 tested configuration/split cases. At the
default 512-byte setting it beats Porder with original-order fetch by 14.25%; at
128 bytes the selected BFS path remains 1.35% slower than Gorder. The evaluation is exploratory;
it neither implements a PIM accelerator nor claims a new ANN algorithm.

[Revision disposition](REVISION_DISPOSITION.md) maps the latest review
priorities to the changes. The author's requested thesis and IEEE formats are
retained, with Artashes Atanesyan as author and supervisor details left for later.
