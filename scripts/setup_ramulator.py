#!/usr/bin/env python3
"""Build the pinned simulator from verified archives and the project frontend."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "ramulator": (
        "https://codeload.github.com/CMU-SAFARI/ramulator2/tar.gz/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da",
        "15c9c3f0c2e1eb3695f3c3dcec71cac9ee4d9b1faf892356622707a179886b59",
    ),
    "fmt": (
        "https://codeload.github.com/fmtlib/fmt/tar.gz/10.2.1",
        "1250e4cc58bf06ee631567523f48848dc4596133e163f02615c97f78bab6c811",
    ),
    "yaml-cpp": (
        "https://codeload.github.com/jbeder/yaml-cpp/tar.gz/yaml-cpp-0.9.0",
        "25cb043240f828a8c51beb830569634bc7ac603978e0f69d6b63558dadefd49a",
    ),
    "nanobind": (
        "https://codeload.github.com/wjakob/nanobind/tar.gz/v2.4.0",
        "bb35deaed7efac5029ed1e33880a415638352f757d49207a8e6013fefb6c49a7",
    ),
    "robin-map": (
        "https://codeload.github.com/Tessil/robin-map/tar.gz/v1.3.0",
        "a8424ad3b0affd4c57ed26f0f3d8a29604f0e1f2ef2089f497f614b1c94c7236",
    ),
}


def sha(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--jobs", type=int, default=4)
    a = p.parse_args()
    if a.jobs < 1:
        p.error("jobs must be positive")
    downloads = ROOT / ".downloads"
    downloads.mkdir(exist_ok=True)
    for name, (url, digest) in SOURCES.items():
        archive = downloads / (name + ".tar.gz")
        if not archive.exists():
            if a.offline:
                raise RuntimeError(f"missing {archive}")
            subprocess.run(
                ["curl", "-L", "--fail", "--retry", "2", url, "-o", str(archive)],
                check=True,
            )
        if sha(archive) != digest:
            raise RuntimeError(f"archive checksum mismatch: {archive}")
        dest = (
            ROOT / "ramulator2"
            if name == "ramulator"
            else ROOT / "ramulator2/ext" / name
        )
        if name == "robin-map":
            dest = ROOT / "ramulator2/ext/nanobind/ext/robin_map"
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as t:
            prefix = t.getmembers()[0].name.split("/")[0] + "/"
            for member in t.getmembers():
                if not member.name.startswith(prefix):
                    continue
                member.name = member.name[len(prefix) :]
                if member.name:
                    t.extract(member, dest, filter="data")
    shutil.copyfile(
        ROOT / "simulator/thesis_trace.cpp",
        ROOT
        / "ramulator2/src/ramulator/frontend/impl/memory_trace/loadstore_trace.cpp",
    )
    args = [
        "cmake",
        "-S",
        str(ROOT / "ramulator2"),
        "-B",
        str(ROOT / "ramulator2/build"),
        "-DFMT_TEST=OFF",
        "-DYAML_CPP_BUILD_TESTS=OFF",
    ]
    for name in ["fmt", "yaml-cpp", "nanobind"]:
        args.append(
            f"-DFETCHCONTENT_SOURCE_DIR_{name.upper()}={ROOT}/ramulator2/ext/{name}"
        )
    subprocess.run(args, check=True)
    subprocess.run(
        ["cmake", "--build", str(ROOT / "ramulator2/build"), "-j", str(a.jobs)],
        check=True,
    )
    manifest = {
        "archives": SOURCES,
        "frontend_sha256": sha(ROOT / "simulator/thesis_trace.cpp"),
        "library_sha256": sha(ROOT / "ramulator2/libramulator.so"),
    }
    (ROOT / "ramulator2/build-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
