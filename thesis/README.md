# Thesis draft: When Is WRAM Reuse Worth It?

**Revised 24 November 2026.** The draft explains the domain and terminology,
then develops the question: when do local reuse and its preparation pay off?
It preserves the original graph-aggregation pilot and adds a completed
[standard sparse-operation evaluation](../experiments/decision-study/README.md).
The frozen selector failed its practical-success criterion; the text reports
that negative result alongside useful static-retention regimes.

Start with [short-thesis.pdf](short-thesis.pdf), or read the same text in
[short-thesis.md](short-thesis.md). The filenames are retained for existing links.
The reading path is:

1. Sections 1–3: memory movement, UPMEM and a worked graph/matrix example.
2. Sections 4–6: prior work, three research questions and competing mechanisms.
3. Sections 7–10: the historical pilot, stronger controls and initial preparation costs.
4. Sections 11–12: cost accounting and the completed standard-workload methodology.
5. Section 13: capacity/width results, payback, failed selection and robustness checks.
6. Sections 14–15: practical guidance, the boundary between this study and later
   research stages, and an explicit answer to each RQ.

The appendices provide a reproduction path and glossary. PDF bookmarks follow
the section/subsection hierarchy. Three schematics explain the architecture,
mechanisms and evaluated decision process. Five numerical figures distinguish
executed settings from modelled lifetimes; infeasible full-retention points are
not interpolated. The [gap-closure record](../docs/GAP_CLOSURE.md) explains which
concerns were tested and which remain outside this simulator study.

The contribution is comparative evidence and a held-out negative result,
not a new retention algorithm or a hardware/application speedup claim.
The [novelty audit](../docs/NOVELTY_AUDIT.md) documents that distinction.

## Build

From the repository root, install the pinned document dependencies into an
isolated environment, or the ignored local dependency directory:

```sh
python3 -m pip install --target .deps/thesis-pdf -r thesis/requirements.txt
MPLCONFIGDIR=build/matplotlib PYTHONPATH=.deps/thesis-pdf python3 scripts/thesis_figures.py
MPLCONFIGDIR=build/matplotlib PYTHONPATH=.deps/thesis-pdf python3 scripts/decision_analysis.py figures
python3 scripts/decision_report.py
python3 scripts/build_short_thesis.py
pdfinfo thesis/short-thesis.pdf
```

The build uses Liberation Serif, Liberation Mono and GNU FreeSans font files
from `/usr/share/fonts`, plus `pdfinfo` from Poppler. The source is Markdown;
ReportLab produces the PDF with embedded fonts and numbered references.
Four result tables are refreshed from retained data during the build. Figure
scripts generate PNGs and standalone vector PDFs. Their plotted values are in
[figures/plotted-data.json](figures/plotted-data.json) and the
[decision-study plot record](../experiments/decision-study/plotted-data.json).

[build.json](build.json) records the actual PDF page count, dependency versions
and source/PDF/figure/evidence hashes. It is the authoritative page-count record;
rebuilding does not require manually synchronizing a second count. PDF and figure
metadata use fixed timestamps; the research date appears in the text. The PDF
includes no fabricated supervisor or university information. The
[validation record](../docs/VALIDATION.md) ties checks to the current artifacts.

## Verify and replay

```sh
python3 scripts/access_plan_fivepoint.py verify
python3 scripts/access_plan_gates.py verify
python3 scripts/decision_artifact.py verify
python3 scripts/decision_artifact.py replay
```

Audits read retained records. Fresh replay needs the pinned simulator, but no
compiler SDK or dataset download; see the experiment README for setup. Keep
source rebuilds and new CPU measurements separate from the retained campaign.
Rebuilding figures/reports does not refit or retime the frozen decision model.
