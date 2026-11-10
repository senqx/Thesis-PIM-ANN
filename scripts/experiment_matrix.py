"""Exact retained replay names; validation must not substitute a total count."""

LAYOUTS = ("identity", "random", "bfs", "community", "query_aware")
WIDTHS = (128, 512)


def expected_replays():
    labels = []
    for name in ("sequential", "random"):
        labels.append(f"micro/order/{name}")
        for cap in (1, 4):
            labels.append(f"micro/cap{cap}/{name}")
    for window in (1, 16, 64, 256, 1024, 4096, 16384):
        labels.append(f"micro/reorder/w{window}")
    for condition in ("reorder_rowhit", "reorder_inflight1"):
        for window in (1, 256, 16384):
            labels.append(f"micro/{condition}/w{window}")
    for width in (96, 128, 192, 256, 384, 512):
        for offset in (0, 32, 480):
            for run in (1, 2, 4, 8, 16, 32, 64):
                labels.append(f"micro/runs/width{width}_offset{offset}_run{run}")
        for run in (1, 4, 16, 64):
            labels.append(f"micro/runs_alternate/width{width}_run{run}")
    for quality in (0, 25, 50, 75, 90, 100):
        labels.append(f"micro/quality/q{quality}")
    for layout in LAYOUTS:
        for width in WIDTHS:
            stem = f"{layout}_{width}"
            labels.append(f"synthetic/timing/{stem}")
            for seed in range(1, 11):
                labels.append(f"sift/seed{seed}/timing/{stem}")
                for condition in ("inflight1", "cap4", "alternate_mapping"):
                    labels.append(
                        f"robustness/controllers/{condition}/seed{seed}/{stem}"
                    )
            for condition in (
                "inflight1",
                "inflight16",
                "queue8",
                "issue4",
                "cap1",
                "cap4",
                "rowhit",
                "alternate_mapping",
            ):
                labels.append(f"sensitivity/{condition}/{stem}")
            for graph in ("index101", "index102", "order17"):
                for seed in range(1, 4):
                    labels.append(f"robustness/graphs/{graph}/seed{seed}/timing/{stem}")
    for condition in ("train100", "train1000", "window4", "window64", "block2048"):
        for width in WIDTHS:
            for layout in ("bfs", "query_aware"):
                labels.append(f"ablations/{condition}/timing/{layout}_{width}")
    for inflight in (1, 64):
        for layout in ("sequential", "random"):
            labels.append(f"mechanism/micro/{layout}_inflight{inflight}")
        for layout in ("bfs", "query_aware"):
            for component in ("mixed", "vectors", "adjacency"):
                labels.append(f"mechanism/sift/{layout}_{component}_inflight{inflight}")
    paths = {label + ".json" for label in labels}
    if len(paths) != len(labels):
        raise ValueError("duplicate planned replay")
    from followup import expected_followup
    from followup_mechanism import expected_mechanism
    from scheduling import expected_scheduling
    from profiled_fetch import expected_calibration

    paths |= expected_followup()
    paths |= expected_mechanism()
    paths |= expected_scheduling()
    paths |= expected_calibration()
    return paths
