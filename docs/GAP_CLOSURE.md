# Closing the testable gaps

**24 November 2026.** This record connects the earlier
[novelty audit](NOVELTY_AUDIT.md) to the completed
[standard sparse-operation study](../experiments/decision-study/README.md).
The scope is one simulated UPMEM DPU and local representation choice. It does
not revive the original proposal for a general adaptive prefetching framework.

## Completed work and what it establishes

| Concern | Completed check | Outcome and boundary |
| --- | --- | --- |
| Only a custom sampled aggregation workload | Complete sparsity patterns from seven public Matrix Market inputs, weighted integer SpMV/SpMM | Three calibration matrices and four held-out matrices; small structural projections, not original floating-point problems |
| Weak alternatives | Two streaming buffers, feasible full retention, frequency retention, prepared batches and 2x2/4x4 blocked reuse | Stronger controls change recommendations; established mechanisms are credited |
| Working sets always fit | Five source-table sizes spanning 0.25–4 times configured residency capacity, at fixed work count | Separates source capacity from increasing work volume; two controlled families |
| Only one record width | Five executed SpMM widths, 8–128 bytes, plus scalar SpMV | Retention helps at 16 bytes and loses at 128 bytes on the primary held-out configuration; arithmetic also changes |
| Unequal WRAM assumptions | Every linked image checked, including the upstream 49,152-byte stack reservation | A 70,096-byte twelve-tasklet batch image is excluded; no impossible allocation receives a timing |
| One concurrency setting | Fifty additional four/twelve-tasklet runs, compared with the eight-tasklet baseline | Concurrency and feasible retention capacity can change the winner; not isolated causation or exhaustive tuning |
| Python-only setup costs | Native preparation, structural inspection and feature refresh; 31 samples after three warmups | Practical margins now describe the native implementation; old Python results remain historical |
| Ignoring setup, host work or extra traffic | Charge rejected-candidate construction, inspection, selection, installation, refresh and modelled transfers; enforce byte budgets per input | A fast but over-budget choice cannot pass by averaging; host candidate storage is reported separately |
| Assuming an adaptive rule works | Freeze model/rules/input hashes before held-out timings; compare against fixed, capacity and reuse rules | Model finds an equally fastest feasible kernel in 8/24 conditions and fails the practical criterion at all eight lifetimes |
| Lifetimes assume valid state | Thirteen records with three changed-feature invocations each; fourteen structural/empty-input checks | All outputs and traffic pass; triple-run cycles differ from 3×single by −0.391% to +0.194%, so linearity is an approximation |
| Dependence on one DRAM setting | Five joint timing scales on the same images; 52 new runs and 13 reused comparators | The narrow-retention/wide-streaming ranking persists on this subset; this is sensitivity, not hardware validation |
| Fragile payback thresholds | Recompute margins using extreme combinations of observed native samples | Ten of sixteen 8–64-byte cases retain a positive first-use margin; six span zero. These are descriptive envelopes |
| Unclear originality | Explicit comparisons with SparseP, DRIM-ANN, PyGim, ATiM and related preprocessing work | Contribution is scoped comparative evidence and a negative selector result; no new mechanism or universal priority claim |
| Results cannot be independently checked | Exact images, inputs, outputs, raw timings, counters, options and frozen hashes; independent decoding and fresh replay | See the [validation record](VALIDATION.md) for executed checks and the current PDF/build record |

## What an engineer gains

The results give a concrete order of decisions: calculate usable WRAM, test
simple streaming and feasible retention, inspect the scope of reuse, enforce
traffic/storage limits, then include setup and refresh costs. They show where
this order changes the answer. In the tested held-out 16-byte cases, static
frequency retention saves 11.97–15.71% of complete simulated cycles; at 128 bytes,
streaming wins under the primary budget. Building and inspecting every candidate
makes the tested adaptive model unattractive, even when preparation is amortized.

These are usable conditional findings and reproducible counterexamples to an
unsupported general recommendation. They are not an empirical basis for saying
that an arbitrary graph, ML model or hardware platform will accelerate.

## Limits that remain explicit

- **Hardware and energy:** no measured DPU timing, physical host transfers, power
  or joules. The available Go simulator has no hardware validation for these
  new kernels. Changing its DRAM parameters cannot replace that evidence.
- **Full application costs:** parsing, program loading, SDK integration,
  multi-DPU partitioning/merging and CPU/GPU orchestration are outside the
  declared accounting interval. They need implementation and measurement before
  an application speedup claim; the current positive margins are conditional.
- **Coverage:** seven small public structures, two controlled families and one
  integer operator family do not establish generality across large graphs,
  floating-point training, evolving frontiers or dependent pointer traversal.
- **Tuning:** the study screens meaningful buffers, blocked formats and tasklet
  counts. It does not find the globally optimal implementation of each policy,
  exhaust all software caches, or validate the predictor beyond eight tasklets.
- **Prediction and novelty:** the tested selector failed. A better selector would
  require a new declared hypothesis and new held-out inputs; changing it on these
  test outcomes would not repair this evaluation. Literature inspection can
  establish the nearest known precedents, not prove that no similar result exists.

The bounded research questions now have experimental answers. The broader limits
remain part of the thesis's claim boundary, rather than unperformed work hidden
behind a claim of a complete adaptive PIM system.
