#!/usr/bin/env python3
"""Check PDF layout, maintained navigation, page counts and evidence inventory."""

import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
page_counts = {}
for stem in ["pim_ann_thesis", "pim_ann_ieee", "pim_ann_defence"]:
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
    if re.search(r"Overfull \\vbox", log):
        raise SystemExit(stem + ": vertical overflow")
    text = subprocess.check_output(
        ["pdftotext", str(ROOT / "doc" / (stem + ".pdf")), "-"], text=True
    )
    if "??" in text:
        raise SystemExit(stem + ": unresolved text marker")
    info = subprocess.check_output(
        ["pdfinfo", str(ROOT / "doc" / (stem + ".pdf"))], text=True
    )
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    page_counts[ROOT / "doc" / (stem + ".pdf")] = pages
    if stem == "pim_ann_defence":
        slides = (ROOT / "doc" / (stem + ".tex")).read_text().count(r"\begin{slide}")
        if pages != slides:
            raise SystemExit(f"{stem}: {slides} slides spill into {pages} PDF pages")
    print(stem, "Pages:", pages)
print(
    "All three PDFs have resolved citations/references and no significant overflow."
)

# The validation table puts its counts in a separate cell from the PDF link.
# Restrict this check to the current set; historical revisions retain old counts.
validation = (ROOT / "doc/VALIDATION.md").read_text()
current_set = re.search(
    r"^## Current document set\n(.*?)(?=^## |\Z)", validation, re.M | re.S
)
if not current_set:
    raise SystemExit("VALIDATION.md: missing current document set")
documented_counts = {
    (ROOT / "doc" / target).resolve(): int(count)
    for target, count in re.findall(
        r"^\| \[[^\]]+\]\(([^)]+)\) \| (\d+) (?:pages|slides)\b",
        current_set.group(1), re.M,
    )
}
if documented_counts != page_counts:
    raise SystemExit("VALIDATION.md: current Extent column must match PDF page counts")
print("Current validation table agrees with PDF page counts.")

# Check maintained navigation, including relocated review notes. Byte-identical
# historical snapshots deliberately retain the links and claims of their revision.
documents = [
    *sorted(ROOT.glob("*.md")),
    *sorted((ROOT / "doc").glob("*.md")),
    ROOT / "archive/README.md",
    *sorted((ROOT / "archive/review-notes").glob("*.md")),
    ROOT / "reproduction/README.md",
]
checked = 0
for document in documents:
    for label, target in re.findall(
        r"\[([^\]\n]+)\]\(([^)\n]+)\)", document.read_text()
    ):
        url = urlsplit(target.strip("<>"))
        if url.scheme or url.netloc:
            continue
        path = (document.parent / unquote(url.path)).resolve() if url.path else document
        if not path.exists():
            raise SystemExit(f"{document.relative_to(ROOT)}: broken link {target}")
        if url.fragment and path.suffix == ".md":
            headings = re.findall(r"^#{1,6}\s+(.+?)\s*#*$", path.read_text(), re.M)
            anchors = {
                re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                for heading in headings
            }
            if unquote(url.fragment) not in anchors:
                raise SystemExit(f"{document.relative_to(ROOT)}: broken anchor {target}")
        stated_pages = re.search(r"(\d+)\s+(?:pages|slides)", label)
        if path in page_counts and stated_pages:
            if int(stated_pages.group(1)) != page_counts[path]:
                raise SystemExit(f"{document.relative_to(ROOT)}: stale page count {label}")
        checked += 1
print(f"{checked} local documentation links resolve; linked PDF page counts agree.")

# This is a documentation inventory check, not a substitute for check_results.py.
replays = []
for path in (ROOT / "results").rglob("*.json"):
    if ".cache." in path.name:
        continue
    record = json.loads(path.read_text())
    if isinstance(record, dict) and {
        "ramulator_commit", "trace_sha256", "stats"
    } <= record.keys():
        replays.append(path)
count_patterns = {
    "README.md": r"Current evidence: ([\d,]+) replay records",
    "doc/VALIDATION.md": r"current artifact contains \*\*([\d,]+) distinct replay records",
    "doc/REPRODUCIBILITY.md": r"current matrix contains \*\*([\d,]+) distinct replay records",
    "archive/review-notes/PROJECT_OVERVIEW.md": r"Current evidence is \*\*([\d,]+) replay records",
}
for path, pattern in count_patterns.items():
    match = re.search(pattern, (ROOT / path).read_text())
    if not match or int(match.group(1).replace(",", "")) != len(replays):
        raise SystemExit(
            f"{path}: current evidence count must match {len(replays)} retained records"
        )
print(f"Current evidence counts agree with {len(replays):,} retained replay JSON records.")
