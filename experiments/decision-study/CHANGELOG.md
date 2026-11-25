# Post-freeze correction log

## 24 November 2026 — fair preparation and deployment accounting

The reviewed correction is now backed by new native measurements, complete
input-equivalence checks, representative simulation replay and regenerated
reports. Current evidence lives in [corrected/](corrected/README.md); the
historical manifest, raw samples and model remain unchanged.

### What was corrected

- Only `hot` allocates/sorts a source permutation, builds its inverse and copies
  source values into reordered storage. Identity policies keep original column
  IDs and use the existing source buffer. Their measured refresh interval is
  timer/dispatch overhead, not a full-array copy.
- Corrected decisions charge preparation and inspection separately. They count
  rejected candidates, include streaming references when used, skip absent full
  retention and stop the reuse search when it accepts a candidate. Direct
  dispatch pays no unused inspection. Original `choose()` and `total()` remain
  unchanged for historical verification.
- Review also fixed an absent-full crash and rejected-fixed undercount in the
  initial draft. Original documentation snapshots now preserve exact bytes.

### Timing and research status

446 distinct preparations were remeasured, each with 31 samples after three
warmups. They reproduce the input data, arguments and reference outputs of all
511 archived invocations exactly. The 485 original simulation records and
cycle-model coefficients are reused, not retimed or refitted. Four fresh replay
records check six invocations and all simulator counters.

This is a correction using already observed inputs, not fresh confirmation.
A final accounting review after initial native timing removed unnecessary
inspection for capacity-forced fallback and unconstrained direct dispatch;
[the protocol](corrected/PROTOCOL.md) discloses that amendment. Final Python
prediction timing was collected after simulator replay had finished. None of
these steps changes policy thresholds or fits to evaluation outcomes. The
separate one-time calibration total also includes native structural inspection;
the original fit-time measurement is retained.

The tested selector still fails the original practical-success criterion at all
eight lifetimes. Corrected totals and host timing envelopes replace the old
values in the current thesis. Original reports remain available for audit.
