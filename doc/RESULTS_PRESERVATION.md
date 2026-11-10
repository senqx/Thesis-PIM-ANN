# What is preserved, and where

Earlier work remains part of this project even when the main argument becomes
more focused. A revision to the interpretation is not a deletion of its evidence.

| Material | Location | Status |
| --- | --- | --- |
| Validated thesis, companion paper, source text, graphics and tables before the published-layout/expansion follow-up | [9 November checkpoint](../archive/2026-11-09-validated/README.md) | Byte-for-byte copies from commit `71ce10b`; useful prior version. |
| Original 791 validated replay records, query timings, splits and correctness evidence | Original paths under [results](../results/) | Retained as the flat-replay and diagnostic baseline; still used in the thesis. |
| Published-layout and expansion-bounded measurements | [results/followup](../results/followup/) | Additional evidence, kept separately. |
| Validated documents before scheduling sensitivity and the training-selected path | [10 November checkpoint](../archive/2026-11-10-validated/README.md) | All 57 document files copied byte for byte from `94d3f1d`, including the 51-page thesis and seven-page paper. |
| Scheduling sensitivity and training calibration | [results/scheduling](../results/scheduling/) and [results/calibration](../results/calibration/) | Separate additions: 360 held-out sensitivity replays and 420 calibration replays. Earlier evidence stays in its original paths. |
| Earlier material superseded by correctness repairs | [pre-review archive](../archive/pre-review/README.md) | Historical record; do not mix these numbers into validated comparisons. |
| Complete source history of the validated checkpoint | Git commit `71ce10b` | Reconstructs the source and all tracked evidence at that point. |

The current PDFs give the developing argument; they need not carry every raw
measurement as a table. Supporting measurements stay in the repository with their
configuration, provenance and interpretation. Generated current summaries may be
regenerated, while the checkpoint retains their previous versions.

Large transaction traces in `work/` are reproducible intermediates, following the
existing artifact policy. Follow-up raw phase timings are retained losslessly as
`.queries.csv.gz`, together with phase-to-query maps and trace hashes. Compression
does not remove measurements. Do not use `make clean` or a new study to remove
tracked results or any archive.
