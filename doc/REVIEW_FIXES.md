# Review remediation record

The review covered commit `40d0edd` on 9 November 2026. Its old simulator revision
could not be recovered. The corrected artifact therefore establishes a new pinned
baseline and preserves the old files under `archive/pre-review` as superseded
material. It does not present corrected numbers as a reproduction of the old ones.

| Finding | Repair and retained evidence |
| --- | --- |
| 1. Overlapping adjacency | Prefix allocations for every node/level list, aligned to the native transaction size; bounds/span checks and large-list regression cases. |
| 2. Colliding quality layout | Cyclic permutation of selected slots; tests verify exact fixed-slot count, bijection and identical address multiset for every tested quality. |
| 3. Float32 layout reused for small footprint | Rebuild the workload-trained layout at each footprint; replay both through the simulator. The 128-byte case is explicitly hypothetical repacking, not quantised search. |
| 4. Proxy called row hits | Rename to consecutive-vector same-block fraction, reset at query boundaries and separate it from simulator classifications/cycles. |
| 5. Non-stock search loop | Observer calls in stock search; include entry reads and upper graph levels; 800 independent-index comparisons across corpus and shuffled insertion plus equality checks for every real evaluation query. |
| 6. Groups crossing boundaries | Bound partner placement by the current physical block's remaining capacity; regression cases include a short preceding group and width-dependent layouts. |
| 7. Universal BFS/learned-layout claims | Replace with conditional measured comparisons. Add identity, construction costs, coverage, training/window/block ablations; share synthetic corpus/query centroids. No optimality or causal-mechanism proof is claimed. |
| 8. Unfinished timing statistics | Ten paired real-data timing repetitions, exact per-split IDs, relative cycle differences, Student intervals with nine degrees of freedom. No inference from overlapping marginal intervals or claim of equivalence. |
| 9. Synthetic runs presented as real layout | Distinguish run construction from fixed-traversal HNSW placement. Include full-stream sorting and explicit scheduler/concurrency sensitivities. |
| 10. Missing query dependencies | Scope all timing to DRAM streams; preserve boundaries, drain between queries, bound outstanding reads and vary issue/concurrency. Compute, scratch, cache and host/PIM transfers remain outside scope. |
| 11. ClosedCAP ambiguity | Explicit cap one and four; replay actual layouts in both cases; document scheduling-time row classification and avoid inferring universal open-page dependence. |
| 12. Unverified byte-budget law | Decode actual addresses in simulator callbacks, verify native **32-byte** transactions and the 1-KiB contiguous row span; test six widths, three offsets and another mapper. Replace the law with a stated finite-grid saturation criterion. |
| 13. Reproduction/build gaps | Consolidate drivers; pin/archive-hash simulator dependencies; checked runner, complete raw stats and trace hashes, executable scripts, CI, data-derived tables and figures, documented build paths. Missing/interrupted outputs are regenerated. |
| 14. Missing recall/input checks | Exact top ten over the indexed 100k prefix; retain returned/truth IDs; reject short, empty, nonfinite and truncated input; check mapping output and explicit file close failures. |
| 15. Scholarship/novelty | Shared bibliography in both documents, contextual related-work comparison, PIMCQG coverage, exact PIMANN title and DRIM-ANN enhancement qualification. Literature check is explicitly targeted and dated. |
| 16. Counts, language and narrative | Every replay must reconcile submitted/completed/served/classified reads. Replace obsolete numbers and preparatory narrative. Distinguish simulation, footprint sensitivity, PQ and PIM system performance consistently. |

Additional validation found an out-of-bounds vendor read used to construct an
optional CPU prefetch address. The maintained build disables that path with
`HNSWLIB_USE_PREFETCH=0`; SIMD distance computation and stock search decisions remain.
The normal and sanitizer suites cover the maintained configuration.

The [validation record](VALIDATION.md) lists the completed checks and their limits.

The completed matrix consists of 175 controlled microbenchmark replays, 100 primary
SIFT replays, 80 controller sensitivities, 20 heuristic-ablation replays and ten
synthetic HNSW replays. `scripts/check_results.py` verifies all 385, their request
counts, query timing records, recall arithmetic and fixed-test ablation splits.

The primary conclusion changed: the workload-trained heuristic is slightly faster
than BFS at 512 bytes and slightly slower at 128 bytes under the default model.
This correction is material; the previous universal negative result is withdrawn.
The results support the thesis's revised DRAM-locality scope, not a completed PIM
accelerator or a general claim about all ANN datasets and hardware.

## Final robustness and explanation pass

The additional design in [RESEARCH_CLOSURE.md](RESEARCH_CLOSURE.md) is complete:
300 repeated controller replays, 90 graph-construction replays, and 16 command or
component-stream diagnostic replays. Together with the initial 385, the artifact
retains **791 named timing records**. These include deliberate diagnostic repeats;
the count is not a statistical sample size.

The new graph seeds reverse the 128-byte query-aware/BFS comparison, while the
512-byte advantage persists in the tested constructions. Both documents now
explain this distinction, the locality/parallelism trade-off, within-vector traffic,
paired uncertainty, and practical effect size. Their figures and tables are derived
from the retained evidence. A reading guide supports readers without ANN or DRAM
specialisation.

Cache reuse now validates result contents, sidecars and output hashes. Missing
sensitivity prerequisites fail before any replay; interrupted study regeneration
invalidates the completion marker. The result checker enumerates required names,
and analysis validates the complete evidence before replacing figures or tables.
The new corpus-ID translation is checked under shuffled insertion; all 100 original
primary trace hashes remain unchanged.

## Published baselines and available-request follow-up — 10 November

The literature correction is explicit: Coleman's published NeurIPS 2022 paper
adds profile-guided **Porder**, absent from its earlier preprint. Query-guided
placement is established prior art. PIMCQG's current public manuscript states
acceptance at SC26. Both documents now use that positioning and evaluate the
supplied RCM/Gorder/Porder routines as stronger baselines.

A fixed 494-comparison campaign adds expansion boundaries and within-expansion
schedules; four diagnostic repeats explain the round-robin contrast. The artifact
retains 1,289 named replays. Phase maps, per-phase transaction conservation, original
query timing, source equivalence, published-layout differential tests and gzip
recovery checks extend the previous correctness work. The full execution costs
remain outside the model; the dependency gap is reduced, not represented as fully
solved.

The previous 791 replay records remain unchanged. The 44-page thesis, 5-page paper
and all 37 document files from commit `71ce10b` are preserved byte for byte in
[the validated archive](../archive/2026-11-09-validated/README.md). They remain useful
evidence under their assumptions. This archive is distinct from the earlier
material superseded by correctness repairs.
