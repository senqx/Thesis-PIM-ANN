# Validation performed on 10 November 2026

The previous validated checkpoint is preserved in
[archive/2026-11-09-validated](../archive/2026-11-09-validated/README.md).
Its 37 document files match commit `71ce10b` byte for byte, and its 791 raw replay
records remain unchanged. The current artifact supplements that evidence.

* **Build and core behaviour:** `make test` passes 27 root-tool checks, 800
  independent-index stock-search comparisons, four Python pipeline groups, three
  recovery/diagnostic groups and six follow-up groups. The new groups check phase
  membership, transaction conservation, exact round-robin ordering, original-query
  accounting across phase gaps, compressed sidecars and published-layout adapters.
* **Published implementation:** the NeurIPS 2022 supplementary archive is SHA-256
  pinned. The adapted and untouched implementations produce identical permutations
  for RCM, Gorder and Porder on 30 weighted directed graphs with 20–513 nodes and
  degrees up to 32: **90 exact comparisons**. The ordered-set helper preserves the
  score and tie semantics; the supplied layout/window rules are retained.
* **Sanitizers:** all three published-layout methods run under AddressSanitizer and
  UndefinedBehaviorSanitizer on the 100,000-node reference graph and reproduce the
  normal mappings. The previous core-search sanitizer check remains applicable to
  unchanged core sources. Leak detection is disabled because of this environment's
  tracing restrictions; no LeakSanitizer result is claimed.
* **Fresh build:** a source-only copy in a new `/tmp/thesis-followup-clean-*`
  directory builds both published adapters from the verified source archive and
  passes the complete normal suite. Its inputs include only the small retained
  fixture needed by the cache tests. Formatting preserves the measured study and
  published-adapter executable bytes with the same compilation/link inputs;
  binary identity across different build directories is not assumed.
* **Simulator integration:** native 32-byte geometry, both mappers, query draining,
  outstanding bounds, page policies, malformed-input rejection and non-perturbing
  command observation pass. The simulator/library used by all retained replays is
  unchanged; expansion boundaries use the existing draining marker.
* **Complete matrix:** `scripts/check_results.py` validates **all 1,289 expected
  replay names**: the previous 791, 494 follow-up comparisons and four scheduling
  diagnostics. Submitted, completed, served and classified counts agree. Every
  sidecar is checked, including losslessly compressed phase timings. This is a
  replay count, not a count of independent statistical replications.
* **Search and layout preservation:** all 19 follow-up graph/split preparations
  reproduce their earlier graph, insertion order, logical records, original ten
  mappings, query partitions and returned/exact IDs. The independent emitter
  reproduces all **114 reused identity/BFS/query-aware flat trace hashes** (60 on
  the ten reference splits and 54 on the other constructions). The earlier
  100-primary-trace proof remains historical evidence; it is not relabelled as a
  new 100-trace check by the follow-up binary.
* **Phase integrity:** phase maps are reconstructed from the hashed original
  logical records and graph, then compared byte for byte and bound to their source
  and content hashes. Each candidate belongs to its preceding list at the same
  level. The schedules preserve each phase's transaction multiset, including
  duplicates. Phases aggregate into the same 200 queries and read counts, retaining
  inter-phase gaps in query service. Static RCM/Gorder mappings remain identical
  across splits of the same graph.
* **Mechanism:** four new command-observer replays reproduce their original total
  cycles, row classifications and every phase service interval. Command/no-command
  accounting reconciles exactly. Offered-bank windows reset at every phase and
  retain trace hashes; they are not labelled controller occupancy. The previous
  component-stream and command-trace invariants also pass the full result checker.
* **Statistics and presentation:** paired intervals use ten reference split effects.
  Graph-construction comparisons use three matched splits and descriptive ranges.
  Per-query improvement fractions and empirical 95th-percentile service checks are
  descriptive, without treating reused queries as independent replications. Python
  formatting and Ruff's `F` checks pass, and Git whitespace checks pass.
* **Documents:** both PDFs build offline, with resolved citations/references and no
  significant horizontal overflow. The thesis has **51 pages** and the
  companion has **7 pages**. Page overviews and representative full-size
  pages were inspected, including the phase diagram, layout and scheduling plots,
  result tables and conclusion. The older 44-page thesis and 5-page companion
  remain in the validated archive.

`results/artifact_manifest.json` inventories the current maintained sources.
`results/followup_source_recheck.json` describes the follow-up preservation proof;
`results/final_source_recheck.json` retains the earlier checkpoint's proof.
`doc/generated/provenance.json` records the result and generator hashes behind the
current generated artifacts.

These checks establish the artifact's stated comparisons. They do not validate
HBM timings against physical hardware or supply an application-speedup measurement.
The model omits compute, caches/local storage, inter-query concurrency, real
mapping/scheduling cost and host/PIM communication. The 128-byte footprint remains
a repacking sensitivity of float32 search.
