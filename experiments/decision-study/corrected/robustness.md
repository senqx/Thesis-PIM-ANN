# Robustness and state checks

These checks were performed after model freeze. They do not refit the model.
All results describe the pinned simulator, not a hardware error bound.

## Same-process repetition and changed structure

13 records each execute three invocations with changed source values and unchanged metadata.
Every output and read/write count passed. Relative to three times the corresponding
single-run cycles, total cycles differ from -0.391% to +0.194%.
This supports the linear repeated-cost approximation on this subset; it does not prove
exact linearity at 1,024 uses. See [repeated-comparisons.csv](repeated-comparisons.csv).
Fourteen further checks rebuild each of the seven representations for changed coordinates
and an empty matrix. Stale structural plans are not reused after those changes.

## Five joint DRAM timing settings

The same instruction images run with tRCD, tCL, tRP and tRAS jointly scaled.
The 65 rows contain 52 new executions and 13 reused default-setting comparators.
Joint scaling is a model-dependence check, not an isolated attribution to one parameter.

| Record bytes | Timing scale | Best feasible policy | Best cycles | Hot saving vs stream512 |
| ---: | ---: | --- | ---: | ---: |
| 8 | 0.5 | full | 136,022 | +10.33% |
| 8 | 0.75 | full | 137,578 | +10.60% |
| 8 | 1 | full | 138,781 | +10.71% |
| 8 | 1.25 | full | 139,729 | +11.19% |
| 8 | 1.5 | full | 141,445 | +11.63% |
| 128 | 0.5 | stream128 | 1,730,502 | -2.26% |
| 128 | 0.75 | stream128 | 1,737,463 | -2.11% |
| 128 | 1 | stream128 | 1,742,543 | -2.21% |
| 128 | 1.25 | stream128 | 1,749,500 | -2.04% |
| 128 | 1.5 | stream128 | 1,756,948 | -2.02% |

Exact settings and absolute cycles are in [sensitivity.json](sensitivity.json)
and [dram-comparisons.csv](dram-comparisons.csv).

## Native timing variation

[host-timing-sensitivity.csv](host-timing-sensitivity.csv) recomputes hot-versus-streaming
margins using the most favorable and unfavorable combinations of the 31 observed
preparation and refresh samples at 80 MB/s. These are descriptive envelopes, not
confidence intervals or bounds on future host timings. A margin spanning zero makes
the reported median-based payback sensitive to observed host timing variation.
9/16 SpMM cases at 8–64 bytes retain a positive first-use margin across this envelope.
7/16 do not retain a strictly positive first-use margin across the envelope.

## Feasible concurrency

[concurrency.json](concurrency.json) adds 50 executions at four/twelve tasklets.
The twelve-tasklet, 128-byte batch image requires 70,096 WRAM bytes and is excluded.
Changing tasklets also changes configured residency capacity. This tests a combined
resource trade-off; the frozen eight-tasklet model is not validated at these settings.
