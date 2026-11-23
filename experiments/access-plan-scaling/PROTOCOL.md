# Preparation and work-size scaling

Exploratory follow-up, 23 November 2026; specified before the new executions.
Preserve both earlier studies and their manifests unchanged.

Question: does a useful range of preparation amount exist after charging CPU
construction, plan storage/installation and complete DPU execution?

Vary three separate quantities:

1. Work per invocation: 192, 768 and 3,072 destinations (eight references each).
2. Batch planning window: 16, 32 and 64 references, with the same 512-byte
   retained-payload capacity per tasklet. Keep the same twelve tasklets and
   8-byte feature rows. Compare with compressed 16-bit demand streaming.
3. Plan lifetime: analytically evaluate 1, 10, 100, 1,000 and 10,000 uses.
   Repeated deterministic simulation is not independent evidence. Each kernel
   invocation starts with empty logical retention; graph/order must stay fixed.

Use community, uniform and sampled ca-GrQc inputs, seeds 23 and 61. Synthetic
source universe remains 512: this is not a sweep of graph capacity, though
the number of distinct sources actually touched can vary. For ca-GrQc, sample distinct destinations from the
same public graph; samples at different sizes need not be nested. Keep the
original generator. This gives 72 performance configurations, not 72 independent
workloads. No policy tuning after inspecting this sweep.

Reuse the exact earlier linked stream16 and batch64 programs. Compile/link
batch16/32 with only the batch bound changed. Retain all images for exact replay.
Check outputs, precise byte counts, plan semantics, MRAM/WRAM bounds and matching
logical inputs across policies. Check that new batch64 metadata matches the
previous encoder byte for byte.

Measure host preparation separately from simulation: one untimed warm-up and
11 timed constructions per policy/input, rotating policy order, with no simulator
jobs launched by this experiment concurrently. Include allocation and encoding
into the final index/plan byte string for all policies. Exclude shared graph
generation, feature creation, disk I/O, correctness validation and dependency
setup. Report all raw times, median, quartiles, and host/software information.
Use a Python reference planner, not a claim about optimized native preprocessing.
Independent validation is outside the timed construction. The earlier planner's
timing included validation and must not be compared directly with these times.

Evaluate the serial resident-data accounting model:

    difference = (plan preparation - stream preparation)
                 + (plan metadata bytes - stream index bytes) / bandwidth
                 + uses * (plan kernel time - stream kernel time)

Use 350 MHz to convert simulated cycles. The bandwidth-free comparison first
sets extra installation to zero; sensitivity uses assumed effective host–DPU
rates 0.1, 1 and 5 GB/s. These are scenarios, not measured UPMEM rates. Count
tasklet-segment padding in installed metadata. Equal feature transfers, launches
and output traffic cancel only under the declared common-work assumptions.
Plan-dependent host merging, transfer setup differences and pipeline overlap
are unmeasured. Do not present mixed measured/modelled differences as observed
end-to-end speedups.

Report the first strictly faster integer reuse count only where the inequalities
support it, including cases of cheaper installation but slower recurring work.
If a candidate is slower per use and costs more to prepare/install, there is no
amortization threshold. If an improvement is tiny, keep the absolute difference
and timing-fidelity limit prominent. Report all regressions and traffic-budget
failures; do not select a hindsight winner and call it an adaptive policy.

## Baseline check added during the sweep

The first 768-destination community result showed batch64 beating the earlier
128-byte-buffer stream. Before claiming an opportunity, add 256- and 1,024-byte
buffers to the same 16-bit streaming kernel for all 18 input/size conditions
(36 records). These fit the same WRAM ceiling. Keep the candidate unchanged.
Compare with the fastest tested streaming buffer per condition as a strong
hindsight comparator, not as a deployed selector. This is an exploratory
baseline correction; no untouched confirmatory evaluation is claimed.

All three streaming kernels consume identical encoded host indices. Reuse
the same measured stream16 preparation samples for these identical host
operations, rather than counting those samples three times. Final evidence:
108 DPU configurations and 792 host construction timings (72 × 11).
