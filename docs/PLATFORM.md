# uPIMulator: acquisition and feasibility status

Updated **24 November 2026**. No UPMEM hardware is available. The archived
SDK now compiles DPU programs inside an isolated container. The Go simulator
has passed a deterministic upstream vector-addition check and is being used
for the bounded [WRAM execution pilot](../experiments/wram/README.md) and
[prepared-access study](../experiments/access-plan/README.md), followed by the
[standard sparse-operation study](../experiments/decision-study/README.md).
This establishes a working execution path, not hardware timing validation.

## Pinned source and completed checks

| Item | Value / result |
| --- | --- |
| Upstream | [VIA-Research/uPIMulator](https://github.com/VIA-Research/uPIMulator) |
| Commit | `870d916334e9ff0b190f555f951a9ec3c4257781` |
| Implementation built | `golang/uPIMulator` |
| Local source | `.deps/upimulator/` (ignored by Git) |
| Source archive SHA-256 | `03b75a41f92a7f7cdd44d5a141c2d572d84952c32517a5ed3c45a0b8fc3ecfda` |
| Source verification | All 2,598 extracted upstream files matched the completed archive |
| Build | `go build -o build/uPIMulator ./src` passed with Go 1.27.4, linux/amd64 |
| CLI check | `./build/uPIMulator -help` passed; upstream uses one dash for this flag |
| Docker | Server 26.1.3; isolated SDK 2023.1.0 compiler image built |
| Workload checks | Reference-checked vector addition and integer neighbor aggregation; see pilot record |

No upstream timing or instruction model source was modified. A generated frontend
reuses the linker and simulator while bypassing the original compiler launcher. The Go toolchain was downloaded
from `go.dev`; its archive SHA-256 was checked against the official release
metadata: `7226736c2339719cda28fbf3a54d71aa63bcefe376e98cef00034268dab24840`.
It is installed in ignored `.deps/go/`, not system-wide.

## Reproduce source acquisition and build

Run from the repository root with `curl`, `sha256sum`, `tar` and Go available.
The upstream minimum is Go 1.21.5; the checked build used 1.27.4. Source download
is approximately 97 MiB and extraction approximately 275 MiB. Keep enough room
for the Go toolchain, build cache and later compiler environment as well.

```sh
set -eu
test ! -e .deps/upimulator
mkdir -p .downloads .deps/upimulator
curl -L --fail \
  https://codeload.github.com/VIA-Research/uPIMulator/tar.gz/870d916334e9ff0b190f555f951a9ec3c4257781 \
  -o .downloads/upimulator.tar.gz
printf '%s\n' '03b75a41f92a7f7cdd44d5a141c2d572d84952c32517a5ed3c45a0b8fc3ecfda  .downloads/upimulator.tar.gz' | sha256sum -c -
tar -xzf .downloads/upimulator.tar.gz -C .deps/upimulator --strip-components=1
cd .deps/upimulator/golang/uPIMulator
go build -o build/uPIMulator ./src
./build/uPIMulator -help
```

An existing checkout can use just the last three commands. These checks do not
exercise the compiler, linker, DPU instruction execution or result checking.

## Compiler dependency and compatibility adaptation

The pinned upstream Dockerfile requests SDK 2023.2.0 from
`sdk-releases.upmem.com`; that URL redirected to a parked domain during setup.
The working fallback is **SDK 2023.1.0**, from the
[CMU-SAFARI archive](https://github.com/CMU-SAFARI/UPMEM/tree/84a0dcd3f57ded98ea049f2be5d45c71eda96ace).
Do not describe this as the original simulator toolchain. The archive checksum
pins the mirror's contents, not an original vendor checksum.

```sh
mkdir -p .downloads .deps/upmem-sdk
curl -L --fail \
  https://codeload.github.com/CMU-SAFARI/UPMEM/tar.gz/84a0dcd3f57ded98ea049f2be5d45c71eda96ace \
  -o .downloads/upmem-sdk-archive.tar.gz
printf '%s\n' 'c4ccd44a2d7903b4c1b25c2ede759a28705348388756d55193d953dfa8e1413c  .downloads/upmem-sdk-archive.tar.gz' | sha256sum -c -
tar -xzf .downloads/upmem-sdk-archive.tar.gz -C .deps/upmem-sdk --strip-components=1
```

Extraction needs approximately 601 MiB; keep it in the workspace rather than a
small temporary filesystem. Native compilation failed because the host lacked
`libedit.so.2`. The container supplies its runtime dependencies. An initial
container build also failed against HTTP Ubuntu package sources; HTTPS with a
trusted CA bundle succeeded.

Copy the host's trusted CA bundle into the ignored build context. On this host:

```sh
cp /etc/pki/tls/certs/ca-bundle.crt .deps/upmem-sdk/ca-bundle.crt
# On Debian/Ubuntu the source is usually /etc/ssl/certs/ca-certificates.crt.
docker build -t thesis-upmem-compiler:2023.1.0 \
  -f experiments/wram/Compiler.Dockerfile .deps/upmem-sdk
python3 scripts/wram_platform.py prepare
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,nodev \
  --mount "type=bind,src=$PWD,dst=/work" \
  thesis-upmem-compiler:2023.1.0 \
  python3 scripts/wram_platform.py compile --sdk
python3 scripts/wram_platform.py smoke
```

The Ubuntu base image is pinned by digest. Package repositories can change;
the local image ID is
`sha256:4c02b14d0e5aa24514b836a3c7fbce05811b76d3e658927ddef064d5f5321bc3`.
The compiler reports Clang 12.0.0, UPMEM LLVM revision
`60b8f628d9878b2690999bb237f3140c8defda60`. Compilation uses upstream SDK C
sources with `-O3 -S`, and benchmark C with `-O2 -S`; tasklet counts are explicit.
The upstream `stdio` and `strrchr` sources emit declaration warnings with this
SDK. Compilation succeeds; no source edits suppress those warnings.

[`wram_platform.py`](../scripts/wram_platform.py) generates a frontend from the
pinned `main.go`. It removes the hard-coded privileged Docker compiler and
benchmark-specific input generator, then exposes linking and simulation as
separate stages. Inputs and expected outputs are deterministic Python-generated
byte files. Neither timing nor instruction semantics are patched. Ordinary
compilation uses an unprivileged, network-disabled container.

The Go linker iterates some maps in unspecified order, so fresh linking need
not produce byte-identical instruction images. The pilot preserves the exact
linked images for replay, plus source-based rebuild commands. Passing these
workloads does not establish SDK compatibility for every upstream benchmark.

## Model boundaries to establish before experiments

- **DPU execution:** the Go implementation models instruction execution,
  tasklet scheduling and memory operations. Its DMA path blocks the issuing
  tasklet and wakes it on completion (`src/simulator/dpu/logic/logic.go`).
  Prefetching cannot assume an absent same-tasklet asynchronous primitive.
- **Memory:** the included `sdk/syslib/mram.h` specifies transfers of 8–2,048
  bytes in multiples of 8. Validate address alignment and shared WRAM limits
  for the chosen workload/toolchain.
- **Host and communication:** the frontend prepares benchmark-specific input
  and expected output. The host model schedules transfers; this is not proof
  that arbitrary CPU application code and its execution cost are simulated.
  Audit phase dependencies, startup, exchange, merge work and overlap before
  reporting complete application time.
- **Fidelity:** upstream reports 12.0% MAE for single-DPU and 26.9% for multi-DPU
  validation, with R² of 98.4% and 83.6%, respectively. These results concern
  its **Python/C++ implementation**, tested PrIM kernels and specific settings.
  They are not error bounds for this Go build, new workloads or relative
  speedups. Independent replication and parameter sensitivity are still needed.
- **Energy:** this review established no validated energy path. Do not equate
  traffic counters or simulated cycles with joules.

The vector-addition check compares all output elements with a reference and
retains its command options and statistics. The pilot also checks complete
aggregation outputs, traffic accounting and WRAM reservations. These are
functional and internal-accounting checks; the timing model still needs
independent hardware validation before deployment claims.

The standard-operation follow-up also checks four/eight/twelve tasklets, changed
source values across three invocations, structural rebuilds and five joint DRAM
timing settings. These extend functional and sensitivity evidence; they do not
calibrate this Go implementation against hardware. The linker reserves 49,152
WRAM bytes for all 24 possible stacks even with fewer active tasklets. The study
keeps that reservation and checks every linked allocation against 65,536 bytes.

## Transfer-throughput sanity check

The follow-up includes three checked probes, each with twelve tasklets and
32 interleaved contiguous reads per tasklet. Effective read throughput is
290.1 MB/s at 8 bytes/transfer, 448.3 MB/s at 64 bytes, and 484.7 MB/s at
1,024 bytes. The calculation divides read bytes by complete simulated kernel
time at 350 MHz, including startup and final stores. Exact images, inputs,
options and counters are in the [replay artifact](../experiments/access-plan/README.md).

The [uPIMulator paper](https://arxiv.org/pdf/2308.00846v3) discusses roughly
600–700 MB/s MRAM–WRAM bandwidth on real UPMEM. The small probe does not match
that characterization's workload or establish an error bound. It does not
support a suspected excessive-bulk-bandwidth explanation for the negative
retention results. Tiny-transfer latency, instruction timing and mixed
workloads still require matched validation. No timing parameters were changed
to improve the candidates' results.
