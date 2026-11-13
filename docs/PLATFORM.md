# uPIMulator: acquisition and feasibility status

Checked **13 November 2026**. There is no UPMEM hardware available for this
project. The simulator has been obtained and built; **a complete DPU program
has not yet been simulated**. This document is a setup record, not experimental
validation.

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
| Docker | Server 26.1.3 available; no compiler image built in this review |
| New policy or workload results | None |

No upstream simulator source was modified. The Go toolchain was downloaded
from `go.dev`; its archive SHA-256 was checked against the official release
metadata: `7226736c2339719cda28fbf3a54d71aa63bcefe376e98cef00034268dab24840`.
It was installed temporarily, not system-wide.

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

## Compiler dependency: original path unavailable, fallback identified

The pinned [Dockerfile](https://github.com/VIA-Research/uPIMulator/blob/870d916334e9ff0b190f555f951a9ec3c4257781/golang/uPIMulator/docker/Dockerfile)
downloads UPMEM SDK 2023.2.0 from `sdk-releases.upmem.com`. During this review,
the corresponding HTTPS URL redirected to a domain-parking page, not an SDK
archive. The documentation domain also failed to serve the expected SDK docs.
Do not treat an HTTP 200 HTML response as a successful SDK download.

A credible fallback is the [CMU-SAFARI SDK archive](https://github.com/CMU-SAFARI/UPMEM/tree/84a0dcd3f57ded98ea049f2be5d45c71eda96ace),
commit `84a0dcd3f57ded98ea049f2be5d45c71eda96ace`. It contains **SDK 2023.1.0**,
not the expected 2023.2.0. The downloaded GitHub source archive has SHA-256
`c4ccd44a2d7903b4c1b25c2ede759a28705348388756d55193d953dfa8e1413c`
and expands to approximately 601 MiB. This pins the mirror's contents; it is
not verification against an original vendor checksum.

An attempted extraction exceeded the temporary filesystem's free space; the
incomplete extraction was removed. The extracted compiler also reported a
missing `libedit.so.2` when probed on this host. Therefore the archive is an
**identified installation route, not a working or compatibility-validated SDK**.
Use a suitable isolated build environment and enough disk space. The official
[UPMEM LLVM fork](https://github.com/upmem/llvm-project) is another source route;
building it and establishing compatibility would be additional work.

Next, resolve the compiler/runtime environment and record any version/path
adaptation as a reviewable build-only patch. The Go frontend currently invokes
Docker and hard-codes SDK paths. Its compiler container also requests
`--privileged`; ordinary compilation should not require that capability.
Verify a narrowly configured compilation path before following the upstream
run command. Do not silently substitute SDK versions and inherit the original
validation claim.

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

The first execution check should compile a tiny upstream vector-addition
example, compare its result with the reference, and retain the command,
toolchain identity, output and simulator statistics. That is a functional
check; research results require the further controls in the
[research plan](RESEARCH_PLAN.md).
