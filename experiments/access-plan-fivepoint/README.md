# Five workload sizes: evidence for the short thesis

The [short thesis](../../thesis/short-thesis.md) uses **five size points for
each input family**: 192, 384, 768, 1,536 and 3,072 destinations. Each
destination sums eight requested 8-byte records. Every point has two paired
seeds and the same six DPU programs: three batch windows and three compressed
streaming buffers. This is single-DPU integer aggregation, not full graph
processing or measured ML training.

The combined grid contains **180 configurations**. It reuses all 108 frozen
DPU records from the [three-point study](../access-plan-scaling/README.md)
and adds 72 simulations at 384 and 1,536 destinations. It is not 180 new or
independent experiments. All five sizes receive a fresh, separate CPU timing
campaign: **1,320 construction measurements**, 11 for each of the four distinct
encoders per input/size. Streaming buffers share identical host encoding.

No method was retuned for the two new sizes. The [protocol](PROTOCOL.md)
records the extension. Earlier artifacts and their timing samples are unchanged.
Use this campaign's times for its amortization curves; host timings are not
bitwise deterministic and differ slightly from the earlier campaign.

## Main result

Mean paired changes in complete simulated DPU cycles for 64-reference batches,
relative to the fastest tested streaming buffer. Negative means faster.

| Destinations | Community | Sampled ca-GrQc | Uniform |
| ---: | ---: | ---: | ---: |
| 192 | +1.44% | +5.38% | +53.82% |
| 384 | +1.09% | +1.97% | +51.21% |
| 768 | −3.04% | −0.60% | +50.71% |
| 1,536 | −4.74% | −4.07% | +49.22% |
| 3,072 | −5.35% | −5.05% | +49.26% |

The additional points support a size-dependent benefit in the two reusable
input families. The uniform case remains a failure. The data do not locate
a global optimum or establish hardware significance. At 3,072 destinations,
preparation is repaid after 89–91 uses for community and 72–99 for sampled
ca-GrQc in this CPU timing campaign, before extra installation. These are
per-input estimates from medians, not confidence intervals.

At that size, local reads fall by 47.80% and 40.77% respectively, while
installed metadata grow by 26.76–29.10% and 40.23–42.38%. The strict
zero-extra-host-setup budget is therefore not met. The Go model's hardware
timing is unvalidated; physical application latency and energy are unmeasured.

## Inspect and reproduce

- [comparisons.md](comparisons.md): every policy and size.
- [results.csv](results.csv), [controls.csv](controls.csv): counters, costs and provenance.
- [preparation.csv](preparation.csv), [host.json](host.json): the new CPU measurements.
- [paired.csv](paired.csv), [amortization.csv](amortization.csv): differences and installation scenarios.
- `replay.zip`: exact programs, input/expected-output bytes, counters and options.
- [Runtime notices](../wram/THIRD_PARTY_NOTICES.txt) apply to the linked programs;
  [SNAP ca-GrQc](https://snap.stanford.edu/data/ca-GrQc.html) attribution and
  dataset checksum are retained in the earlier study.

From the repository root:

```sh
python3 scripts/access_plan_fivepoint.py verify
python3 scripts/access_plan_fivepoint.py replay
```

Replay requires the [pinned simulator setup](../../docs/PLATFORM.md), but no
compiler or dataset download. The four default replays exercise the newly
added sizes, both input types and different policies. Use `replay --all
--destination build/fivepoint-all` to check all 180 records. A fresh output
directory is required. All output values, simulator counters and non-path
model options must match.

For a new timing campaign and rerun of the 72 added configurations, use
`python3 scripts/access_plan_fivepoint.py run` in a fresh checkout/workspace
with the simulator and checked dataset available. It reuses the prior frozen
images and records, builds the new inputs, measures preparation and writes
new CSV files. Do not overwrite the retained evidence when comparing results.
`summarize` regenerates the analysis. `record` is only for maintaining the
archive after completed runs; it must not bypass a failed integrity check.
