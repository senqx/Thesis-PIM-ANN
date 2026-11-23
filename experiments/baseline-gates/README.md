# Baseline controls: compact dictionaries and shared residency

**23 November 2026. Fourteen new simulated executions, with 24 frozen reference
records from the earlier five-point study.** This single-size screen tests the
two baseline gaps in the [contribution plan](../../docs/CONTRIBUTION_PLAN.md).
It changes which method is preferable in the small-table regime. It does not
establish a new method, a hardware speedup or a successful adaptive selector.

## What changed

- `compact64`: use 16-bit dictionary IDs, matching streaming's source-ID width.
  Keep the existing 64-reference batches and per-tasklet buffers. This is a
  conventional representation improvement.
- `preload128` / `preload512`: load the entire 4 KiB synthetic feature table
  into shared WRAM, synchronize the tasklets, then aggregate using those values.
  The suffix is the per-tasklet index-buffer size. Fresh values are loaded on
  every invocation; preload and synchronization are included in kernel cycles.

Use the same 3,072 destinations, twelve tasklets, 8-byte records, three input
families and two seeds as the largest earlier cases. The 41,928-byte ca-GrQc
table cannot fit with this linker's fixed 49,152-byte stack reservation, so
full residency is not tested for that input. Partial residency remains open.

## Outcome

Mean paired changes against the fastest of the three retained streaming
buffers for each input. Negative means fewer cycles or bytes. Both preload
buffers and every per-seed result appear in the [generated comparisons](comparisons.md).

| Input | Control | Complete cycles | Local reads | Installed index/plan bytes |
| --- | --- | ---: | ---: | ---: |
| Community | Compact batch64 | −6.18% | −54.43% | −6.25% |
| Community | Shared preload, 128-byte buffer | −29.10% | −78.33% | 0.00% |
| Sampled ca-GrQc | Compact batch64 | −6.10% | −48.56% | +0.49% |
| Uniform | Compact batch64 | +41.31% | +5.94% | +54.00% |
| Uniform | Shared preload, 128-byte buffer | −29.63% | −78.33% | 0.00% |

Shared preload with a 128-byte index buffer takes 367,193 cycles on each of
the four synthetic inputs. Its WRAM reservation is 56,256 bytes, including
stacks, runtime state, synchronization, private buffers and the shared table.
The 512-byte variant uses 60,864 bytes and is slightly slower. Compact batch64
uses 59,904 bytes. All fit the same 65,536-byte ceiling. Equal preload cycle
counts do not establish general insensitivity to graph structure: these
kernels execute the same number of fixed-cost WRAM accesses in this model.

Compact dictionaries improve cycles over the original 32-bit-dictionary batch
by 0.88% on community, 1.10% on ca-GrQc and 5.33% on uniform inputs. This is a
control improvement, not a novel scheduling result. Feature placement in MRAM
also changes as metadata shrink; this is not a pure instruction-cost ablation.

The ca-GrQc metadata mean hides a budget violation on one input: seed 23 grows
by 1.17%, while seed 61 shrinks by 0.20%. Therefore compact fixed batching
does not satisfy the zero-extra-installation constraint across this screen.
Uniform access fails both the latency and local-read constraints.

## Research decision

**Where the whole feature table fits, shared residency is the strongest tested
control here.** Prepared batching's roughly 6% advantage over streaming is
not an advantage over that residency control. Preserve the earlier results
as conditional streaming comparisons, not proof that prepared reuse is the
best use of WRAM.

The next justified opportunity test concerns working sets larger than available
WRAM. Include compact fixed batching and applicable static/partial residency
before developing a selective planner. The sampled real graph leaves a
candidate opportunity, but one graph and two seeds do not establish it.

No size curve is inferred from this screen. The earlier artifact retains five
actual size points; these new controls require their own five-point extension
before making comparative size-trend claims. Host preparation, installation,
launch costs and energy are unmeasured here. The Go simulator remains
unvalidated against hardware for these kernels.

## Reproduce

The [protocol](PROTOCOL.md) was written before running the controls. Results
are in [results.csv](results.csv), derived paired differences in
[comparisons.csv](comparisons.csv), and exact images/inputs/outputs/options/
counters in `replay.zip`. [Runtime notices](../wram/THIRD_PARTY_NOTICES.txt)
apply to linked programs. Graph generation and dataset attribution are in the
[prior artifact](../access-plan/README.md).

From the repository root:

```sh
python3 scripts/access_plan_gates.py verify
python3 scripts/access_plan_gates.py replay
```

Verification checks all 38 records, archive/source hashes, every new reference
sum, decoded batch membership, exact traffic and linked WRAM reservations.
Replay freshly executes a shared-preload case and a compact real-graph case
and requires every counter and non-path simulator option to match. It uses
the [pinned simulator](../../docs/PLATFORM.md) and needs no compiler or dataset
download. Use `--destination` to select a fresh replay directory.

For source rebuilding, first set up the pinned simulator, SDK and dataset as
in the prior artifacts. In a fresh working copy without this screen's generated
results or run directory, compile with:

```sh
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,nodev \
  --mount "type=bind,src=$PWD,dst=/work" \
  thesis-upmem-compiler:2023.1.0 python3 scripts/access_plan_gates.py compile
python3 scripts/access_plan_gates.py run
python3 scripts/access_plan_gates.py summarize
python3 scripts/access_plan_gates.py record
python3 scripts/access_plan_gates.py verify
```

The compile command reuses previously compiled twelve-tasklet SDK objects;
run the existing access-plan compiler setup first if they are absent. Fresh
linking can alter instruction images due to the upstream Go linker, so exact
reproduction should use archived images. Never overwrite retained evidence
to make a failed verification pass.
