"""Static offered-stream diagnostics, distinct from controller queue occupancy."""

from collections import Counter, deque
import json
from pathlib import Path
from result_validation import sha256


def offered_bank_diversity(path):
    counts = Counter()
    window = deque()
    total = samples = 0
    previous_query = None
    with Path(path).open() as stream:
        for line in stream:
            parts = line.split()
            query = int(parts[2]) if len(parts) == 4 else 0
            if query != previous_query:
                counts.clear()
                window.clear()
                previous_query = query
            bank = (int(parts[1], 0) >> 10) & 63
            window.append(bank)
            counts[bank] += 1
            if len(window) > 64:
                old = window.popleft()
                counts[old] -= 1
                if not counts[old]:
                    del counts[old]
            if len(window) == 64:
                total += len(counts)
                samples += 1
    if not samples:
        raise ValueError("no complete within-query 64-request window")
    return dict(
        mean_distinct_banks=total / samples,
        windows=samples,
        bank_count_sum=total,
        trace_sha256=sha256(path),
    )


def record_offered_banks(root, work):
    inputs = dict(
        sequential=work / "micro/seq.trace",
        random=work / "micro/rand.trace",
        bfs=work / "robustness/reference/seed1/bfs_128.trace",
        query_aware=work / "robustness/reference/seed1/query_aware_128.trace",
    )
    output = root / "results/mechanism/offered_banks.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({k: offered_bank_diversity(v) for k, v in inputs.items()}, indent=2)
        + "\n"
    )
