# Validation performed on 9 November 2026

The maintained checks passed for the completed artifact and the final research pass.

* **Build and core behaviour:** `make test` passes 27 root-tool checks, 800
  independent-index stock-search comparisons, four Python pipeline test groups,
  and three recovery/diagnostic test groups. The C++ comparisons cover continuous
  and tie-heavy data, `ef < k`, corpus insertion and shuffled insertion. They also
  verify adjacency IDs against the independent index's external corpus labels.
* **Sanitizers:** AddressSanitizer and UndefinedBehaviorSanitizer pass the extended
  C++ suite with `HNSWLIB_USE_PREFETCH=0`. LeakSanitizer is incompatible with this
  environment's tracing restrictions, so leak detection is disabled; no leak-check
  result is claimed.
* **Clean build:** an isolated source copy in `/tmp/thesis-strengthening-check`
  rebuilds from empty build directories and passes `make test`. The unchanged
  pinned simulator had also passed the prior isolated offline setup and exact
  sequential-replay check documented in the remediation phase.
* **Actual simulator integration:** `make test-simulator` passes native 32-byte
  geometry, both mappers, query draining, outstanding bounds, page policies,
  malformed-input rejection, and non-perturbing command observation.
* **Complete evidence:** `scripts/check_results.py` validates every one of the
  **791 expected replay names**, with submitted/completed/served/classified counts,
  per-query service intervals, exact ID recall and matching query partitions.
  It checks the original 385 records, 300 repeated controller records, 90 graph
  records, and 16 diagnostic records. These are replay counts, not independent
  statistical replications.
* **Primary preservation:** regenerating all ten primary query splits with the
  insertion-order-capable driver preserves split IDs, returned/truth IDs, logical
  records, mappings, and all **100 transaction-trace hashes**. Proof records are in
  `results/robustness/reference/seed*/primary_equivalence.json`.
* **Graph variation:** four distinct graph hashes are retained. Each construction
  is stable across its query splits. Corpus IDs, exact-neighbour IDs and test
  selection remain comparable after insertion shuffling. Layout comparisons use
  matching work within each graph, and achieved recall is reported separately.
* **Mechanism checks:** command read counts reconcile with requests. Command and
  no-command cycles sum to total cycles. Full command traces agree with command
  counters. Observed mixed-stream and microbenchmark replays reproduce prior
  timings; adjacency-only traces agree across the two layouts. Filtered vector and
  adjacency read counts sum to the original mixed count. Static bank-window counts
  reset at query boundaries and retain their input trace hashes.
* **Recovery:** missing query sidecars, truncated JSON or cache stamps, wrong
  counts, wrong means, wrong trace identities, and changed cached files invalidate
  reuse. Missing or partial sensitivity traces fail before any replay. Analysis
  checks the complete result matrix before generating output.
* **Source consistency:** Python formatting preserves parsed syntax trees, unused
  imports are removed, and Ruff's `F` checks pass. Formatting the modified C++
  sources leaves the study binary byte-for-byte unchanged. The source inventory is
  `results/artifact_manifest.json`; generated-data provenance is
  `doc/generated/provenance.json`. Git whitespace checks pass. The attributes
  preserve hashed result bytes and recognise CSV record terminators and the raw
  recall export's trailing ID separator; scientific records are not reformatted
  merely to satisfy source whitespace rules.
* **Documents:** both PDFs build offline using Tectonic 0.15.0 and the pinned bundle.
  The thesis has **44 pages** and the companion paper **5 pages**. There are no
  unresolved references/citations or significant horizontal overflows. Page
  overviews and representative full-size pages were inspected, including the
  pipeline, placement example, command timeline, primary results, repeated
  sensitivities, graph variation and mechanism accounting. Short contents-list
  captions and nearby tables improve navigation without removing explanations.

These checks validate the artifact and its stated stream model. They do not
validate HBM timing against a physical device, implement quantised HNSW, or measure
PIM application speedup. Additional real datasets, search operating points and an
integrated execution model remain explicit future work.
