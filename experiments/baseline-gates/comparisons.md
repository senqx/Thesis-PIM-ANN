# Baseline-gate results

Two-seed arithmetic means of paired percentage changes at 3,072 destinations.
Negative changes mean less time or fewer bytes. The comparator is the fastest
retained streaming buffer for each input; this is a hindsight comparator.
These are descriptive results from the Go simulator, not hardware measurements.

| Input | New control | Cycles vs streaming | Reads vs streaming | Installed metadata vs streaming |
| --- | --- | ---: | ---: | ---: |
| community | compact64 | -6.18% | -54.43% | -6.25% |
| community | preload128 | -29.10% | -78.33% | +0.00% |
| community | preload512 | -28.28% | -78.33% | +0.00% |
| grqc | compact64 | -6.10% | -48.56% | +0.49% |
| uniform | compact64 | +41.31% | +5.94% | +54.00% |
| uniform | preload128 | -29.63% | -78.33% | +0.00% |
| uniform | preload512 | -28.81% | -78.33% | +0.00% |

The [CSV](comparisons.csv) includes both seeds, absolute cycle differences,
original-batch comparisons and complete WRAM reservations. No size trend
or preparation payback is inferred from this single-size screen.
