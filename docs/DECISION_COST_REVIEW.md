# Independent review of required decision costs

**Reviewed revision:** `67bb4be`, PR #1, 24 November 2026. **Recommendation:
resolve the two findings below before merging.** The retained artifact passes
its consistency checks, but those checks do not establish that every charged
operation is necessary for a simple decision rule.

This pass derives decisions and byte counts from the DPU kernel and input
structure, without calling `choose_corrected()` or `candidate_work()`.
The [audit script](../scripts/review_decision_costs.py) reproduces the
[numerical evidence](DECISION_COST_REVIEW.json). Alternative totals are
calculations using existing native measurements and simulator cycles; no new
native timing, DPU execution, model fitting or experimental claim is added.
The thesis tables and corrected artifact remain unchanged during this review.

## 1. Simple rules still pay for avoidable work

**High priority for accounting accuracy.** In
[decision_analysis.py](../scripts/decision_analysis.py), `candidate_work()`
charges constrained fixed and capacity rules for preparing and inspecting a
streaming reference and their retention candidate. The full-retention branch
of the reuse rule inherits the same charge. The reference bytes and these
particular feasibility decisions can instead be calculated from information
already available in the input header.

Let `R` be padded output rows, `M` source records, `Z` stored contributions,
`F` bytes per source record, and `C` the configured residency capacity. The
accounting starts with host CSR, so these are already known. Streaming, full
retention and hot retention have the same **metadata size**:

```text
metadata bytes = align_to_32(4 * (R + 1)) + 8 * Z
common metadata reads = 8 * R + 8 * Z
output writes = R * F
```

The kernel reads 32 pointer bytes per group of four rows and eight index/weight
bytes per contribution. Its streaming source reads are `Z * F`; full retention
loads `M * F`. Therefore, when `M * F <= C`, full retention meets the no-growth
traffic budget exactly when **`M <= Z`**. Neither candidate construction nor a
structural scan is needed to decide this. Only the selected representation
needs preparation.

For the actual frozen fixed policy, `hot`, let `H = min(M, floor(C/F))` and
let `hits` count references served by its frequency-ranked retained prefix.
Its source reads are `(H + Z - hits) * F`. For this ranking, the traffic test
is equivalent to **`Z >= H`**:

- If `Z < H`, all references fit in the retained prefix, but preloading `H`
  records reads more than streaming's `Z` records.
- If `Z >= H`, either at least `H` records are referenced, so each of the top
  `H` contributes at least one hit, or fewer are referenced and the prefix
  captures all `Z` references. In both cases, `hits >= H`.

The fixed rule can consequently choose hot or its fallback from known counts
before building either candidate. A rejected candidate should be charged for
the work actually used to reject it, not automatically for a full construction
and inspection. Later reuse-threshold decisions may still need structural work;
this proof does not eliminate that work.

The closed-form counts match **134 streaming/full rows and 52 hot rows** from
the primary calibration, held-out and controlled phases. All 24 held-out
fixed/capacity choices match the header-derived decisions. A further 7,736
small frequency-vector cases check empty, skewed and exact-boundary behavior.

The accounting effect is material. At 80 MB/s, zero added launch cost and one
use, keeping the same native encoder timings and excluding simple dispatch as
the current paper does gives:

| Rule | Reported mean regret | With header-based feasibility and one selected encoder |
| --- | ---: | ---: |
| Fixed hot with fallback | 11.46% | 1.90% |
| Capacity-first | 7.46% | 1.97% |

These remain modelled totals, not measurements of an integrated controller.
For the eleven held-out shapes with full retention available, the capacity
ledger adds 37.72–210.936 microseconds beyond the selected encoder. That extra
charge is not required by the decision above.

Section 12.3 already discloses that an analytical inspector or shared metadata
could cost less. That is a useful limitation, but it does not justify describing
the current charges as the work **required** by these simple rules. Either use
the direct header-based rules, or explicitly identify the old comparisons as
generic-inspector implementations and include the direct rules as baselines.
The corresponding Table 6, Figure 8 and summaries need synchronized accounting.

## 2. Selection receives per-input refresh timings without paying to obtain them

**Medium priority for deployment claims.** `choose_corrected()` calls `total()`
when selecting the model's candidate. That score includes each candidate's
`refresh_ns`, taken from the 31 native samples of the evaluation input. The
model setup ledger charges candidate preparation and inspection plus Python
prediction arithmetic; it does not include a defined procedure for obtaining
those per-input refresh estimates. Only the chosen policy's subsequent refresh
executions are charged.

This is not held-out DPU-cycle leakage into model fitting. It is an undisclosed
source of timing information in the setup-inclusive selection scenario. To
describe a deployable mechanism, either estimate refresh from previously
available calibration information or define and charge its profiling procedure.
An alternative appropriate for a negative result is to state explicitly that
per-input refresh knowledge is granted at no collection cost, making the
accounting optimistic in this respect.

The audit independently reconstructs **1,920 model decisions** (24 shapes,
two budget modes, eight lifetimes and five bandwidths). Setting every refresh
estimate to zero during selection changes **none** of their selected policies.
Launch cost is common to alternatives, so the three launch scenarios do not
add distinct decision cases. This check limits the consequence on this artifact;
it does not make collecting those estimates free in a deployed implementation.

## What remains supported

The native identity-copy correction and original device evidence remain sound
under the retained checks. This pass reran both artifact verifiers and all seven
existing accounting tests successfully. No source, sample or cycle record in
either retained artifact was changed. The tests check the declared ledger;
they currently do not challenge its necessity with the header-derived rules.

The central research conclusion survives a stronger analytical check. Give
the model free inspection, rejected-candidate construction, prediction and
native-cost knowledge, while still paying for its selected encoder, execution,
refresh and transfers. Compare its existing choices with the direct fixed and
capacity rules and the existing reuse rule at the reference 80 MB/s and zero
added launch cost, with the no-growth budget enforced. It still fails the declared
practical-success criterion at **all eight lifetimes**. The exact per-lifetime
mean times and worst slowdowns are in the audit JSON. This is an optimistic
accounting exercise, not an implemented faster selector or a new experiment.

Thus the remaining problems concern the precise cost attribution and how the
selection procedure is described. They do not erase the useful static-retention
regimes or rescue the tested model's recommendations. The separation between
the value of retention and the value of selecting it remains the thesis's
strongest engineering finding.

## Reproduce this review

```sh
python3 scripts/decision_artifact.py verify
python3 scripts/decision_correction.py verify
python3 scripts/test_decision_correction.py
python3 scripts/review_decision_costs.py
```

The last command checks the corrected manifest and writes only the audit JSON.
It records input/source hashes and never calls the existing decision ledger.
After changing the implementation, retain this reviewed checkpoint and document
which findings the replacement accounting resolves. No further broad simulator
campaign is needed to establish the header formulas or these diagnostic totals.
