# Reading the thesis

Start with [the companion paper](pim_ann_ieee.pdf) for the argument, then use
[the full thesis](pim_ann_thesis.pdf) for the implementation, experiments and
limits. Both introduce the required ANN and DRAM concepts. You do not need to
know HNSW internals or memorise the address-bit table before reading the results.

## The question that holds the story together

**If a graph search reads the same data, can changing its storage locations
and the order of available reads make memory finish that work sooner?**

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
   simulated time. Published Porder is a separate trained baseline. Check the
   denominator of each reported percentage.
5. **Protocol.** Distinguish query-split repetition from graph-construction
   variation. Paired comparisons use matching work; different kinds of repetition
   answer different robustness questions.
6. **Results.** Start with sequential versus permuted reads. Follow the command
   accounting, then the SIFT layout comparison, repeated controller settings,
   graph variations and vector/adjacency diagnostic streams. Then follow the
   expansion-boundary diagram: first a list reveals candidates, then their vector
   reads become available. The published-layout and scheduling comparisons test
   whether the original result depended on the heuristic or on early future work.
7. **Interpretation and conclusion.** Read the overhead-budget example and
   decision path. These explain what an engineer can do with the findings and
   what additional evidence an application-speedup claim would require.

Use the terminology appendix as a reference, not as a list to memorise.

## Distinctions that prevent most confusion

| Distinction | Why it matters |
| --- | --- |
| A logical vector read versus a memory transaction | One 512-byte vector generates sixteen 32-byte transactions. Their row reuse can dominate an aggregate hit percentage. |
| Address locality versus completed time | Nearby vectors may share a row, but the controller still has timing constraints and shared resources. |
| A trace's offered bank diversity versus ready work in the controller | The former describes addresses in an input window. It does not measure instantaneous queue occupancy or how many banks can issue now. |
| Flat replay versus expansion boundaries | Both omit compute, but the latter waits for earlier memory work before offering the next expansion. |
| Phase service versus original-query service | One query has many phases. Its interval must include the gaps between them; a phase mean is not a query mean. |
| A smaller stored footprint versus actual quantisation | Repacking the same float32 trace isolates size. A real quantised index can also change distances, traversal, accuracy and compute cost. |

## How to explain the original result yourself

Under flat replay at the default 512-byte footprint, the trained layout saves about 0.31% of service
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

## What the follow-up adds

The published baselines prevent one local heuristic from representing an entire
idea. Under expansion boundaries, Porder reduces the reference 512-byte service
cycles by about 0.38% relative to BFS. Gorder reduces the hypothetical 128-byte
case by about 1.33%. Both improve total service in all 19 selected graph/split
cases at both widths, although the size varies. These are small placement gains
before integration cost.

The phase diagram then addresses which requests the controller can see. Read a
list, make its candidate vectors available, finish that group, then move to the
next expansion. Sorting that available group's addresses is slower on average under the default settings.
Offering chunks round-robin instead reduces 512-byte BFS service by **14.58%**,
about **5,802 simulated cycles per query**, on the reference graph. Every tested
query record improves in each of the 19 cases. At 128 bytes, however, round-robin
adds **3.43%** on the reference graph. The opposite signs persist across the tested
constructions and both evaluated placements.

This is the positive/negative contrast to understand: exposing chunks from
several vectors early can be more useful than maximising row hits, but the value
depends on footprint, address mapping and available overlap. At 512 bytes the command record shows
more row operations and fewer total cycles. At 128 bytes, the extra operations
are not recovered in total service. Scheduling cost, computation and application
concurrency still need an execution-level evaluation.

The new boundary model also changes small placement rankings. One seed-101
512-byte query-aware comparison becomes a loss, despite the earlier flat-replay
advantage. Keep the boundary mode attached to every performance statement.

## The final step: choose the execution order from training

The new sensitivity study asks whether the default scheduling recommendation
survives smaller request limits, smaller candidate batches and a different address
mapper. It does not. At the same footprint, a different amount of exposed work or
a different mapping can change the preferred schedule. A rule based only on
vector size would miss that interaction.

The proposed path therefore tries original order, sorting and round-robin on
50 training queries for each configuration, stores the fastest choice and uses it
for all 200 held-out queries. Read the selection-count and paired-result table
before interpreting the gain: selection may simply recover a good fixed schedule.
The oracle column asks how far that training choice is from the best fixed order
selected after seeing the test outcomes. The oracle is a comparison tool, not an
implementable policy. In this matrix the training choice matches that best order
in all 140 cases. Each configuration receives the same choice across its ten
training splits, so the result supports a configuration-specific fixed order;
it does not establish that every new workload will select correctly.

Then read the published-baseline table. A selected BFS schedule is not necessarily
better than Gorder or Porder, and their individual gains cannot be added to predict
an untested combination. The appendix shows calibration service and absolute
service under all tested configurations; an attractive percentage against a slower
batch baseline is not automatically a better execution path.

The execution diagram and pseudocode make the PIM connection concrete: HNSW
supplies a candidate batch, a compatible near-memory gather operation applies the
profiled order, and distance/state updates retain the original order. The replay
times the DRAM requests; it does not execute that whole engine. The next necessary
step for an application-speedup claim is to implement and charge those operations.
That is directly related future work, not a result already established here.

## Questions to check your understanding

* Why can a row hit still wait, and why does allowing other outstanding reads
  change the value of row reuse?
* Why must all layouts use the same queries and logical traversal for a placement
  comparison to be interpretable?
* What does the confidence interval vary, and what remains fixed?
* Why can vector-only and adjacency-only replay times not be added to predict
  the mixed stream's time?
* Why is sorting within one available expansion a different experiment from
  sorting a complete future trace?
* Why can a weak local query-aware result not stand in for published Porder?
* Why should separately measured placement and scheduling gains not be added?
* Why can a schedule chosen on training queries still regress on held-out work?
* Why does a smaller candidate batch differ from a smaller transaction limit?
* What implementation costs could erase a saving of about 97 simulated cycles
  per query, and which of those costs has this study actually measured?

The answers are in the main text. Being able to explain those points in your own
words is more useful than memorising every result-table entry.

## Finding the supporting evidence

* [Research position](RESEARCH_POSITION.md): current RQs, established prior work,
  the Master's scope, and the claims that would require further research.
* [Preservation guide](RESULTS_PRESERVATION.md): the earlier validated PDFs and
  evidence, kept separately from superseded pre-review material.
* [Follow-up design](FOLLOWUP_DESIGN.md): fixed comparisons and the explicitly
  identified diagnostic addition after the pilot.

* [Review fixes](../archive/review-notes/REVIEW_FIXES.md): disposition of the original correctness and
  claim-scope findings.
* [Research closure](RESEARCH_CLOSURE.md): the bounded additional experiment design
  and remaining research questions.
* [Validation](VALIDATION.md): checks actually performed and their limits.
* [Reproducibility](REPRODUCIBILITY.md): claim-to-data links, fresh simulation
  commands and exact comparison against retained evidence.
* [Results](../results/): raw statistics and generated summaries.
