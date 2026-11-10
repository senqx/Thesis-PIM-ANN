"""Independent checked address emission and graph-expansion request boundaries."""

from collections import Counter
import csv
import hashlib
from pathlib import Path

VECTOR_BASE = 0x10000000


def rows(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))


def records(path):
    return [
        (int(r["query"]), int(r["node"]), r["kind"], int(r["level"]), int(r["bytes"]))
        for r in rows(path)
    ]


def graph_rows(path):
    graph = {}
    for r in rows(path):
        key = (int(r["node"]), int(r["level"]))
        if key in graph:
            raise ValueError("duplicate node/level")
        graph[key] = tuple(map(int, r["neighbors"].split()))
    n = sum(level == 0 for _, level in graph)
    if {node for node, level in graph if level == 0} != set(range(n)):
        raise ValueError("non-dense graph")
    if any(v < 0 or v >= n for neighbors in graph.values() for v in neighbors):
        raise ValueError("edge outside graph")
    return graph


def mapping_rows(path, n):
    values = rows(path)
    if [int(r["logicalId"]) for r in values] != list(range(n)):
        raise ValueError("invalid mapping IDs")
    mapping = [int(r["slot"]) for r in values]
    if sorted(mapping) != list(range(n)):
        raise ValueError("mapping is not a permutation")
    return mapping


def profile_edges(training, graph):
    counts = Counter()
    query = parent = None
    for q, node, kind, level, span in training:
        if q != query:
            parent, query = None, q
        if kind == "A":
            if span != 4 + 4 * len(graph[node, level]):
                raise ValueError("adjacency span mismatch")
            parent = (node, level)
        elif kind == "V":
            if parent is not None and level == parent[1] == 0:
                if node not in graph[parent]:
                    raise ValueError("profile traversal is not a graph edge")
                counts[parent[0], node] += 1
        else:
            raise ValueError("unknown access kind")
    return counts


def split_phases(trace, graph):
    """One list-read phase, then its available vector-read phase; entry reads separate."""
    phases = []
    query = parent = None
    vector_phase = False
    for record in trace:
        q, node, kind, level, span = record
        if q != query:
            if query is not None and q <= query:
                raise ValueError("nonmonotonic query")
            query, parent, vector_phase = q, None, False
        if kind == "A":
            if span != 4 + 4 * len(graph[node, level]):
                raise ValueError("adjacency span mismatch")
            phases.append([record])
            parent, vector_phase = (node, level), False
        elif kind == "V":
            candidate = parent is not None and parent[1] == level
            if candidate and node not in graph[parent]:
                raise ValueError("candidate absent from its expansion list")
            if candidate and vector_phase:
                phases[-1].append(record)
            else:
                phases.append([record])
            vector_phase = candidate
        else:
            raise ValueError("unknown access kind")
    return phases


def phase_rows(phases):
    return [
        dict(
            phase=i,
            query=p[0][0],
            kind=p[0][2],
            logical_records=len(p),
            vector_records=sum(r[2] == "V" for r in p),
            adjacency_transactions=sum((r[4] + 31) // 32 for r in p if r[2] == "A"),
        )
        for i, p in enumerate(phases)
    ]


def adjacency_addresses(graph, n, width):
    cursor = ((VECTOR_BASE + n * width + 1024 * 1024 + 31) // 32) * 32
    result = {}
    for key in sorted(graph):
        result[key] = cursor
        cursor += ((4 + 4 * len(graph[key]) + 31) // 32) * 32
    return result


def phase_addresses(phase, mapping, adjacency, width, mode):
    chunks = []
    for q, node, kind, level, span in phase:
        start = (
            VECTOR_BASE + mapping[node] * width
            if kind == "V"
            else adjacency[node, level]
        )
        size = width if kind == "V" else span
        chunks.append(list(range(start, start + size, 32)))
    original = [a for chunk in chunks for a in chunk]
    if mode in ("flat", "bounded"):
        result = original
    elif mode == "sorted":
        result = sorted(original)
    elif mode == "roundrobin":
        result = [
            chunk[offset]
            for offset in range(max(map(len, chunks)))
            for chunk in chunks
            if offset < len(chunk)
        ]
    else:
        raise ValueError("unknown request schedule")
    if Counter(result) != Counter(original):
        raise ValueError("schedule changed phase transaction multiset")
    return result


def emit(phases, graph, mapping, width, mode, path):
    adjacency = adjacency_addresses(graph, len(mapping), width)
    count = 0
    canonical = hashlib.sha256()
    digest = hashlib.sha256()
    with Path(path).open("wb") as out:
        for i, phase in enumerate(phases):
            addresses = phase_addresses(phase, mapping, adjacency, width, mode)
            canonical.update(
                (str(i) + ":" + ",".join(map(str, sorted(addresses))) + "\n").encode()
            )
            marker = phase[0][0] if mode == "flat" else i
            kind = phase[0][2]
            content = "".join(
                f"LD 0x{a:x} {marker} {kind}\n" for a in addresses
            ).encode()
            out.write(content)
            digest.update(content)
            count += len(addresses)
    return dict(
        trace_sha256=digest.hexdigest(),
        phase_multiset_sha256=canonical.hexdigest(),
        reads=count,
    )
