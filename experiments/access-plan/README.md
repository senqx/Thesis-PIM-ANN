# Prepared access plans: a bounded DPU experiment

**23 November 2026. No candidate established a latency improvement over the
strongest tested streaming baseline.** The study tests whether preparing reuse
decisions on the CPU makes WRAM retention cheap enough to help DPU execution.
It follows the [earlier 160-configuration pilot](../wram/README.md), whose
artifacts are unchanged.

The new evidence contains **132 performance configurations**, **two feature
update correctness checks**, and **three transfer-throughput probes**. These
are configuration records, not 137 independent statistical experiments. They
are exploratory, single-DPU simulations in the pinned Go uPIMulator, without
hardware timing validation, host communication measurements or energy results.

## Idea and controls

When graph connectivity and work assignment stay fixed, the CPU can prepare
which feature records should occupy each WRAM slot. The DPU then follows this
plan instead of performing cache lookups and replacement decisions repeatedly.
The plan contains addresses and slot choices; feature values are fetched fresh
on each invocation. This applies to known worklists, not unknown traversal
frontiers. [The research note](../../docs/DPU_ACCESS_PLANS.md) explains the
closest papers and why offline caching itself is not novel.

| Policy | What executes on the DPU |
| --- | --- |
| `stream128`, `stream256` | Read 32-bit source IDs in chunks of up to 128/256 bytes; fetch each requested feature record. |
| `stream16` | Same demand fetching with 16-bit source IDs and 128-byte index buffering. All tested local IDs fit. |
| `history` | Runtime direct-mapped retention using 512 bytes of payload per tasklet. |
| `plan_direct` | One 32-bit plan word per reference, making exactly the same feature loads as `history`. Isolates lookup overhead. |
| `plan_lru`, `plan_nextuse` | Same encoding with offline LRU or established Belady next-use replacement. |
| `batch` | Prepare 64-reference batches. Load each distinct 8-byte feature record once, then aggregate using byte-sized slot indices. No cache decision in the aggregation loop. |

All methods sum the same eight neighboring feature vectors per destination,
in the same arithmetic order, using unsigned 32-bit integers. This is not
floating-point GNN training. The kernel processes 192 destinations and 1,536
references. MRAM inputs are resident before timing starts; all kernel startup,
DMA, bookkeeping, aggregation and final stores are included in DPU cycles.

All methods fit the same 64 KiB WRAM ceiling. Reported reservations range from
51,424 to 64,320 bytes across the performance records, including the Go
linker's fixed 24 × 2 KiB stack reservation. Private retention gives no reuse
across tasklets. Equal capacity limits do not mean identical allocations, and
this is not exhaustive buffer/tasklet tuning. The baseline does not need to
use all available WRAM to invalidate a candidate's performance claim.

## Results

The following held-out checks use twelve tasklets, 8-byte features and seeds
23/61, after freezing the batch implementation. Each cell is the arithmetic
mean of two paired comparisons with `stream16`; negative means fewer bytes.
Output traffic is identical: 1,536 bytes per invocation.

| Input family | Streaming cycles | Batch cycles | Extra cycles | Cycle change | MRAM read-byte change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Community | 33,146 | 33,230 | +84 | +0.25% | −48.41% |
| Uniform | 33,681 | 51,454.5 | +17,773.5 | +52.77% | +25.73% |
| Hub-heavy | 33,492 | 37,318 | +3,826 | +11.42% | −33.41% |
| Sampled ca-GrQc | 35,041.5 | 36,759 | +1,717.5 | +4.91% | −41.64% |

Batching nearly breaks even on community inputs while halving read traffic.
It is still slower on both seeds, and the other inputs regress more. Its
dictionary and headers actually increase traffic on uniform accesses. Lower
traffic alone does not satisfy the latency-and-traffic hypothesis, and cannot
be converted into an energy claim. The near-tie is not a robust hardware ranking.

Per-reference plans also lose to streaming. The direct-map control has the
same load count as runtime caching and removes instructions, but that saving
is insufficient. Next-use eviction minimizes feature misses for its cache
model; it does not minimize all metadata, decoding, DMA or execution costs.

**An established optimization does help:** 16-bit indices reduce cycles by
5.75–6.03% in the four held-out family means relative to the better of the two
32-bit streaming variants. MRAM reads fall by 16.67%; writes are unchanged.
This requires local IDs that fit in 16 bits. It is a baseline improvement,
not an original contribution. Do not claim a batch win against a weaker
32-bit baseline while omitting this control.

[Generated comparisons](comparisons.md) include the runtime-cache and
next-use results. [CSV records](validation.csv) retain both seeds and absolute
counters. Two seeds provide descriptive checks, not a precise population
estimate or a confirmatory statistical study.

## Workloads and experimental sequence

| Stage | Records | Conditions |
| --- | ---: | --- |
| [Initial screen](screen.csv) | 18 | Four tasklets, 64-byte features, seed 7, three synthetic families, six policies. |
| [Footprint screen](footprints.csv) | 63 | Twelve tasklets, 8/64/256-byte features, seed 7, three synthetic families, seven policies including compressed streaming. |
| [Batch screen](batch-screen.csv) | 3 | Twelve tasklets, 8-byte features, seed 7, batch only; compare with the preceding footprint controls. |
| [Held-out check](validation.csv) | 48 | Twelve tasklets, 8-byte features, seeds 23/61, four families, six policies. |
| [Feature update check](value-check.csv) | 2 | Reuse the linked batch/next-use programs and unchanged access metadata with changed features; both produce the new reference output. |
| [Throughput probe](memory-probe.csv) | 3 | Twelve tasklets, 32 contiguous reads each, transfer sizes 8/64/1024 bytes. |

Synthetic families have 512 sources: community accesses are 90% within a
16-source group; hub-heavy accesses are 65% within eight sources; uniform
accesses use the full source range. The public case derives from
[SNAP ca-GrQc](https://snap.stanford.edu/data/ca-GrQc.html). It selects 192
distinct vertices, then samples eight neighbors **with replacement** per
vertex. It is a sampled neighborhood aggregation, not a full graph pass or
an evaluation across multiple real datasets. Seeds 23/61 are held out from
implementation tuning, not independent new graph datasets.

The [protocol](PROTOCOL.md) preserves the exploratory changes in direction.
Earlier source snapshots are in `screen-sources.zip` and
`footprint-sources.zip`; current source implements the final batch comparison.
The exact images used at every stage are retained because Go linking can
produce different instruction layouts on a fresh link.

## Model and cost limits

The probe reports effective read throughput of **290.1, 448.3 and 484.7 MB/s**
for 8-, 64- and 1,024-byte transfers at the model's 350 MHz DPU clock. It counts
read bytes divided by complete kernel time, including startup and final writes.
[Pathfinding Future PIM Architectures](https://arxiv.org/pdf/2308.00846v3)
discusses approximately 600–700 MB/s MRAM–WRAM bandwidth on real UPMEM.
Our small probe is not a matched replication of that measurement. It does not
support the suspected explanation that excessive bulk bandwidth made retention
lose, but it cannot validate DMA latency, tiny transfers or instruction timing.
Published simulator error figures concern another implementation, not this Go
build. See [platform boundaries](../../docs/PLATFORM.md).

Host planning time is a median of five Python constructions, including plan
validation. It is neither an optimized implementation nor a lower bound on
preprocessing. `index_or_plan_bytes` counts stored metadata, including unread
padding between tasklet batch segments; `read_bytes` counts actual reads of
headers, dictionaries, slot codes and features. This distinction matters for
both MRAM capacity and initial host installation.

If a candidate saved ΔT > 0 per invocation, a simple serial break-even count
would be `ceil((planning + extra installation) / ΔT)`. None of these candidates
has positive ΔT against the strongest tested baseline, so repeated reuse cannot
amortize its way into a latency win in these settings. No host/DPU, multi-DPU,
GPU, training-accuracy or energy experiment is included.

## Reproduce and audit

Start at the repository root. Python checks need only its standard library:

```sh
python3 scripts/access_plan_artifact.py verify
python3 scripts/access_plan_artifact.py summarize
```

The verifier checks file hashes, 137 records, stored inputs and expected-output
hashes, WRAM bounds, counter/CSV agreement, equal logical work across policies,
and identical traffic for the direct-map pair. Hashes protect retained evidence;
they do not independently prove the simulator's timing model.

Build the pinned simulator using [platform setup](../../docs/PLATFORM.md), then:

```sh
python3 scripts/wram_platform.py prepare
python3 scripts/access_plan_artifact.py replay
```

Default replay runs four representative frozen programs: streaming, batch,
next-use on a public-graph sample, and the 1,024-byte throughput probe. Every
output is checked by the simulator, and **all** simulator counters and
non-path options must match. A fresh destination is required. To replay all
137 records (slower), use:

```sh
python3 scripts/access_plan_artifact.py replay --all \
  --destination build/access-plan-replay-all
```

**Verification completed on 23 November 2026:** all 137 retained records
passed the artifact audit, and all four default fresh replays matched every
counter and checked output. The earlier pilot's 160-record manifest and seven
previously saved fresh-replay comparisons also still pass. Local Markdown
links, Python syntax and tracked whitespace checks passed. These checks do
not establish hardware timing accuracy.

`replay.zip` stores a `records.json` catalog and deduplicated file contents
under `blobs/<sha256>`. It contains linked images, arguments, initial data,
expected outputs, completion records, model options and counters. It needs
neither the compiler image nor a dataset download for frozen replay.
The [runtime notices](../wram/THIRD_PARTY_NOTICES.txt) apply to linked images.
Graph data are credited to J. Leskovec, J. Kleinberg and C. Faloutsos,
*Graph Evolution: Densification and Shrinking Diameters*, ACM TKDD 1(1), 2007,
as requested by the SNAP dataset page.

For a **source rebuild** of the final comparison, first obtain the compiler
image following platform setup, then run:

```sh
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,nodev \
  --mount "type=bind,src=$PWD,dst=/work" \
  thesis-upmem-compiler:2023.1.0 \
  python3 scripts/access_plan.py compile --tasklets 12 --features 8 \
    --policies stream128 stream256 stream16 history plan_nextuse batch
curl -L --fail https://snap.stanford.edu/data/ca-GrQc.txt.gz \
  -o .downloads/ca-GrQc.txt.gz
python3 scripts/access_plan.py run --tasklets 12 --features 8 \
  --policies stream128 stream256 stream16 history plan_nextuse batch \
  --cases community uniform hubs grqc --seeds 23 61 \
  --run-directory runs/access-plan-rebuilt --output build/access-plan-rebuilt.csv
```

The script verifies the compressed dataset SHA-256
`a254442cdf5d684712578b630c2e0d7543518ab154ef2341cabb607572ce7230`.
Fresh links may change cycles; compare results and report that difference,
rather than silently replacing the frozen records. `record` is a maintainer
command to archive completed original run directories, not a prerequisite
for verification or replay. It also refreshes the manifest, so must not be
used to bypass a failed integrity check.

## Research decision

Keep this as a reproducible negative feasibility result. Do not promote the
current retention schemes into an adaptive framework: choosing between losing
variants does not establish value beyond streaming. Before a larger campaign,
establish credible timing and an opportunity on longer, realistic repeated
worklists. A useful continuation would have to demonstrate a latency/traffic
trade-off that survives compressed indices, full program costs and fresh
graphs. PIM–GPU remains a conditional later extension.
