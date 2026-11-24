# Validated preparation and decision-accounting correction

**24 November 2026.** These are the current native-cost and accounted results
for the thesis. Read [results.md](results.md) for the regenerated comparisons
and [PROTOCOL.md](PROTOCOL.md) for the correction and its disclosed amendment.
The [parent study](../README.md) explains the workloads, policies and budgets.

The original implementation unnecessarily allocated identity permutations and
copied already ordered source values. Those operations are removed. Only `hot`
still performs and pays for its frequency ordering and feature permutation.
Fixed hot and capacity-first now use direct header feasibility tests and
construct only the selected representation. Reuse applies the same full-retention
shortcut, then constructs/inspects hot and batch only as needed. A header bound
also skips hot inspection when even evenly spread references guarantee the
frozen 50% reuse threshold. Streaming
reference bytes come from header arithmetic. Visited rejected candidates are
charged; header-rejected candidates are skipped.

The cycle model is calibrated offline. Its per-input refresh-time estimates are
**granted free of collection cost**, an optimistic information assumption. No
runtime profiling or calibrated refresh estimator is claimed. Every policy still
pays its actual refresh work on every use. Setting the selection estimates to
zero changes none of the 1,920 model decisions. The
[independent audit](accounting-audit.json) checks this and the header formulas.

This is an implementation/accounting correction using already observed inputs.
It is not fresh confirmation, a new learned model or a new workload campaign.
The original cycle coefficients, selection thresholds and practical-success
criterion remain fixed. The [historical results](../results.md), raw samples,
manifest and exact source snapshots remain available. The immediately preceding
accounting, source and PDF checkpoint is in [pre-direct.zip](../archive/pre-direct.zip);
its unchanged native measurements are shared and verified against its original
manifest. See the [archive index](../archive/README.md) for reconstruction.

## What was measured and reused

| Evidence | Status |
| --- | --- |
| 446 distinct native preparations | Newly executed sequentially, 31 samples after three warmups; 13,826 retained sample rows, each with preparation, inspection and refresh intervals |
| 511 archived DPU invocations | Every regenerated input, argument block and expected output matches byte for byte |
| 485 distinct simulation records | Original cycles reused after that equivalence check; not 485 new runs |
| Four representative replay records | Six fresh invocations; all counters, output checks and non-path options match |
| 23,040 cost scenarios | Recomputed using unchanged corrected native costs and retained prediction timings; calculations, not independent experiments |
| Direct-rule accounting revision | No new native timing, simulator execution or fitting; provenance in [accounting-provenance.json](accounting-provenance.json) |
| Cycle model and fit time | Original calibration-only coefficients and original fitting-time measurement; no refit |

The 342 calibration/held-out/controlled phase rows combine new native timings
with original kernel counters. Additional native cases cover boundary inputs,
changed values and tasklet variants. Copied sensitivity, repeated and concurrency
tables are unchanged historical simulator evidence; their old host-cost fields
are not used in corrected totals. The copied `frozen-model.json` retains its
original calibration hash, which refers to the **parent** calibration table.

Raw regenerated representations and timing samples are in
[preparation.zip](preparation.zip). [identity.json](identity.json) maps every
archived invocation to its corrected preparation. [native.json](native.json)
contains medians and structural counters; [host.json](host.json) pins the host,
GCC 15.1.0 compiler and flags. [checks.json](checks.json) records native
sanitizer checks, accounting regressions and fresh replay evidence.
[manifest.json](manifest.json) binds these to the historical manifest and
current sources. Host timing variation remains a measurement limitation.

## What changed in the conclusions

The kernel-only result is unchanged: 8/24 equally optimal feasible selections,
6.44% mean kernel regret and 18.27% worst regret. Corrected setup-inclusive
totals still fail the practical-success criterion at all eight lifetimes against
the current fixed, capacity and reuse rules. Granting the model zero selection
overhead also fails at all eight. Both tests are computed from the corrected
alternatives, not copied from the earlier review.
Their exact values are in [summary.json](summary.json) and
[success-criteria.csv](success-criteria.csv).

At 80 MB/s, median native costs give hot-retention payback in one use for 15 of
16 held-out SpMM cases at 8–64 bytes, and two uses in the remaining case. Only
9/16 retain a positive first-use margin throughout the observed sample envelope;
seven span zero. The 1138_bus/16-byte example leaves about 83 µs by the medians,
with an observed envelope of approximately −7 to +158 µs. These are conditional
accounting margins, not hardware speedups or confidence intervals. At 128 bytes,
hot retention still loses kernel cycles on all four held-out matrices.

Comparing historical and corrected totals does not isolate a causal performance
effect: native measurements were taken at different times and the accounting
also changed. Use the corrected paired comparisons to assess the current code.

## Audit or rebuild reports

From the repository root:

```sh
python3 scripts/decision_artifact.py verify
python3 scripts/test_decision_correction.py
python3 scripts/decision_correction.py verify
python3 scripts/review_decision_costs.py --current
MPLCONFIGDIR=build/matplotlib python3 scripts/decision_correction.py render
python3 scripts/build_short_thesis.py
```

To recompute derived accounting using the same retained timings, run
`MPLCONFIGDIR=build/matplotlib python3 scripts/decision_correction.py reaccount`
before rendering. This uses the archived prediction intervals; it does not retime
the selector. `python3 scripts/review_decision_costs.py` reproduces the historical
review separately. The current audit records hashes of its inputs without hashing
the manifest that includes the audit itself.

Rendering does not remeasure native costs or prediction arithmetic. The two
verifiers separately check the historical and corrected artifacts. The native
timing intervals exclude destruction, file output and feature synthesis. Identity
refresh timings contain timer/dispatch overhead. Simple-rule dispatch, loading,
SDK integration and full-application orchestration remain unmeasured.

## Rerun corrected measurements separately

Use the [pinned platform](../../../docs/PLATFORM.md) and document dependencies.
Choose fresh run and output paths; the final component of the output path must
be `corrected`. Never overwrite either retained artifact. The following example
keeps all new evidence in ignored `runs/`:

```sh
mkdir -p runs/correction-reproduction/corrected
cp experiments/decision-study/corrected/PROTOCOL.md runs/correction-reproduction/corrected/PROTOCOL.md
python3 scripts/decision_correction.py prepare --output runs/correction-reproduction/corrected --run-directory runs/correction-reproduction/native-run
MPLCONFIGDIR=build/matplotlib python3 scripts/decision_correction.py analyze --output runs/correction-reproduction/corrected --run-directory runs/correction-reproduction/native-run
python3 scripts/decision_artifact.py replay --replay-directory runs/correction-reproduction/native-run/replay --key 494_bus-w2-hot-t8-e0 --key can__256-w32-bcsr4-t8-e0 --key repeated-494_bus-w32-batch --key 494_bus-w2-hot-t8-e0-dram0.5
python3 scripts/decision_correction.py check --output runs/correction-reproduction/corrected --run-directory runs/correction-reproduction/native-run
python3 scripts/decision_correction.py record --output runs/correction-reproduction/corrected --run-directory runs/correction-reproduction/native-run
python3 scripts/decision_correction.py verify --output runs/correction-reproduction/corrected --run-directory runs/correction-reproduction/native-run
```

Run commands sequentially so simulation does not compete with native timing.
`check` uses AddressSanitizer, LeakSanitizer and UndefinedBehaviorSanitizer; leak
checking requires a normal process environment without ptrace tracing.
Native measurements and new prediction overhead will vary. The input-equivalence
and frozen-replay counter checks are exact in the pinned simulator environment.
