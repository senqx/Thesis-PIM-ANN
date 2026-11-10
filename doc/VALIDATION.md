# Validation performed on 10 November 2026

The current artifact contains **2,069 distinct replay records**. This revision
adds 360 scheduling-sensitivity and 420 training-calibration runs to the 1,289
previously validated records. Calibration runs are training evidence, not
additional independent performance replications. Three separately retained fresh
reproduction repeats are described below; they are not counted in that matrix.

## Checks executed for this revision

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
* **Documents:** both PDFs build offline with resolved citations/references and no
  significant horizontal overflow. The thesis has **65 pages** and the IEEE
  companion **8 pages**. Page overviews and representative full-size pages were
  inspected, including the availability diagram, sensitivity/selection figures,
  execution sketch, result tables, conclusion and reproduction appendix. A shared
  bibliography is used; publication details and DOIs were checked for the revised
  entries. The author and format follow the supplied preferences; no unspecified
  university-template compliance is claimed.

## Preservation and earlier validation

All prior tracked results are unchanged except the maintained source manifest.
The 49 inventoried core/search/simulator files and the measured study executable
match the previous checkpoint. Twenty new per-seed input-proof records bind the
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
`results/scheduling_source_recheck.json` records this revision's preservation and
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
