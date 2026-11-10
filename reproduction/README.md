# Fresh reproduction checks

[10 November 2026](2026-11-10/comparison.json) retains three fresh checks:

| Retained reference | Purpose |
| --- | --- |
| `followup/reference/seed1/roundrobin/bfs_512.json` | The default 512-byte round-robin path. |
| `scheduling/seed1/alternate_mapping/roundrobin_512.json` | A configuration where that order increases service time. |
| `calibration/seed1/default/roundrobin_512.json` | The separate training-calibration stream. |

For each, `scripts/reproduce_replay.py` built the HNSW graph/search outputs in a
new directory, verified their hashes against retained evidence, emitted a new
trace, and directly invoked the simulator without replay-cache reuse. The search
and simulator executables were the existing checked builds; these spot checks
are not an additional compiler or hardware validation.

The `results/` subtree contains the fresh raw JSON and losslessly compressed
query/phase sidecars. `details/` retains reconstruction proofs and search/replay
logs. All three match their references exactly in trace hash, model settings,
simulator statistics, total cycles and each query/phase service record.

These are **three reproduction repeats**, separate from the 2,069 distinct records
in the experiment matrix. They provide no additional independent performance
samples. Large regenerated traces and graph/search intermediates remain in
`work/` under the usual artifact policy; their hashes and regeneration command
are retained.

The [reproducibility guide](../doc/REPRODUCIBILITY.md) explains how to repeat these
checks and run the entire matrix in a separate checkout. A successful comparison
of committed copies alone must not be described as a fresh simulation.
