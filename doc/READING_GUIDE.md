# Reading the thesis

Start with [the companion paper](pim_ann_ieee.pdf) for the argument, then use
[the full thesis](pim_ann_thesis.pdf) for the implementation, experiments and
limits. Both introduce the required ANN and DRAM concepts. You do not need to
know HNSW internals or memorise the address-bit table before reading the results.

## Defence presentation

Use the [defence PDF](pim_ann_defence.pdf) for a roughly 15-minute talk: twelve
main slides followed by two backup slides. It reuses the thesis's generated
figures and values and builds with the same `make docs` command. The
[validation record](VALIDATION.md#current-document-set) identifies this document
set. The detailed defence answers later in this guide support questions.

| Slide | Speaking purpose |
| --- | --- |
| 1 — Question | Start with the apparent contradiction: putting related data together can reduce row operations yet delay completion. State immediately that timings are simulated DRAM service. |
| 2 — RQs and contribution | Name the added evidence: placement failure cases, explained scheduling reversals and implementation cost thresholds. Gorder/Porder are measured placements; PIM systems are literature comparisons. The general techniques are established. |
| 3 — Fixed work | Explain node IDs versus storage addresses. The same search results and logical reads are preserved. A paired split compares matching queries; ten splits are not ten independent datasets. |
| 4 — Availability | Walk through one neighbour list and its vectors. Flat replay knows future requests; phase replay withholds them until memory completion. Neither executes real search control or distances. |
| 5 — Small placement effect | Distinguish a conditional interval excluding zero from a worthwhile implementation. About 97 cycles/query is a small allowance for extra work. |
| 6 — Larger scheduling contrast | Explain original, sorted and round-robin orders in words before reading the graph. A negative cycle change is favourable; the hypothetical smaller footprint reverses the recommendation. |
| 7 — Mechanism | Read the command-cycle identity aloud. More banks are offered and fewer no-command cycles outweigh extra row work. Do not describe the input-window diagnostic as live bank occupancy. |
| 8 — Sensitivity | Highlight the 16-outstanding and alternative-mapper reversals. All seven conditions remain visible. This is one-setting-at-a-time evidence, not an optimal combination search. |
| 9 — Profiling | Expand 140 into 7 × 2 × 10. The training rule is frozen, but the policy was motivated by inspected test results. Matching a fixed winner does not beat that winner or establish a universal success rate. |
| 10 — Overhead | Explain the 985-query ratio as service-only arithmetic. Costs, overlap and reuse lifetime determine real amortisation; a known good fixed schedule avoids repeated calibration. |
| 11 — PIM direction | Trace query, candidate addresses and returned distances. Local distance computation could avoid returning whole vectors, but the proposed engine and its costs are unmeasured. |
| 12 — Answers | Answer all RQs, state the conditional engineering lesson, then name what is needed before claiming end-to-end PIM speedup. Stop here; use slides 13–14 for questions and references. |

Spend most of the time on slides 4 and 6–10. Keep the arithmetic illustrative,
and use the named baseline whenever quoting a percentage. If asked for expected
application speedup, explain which costs and overlap remain unmeasured instead
of converting a service percentage into an end-to-end prediction.

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
in all 140 cases: seven memory/batch settings × two footprints × ten splits.
All use the same graph and query pool. Each setting receives the same choice
across its ten training splits, so the result supports selecting a stable fixed
order among three choices. It does not estimate a universal success probability;
the cases are not independent trials across new workloads or hardware.

Then read the published-baseline table. A selected BFS schedule is not necessarily
better than Gorder or Porder, and their individual gains cannot be added to predict
an untested combination. The appendix shows calibration service and absolute
service under all tested configurations; an attractive percentage against a slower
batch baseline is not automatically a better execution path. For example, default
512-byte calibration uses about 5.72 million simulated cycles to find an order
saving about 5,802 cycles per query. Their ratio is about 985 query services before
extra cost; consuming half the saving doubles that ratio to about 1,971. This is
an illustration using stable means in a serial service model, not a deployment
break-even prediction. The 200-query evaluation does not itself repay calibration
in that accounting. Only extra costs relative to the matching baseline should be
charged as scheduling overhead; costs shared by both paths still affect total time.

The execution diagram now assigns work and data to a concrete proposed host and
near-memory engine. The host reads neighbour IDs, filters candidates and supplies
resolved addresses. The engine retains the query, gathers resident vectors and
returns tagged distances; the host updates search state in the original order.
Gathering alone would still transfer full vectors to the host. Local distance
evaluation is the operation that could avoid that payload. Its arithmetic,
buffering, interface and numerical behaviour need implementation and measurement.

## Preparing for the defence

These are concise answers to practise explaining in your own words. The thesis
provides the methods, qualifications and evidence behind each answer.

1. **What is original when graph reordering and PIM ANN already exist?**
   My contribution is the measured failure cases, conditional alternatives and
   their explanation for a fixed HNSW/HBM2 workload. For example, round-robin
   within available expansions reduces default 512-byte service by 14.58%, but
   changing only the address mapper makes it 112.71% slower than matching original
   order. Command accounting explains how less waiting can outweigh extra row
   operations in the default case. That gives a fetch-interface designer both a
   useful case and a concrete counterexample to a universal recommendation.

   Gorder/Porder contribute established placement algorithms; I evaluate their
   supplied routines at fixed search work under explicit DRAM and availability
   assumptions. The cited PIM systems contribute fuller execution designs; I do
   not benchmark those accelerators. My artifact isolates candidate fetching and
   quantifies its service savings and cost thresholds. About 5,802 saved cycles
   per query in the default 512-byte case is a testable allowance for extra work
   in an additive model, not a promised PIM speedup. The contribution is original
   empirical evidence and reusable tests, not invention of the general
   locality–parallelism trade-off or a new scheduling principle. The
   [contribution statement](RESEARCH_POSITION.md#the-original-contribution)
   connects each output to its evidence and intended use.

2. **What does DRAM service establish about PIM?**
   It evaluates one component that a compatible near-memory engine must execute:
   serving available list and vector reads. Moving arithmetic near memory does
   not remove bank timing constraints. The result guides the engine's fetch
   interface; it does not establish a benefit unique to PIM or a PIM speedup.
   The same mechanism can matter to a host memory controller.

3. **Why HNSW and SIFT100k?**
   HNSW supplies a widely used graph index and a stock implementation to observe.
   Public SIFT supplies a fixed, reproducible corpus and query pool. The 100k
   prefix makes exact subset ground truth and repeated simulation tractable.
   This is a deliberate case study, not a representative sample of ANN workloads.
   New dimensions, datasets, graph families and recall targets remain untested.

4. **How do layouts perform the same search?**
   Stock HNSW produces one logical record sequence for each graph/query split.
   Every layout maps those same node IDs to unique physical slots; it does not
   rerun a different traversal. Instrumented and unobserved search answers must
   agree, and independent-index tests check the observer. Permutation checks,
   read accounting and phase-membership checks verify the physical transformation.
   Fixed logical work isolates placement; an implementation must still validate
   its mapping, arithmetic and ordered updates.

5. **Why ten paired splits?**
   They give an estimate of variability from query selection on the fixed graph
   and query pool, with the achieved precision shown by paired Student intervals
   and individual split effects. No prospective power calculation proves ten is
   sufficient for every claim. Pairing compares each alternative on the same
   work. Repeating an identical deterministic replay adds no sampling information;
   neither do the 2,069 retained records constitute 2,069 independent experiments.
   More splits would refine this conditional estimate, not establish generality.

6. **What can the simulator miss?**
   It enforces the configured DRAM command/timing rules, but the preset has not
   been checked here against a physical HBM2 device. It omits caches, computation,
   local storage, control and communication. It models one channel and sequential
   queries. Actual application dependencies and concurrent queries can change
   what requests are available, so the cycle ratio is not an application ratio.

7. **Why can higher row-hit rate mean slower service?**
   A row hit still waits for command timing and shared resources. Concentrating
   reads can reduce opportunities for other banks to make progress. The command
   records show cases where fewer row operations coincide with more no-command
   cycles. Those counts explain the arithmetic of the loss; they do not identify
   every wait cause. Offered-bank diversity is a trace diagnostic, not measured
   instantaneous controller occupancy.

8. **Why can the ranking change at 128 bytes?**
   A vector uses four native reads instead of sixteen. At the same transaction
   limit, more vectors can be exposed, and more vector starts fit in a contiguous
   grouping span. Both placement and ordering therefore interact differently
   with the address map. This explains why unchanged behaviour cannot be assumed.
   The experiment retains float32 traversal; it measures neither a quantised
   distance kernel nor the accuracy consequences of compression.

9. **Why does default round-robin help at 512 bytes but hurt at 128?**
   It exposes chunks of several vectors earlier. On the diagnostic 512-byte
   stream, extra row operations are outweighed by fewer no-command cycles.
   The 128-byte original order already exposes more bank diversity; interleaving
   adds both command and no-command cycles there. This supports an overlap/locality
   explanation without claiming a universal size threshold. The 128-byte result
   becomes favourable with a 16-read limit, and the alternative mapper makes
   round-robin much worse at both widths.

10. **How does bounded replay differ from flat replay?**
    Flat replay can offer requests from future expansions before real search
    could discover them. Bounded replay drains a list phase, exposes its recorded
    vector group, then drains before later work. It withholds future memory
    requests but still omits distance and control time. Smaller candidate batches
    add drains between vector groups; a transaction limit only caps uncompleted
    reads. Neither model is an execution-latency bound for every implementation.

11. **What would an actual PIM implementation require?**
    Implement the host/engine split described above, including query transfer,
    list traffic, candidate descriptors, local arithmetic/storage and returned
    distances. The target must expose suitable request ordering and enough
    independent reads; whole-vector DMA or bank-local access may require a
    different design. Compare host-only HNSW, the accelerator with original fetch,
    and the same accelerator with fixed and profiled alternatives, at equal
    accuracy and concurrency. Measure complete latency and throughput.

12. **How much benefit remains after overhead?**
    We do not know. The flat 512-byte placement saving is about 97 service cycles
    per query; default bounded round-robin saves about 5,802. These are different
    comparisons, not additive gains. In an illustrative additive model, if the
    affected service were half of baseline time, a retained 14.58% service
    reduction would reduce total time by 7.29% before overhead. That fraction,
    overhead and compute/memory overlap are unmeasured. Statistical detectability
    does not establish practical value; the architectural value is learning which
    interface assumptions change the result.

13. **When is profiling not worthwhile, and what if it fails?**
    A correctly chosen fixed schedule gives the same measured benefit without
    repeated calibration. Short-lived configurations, low gains, frequent drift
    or expensive profiling/dispatch can erase the value of selection. Training
    can choose poorly on a changed workload, and aggregate gains can hide slower
    queries. The study discloses that previously inspected outcomes motivated
    the policy; this remains exploratory. A proposed deployment would monitor
    mean and tail costs, re-evaluate after relevant changes, and return to a
    validated fixed baseline when complete execution regresses. There is no
    measured reprofiling interval or automatic guarantee from original order.

Two further comparison rules matter: vector-only and adjacency-only times cannot
be added to predict their mixed-stream time, because they interact in the
controller; separately measured placement and scheduling gains cannot be added
to predict an untested combination. A weak local heuristic also cannot stand in
for published Porder, which uses a different trained placement method.

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
