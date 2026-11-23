#!/usr/bin/env python3
"""Reproducible frontend for the pinned Go uPIMulator; no model edits.

`prepare` generates a driver that bypasses upstream's privileged Docker build.
`compile` runs INSIDE Compiler.Dockerfile's image, mounted at /work.
`smoke` links and runs upstream VA with deterministic, checked integer data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / ".deps/upimulator/golang/uPIMulator"
BUILD = ROOT / "build/wram"


def run(cmd, **kwargs):
    return subprocess.run([str(x) for x in cmd], check=True, **kwargs)


def bytefile(path, data):
    path.write_text("".join(f"{b}\n" for b in data))


def prepare():
    source = (SIM / "src/main.go").read_text()
    source = source.replace('\n\t"uPIMulator/src/compiler"', '')
    source = source.replace('\n\t"uPIMulator/src/assembler"', '')
    start = source.index('\t\tcompiler_ :=')
    end = source.index('\t\tsimulator_ :=', start)
    source = source[:start] + '''
        if os.Getenv("WRAM_STAGE") == "link" {
            linker_ := new(linker.Linker)
            linker_.Init(command_line_parser)
            linker_.Link()
            return
        }
        if os.Getenv("WRAM_STAGE") != "simulate" {
            panic("set WRAM_STAGE to link or simulate")
        }
''' + source[end:]
    driver = SIM / "wram_driver"
    driver.mkdir(exist_ok=True)
    (driver / "main.go").write_text(source)
    BUILD.mkdir(parents=True, exist_ok=True)
    go = ROOT / ".deps/go/bin/go"
    run([go if go.exists() else "go", "build", "-o", BUILD / "simulator", "./wram_driver"],
        cwd=SIM, env={**os.environ, "GOCACHE": str(ROOT / ".deps/go-cache")})


def compile_sources(args):
    compiler = "dpu-upmem-dpurte-clang"
    run([compiler, "--version"])
    dest = BUILD / f"t{args.tasklets}"
    includes = [f"-I{SIM / 'sdk' / d}" for d in ("misc", "stdlib", "syslib")]
    flags = ["-S", f"-DNR_TASKLETS={args.tasklets}", *includes]
    if args.sdk:
        for directory in ("misc", "stdlib", "syslib"):
            output = dest / "sdk/build" / directory / "CMakeFiles" / f"{directory}.dir"
            output.mkdir(parents=True, exist_ok=True)
            for source in sorted((SIM / "sdk" / directory).glob("*.c")):
                run([compiler, "-O3", *flags, source, "-o", output / (source.name + ".o")])
    output = dest / "benchmark/build" / args.benchmark / "dpu/CMakeFiles" / f"{args.benchmark}_device.dir/task.c.o"
    output.parent.mkdir(parents=True, exist_ok=True)
    source = Path(args.source) if args.source else SIM / f"benchmark/{args.benchmark}/dpu/task.c"
    run([compiler, "-O2", *flags, "-DBL=10", "-DINT32", *args.define, source, "-o", output])


def invoke(stage, directory, benchmark="VA", tasklets=1):
    directory.mkdir(parents=True, exist_ok=True)
    cmd = [BUILD / "simulator", "--root_dirpath", BUILD / f"t{tasklets}",
           "--bin_dirpath", directory, "--log_dirpath", directory,
           "--benchmark", benchmark, "--num_tasklets", tasklets,
           "--num_simulation_threads", 1]
    start = time.monotonic()
    with (directory / f"{stage}.stdout.txt").open("w") as log:
        run(cmd, env={**os.environ, "WRAM_STAGE": stage}, stdout=log,
            stderr=subprocess.STDOUT, timeout=600)
    return time.monotonic() - start


def smoke(args):
    directory = ROOT / f"runs/wram/va-t{args.tasklets}"
    invoke("link", directory, tasklets=args.tasklets)
    n = 256 * args.tasklets
    a = [i % 101 for i in range(n)]
    b = [(3 * i + 7) % 97 for i in range(n)]
    pack = lambda values: struct.pack(f"<{len(values)}I", *values)
    bytefile(directory / "input_DPU_INPUT_ARGUMENTS_0_0.bin", pack([n * 4, n * 4, 0]))
    bytefile(directory / "input_dpu_mram_heap_pointer_name_0_0_0.bin", pack(a + b))
    bytefile(directory / f"output_dpu_mram_heap_pointer_name_{n * 4}_0_0.bin", pack([x + y for x, y in zip(a, b)]))
    (directory / "num_executions.txt").write_text("1\n")
    elapsed = invoke("simulate", directory, tasklets=args.tasklets)
    result = {"benchmark": "upstream VA", "tasklets": args.tasklets, "elements": n,
              "output_check": "passed", "simulator_wall_seconds": elapsed,
              "driver_sha256": hashlib.sha256((SIM / "wram_driver/main.go").read_bytes()).hexdigest()}
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "compile", "smoke"))
    parser.add_argument("--tasklets", type=int, default=1)
    parser.add_argument("--benchmark", default="VA")
    parser.add_argument("--source")
    parser.add_argument("--sdk", action="store_true")
    parser.add_argument("--define", action="append", default=[])
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "compile":
        compile_sources(args)
    else:
        smoke(args)
