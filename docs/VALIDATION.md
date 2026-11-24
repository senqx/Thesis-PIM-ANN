# Document and artifact validation

**Direct-rule accounting revision:** the [independent cost review](DECISION_COST_REVIEW.md)
is resolved in the current draft through header feasibility checks, lazy candidate
construction and explicit free refresh-time information. Subsequent review feedback
found no remaining conceptual accounting blocker. The final presentation revision
distinguishes the model's preparation path from the simple policies in Figure 5
and explains the one-use accounted regret next to Table 6. The prior corrected checkpoint
is preserved in the [archive](../experiments/decision-study/archive/README.md).
No native timing or simulator campaign was repeated for this accounting revision.

The supplied review assessed source and artifacts, without independently rendering
the PDF or rerunning the commands. The executed checks recorded here are local
validation. GitHub reports no attached CI checks; this is not a CI pass claim.

**Current checkpoint: 24 November 2026.** The follow-up adds a completed
standard sparse-operation study to the preserved 23 November graph pilot.
The [current PDF](../thesis/short-thesis.pdf) and
[build record](../thesis/build.json) belong together: the build record contains
the actual page count and source, PDF, figure and evidence-manifest hashes.
Page count is maintained there rather than duplicated across READMEs.

The new selector failed its declared practical-success criterion. The thesis
reports that result alongside useful static-retention regimes. It does not
claim hardware speedup, measured energy or complete application acceleration.
The [gap-closure record](GAP_CLOSURE.md) maps the research concerns to evidence
and explains the remaining scope limits.

## Corrected preparation and accounting checkpoint

The current thesis uses the [corrected artifact](../experiments/decision-study/corrected/README.md)
and its [manifest](../experiments/decision-study/corrected/manifest.json).
The original experiment remains independently auditable. This is a post-freeze
correction on already observed inputs; model coefficients, thresholds and DPU
kernels were not changed. The original kernel test split remains valid, while
the corrected host-cost analysis must not be described as fresh confirmation.

Retained measurement checks from the native correction (not newly executed in
the direct-rule revision):

- **446 new native preparation cases**, each with 31 samples after three
  warmups (13,826 retained sample rows). GCC 15.1.0 and `-O3 -std=c++17` match
  the declared environment. Cases ran sequentially without concurrent simulation.
- Regenerated metadata, feature values, arguments and expected outputs match
  **all 511 archived invocations** exactly. Original cycles are reused on that
  basis; this does not add 485 new simulation runs.
- Four representative replay records (six invocations) reproduce every counter,
  non-path option and complete output. The record names are listed below.
- **28 boundary/changed-structure native cases** pass AddressSanitizer,
  LeakSanitizer and UndefinedBehaviorSanitizer. The sandbox's ptrace environment
  prevented leak checking, so that check was rerun successfully outside it.
- Both artifact verifiers pass. The corrected verifier checks raw timing
  medians, decoded representations, all 23,040 unique scenarios, paired margins,
  payback thresholds, timing envelopes, success criteria and plotted data.
- The optimized native binary retains preparation and inspection calls inside
  their timer boundaries. Assembly inspection shows the hot refresh `memcpy`
  loop between the refresh timestamps, with an identity branch bypassing it.
- Final Python prediction arithmetic was timed after replay completed. Simple-
  rule dispatch remains outside the measured interval, as disclosed in the paper.

The direct-rule revision additionally passes **14 accounting regression tests**:
header capacity/traffic boundaries, absent and rejected full retention, selected-
encoder-only callbacks, guaranteed hot reuse, empty and zero-capacity inputs,
rejected-candidate charging, analytical reference counts, and preservation of all
1,920 model/rule decisions. The
[check record](../experiments/decision-study/corrected/accounting-checks.json)
distinguishes these tests from the seven tests retained in the earlier native
check file.

The [independent current audit](../experiments/decision-study/corrected/accounting-audit.json)
checks 134 streaming/full and 52 hot counter rows, 7,736 small frequency cases,
and all 1,920 model choices without calling the current decision ledger. It
verifies that direct fixed/capacity totals contain only the selected encoder.
The current verifier checks all 23,040 scenarios, preserved raw samples and
archived hashes, and confirms that every model scenario retains identical field
values, including prediction time. Simple-policy costs are recomputed.

Both charged and zero-selection-overhead criteria are recalculated from the
**current** fixed, capacity and reuse totals in
[success-criteria.csv](../experiments/decision-study/corrected/success-criteria.csv).
The independent zero-overhead calculation agrees with those results. Setting
refresh estimates to zero changes none of the selections; obtaining the original
estimates for free remains an explicit optimistic assumption.

The corrected selector still fails at all eight lifetimes, with or without
selection overhead. At 1/16/1,024 uses,
its mean accounted regrets are 89.71%/12.76%/5.22%. Native payback remains one use
for 15 of 16 narrow SpMM cases and two for one; only 9/16 retain a positive
first-use margin across observed sample extremes. Current results replace old
accounted values without deleting them. The
[protocol](../experiments/decision-study/corrected/PROTOCOL.md) discloses both
post-review accounting amendments and the free-information assumption.

## Preserved decision-study simulator evidence

The [manifest](../experiments/decision-study/manifest.json) contains **485 distinct
simulation records and 511 kernel invocations**. The difference is thirteen
records with three invocations each. Counts are:

| Role | Distinct records |
| --- | ---: |
| Calibration | 121 |
| Held-out primary comparison | 155 |
| Controlled capacity sweep | 66 |
| Additional four/twelve-tasklet checks | 50 |
| Boundary and changed-structure checks | 28 |
| Three-invocation changed-feature checks | 13 |
| Additional DRAM settings | 52 |

The sensitivity table has 65 rows: 52 new records and 13 reused default-setting
comparators. The 23,040 host-bandwidth/launch/lifetime scenarios are calculations,
not additional simulator runs. Four held-out matrices at six shapes make 24
related evaluation conditions, not 24 independent datasets. Replaying a record
does not increase the independent evidence count.

`python3 scripts/decision_artifact.py verify` passed. It checks:

- Every file/content hash, frozen kernel/native/protocol/model-rule hash,
  calibration hash and held-out input hash.
- Independent decoding of all weighted coordinates and complete expected
  outputs, deterministic source values, exact MRAM reads/writes and linked
  WRAM allocations.
- Recorded completion of every invocation and coverage of all feasible primary
  policy/input/shape combinations.
- Native preparation/inspection/refresh medians against the 31 retained raw
  samples per preparation, and consistency between phase tables and archived rows.
- All 23,040 accounted scenarios against the frozen rules and retained costs,
  plus plotted values, point counts and numeric x-axis order.

The original native implementation previously passed sanitizer checks on
fourteen boundary combinations. The corrected source has the 28-case check
reported above. These complement the independent representation/output checks.

Four fresh frozen-image replays passed:

| Record | Purpose |
| --- | --- |
| `494_bus-w2-hot-t8-e0` | Frequency retention |
| `can__256-w32-bcsr4-t8-e0` | Widest blocked representation |
| `repeated-494_bus-w32-batch` | Three invocations with changed source values |
| `494_bus-w2-hot-t8-e0-dram0.5` | Non-default DRAM options |

Each matched every simulator counter and non-path option and passed complete
output checking. These four records comprise six fresh kernel invocations.
They check reproduction of the retained programs, not hardware timing fidelity.
The [artifact instructions](../experiments/decision-study/README.md) give source
rebuilds, selected-record replay and full-inventory replay commands.

## Preserved historical evidence

The five earlier artifact audits were recorded as passing on 24 November
before this correction. Their evidence is unchanged; those unrelated campaigns
were not rerun for the correction:

| Artifact | Retained records | Check |
| --- | ---: | --- |
| [Initial WRAM pilot](../experiments/wram/README.md) | 160 | File hashes and distinct records |
| [Prepared-access study](../experiments/access-plan/README.md) | 137 | Hashes, counters, outputs and paired controls |
| [Three-size checkpoint](../experiments/access-plan-scaling/README.md) | 108 | Records and 792 CPU timings; configurations included in the next row |
| [Five-size study](../experiments/access-plan-fivepoint/README.md) | 180 | Records, 1,320 CPU timings, preserved inputs and five sizes |
| [Baseline controls](../experiments/baseline-gates/README.md) | 38 | Fourteen new records and 24 reused comparators; outputs, traffic, WRAM and hashes |

The last two artifacts contain 194 distinct configurations with an intersection
of exactly 24. Their counts must not be summed as independent experiments.
The 137-record study includes 132 performance configurations, two feature-update
checks and three transfer probes. Earlier replays remain documented in their
artifacts; they were not rerun merely to revise the text.

```sh
python3 scripts/wram_verify.py
python3 scripts/access_plan_artifact.py verify
python3 scripts/access_plan_scaling.py verify
python3 scripts/access_plan_fivepoint.py verify
python3 scripts/access_plan_gates.py verify
python3 scripts/decision_artifact.py verify
```

## Document checks

- The PDF was rebuilt and its page count established with `pdfinfo`. The title,
  author and date match the source. No supervisor or university affiliation is
  invented; no additional university formatting requirement was supplied.
- Every page was reviewed for layout, with separate inspection of the numerical
  plots, diagrams and bibliography. Captions stay with their figures/tables.
- Text extracted from the final PDF contains all checked source prose, heading,
  code and caption blocks checked after whitespace normalization and removal
  of page headers/footers. The numeric tables are checked through their retained
  data and generated source.
- Eight figures and six numbered tables resolve. Four result tables are generated
  from retained data. Three explanatory diagrams are labelled as schematics or
  an evaluated process; the other five figures contain numerical evidence.
- Historical data curves have five actual sizes. The follow-up capacity and width
  sweeps have five executed settings, with explicitly missing infeasible full-
  retention points. The lifetime curves are labelled calculations, not new runs.
- Thirteen references follow first-citation order. DOI/title/publication metadata
  retain the targeted literature checks recorded in the novelty audit; inspected
  preprints are labelled. This revision does not claim an exhaustive literature search.
- README, manuscript, experiment inventory and novelty/gap records distinguish
  the historical pilot from the new completed evaluation. All RQs are answered
  explicitly in the conclusion, including the unsuccessful selector result.
- The framing revision identifies local reuse as the completed Stage 1 study,
  with access prediction and heterogeneous coordination as future directions.
  It distinguishes performance-choice errors from incorrect output. The
  frozen cycle model and original retained evidence are unchanged. Current
  native source and cost accounting are separately versioned and validated.
- All checked live local Markdown links, Python syntax and Git whitespace
  checks passed. Immutable source snapshots retain original relative-link context
  and are excluded from the live-link audit. Links
  embedded in the standalone PDF resolve to repository URLs.
- A second build reproduced identical corrected reports, figures, PDF and
  build record in the pinned local environment; the original evidence stays fixed. Source rebuilds of DPU
  instructions remain a separate check because the upstream linker can vary
  instruction layout with map iteration order.

The [document instructions](../thesis/README.md) give dependency versions and
commands. Fixed PDF/figure timestamps support deterministic builds; the research
date is stated in the text. The current local source and PDF are synchronized;
this record does not assert that uncommitted changes have been published.

## Interpretation

The evidence closes the bounded study's main baseline, capacity, native-cost,
held-out-selection, state-validity and simulator-sensitivity gaps. Observed
native timing envelopes qualify near-zero payback margins. The selector's
failure is preserved rather than repaired by tuning on its test outcomes.

Hardware timing, energy, large distributed workloads, full application costs and
universal novelty remain unestablished. The cost interval starts with host CSR
and loaded device code; omitted cleanup, simple-rule dispatch and deployment
work must fit within any positive reported margin. Validation supports the
stated experimental conclusions, not final university acceptance or a general
adaptive PIM system.
