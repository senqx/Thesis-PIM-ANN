# Validation performed on 10 November 2026

The current artifact contains **2,069 distinct replay records**. The scheduling
and profiling extension added 360 sensitivity and 420 calibration runs to the 1,289
previously validated records. Calibration runs are training evidence, not
additional independent performance replications. Three separately retained fresh
reproduction repeats are described below; they are not counted in that matrix.

## Current document set

**The current thesis has 67 PDF pages, including the title page and front matter.**
The narrative revision supersedes the 69-page contribution checkpoint `c673686`.
Historical checkpoints below retain the counts of their own PDFs.

Read these PDFs and this validation record from the **same Git revision**.
The thesis is the full argument; the IEEE companion condenses it, and the defence
presentation reuses its figures and values. Exact distributed-file hashes are
recorded below. PDF metadata may differ on a later rebuild;
the numerical regeneration checks compare the evidence-derived content separately.

| Document | Extent |
| --- | --- |
| [Full thesis](pim_ann_thesis.pdf) | 67 pages |
| [IEEE companion](pim_ann_ieee.pdf) | 8 pages |
| [Defence presentation](pim_ann_defence.pdf) | 14 slides: 12 main and 2 backup |

These counts were confirmed by rebuilding the current sources and running
`pdfinfo` on each output:

```bash
TECTONIC_OFFLINE=1 bash scripts/build_docs.sh
pdfinfo doc/pim_ann_thesis.pdf   # Pages: 67
pdfinfo doc/pim_ann_ieee.pdf     # Pages: 8
pdfinfo doc/pim_ann_defence.pdf  # Pages: 14
```

The build checks both the README's linked counts and the **Extent** column above
against the PDFs. At checkpoint `bdab0e6`, a temporary copy with an incorrect
69-page extent for its 68-page thesis was rejected. The current document-only
rebuild adds no experimental results.

SHA-256 of the distributed PDFs (paths relative to the repository root):

```text
469d56693783eef90c30bf5e23a9d2e5dc081f4ae486346b8b98340559b891e7  doc/pim_ann_thesis.pdf
019f42a87558f2609cef8753f8f0191c53199e2f2cdf934ae88ceb8044fb13fe  doc/pim_ann_ieee.pdf
e960b2fda9c2b7a0260d84f04d12e900cd48a68cf57407eb614f0145825695ac  doc/pim_ann_defence.pdf
```

Check with `sha256sum doc/pim_ann_{thesis,ieee,defence}.pdf` from the repository root.

All 2,069 current records and the previous 1,289-record checkpoint use the same
corrected pinned simulator. Only the pre-review evidence was invalidated by the
original correctness repairs; see the
[baseline distinction](REPRODUCIBILITY.md#corrected-baseline-and-historical-evidence).
Historical checkpoints below retain their original page counts and validation
scope. They do not describe the current PDFs.

## Narrative and structure check

The thesis and IEEE companion now follow the requested sequence: domain and
motivation; prior work; research questions; study design and methodology;
results; what we learned and practical implications; conclusion. The thesis
introduces the memory wall, latency, bandwidth and PIM before ANN and DRAM
mechanisms. Three former method chapters form one chapter with four navigable
sections. The contribution is previewed with the RQs and explained with evidence
after the results. The reading guide, README and defence opening follow this order.

All three PDFs were rebuilt offline, with resolved references and no significant
overflow. The revised chapter transitions, contents, contribution discussion and
companion layout were visually checked. Documentation links, current evidence
counts and page counts pass `scripts/check_docs.py`. The main method text is unchanged apart from headings. The six included
methodology/result fragments retain their experimental content: heading levels
change, the companion's final table is declared earlier to keep it near its
results, and two interpretation paragraphs move to the discussion. All **5,082
protected tracked files** outside this structural edit match their pre-edit
hashes. All 2,069 replay records, frozen protocols, numerical tables/figures and
experimental/analysis code are preserved. No simulations or full numerical
regeneration were needed. Current PDF hashes and source provenance are refreshed.

## Contribution clarification (`c673686`)

This editorial pass makes each contribution explicit in the thesis introduction,
related-work section and conclusion, with corresponding updates to the README,
research position, IEEE companion and defence material. It distinguishes the core
empirical findings (placement limits and scheduling reversals) from the derived
engineering guidance (an execution proposal with cost thresholds). Gorder/Porder
are measured placement baselines; the cited PIM systems are literature comparisons.
No new algorithm, general locality principle or application/PIM speedup is claimed.

All three PDFs were rebuilt offline. The changed pages and contribution slides
were visually checked; references, overflow, page counts and local navigation
pass `scripts/check_docs.py`. The numerical examples use the retained generated
values and tables. All **5,088 protected tracked files** outside this editorial
scope match their pre-edit hashes, including raw evidence, generated numerical
tables/figures, frozen protocols and experimental/analysis code. The **2,069**
records remain unchanged; the simulation campaign and full numerical analysis
were not rerun for this prose revision. PDF hashes, source inventory and
provenance identify the revised document set.

## Earlier submission presentation check (`bdab0e6`)

The experimental scope remains frozen. At the start of this review, GitHub
`main` and the local checkout both pointed to `44200ad`, whose README already
reported 2,069 records. The historical overview now has a prominent status label;
the old root overview address leads to the maintained README. The current PDFs,
validation and baseline history are linked together.

* **Retained evidence:** `python3 scripts/analyze.py` completed the full validation
  of all **2,069 replays**, including phase/query accounting and training selection,
  and regenerated the analyses. All **18 root CSV summaries** and **36 generated
  TeX files** are byte-identical to their prior versions. All **17 figure renders**
  match at 120 dpi; original figure PDF bytes were retained to avoid timestamp-only
  changes. No new simulations or independent performance observations were added.
* **PDF review:** all **30 tables and 16 figures** in the thesis and **six tables
  and three figures** in the companion were checked on rendered pages. Numeric
  entries from the 31 generated table bodies match the corresponding PDF-page
  text; the five authored explanatory tables were reviewed against the model and
  cited scope. Captions, baselines and interval labels were checked. The conclusion
  now answers RQ1–RQ3 explicitly. All 14 defence slides were visually checked.
* **References:** revised entries were checked against Crossref and official
  proceedings metadata. The PIM primer and Coleman/Porder entries now include
  their published DOIs and pages; the SC/USENIX entries include page ranges, and
  DiskANN links to its paper record. PIMCQG retains its dated public acceptance
  disclosure. This is a bibliography check, not a new comprehensive literature survey.
* **Build and navigation:** all three PDFs build offline, with resolved references
  and no significant horizontal or vertical overflow. Checks resolve **118 local
  Markdown links** and all **14 presentation evidence links**. The build rejects
  stale current evidence totals, linked page counts and slides spilling onto extra
  pages. The preceding revision's
  [full CI run](https://github.com/senqx/Thesis-PIM-ANN/actions/runs/42818960856)
  passed; the retained-record and document checks above were also run locally here.
* **Preservation:** all retained measurements, frozen protocols, search/simulator
  sources and validated snapshots are unchanged. Of 4,980 initially protected
  paths, only the two archive navigation pages changed; the other 4,978 match their
  pre-edit hashes. Source inventory and generated provenance reflect the final
  documentation/build-check revision. No numerical analysis code changed.

## Historical editorial revisions

<details>
<summary>Superseded document versions: editorial and architectural review notes</summary>

### Editorial checkpoint `44200ad`

The experimental scope and results are unchanged. The complete text of the
incoming thesis from checkpoint `7f5dfdc` was extracted and reviewed, including tables, captions,
appendices and bibliography. This pass clarifies the 140-case denominator,
distinguishes the contribution explicitly from Gorder/Porder and PIM-ANN systems,
adds a worked service-only overhead example and tightens the conclusion. It also
corrects the explanation of `efSearch`: the retained best-result set is bounded,
while the pending candidate frontier can contain more entries. The stock source
was checked for that distinction; search code was not changed.

The PDFs at checkpoint `44200ad` built offline with resolved citations/references
and no significant horizontal overflow: 68 pages for the thesis and 8 for the companion.
Page overviews cover both complete PDFs, with detailed visual checks of the
changed passages and the conclusion. Removing repetition and short overflow
pages reduced the thesis length. The
[campaign inventory](REPRODUCIBILITY.md#record-counts-and-frozen-protocols)
reconciles current and historical counts without altering frozen protocol hashes.
Local documentation links and Git whitespace checks pass.

The overhead arithmetic was recomputed from retained selection summaries:
5,716,851.1 mean calibration cycles divided by 5,802.4195 mean saved cycles per
query is 985.253 query services; consuming half the saving gives 1,970.506.
The 200-query saving is 1,160,483.9 cycles. These are ratios and differences of
existing means, not new simulations or deployment predictions. All **4,977
protected evidence/source files** are unchanged, and no computational or analysis
code changed. Source hashes and figure provenance reflect the editorial revision.
The preceding commit's
[full CI run](https://github.com/senqx/Thesis-PIM-ANN/actions/runs/42814930326)
passed; that validation is distinguished from the document checks performed here.

### Architectural checkpoint `7f5dfdc`

The preceding documentation revision added no experimental observations. It clarified the
original contribution, the proposed host/near-memory division of work, transfers,
hardware requirements, statistical versus practical significance, profiling
decisions and the limits of generalisation. The existing reading guide now gives
answers to the thirteen defence questions. The README already reported 2,069
records before this pass; 1,289 refers to a preserved earlier checkpoint.

At the superseded checkpoint `7f5dfdc`, both PDFs built offline with resolved
citations/references and no significant horizontal overflow: 69 pages for that
historical thesis and 8 for its IEEE companion. The new execution diagram and the changed contribution,
profiling, interpretation, architecture and conclusion pages were visually
reviewed. Source/guide links, Ruff's `F` checks and Git whitespace checks pass.
The figure generator's numerical-analysis code is unchanged, verified by
comparing its Python syntax tree with the preceding revision while excluding the
diagram function. All **4,977 protected files** in the evidence, reproduction,
archives, core/search/simulator and test directories match their pre-edit hashes.
The source inventory and figure provenance are updated for the revised text and
diagram. The simulation matrix, calibration records and fresh-reproduction
records below are retained evidence; they were not rerun for this prose revision.

</details>

## Checks executed for the scheduling and profiling extension

* **Core and pipeline tests:** `make -j2 test` passes 27 root-tool checks, 800
  independent-index stock-search comparisons, four pipeline groups, three
  recovery/diagnostic groups, six follow-up groups, three scheduling groups and
  five profiled-fetch groups. The reproduction suite was subsequently expanded
  to four groups and passes. Tests include phase membership, transaction
  conservation, query accounting, training/test separation and fixed selection.
  Deliberately adverse held-out outcomes cannot change a training-only choice.
  Reproduction tests reject changed statistics, query IDs and phase service even
  when aggregate cycles match, while accepting path and gzip-header differences.
* **Simulator integration:** `make test-simulator` passes checks of native
  32-byte geometry, both mappers, query draining, outstanding limits, row policies,
  malformed-input rejection and non-perturbing command observation. Core search
  and simulator sources are unchanged from the previous validated checkpoint.
* **Complete evidence matrix:** `scripts/analyze.py` runs the full result checker
  and regenerates all analyses successfully. Every one of the **2,069 expected
  replay paths** validates, with complete submitted/completed/served/classified
  accounting and query/phase sidecars. The checks also cover graph/split identity,
  recall, primary trace equivalence, component streams and command conservation.
  This validates retained evidence; it is not a second execution of the entire
  simulation matrix.
* **Scheduling sensitivity:** all 360 new replays pass source-trace, configuration,
  batch-membership, phase-multiset and original-query timing checks. The 60
  raised-outstanding-limit records reproduce default cycles exactly; the largest
  default observed peak is 50 uncompleted reads. Original-query service includes
  gaps between phases. All orders and losses are retained.
* **Training-selected fetching:** all 420 calibration replays pass. The first 50
  training IDs are disjoint from the 200 held-out IDs within each split. The
  checker recomputes all 140 choices from calibration cycles alone, with fixed tie
  rules, and then checks their matching held-out paths. All choices match the
  retrospectively best fixed held-out order in this matrix. This is an
  exploratory observation, not a general guarantee: individual-query regressions
  and the published-placement comparison remain visible.
* **Fresh reconstruction and simulation:** `scripts/reproduce_replay.py` rebuilds
  HNSW graph/search inputs in new directories, checks their hashes, regenerates
  traces and invokes the simulator directly, bypassing replay caches. Three runs
  match all scientific outputs, including every query/phase interval:

  | Reference record | Fresh total cycles |
  | --- | ---: |
  | `followup/reference/seed1/roundrobin/bfs_512.json` | 6,673,884 |
  | `scheduling/seed1/alternate_mapping/roundrobin_512.json` | 44,097,986 |
  | `calibration/seed1/default/roundrobin_512.json` | 1,780,689 |

  The fresh raw JSON, lossless sidecars, reconstruction logs and comparison reports
  are retained under [reproduction/](../reproduction/README.md). These are three
  spot checks using the existing checked executables, not a full-matrix rerun,
  a new compiler/hardware validation or independent statistical samples. The
  canonical SIFT files also match the recorded dataset hashes.
* **Statistics and presentation:** paired 95% intervals use ten reference split
  effects. Construction comparisons use three matched splits and descriptive
  ranges. Per-query regressions and empirical 95th-percentile changes remain
  descriptive. All fixed orders, selected paths, published baselines, calibration
  costs and absolute service values are generated from raw evidence. Ruff's `F`
  checks and Git whitespace checks pass. CI checks regeneration of every root
  result CSV and generated TeX table/value file.
* **Documents at that checkpoint:** both PDFs built offline with resolved citations/references and no
  significant horizontal overflow. The thesis had **65 pages** and the IEEE
  companion **8 pages**. Page overviews and representative full-size pages were
  inspected, including the availability diagram, sensitivity/selection figures,
  execution sketch, result tables, conclusion and reproduction appendix. A shared
  bibliography is used; publication details and DOIs were checked for the revised
  entries. The author and format follow the supplied preferences; no unspecified
  university-template compliance is claimed.

## Repository cleanup

After removing local scratch files and redundant download/installer copies,
`make -j2 test` and `make test-simulator` pass. The retained 2,069-record
matrix is unchanged from the complete validation described above.
All 4,918 protected evidence/source files match their pre-cleanup hashes,
including the current PDFs and both validated document snapshots. Canonical SIFT
hashes were checked before deleting the redundant downloaded HDF5. Document
checks, relocated links and Git whitespace checks pass. Historical progress notes
were archived, the unused microbenchmark wrapper removed, and a `clean-work`
target added. The source inventory reflects these documentation/build-file
changes; computational source and numerical evidence are unchanged. This cleanup
adds no experimental observations.

## Preservation and earlier validation

All prior tracked results are unchanged except the maintained source manifest.
At the scheduling checkpoint, the 49 inventoried core/search/simulator files
and the measured study executable matched the preceding checkpoint. Twenty new per-seed input-proof records bind the
scheduling and calibration campaigns to their source inputs.

All **57 document files** from `94d3f1d` are preserved byte for byte in
[archive/2026-11-10-validated](../archive/2026-11-10-validated/README.md), including
the 51-page thesis and seven-page companion. The **37 document files** archived
from `71ce10b` also remain byte-identical, including the earlier 44-page thesis
and five-page paper. Preservation does not relabel older evidence as a new check.

The [previous validation record](../archive/2026-11-10-validated/doc/VALIDATION.md)
retains these checks, which were not repeated as fresh experiments in this revision:

* 90 exact permutation comparisons between adapted and untouched published
  RCM/Gorder/Porder routines on 30 weighted directed graphs.
* AddressSanitizer and UndefinedBehaviorSanitizer checks of the published-layout
  methods on the reference graph, reproducing the normal mappings. The earlier
  core-search sanitizer check also applies to unchanged sources. Leak detection
  was disabled; no LeakSanitizer result is claimed.
* A source-only build in a fresh directory, using the pinned published archive,
  followed by the normal test suite.
* Reconstruction of 19 follow-up graph/split preparations and independent
  reproduction of 114 earlier identity/BFS/query-aware flat-trace hashes.

`results/artifact_manifest.json` inventories maintained source hashes.
`results/scheduling_source_recheck.json` records the scheduling extension's preservation and
input-proof checks; `results/reproduction_checks.json` hashes the fresh evidence.
Earlier `followup_source_recheck.json` and `final_source_recheck.json` retain their
original scope. `doc/generated/provenance.json` identifies the inputs and
generators behind current tables and figures.

The [reproducibility guide](REPRODUCIBILITY.md) gives the full fresh-checkout
workflow and an exact comparison against a separate retained result tree. These
checks establish the stated comparisons within the model. They do not validate
HBM timing against physical hardware or measure application/PIM speedup. Compute,
caches/local storage, inter-query concurrency, actual scheduling/buffering cost
and host/PIM communication remain unmeasured. The 128-byte case is a hypothetical
repacking of float32 search.
