# Document and artifact validation

Checked on **23 November 2026** for the GitHub publication checkpoint.

The [current PDF](../thesis/short-thesis.pdf) integrates the five-size experiment
and the later baseline controls. Its exact source, figures, evidence manifests,
page count and PDF hash are recorded together in [thesis/build.json](../thesis/build.json).
The research remains exploratory: the predictor and selective planner are
proposed work, and hardware timing and energy are unvalidated.

## Evidence checks

| Artifact | Retained records | Check |
| --- | ---: | --- |
| [Initial WRAM pilot](../experiments/wram/README.md) | 160 | File hashes and distinct records passed |
| [Prepared-access study](../experiments/access-plan/README.md) | 137 | Hashes, counters, outputs and paired controls passed |
| [Three-size checkpoint](../experiments/access-plan-scaling/README.md) | 108 | Records and 792 CPU timings passed; these configurations are included in the next row |
| [Five-size study](../experiments/access-plan-fivepoint/README.md) | 180 | Records, 1,320 CPU timings, preserved inputs and five sizes passed |
| [Baseline controls](../experiments/baseline-gates/README.md) | 38 | Fourteen new records and 24 reused comparators passed output, traffic, WRAM and hash checks |

The last two artifacts contain **194 distinct configurations**, with an
intersection of exactly 24. Their records must not be summed as independent
experiments. The 137-record study includes 132 performance configurations,
two feature-update checks and three transfer probes. CPU timing samples are
separate measurements, not additional DPU experiments.

Reproduce the retained-record audits from the repository root:

```sh
python3 scripts/wram_verify.py
python3 scripts/access_plan_artifact.py verify
python3 scripts/access_plan_scaling.py verify
python3 scripts/access_plan_fivepoint.py verify
python3 scripts/access_plan_gates.py verify
```

Two fresh baseline-control replays also passed on this date:
`community-s23-n3072-preload128` and `grqc-s61-n3072-compact64`.
Each matched every stored simulator counter and non-path option and passed
the simulator's complete output check. Replay instructions and exact linked
programs accompany the artifact. This is reproducibility evidence, not new
independent workloads or a validation of physical hardware timing.

## Document checks

- The PDF was built from the current Markdown source and visually reviewed
  across all pages, with detailed checks of figures and the new baseline table.
- Its title and author are correct; no supervisor or university affiliation
  has been invented. No additional university format was supplied.
- Both numerical tables are generated from retained CSV data. The baseline
  table distinguishes local reads from installed index/plan bytes.
- All twelve plotted data series have five points. Seed ranges are labelled
  as descriptive ranges, and modelled reuse counts are distinguished from
  actual workload-size settings.
- Figures and tables retain their captions. Repository links in the standalone
  PDF resolve to GitHub URLs rather than paths relative to a downloaded PDF.
- References are numbered in order of first citation. SparseP and PyGim DOI,
  title and publication metadata were checked; preprints are labelled.
- A second complete figure/document build produced identical PDF, Markdown,
  figure and build-record hashes in the pinned local environment.
- Local Markdown links, Python syntax and Git whitespace checks passed.

The [build instructions](../thesis/README.md) give the dependency versions and
commands. The PDF and figure metadata use fixed timestamps for reproducible
builds; the research date is stated in the text.

## Interpretation of this checkpoint

The five-size curves use the original batch format and its measured preparation
cost. The later compact-dictionary and shared-residency controls are single-size
kernel comparisons; their preparation payback has not been measured. Shared
residency is the strongest tested choice where the small feature table fits.
Partial residency, larger working sets and a validated selector remain in the
[research direction](CONTRIBUTION_PLAN.md).

This check supports publishing a readable, reproducible research checkpoint.
It does not certify novelty, final university acceptance or application-level
PIM acceleration.
