# Descriptive size and window comparisons

Means of two paired seeds. Negative percentages mean fewer cycles/bytes.
Preparation is the mean of the two per-input medians, excluding validation.

Each cycle comparison uses the fastest tested streaming buffer for that input.
The 256/1,024-byte controls reuse identical stream16 host-encoding samples.

| Input | Destinations | Policy | Preparation (µs) | Cycle change | Read change |
| --- | ---: | --- | ---: | ---: | ---: |
| community | 192 | stream16 | 24.2 | +1.19% | +0.00% |
| community | 192 | batch16 | 857.3 | +38.80% | -1.15% |
| community | 192 | batch32 | 621.5 | +18.69% | -25.42% |
| community | 192 | batch64 | 432.0 | +1.44% | -48.41% |
| community | 192 | stream16_256 | 24.2 | +0.01% | +0.00% |
| community | 192 | stream16_1024 | 24.2 | +0.22% | +0.00% |
| community | 768 | stream16 | 88.9 | +0.54% | +0.00% |
| community | 768 | batch16 | 3,600.7 | +30.36% | -0.03% |
| community | 768 | batch32 | 2,387.7 | +12.02% | -25.13% |
| community | 768 | batch64 | 1,830.0 | -3.04% | -48.00% |
| community | 768 | stream16_256 | 88.9 | +0.02% | +0.00% |
| community | 768 | stream16_1024 | 88.9 | +0.37% | +0.00% |
| community | 3,072 | stream16 | 352.7 | +0.80% | +0.00% |
| community | 3,072 | batch16 | 14,710.3 | +29.92% | +0.43% |
| community | 3,072 | batch32 | 9,423.4 | +10.68% | -24.82% |
| community | 3,072 | batch64 | 7,032.1 | -5.35% | -47.80% |
| community | 3,072 | stream16_256 | 352.7 | +0.33% | +0.00% |
| community | 3,072 | stream16_1024 | 352.7 | +0.00% | +0.00% |
| uniform | 192 | stream16 | 51.9 | +0.68% | +0.00% |
| uniform | 192 | batch16 | 1,029.1 | +62.45% | +34.01% |
| uniform | 192 | batch32 | 791.7 | +56.61% | +30.21% |
| uniform | 192 | batch64 | 666.6 | +53.82% | +25.73% |
| uniform | 192 | stream16_256 | 51.9 | +0.17% | +0.00% |
| uniform | 192 | stream16_1024 | 51.9 | +0.00% | +0.00% |
| uniform | 768 | stream16 | 217.6 | +0.88% | +0.00% |
| uniform | 768 | batch16 | 4,179.3 | +61.72% | +33.79% |
| uniform | 768 | batch32 | 3,105.5 | +55.59% | +29.71% |
| uniform | 768 | batch64 | 2,652.4 | +50.71% | +24.77% |
| uniform | 768 | stream16_256 | 217.6 | +0.41% | +0.00% |
| uniform | 768 | stream16_1024 | 217.6 | +0.00% | +0.00% |
| uniform | 3,072 | stream16 | 838.7 | +0.82% | +0.00% |
| uniform | 3,072 | batch16 | 16,142.6 | +57.99% | +33.82% |
| uniform | 3,072 | batch32 | 12,311.2 | +51.79% | +29.56% |
| uniform | 3,072 | batch64 | 10,040.2 | +49.26% | +24.60% |
| uniform | 3,072 | stream16_256 | 838.7 | +0.27% | +0.00% |
| uniform | 3,072 | stream16_1024 | 838.7 | +0.00% | +0.00% |
| grqc | 192 | stream16 | 25.2 | +0.45% | +0.00% |
| grqc | 192 | batch16 | 806.2 | +7.58% | -37.08% |
| grqc | 192 | batch32 | 606.7 | +3.91% | -40.10% |
| grqc | 192 | batch64 | 462.5 | +5.38% | -41.64% |
| grqc | 192 | stream16_256 | 25.2 | +0.04% | +0.00% |
| grqc | 192 | stream16_1024 | 25.2 | +0.00% | +0.00% |
| grqc | 768 | stream16 | 95.6 | +1.27% | +0.00% |
| grqc | 768 | batch16 | 3,051.9 | +4.24% | -35.67% |
| grqc | 768 | batch32 | 2,129.9 | -0.24% | -38.79% |
| grqc | 768 | batch64 | 1,683.1 | -0.60% | -40.38% |
| grqc | 768 | stream16_256 | 95.6 | +0.85% | +0.00% |
| grqc | 768 | stream16_1024 | 95.6 | +0.00% | +0.00% |
| grqc | 3,072 | stream16 | 379.1 | +0.70% | +0.00% |
| grqc | 3,072 | batch16 | 12,012.7 | +0.97% | -35.94% |
| grqc | 3,072 | batch32 | 8,434.5 | -3.82% | -39.07% |
| grqc | 3,072 | batch64 | 6,606.7 | -5.05% | -40.77% |
| grqc | 3,072 | stream16_256 | 379.1 | +0.39% | +0.00% |
| grqc | 3,072 | stream16_1024 | 379.1 | +0.00% | +0.00% |
