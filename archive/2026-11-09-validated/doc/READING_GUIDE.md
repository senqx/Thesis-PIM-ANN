# Reading the thesis

Start with [the companion paper](pim_ann_ieee.pdf) for the argument, then use
[the full thesis](pim_ann_thesis.pdf) for the implementation, experiments and
limits. Both introduce the required ANN and DRAM concepts. You do not need to
know HNSW internals or memorise the address-bit table before reading the results.

## The question that holds the story together

**If a graph search reads the same data, can changing where the vectors are stored
make memory finish that work sooner?**

The initial intuition is that data used together should live together. The
complication is that memory can benefit both from reusing a row and from spreading
work across banks. The thesis follows that tension through controlled examples,
actual graph-search traces, repeated experiments and command-level explanations.

## A path through the full thesis

1. **Problem and research questions.** Understand what the study wants to learn
   and what its timing represents. PIM is the motivation; the measured object is
   a specified DRAM request stream.
2. **Background and related work.** Follow the example of a graph expansion and
   the explanation of banks, rows and outstanding requests. These are the concepts
   needed to understand the later reversal.
3. **Experimental model.** Follow the pipeline figure and node-to-slot example.
   Ask what stays fixed when a layout changes: vectors visited, results, and
   request count at one footprint. The addresses change.
4. **Layouts and metrics.** Understand what information each layout uses. The
   query-aware heuristic learns co-visitation; it does not directly optimise
   simulated time. Check the denominator of each reported percentage.
5. **Protocol.** Distinguish query-split repetition from graph-construction
   variation. Paired comparisons use matching work; different kinds of repetition
   answer different robustness questions.
6. **Results.** Start with sequential versus permuted reads. Follow the command
   accounting, then the SIFT layout comparison, repeated controller settings,
   graph variations and vector/adjacency diagnostic streams.
7. **Interpretation and conclusion.** Read the overhead-budget example and
   decision path. These explain what an engineer can do with the findings and
   what additional evidence an application-speedup claim would require.

Use the terminology appendix as a reference, not as a list to memorise.

## Four distinctions that prevent most confusion

| Distinction | Why it matters |
| --- | --- |
| A logical vector read versus a memory transaction | One 512-byte vector generates sixteen 32-byte transactions. Their row reuse can dominate an aggregate hit percentage. |
| Address locality versus completed time | Nearby vectors may share a row, but the controller still has timing constraints and shared resources. |
| A trace's offered bank diversity versus ready work in the controller | The former describes addresses in an input window. It does not measure instantaneous queue occupancy or how many banks can issue now. |
| A smaller stored footprint versus actual quantisation | Repacking the same float32 trace isolates size. A real quantised index can also change distances, traversal, accuracy and compute cost. |

## How to explain the central result yourself

At the default 512-byte footprint, the trained layout saves about 0.31% of service
cycles relative to BFS. At the hypothetical 128-byte footprint, it costs about
0.17%, despite a higher row-hit percentage. Both are small effects on the original graph within the specified model.
The additional graph seeds reverse the 128-byte ranking. This demonstrates why
a precise query-split interval for one graph cannot establish a general layout
recommendation.

For the 128-byte first split, command recording makes the arithmetic concrete:
query-aware placement saves 25,125 command-issue cycles, but adds 27,973 cycles
with no issued command. The net cost is 2,848 cycles. That identity explains where
the measured difference lies. The controlled concurrency experiment and bank
statistics support the locality–parallelism interpretation; they do not isolate
every individual timing restriction.

When discussing this result, preserve its scale and scope. It is evidence that
these layout and controller choices interact. It is not evidence that layout is
unimportant in a complete search engine, or that one layout always wins.

## Questions to check your understanding

* Why can a row hit still wait, and why does allowing other outstanding reads
  change the value of row reuse?
* Why must all layouts use the same queries and logical traversal for a placement
  comparison to be interpretable?
* What does the confidence interval vary, and what remains fixed?
* Why can vector-only and adjacency-only replay times not be added to predict
  the mixed stream's time?
* What implementation costs could erase a saving of about 97 simulated cycles
  per query, and which of those costs has this study actually measured?

The answers are in the main text. Being able to explain those points in your own
words is more useful than memorising every result-table entry.

## Finding the supporting evidence

* [Review fixes](REVIEW_FIXES.md): disposition of the original correctness and
  claim-scope findings.
* [Research closure](RESEARCH_CLOSURE.md): the bounded additional experiment design
  and remaining research questions.
* [Validation](VALIDATION.md): checks actually performed and their limits.
* [Results](../results/): raw statistics and generated summaries.
* [Reproduction instructions](../README.md): build, data, experiment and document
  commands.
