# Document and artifact validation

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

## Current decision-study evidence

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

Native preparation also passed AddressSanitizer, LeakSanitizer and undefined-
behavior checks on fourteen boundary combinations. The optimized binary was
inspected to confirm that preparation, inspection and refresh execute inside
the timed regions, including the refresh copies. These tests complement, rather
than replace, the independent CPU output/representation checks.

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

All five historical audits passed again on 24 November against the unchanged
retained evidence:

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
- Text extracted from the final PDF contains all 215 source prose, heading,
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
- Local Markdown links, Python syntax and Git whitespace checks passed. Links
  embedded in the standalone PDF resolve to repository URLs.
- A second build reproduced identical reports, figures, archived evidence, PDF
  and build record in the pinned local environment. Source rebuilds of DPU
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
