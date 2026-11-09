#!/usr/bin/env python3
"""Check compiled documents for unresolved references and significant overflow."""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
for stem in ["pim_ann_thesis", "pim_ann_ieee"]:
    log = (ROOT / "doc" / (stem + ".log")).read_text()
    if re.search(
        r"(undefined references|Citation .* undefined|Reference .* undefined)", log
    ):
        raise SystemExit(stem + ": unresolved reference/citation")
    overflows = [
        float(x) for x in re.findall(r"Overfull \\hbox \(([0-9.]+)pt too wide", log)
    ]
    if any(x > 1 for x in overflows):
        raise SystemExit(stem + ": horizontal overflow: " + str(overflows))
    text = subprocess.check_output(
        ["pdftotext", str(ROOT / "doc" / (stem + ".pdf")), "-"], text=True
    )
    if "??" in text:
        raise SystemExit(stem + ": unresolved text marker")
    info = subprocess.check_output(
        ["pdfinfo", str(ROOT / "doc" / (stem + ".pdf"))], text=True
    )
    print(stem, re.search(r"Pages:\s+(\d+)", info).group(0))
print(
    "Both PDFs have resolved citations/references and no significant horizontal overflow."
)
