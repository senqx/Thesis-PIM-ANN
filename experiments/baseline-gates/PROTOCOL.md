# Two baseline gates before selective preparation

Frozen before these runs, 23 November 2026. This is an exploratory screen,
not a new independent dataset or a confirmatory evaluation of the selector.

Use the five-point study's largest size: 3,072 destinations, eight references
per destination, 8-byte records, 12 tasklets and seeds 23/61. Reuse its exact
community, uniform and sampled ca-GrQc inputs and frozen comparison images.

Run fourteen new configurations:

- Six `compact64` executions: all three families and both seeds. Change the
  batch dictionary from 32-bit to 16-bit source IDs, keeping the 64-reference
  window, 256-byte index buffer and 512-byte retained payload per tasklet.
  Preserve the header, ordered slot list and arithmetic. Count dictionary
  padding and unequal tasklet-segment padding separately.
- Eight shared preload executions: community/uniform, both seeds, with
  128/512-byte index buffers. Cooperating tasklets load the full 4,096-byte
  feature table through eight disjoint 512-byte DMA reads. All twelve tasklets
  synchronize before aggregating. Include initialization and synchronization
  in complete kernel cycles. Each invocation reloads the current feature values.

The 41,928-byte ca-GrQc feature table cannot fit alongside the linker's
49,152-byte stack reservation. Do not run or extrapolate full residency for
that input. No partial/hot-set residency policy is tested by this screen.

Comparators are 24 retained configurations: the three compressed streaming
buffers and original batch64 for each input/seed. All variants share the
64 KiB WRAM ceiling; actual allocations may differ. Report both preload
buffers, with their minimum explicitly a hindsight comparator, not a selector.

For each new execution check every output against the CPU reference, logical
input equality, exact local read/write accounting and complete WRAM reservation.
Record instructions, cycles, installed metadata, read metadata and feature
loads. Freeze linked programs, inputs/outputs and all simulator counters for
replay. The index encoding changes MRAM feature placement; cycle differences
are whole-implementation comparisons, not a pure instruction-cost ablation.

Use the existing pinned Go uPIMulator and SDK/compiler without timing changes.
Two simulator jobs may run concurrently, each with a ten-minute timeout. No
CPU preparation, host transfers or energy are timed here. Kernel cycle savings
do not establish setup-inclusive or hardware acceleration.

Do not produce a size curve from this single-size screen. If a useful
opportunity survives the controls, a separate frozen protocol must extend it
to at least five actual points per plotted sweep. If conventional residency
wins where the full table fits, treat it as the preferred tested baseline for
that regime; it is not an original method.
