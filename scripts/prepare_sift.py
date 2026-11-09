#!/usr/bin/env python3
"""Convert the public ANN-Benchmarks SIFT mirror; never use full-corpus truth for a subset."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".toolchain/python"))
import h5py
import numpy as np

URL = "https://ann-benchmarks.com/sift-128-euclidean.hdf5"
SOURCE_SHA256 = "dd6f0a6ed6b7ebb8934680f861a33ed01ff33991eaee4fd60914d854a0ca5984"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input", type=Path, default=ROOT / ".downloads/sift-128-euclidean.hdf5"
    )
    p.add_argument("--output", type=Path, default=ROOT / "data")
    p.add_argument("--count", type=int, default=100000)
    a = p.parse_args()
    source_digest = sha256(a.input)
    if source_digest != SOURCE_SHA256:
        raise ValueError("SIFT mirror checksum differs from the evaluated source")
    a.output.mkdir(parents=True, exist_ok=True)
    files = {}
    with h5py.File(a.input, "r") as f:
        if not 10 <= a.count <= len(f["train"]):
            p.error("count outside available corpus")
        for source, name, count in [
            ("train", "sift_base.fvecs", a.count),
            ("test", "sift_query.fvecs", len(f["test"])),
        ]:
            x = np.asarray(f[source][:count], dtype="<f4")
            if x.ndim != 2 or x.shape[1] != 128 or not np.isfinite(x).all():
                raise ValueError("invalid SIFT data")
            records = np.empty((len(x), 129), dtype="<f4")
            records[:, 0] = np.array([128], dtype="<i4").view("<f4")[0]
            records[:, 1:] = x
            target = a.output / name
            records.tofile(target)
            files[name] = {
                "sha256": sha256(target),
                "source_key": source,
                "first_id": 0,
                "count": count,
                "dimension": 128,
            }
    manifest = {
        "source_url": URL,
        "source_sha256": source_digest,
        "files": files,
        "ground_truth": "Computed by run_study over exactly the indexed base prefix; distance/id tie order.",
    }
    (a.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
