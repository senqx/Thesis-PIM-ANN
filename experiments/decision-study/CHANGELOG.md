# Post-freeze correction log

## 24 November 2026 — fair preparation and deployment accounting

This branch corrects two implementation/accounting issues found during independent review.
It deliberately preserves the original raw samples, frozen model, replay archive and
historical result tables.

### Native preparation

- Only the frequency-based `hot` policy allocates and sorts a source permutation.
- Only `hot` constructs the inverse permutation used to rewrite sparse column IDs.
- Identity policies write original column IDs directly.
- Feature refresh now writes into an output buffer only when reordering is required.
  For identity policies, refresh is a no-op and the existing feature buffer is used
  directly; the previous return-by-value copied the complete feature array.

The hot policy's permutation and feature reorder remain measured.

### Decision accounting

- The fixed rule is charged for preparing its selected policy, not for an inspection pass
  whose counters it does not consume.
- The capacity rule is charged for preparing its selected policy only.
- The reuse rule continues to pay preparation and inspection for hot, batch and streaming
  candidates because its decision consumes their structural counters.
- The model continues to pay preparation and inspection for every candidate, including
  rejected candidates, plus prediction overhead.

The original `choose()` function remains unchanged as the frozen historical rule.
The corrected analysis uses `choose_corrected()`.

### Required rerun before updated claims

1. Rebuild the native preparation executable with `g++ -O3 -std=c++17`.
2. Regenerate native preparation samples into a new run directory.
3. Re-run affected calibration, held-out and controlled preparation measurements.
4. Rebuild paired reports and the complete decision scenario grid.
5. Re-check the selector success criterion and thesis tables/figures against new samples.

The current branch has not executed these measurements. Until that rerun completes, the
old numeric tables are historical and must not be presented as updated results. DPU
kernels are unchanged, so this correction does not itself imply different simulator cycles.
