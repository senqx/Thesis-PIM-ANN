# Held-out descriptive comparisons

Twelve tasklets, 8-byte feature rows, seeds 23 and 61. Percentage
changes are arithmetic means of paired changes. Negative means fewer
cycles or bytes. These are two-input summaries, not confidence intervals.

| Workload | Policy | Comparator | Mean cycles | Cycle difference | Cycle change | Read-byte change |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| community | stream16 | best 32-bit stream | 33,146.0 | -2,022.5 | -5.75% | -16.67% |
| community | batch | stream16 | 33,230.0 | +84.0 | +0.25% | -48.41% |
| community | history | stream16 | 51,923.5 | +18,777.5 | +56.65% | -32.94% |
| community | plan_nextuse | stream16 | 41,866.0 | +8,720.0 | +26.31% | -33.62% |
| uniform | stream16 | best 32-bit stream | 33,681.0 | -2,137.0 | -5.97% | -16.67% |
| uniform | batch | stream16 | 51,454.5 | +17,773.5 | +52.77% | +25.73% |
| uniform | history | stream16 | 58,640.5 | +24,959.5 | +74.11% | +14.27% |
| uniform | plan_nextuse | stream16 | 52,779.0 | +19,098.0 | +56.70% | +11.33% |
| hubs | stream16 | best 32-bit stream | 33,492.0 | -2,147.5 | -6.03% | -16.67% |
| hubs | batch | stream16 | 37,318.0 | +3,826.0 | +11.42% | -33.41% |
| hubs | history | stream16 | 52,823.0 | +19,331.0 | +57.72% | -26.59% |
| hubs | plan_nextuse | stream16 | 43,165.0 | +9,673.0 | +28.89% | -28.67% |
| grqc | stream16 | best 32-bit stream | 35,041.5 | -2,181.5 | -5.86% | -16.67% |
| grqc | batch | stream16 | 36,759.0 | +1,717.5 | +4.91% | -41.64% |
| grqc | history | stream16 | 52,639.0 | +17,597.5 | +50.22% | -28.46% |
| grqc | plan_nextuse | stream16 | 42,866.0 | +7,824.5 | +22.33% | -28.98% |
