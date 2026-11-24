# Decision study: frozen protocol

24 November 2026. Written before new DPU timings. Existing pilot results informed
the hypotheses; this is a new, bounded evaluation rather than an untouched research
programme. Preserve calibration and held-out separation and record any deviations.

## Question and scope

When does local reuse repay its complete execution and preparation costs under
equal total WRAM capacity and explicit byte budgets? Does a small cost selector
improve on conventional rules? Test one simulated UPMEM DPU; no hardware or energy
claim. Use the pinned Go uPIMulator and SDK from the platform record.

Test standard integer CSR SpMV and SpMM on complete public Matrix Market sparsity
patterns. Expand declared symmetry, discard explicit zeros, merge coordinates,
preserve all remaining coordinates, and assign the deterministic positive integer
weight `1 + (row + 3*column) % 3`. These are structural projections, not reproduction
of the original floating-point problems. Test one scalar (8-byte aligned storage)
and feature widths 2, 4, 8, 16 and 32 int32 values (8–128 physical bytes). Check exact
weighted CPU results and integer overflow bounds. Pad dimensions to multiples of
four with empty rows/columns; report padded and original dimensions.

Calibration matrices: HB/bcsstk01, HB/bcsstk06, HB/west0067.
Held-out matrices: HB/494_bus, HB/1138_bus, HB/can__144, HB/can__256.
They are small feasibility-scale public structures; held-out power-network and
Cannes families do not appear in calibration. Five widths on a matrix are related
conditions, not five independent datasets. Preserve input URLs, hashes and bytes.

## Baselines and budgets

Compare CSR streaming with 128/512-byte metadata buffers; frequency-ordered
partial residency; full residency where the configured linked allocation permits;
prepared dictionaries with ordered weighted contributions; and 2x2/4x4 BCSR.
The BCSR kernels implement published block reuse, not a reproduction of SparseP's
full system. Retain padding, conversion and metadata costs. Partial retention
reorders the source table and rewrites indices so it needs no extra installed
lookup table; count construction and feature permutation on refresh.

All methods share the 64 KiB WRAM ceiling, eight tasklets and assignment of groups
of four rows. Residency reserves as much shared capacity as a conservative static
allocation formula permits, in 2 KiB increments with 2 KiB runtime headroom.
The upstream linker reserves 49,152 bytes for all 24 possible tasklet stacks,
even when fewer tasklets execute. This fixed reservation is included unchanged.
Report actual linked allocations and unused space; this is not exhaustive memory
allocation tuning. Dictionary payload is 512 bytes per tasklet and at most 64 entries.
Compare additional tasklet counts on a bounded sensitivity subset if feasible.

The primary constrained comparison permits no extra installed matrix/plan bytes
or total MRAM–WRAM read/write bytes relative to matched CSR streaming. Apply limits
per input; a faster infeasible method remains in the unconstrained results. Source
and output storage, host temporary storage and host transfers must be disclosed.

## Controlled sweeps and correctness

Use five synthetic source working-set sizes spanning the configured residency
capacity at 8-byte records, with uniform and clustered references and unchanged
row/nonzero counts. Synthetic rows contain unique columns. These explain capacity
effects, not application generality. Public width sweeps contain five actual
SpMM executions per policy. No interpolation counts as an experiment.

Independent Python decoders reconstruct all representations, weighted coordinates
and outputs; predict exact DMA bytes and verify simulator counters. Empty rows,
trailing dimensions, changing feature values and metadata boundaries get explicit
correctness cases. Retain exact linked images, simulator options and complete
expected outputs. Deterministic reruns establish reproduction, not sample size.

## Preparation, selector and evaluation

Use one native C++17 implementation and compiler optimization level for every
preparation policy, record 31 samples after three warmups, and measure structure
preparation separately from feature refresh. Time the implementation actually
used to generate DPU inputs. Repeated samples describe host timing variation.

Fit nonnegative linear cycle models using calibration matrices only; explanatory
features describe arithmetic, DMA traffic/calls and work imbalance. Freeze model
coefficients, feature definitions, rules and their hashes before held-out timings.
The model may inspect candidate representations; charge all that preparation,
including rejected candidates. Count prediction time. Compare a capacity-first
rule, a reuse-only rule, a calibration-selected fixed feasible method and a
hindsight feasible oracle (a diagnostic, not an implementable policy).

Report both kernel-only decisions and total accounted cost including native setup,
refresh and explicitly modelled host installation/transfer. Primary illustrative
effective host bandwidth is 80 MB/s per DPU; sweep 20, 40, 80, 160 and 320 MB/s.
Launch overhead is unmeasured; show 0, 10 and 100 microseconds as scenarios.
No overlap is assumed. Reuse counts 1, 2, 4, 8, 16, 64, 256 and 1024 are modelled
lifetimes, not measured application runs. Confirm refresh correctness in actual
repeated invocations before applying the repeated-cost model.

Report paired absolute cycles/bytes, correct and wrong recommendations, worst
slowdown and regret relative to the hindsight best feasible choice. Show constrained
and unconstrained outcomes. A useful selector must repay its own costs, beat simple
rules and avoid a regression over 5% in the evaluated primary scenarios; failure is
a valid result. Assess this criterion separately at each declared lifetime in the
primary 80 MB/s, zero-launch scenario: mean accounted time must beat each simple
rule, and no condition may be more than 5% slower than its fastest simple rule.
With four held-out matrices, do not claim population-level accuracy.
Do not tune after inspecting held-out timings. If simple methods suffice, stop.

Pre-experiment feasibility correction: the first link check caught an allocation
formula that incorrectly scaled the fixed stack reservation with active tasklets.
No DPU timings had run. Correct the formula to 49,152 bytes and reduce the initial
1 KiB batch workspace to 512 bytes so the widest configuration fits. Regenerate
the capacity controls before collecting any calibration or evaluation timings.

Accounting clarification before model freeze: the timed interval starts with a
compiled, loaded program and a host CSR structure. Native feature synthesis and
artifact filesystem I/O are excluded; inspection and refresh of existing values
are measured. Program loading, parsing and application integration require extra
costs outside this interval. The selector assumes candidate metadata remain in
host memory until selection. Report combined candidate storage and the remaining
time margin for unmodelled deployment costs rather than claim end-to-end speedup.
