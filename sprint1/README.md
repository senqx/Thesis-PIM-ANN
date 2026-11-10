# HNSW trace and layout pipeline

The maintained driver is `run_study`. Build and test with:

```bash
make -C sprint1 test
sprint1/run_study --max-base 8000 --train 300 --test 150 --output work/synthetic
```

For SIFT, provide `--base data/sift_base.fvecs --queries data/sift_query.fvecs` and
`--max-base 100000`. Options also include `--seed`, `--index-seed`, `--ef`, `--k`,
`--window`, `--block-bytes`, and `--no-traces`. The default block is 1024 bytes;
vector footprints are dimension × 4 and dimension × 1, each with a rebuilt layout.
Distance computation remains float32 in both cases.

Outputs retain exact-subset recall, query partitions, all-level logical accesses,
bijective vector mappings, model/cost metadata, proxy metrics, and 32-byte DRAM
transaction streams. See [the reproduction guide](../doc/REPRODUCIBILITY.md) for
simulator configuration, complete experiments, statistics, and document generation. Old duplicated drivers
and figures are under `archive/pre-review/sprint1`; they are not part of this build.
