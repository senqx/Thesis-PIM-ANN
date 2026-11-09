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

On the primary graph, query-aware placement improves cycles relative to BFS
slightly at 512 bytes and loses slightly at 128 bytes. Additional graph
constructions reverse the 128-byte ranking; the 512-byte advantage persists in
the tested cases. These results are conditional on the graph and memory model. The baseline
microbenchmark also shows that sequential access can have more row hits and more
cycles when concurrency exposes different banks. Neither BFS optimality nor a
universal byte-budget law follows. The controller and heuristic sensitivities are
reported in the thesis and retained as raw evidence.

Read [README.md](README.md) for commands, [the thesis](doc/pim_ann_thesis.pdf) for
methods and interpretation, and [the remediation record](doc/REVIEW_FIXES.md) for
the correction history. `archive/pre-review` is explicitly superseded material.

The final research pass adds ten-split comparisons for three controller settings,
three additional graph constructions on matching query splits, and command-level
analysis of the locality/timing reversal. It preserves the original primary traces
and distinguishes within-vector traffic from locality between different vectors.
The artifact retains 791 replay records; these are not 791 independent statistical
replications. Read the [research design](doc/RESEARCH_CLOSURE.md) for the comparison
units and the [reading guide](doc/READING_GUIDE.md) for the narrative path.
