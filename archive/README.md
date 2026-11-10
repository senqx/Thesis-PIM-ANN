# Preserved work

Use the [current PDFs and matching validation](../doc/VALIDATION.md#current-document-set) and
[reproducibility guide](../doc/REPRODUCIBILITY.md) for the maintained artifact.
This directory keeps earlier work accessible without mixing it into the current
results or build.

| Directory | Purpose |
| --- | --- |
| [2026-11-09-validated](2026-11-09-validated/README.md) | Byte-identical validated documents before the published-layout follow-up |
| [2026-11-10-validated](2026-11-10-validated/README.md) | Byte-identical validated documents before scheduling sensitivity and profiling |
| [pre-review](pre-review/README.md) | Superseded evidence and drivers, including results invalidated by correctness repairs |
| [review-notes](review-notes/) | Historical overview, review dispositions and early implementation notes, relocated during repository cleanup |

All 2,069 maintained replay records remain under [`results/`](../results/).
The previous 1,289-record validated checkpoint uses the same corrected baseline;
360 sensitivity and 420 calibration runs extend it. Only `pre-review/` contains
evidence invalidated by the earlier correctness repairs.
The [preservation guide](../doc/RESULTS_PRESERVATION.md) explains checkpoint status;
the [identity translation](../doc/HISTORY_REWRITE.md) resolves old commit IDs.
