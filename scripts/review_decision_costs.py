#!/usr/bin/env python3
"""Independent, untimed cost audit of the corrected artifact at 67bb4be.

Derive simple decisions from kernel work rather than candidate_work(). Do not
change retained measurements, model coefficients, decisions or thesis tables.
All alternative totals below are accounting scenarios, not new timings.
"""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'experiments/decision-study'
DATA = STUDY / 'corrected'
OUTPUT = ROOT / 'docs/DECISION_COST_REVIEW.json'
REVIEWED_COMMIT = '67bb4beed2bfefb55b58fd32e84558ad10fbfb09'
CHECKPOINT = STUDY / 'archive/pre-direct.zip'
CURRENT = False


def checkpoint_bytes(path):
    """Prior derived files are archived; unchanged measurements stay shared."""
    name = str(path.relative_to(ROOT))
    with zipfile.ZipFile(CHECKPOINT) as archive:
        if name in archive.namelist():
            return archive.read(name)
    return path.read_bytes()


def contents(path):
    return path.read_bytes() if CURRENT else checkpoint_bytes(path)


def read(path):
    return json.loads(contents(path))


def digest(path):
    return hashlib.sha256(contents(path)).hexdigest()


def verify_checkpoint():
    manifest = json.loads(checkpoint_bytes(DATA / 'manifest.json'))
    for name, expected in manifest['sha256'].items():
        assert hashlib.sha256(checkpoint_bytes(ROOT / name)).hexdigest() == expected, name
    review = json.loads(checkpoint_bytes(ROOT / 'docs/DECISION_COST_REVIEW.json'))
    for name, expected in review['input_sha256'].items():
        assert hashlib.sha256(checkpoint_bytes(ROOT / name)).hexdigest() == expected, name
    build = json.loads(checkpoint_bytes(ROOT / 'thesis/build.json'))
    for name, expected in build['sha256'].items():
        assert hashlib.sha256(checkpoint_bytes(ROOT / name)).hexdigest() == expected, name



def direct_time(row, uses, bandwidth, cycles=None, refresh=None):
    """One selected encoder, transfers, execution and refresh; no selector tax."""
    device = row['cycles'] if cycles is None else cycles
    refresh = row['refresh_ns'] if refresh is None else refresh
    return (row['prepare_ns'] * 1e-9 + row['stored_metadata_bytes'] / (bandwidth * 1e6)
            + uses * (device / 350e6 + refresh * 1e-9
                      + (row['rows'] + row['columns']) * row['feature_bytes']
                      / (bandwidth * 1e6)))


def capacity_entries(row):
    # The declared allocation, including all 24 reserved stacks; not 64 KiB/F.
    available = (65536 - 49152
                 - row['tasklets'] * (512 + 5 * row['feature_bytes'] + 32) - 2048)
    return (available // 2048 * 2048) // row['feature_bytes']


def run():
    verify_checkpoint()
    phases = ('calibration-t8', 'heldout-t8', 'controlled-t8')
    allrows = [r for phase in phases for r in read(DATA / f'{phase}.json')]
    held = read(DATA / 'heldout-t8.json')
    frozen = read(DATA / 'frozen-model.json')
    assert frozen['fixed'] == 'hot', 'This proof audits the actual frozen fixed policy.'
    groups = {}
    for row in held:
        groups.setdefault((row['input'], row['words']), {})[row['policy']] = row
    assert len(groups) == 24
    scenarios = list(csv.DictReader(gzip.decompress(contents(DATA / 'scenarios.csv.gz')).decode().splitlines()))

    checked = {'streaming_and_full_rows': 0, 'hot_rows': 0}
    for row in allrows:
        n, m, z, f = (row[k] for k in ('rows', 'columns', 'nnz', 'feature_bytes'))
        policy = row['policy']
        if policy not in ('stream128', 'stream512', 'full', 'hot'):
            continue
        assert row['stored_metadata_bytes'] == ((n + 1) * 4 + 31) // 32 * 32 + 8 * z
        assert row['expected_writes'] == n * f
        if policy == 'hot':
            h = min(m, capacity_entries(row))
            assert row['hot_entries'] == h
            counts = [0] * m
            for _, col, _ in read(STUDY / 'inputs' / f'{row["input"]}.json')['entries']:
                counts[col] += 1
            hits = sum(sorted(counts, reverse=True)[:h])
            reads = 8 * n + 8 * z + (h + z - hits) * f
            assert (h + z - hits <= z) == (h <= z)
            checked['hot_rows'] += 1
        else:
            reads = 8 * n + 8 * z + (m if policy == 'full' else z) * f
            checked['streaming_and_full_rows'] += 1
        assert row['expected_reads'] == reads, row['key']

    # Exercise empty, equal-boundary and skewed frequency vectors independently
    # of the retained datasets. The accompanying review also gives the proof.
    frequency_cases = 0
    for columns in range(1, 6):
        for counts in itertools.product(range(4), repeat=columns):
            z = sum(counts)
            for h in range(columns + 1):
                hits = sum(sorted(counts, reverse=True)[:h])
                assert (h + z - hits <= z) == (h <= z)
                # Balanced frequencies minimize the top-H sum; this lower bound
                # can prove the reuse threshold without a structural inspector.
                bound = h * (z // columns) + min(h, z % columns)
                assert hits >= bound
                if 2 * bound >= z:
                    assert 2 * hits >= z
                frequency_cases += 1

    capacity_excess = []
    indexed = {}
    for d in scenarios:
        key = (d['input'], int(d['words']), d['constrained'] == 'True',
               int(d['uses']), int(d['bandwidth_mb_s']), int(d['launch_us']), d['rule'])
        assert key not in indexed
        indexed[key] = d
    assert len(indexed) == 23040

    refresh_changes = []
    choice_checks = 0
    for (name, words), by in groups.items():
        s = by['stream512']
        header_fixed = 'hot' if s['nnz'] >= min(s['columns'], capacity_entries(s)) else 'stream512'
        full_fits = s['columns'] <= capacity_entries(s)
        assert ('full' in by) == full_fits
        header_capacity = 'full' if full_fits and s['columns'] <= s['nnz'] else 'stream512'
        for rule, choice in (('fixed', header_fixed), ('capacity', header_capacity)):
            assert indexed[name, words, True, 1, 80, 0, rule]['chosen'] == choice
        if full_fits:
            d = indexed[name, words, True, 1, 80, 0, 'capacity']
            capacity_excess.append((float(d['setup_ns']) - by[d['chosen']]['prepare_ns']) / 1000)
        for constrained in (True, False):
            eligible = [r for r in by.values() if not constrained or (
                r['stored_metadata_bytes'] <= s['stored_metadata_bytes']
                and r['expected_reads'] + r['expected_writes']
                <= s['expected_reads'] + s['expected_writes'])]
            predictions = {r['policy']: sum(c * x for c, x in zip(
                frozen['models'][r['policy']]['coefficients'], r['model_features'])) for r in eligible}
            for k in frozen['valid_uses']:
                for bw in frozen['bandwidth_mb_s']:
                    def pick(refresh_zero):
                        # All-candidate setup is common to the model's alternatives.
                        def predicted_cost(r):
                            return direct_time(r, k, bw, cycles=predictions[r['policy']],
                                               refresh=0 if refresh_zero else None) - r['prepare_ns'] * 1e-9
                        return min(eligible, key=predicted_cost)['policy']
                    observed, zero = pick(False), pick(True)
                    assert observed == indexed[name, words, constrained, k, bw, 0, 'model']['chosen']
                    choice_checks += 1
                    if observed != zero:
                        refresh_changes.append([name, words, constrained, k, bw, observed, zero])

    alternatives = []
    optimistic = []
    for k in frozen['valid_uses']:
        totals = {r: [] for r in ('model', 'fixed', 'capacity', 'reuse')}
        baseline_regrets = {r: {'reported': [], 'one_encoder': []} for r in ('fixed', 'capacity')}
        slowdowns = []
        for (name, words), by in groups.items():
            d = {r: indexed[name, words, True, k, 80, 0, r] for r in totals}
            # Give the model free inspection, rejected-candidate construction,
            # prediction and knowledge of native costs; retain selected execution.
            case = {r: direct_time(by[d[r]['chosen']], k, 80) for r in ('model', 'fixed', 'capacity')}
            case['reuse'] = float(d['reuse']['total_seconds'])
            for rule, value in case.items():
                totals[rule].append(value)
            for rule in baseline_regrets:
                if CURRENT:
                    assert abs(case[rule] - float(d[rule]['total_seconds'])) < 1e-12
                baseline_regrets[rule]['reported'].append(float(d[rule]['regret_pct']))
                baseline_regrets[rule]['one_encoder'].append(100 * (case[rule] / float(d[rule]['oracle_seconds']) - 1))
            slowdowns.append(100 * (case['model'] / min(case[r] for r in ('fixed', 'capacity', 'reuse')) - 1))
        means = {r: statistics.mean(v) for r, v in totals.items()}
        best = min(means[r] for r in ('fixed', 'capacity', 'reuse'))
        optimistic.append(dict(uses=k,model_mean_ms=means['model']*1000,
            best_simple_mean_ms=best*1000,worst_slowdown_pct=max(slowdowns),
            passes=means['model'] < best and max(slowdowns) <= 5))
        alternatives.append(dict(uses=k, **{rule: {name: statistics.mean(values)
            for name, values in variants.items()} for rule, variants in baseline_regrets.items()}))

    sources = [ROOT / 'scripts/decision_analysis.py', STUDY / 'prepare.cpp', STUDY / 'task.c',
               ROOT / 'scripts/review_decision_costs.py']
    if CURRENT:
        sources += [DATA / name for name in ('heldout-t8.json', 'calibration-t8.json',
            'controlled-t8.json', 'scenarios.csv.gz', 'frozen-model.json')]
        sources += sorted((STUDY / 'inputs').glob('*.json'))
    else:
        sources.append(DATA / 'manifest.json')
    result = dict(reviewed_commit='current-sources-pinned-below' if CURRENT else REVIEWED_COMMIT,accounting_scenarios_not_new_timings=True,
        diagnostic_scenario=dict(constrained=True, bandwidth_mb_s=80, launch_us=0,
            simple_dispatch_timing_included=False),
        input_sha256={str(p.relative_to(ROOT)): digest(p) for p in sources},
        formula_checks=checked,exhaustive_frequency_cases=frequency_cases,
        header_decisions_match_all_24_conditions=True,
        capacity_full_present_conditions=len(capacity_excess),
        avoidable_capacity_charge_us=[min(capacity_excess),max(capacity_excess)],
        model_choice_checks=choice_checks,zero_refresh_changed_choices=refresh_changes,
        simple_rule_accounting=alternatives,zero_selection_overhead=optimistic)
    OUTPUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(f'PASS: {checked}; {frequency_cases} frequency boundary cases; {choice_checks} model choices.')
    print(f'Zero-refresh changes: {len(refresh_changes)}. Optimistic model passes: {sum(r["passes"] for r in optimistic)}/8.')
    print(f'Review evidence: {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', action='store_true', help='Audit regenerated current accounting, preserving the historical review.')
    args = parser.parse_args()
    CURRENT = args.current
    if CURRENT:
        OUTPUT = DATA / 'accounting-audit.json'
    run()
