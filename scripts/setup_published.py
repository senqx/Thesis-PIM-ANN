#!/usr/bin/env python3
"""Fetch hash-pinned NeurIPS supplementary sources and build a small adapter."""

import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://proceedings.neurips.cc/paper_files/paper/2022/file/fb44a668c2d4bc984e9d6ca261262cbb-Supplemental-Conference.zip"
ARCHIVE_SHA = "d91aedfb460b530a1172370d0b2fc084885a67105f9b04d0c33e762c161ddfb7"
HEADERS = (
    "reordering.h",
    "ExplicitSet.h",
    "WeightedPriorityQueue.h",
    "GorderPriorityQueue.h",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup():
    archive = ROOT / ".downloads/coleman-neurips2022.zip"
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        subprocess.run(
            ["curl", "-L", "--fail", "--retry", "2", URL, "-o", str(archive)],
            check=True,
        )
    if digest(archive) != ARCHIVE_SHA:
        raise RuntimeError("Coleman supplementary archive hash mismatch")
    dest = ROOT / ".toolchain/coleman"
    dest.mkdir(parents=True, exist_ok=True)
    original = dest / "original"
    original.mkdir(exist_ok=True)
    with ZipFile(archive) as z:
        for name in HEADERS:
            content = z.read(
                "GraphReorderingSupplementary/GraphReorderingCode/flatnav/" + name
            )
            (original / name).write_bytes(content)
            (dest / name).write_bytes(content)
    header = dest / "reordering.h"
    header.write_text(
        header.read_text().replace(
            '#include "WeightedPriorityQueue.h"',
            '#include "published_priority_queue.h"',
        )
    )
    executable = ROOT / "bin/published_layouts"
    executable.parent.mkdir(exist_ok=True)
    command = [
        "c++",
        "-std=c++20",
        "-O2",
        "-I",
        str(ROOT / "src"),
        "-isystem",
        str(dest),
        str(ROOT / "src/published_layouts.cpp"),
        "-o",
        str(executable),
    ]
    subprocess.run(command, check=True)
    reference = dest / "reference_layouts"
    subprocess.run(
        [
            "c++",
            "-std=c++20",
            "-O2",
            "-isystem",
            str(original),
            str(ROOT / "src/published_layouts.cpp"),
            "-o",
            str(reference),
        ],
        check=True,
    )
    record = dict(
        url=URL,
        archive_sha256=ARCHIVE_SHA,
        headers={name: digest(original / name) for name in HEADERS},
        adapter_header_sha256=digest(header),
        priority_queue_sha256=digest(ROOT / "src/published_priority_queue.h"),
        adaptation="Replace weighted linked-list priority queue with an ordered set, preserving scores and update-recency tie order; retain published layout routines and window-expiration condition.",
        wrapper_sha256=digest(ROOT / "src/published_layouts.cpp"),
        executable_sha256=digest(executable),
        command=command,
        compiler=subprocess.check_output(["c++", "--version"], text=True).splitlines()[
            0
        ],
    )
    (dest / "build.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Built pinned published layout adapter")


if __name__ == "__main__":
    setup()
