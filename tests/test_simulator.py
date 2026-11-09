#!/usr/bin/env python3
"""Integration checks against the actual pinned mapper, callbacks and policies."""

import csv
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_ann_ramulator import run

sys.path.insert(0, str(ROOT / "ramulator2/python"))
import ramulator


def main():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        addresses = [0, 32, 992, 1024, 2048, 4096, 16384, 65536, 0x10000000, 0x7FFFFFE0]
        trace = folder / "mapping.trace"
        trace.write_text(
            "".join(f"LD {a} {i // 5} V\n" for i, a in enumerate(addresses))
        )
        for mapper in ["RoBaRaCoCh", "ChRaBaRoCo"]:
            result = run(trace, folder / "result.json", mapper=mapper, inflight=1)
            assert result["checks"]["completed_callbacks"] == len(addresses)
            assert result["stats"]["frontend"]["peak_inflight"] == 1
            config = result["config"]
            config["frontend"]["mapping_output"] = str(folder / "mapping.csv")
            sim = ramulator.Simulation(config["frontend"], config["memory_system"])
            sim.run()
            sim.finalize()
            for row in csv.DictReader((folder / "mapping.csv").open()):
                a = int(row["address"])
                values = {k: int(v) for k, v in row.items()}
                if mapper == "RoBaRaCoCh":
                    expected = dict(
                        column=(a >> 5) & 31,
                        pseudochannel=(a >> 10) & 1,
                        sid=(a >> 11) & 1,
                        bankgroup=(a >> 12) & 3,
                        bank=(a >> 14) & 3,
                        row=(a >> 16) & 32767,
                    )
                else:
                    expected = dict(
                        column=(a >> 5) & 31,
                        row=(a >> 10) & 32767,
                        bank=(a >> 25) & 3,
                        bankgroup=(a >> 27) & 3,
                        sid=(a >> 29) & 1,
                        pseudochannel=(a >> 30) & 1,
                    )
                for k, v in expected.items():
                    assert values[k] == v, (mapper, a, k, values[k], v)
                assert values["channel"] == 0
        for cap in [1, 4]:
            result = run(
                trace, folder / "result.json", policy="ClosedCAP", cap=cap, inflight=2
            )
            assert result["stats"]["frontend"]["completed"] == 10
            assert result["stats"]["frontend"]["peak_inflight"] <= 2
        plain = run(trace, folder / "plain.json")
        observed = run(trace, folder / "observed.json", commands=2)
        assert observed["cycles"] == plain["cycles"]
        assert observed["row_hit_pct"] == plain["row_hit_pct"]
        assert observed["checks"] == plain["checks"]
        assert observed["command_counts"]["RD"] == len(addresses)
        trace.write_text("LD 0 0 V\n")
        result = run(trace, folder / "single.json")
        assert result["cycles"] > 0 and result["checks"]["completed_callbacks"] == 1
        for invalid in ["", "LD 1\n", "ST 32\n", "LD 32 2 V\nLD 64 1 V\n"]:
            trace.write_text(invalid)
            try:
                run(trace, folder / "invalid.json")
            except RuntimeError:
                pass
            else:
                raise AssertionError("bad trace accepted")
    print(
        "Native 32-byte geometry, both mappers, query drain, policies and malformed traces passed"
    )


if __name__ == "__main__":
    main()
