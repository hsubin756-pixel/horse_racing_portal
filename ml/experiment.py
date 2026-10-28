"""Audited, offline feature ablation and prospectively frozen final evaluation.
Never downloads data, modifies service artifacts or claims pre-race snapshot validity.
"""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
import sklearn

from evaluate_tracks import COHORTS, merge

BASE = ['priorMeanFinish', 'starts', 'distance']
RECENT = ['recentMeanFinish', 'recentTop3Rate', 'daysSinceLastStart', 'hasHistory']
DISTANCE = ['distanceTop3Rate', 'distanceStarts']
CONNECTIONS = ['jockeyTop3Rate', 'jockeyStarts', 'trainerTop3Rate', 'trainerStarts']
PHYSICAL = ['carriedWeight', 'horseWeight', 'gate', 'fieldSize', 'ageYears', 'sexCode']
SETS = {
    'base': BASE,
    'recent': BASE + RECENT,
    'distance': BASE + DISTANCE,
    'connections': BASE + CONNECTIONS,
    'physical': BASE + PHYSICAL,
    'combined': BASE + RECENT + DISTANCE + CONNECTIONS + PHYSICAL,
}
for name, columns in [('recent', RECENT), ('distance', DISTANCE), ('connections', CONNECTIONS), ('physical', PHYSICAL)]:
    SETS['without_' + name] = [c for c in SETS['combined'] if c not in columns]
PARAMS = dict(n_estimators=120, max_depth=5, min_samples_leaf=8, random_state=42, n_jobs=1)
LIMITS = [
    'Retrospective results CSV: pre-race availability timestamps are absent; no live-pre-race validation claim.',
    'Roster contains retained finishers after export exclusions; field size and evaluation population may use post-race selection.',
    'Result-API odds are treated as post-close reference, not a timestamp-matched executable price or model input.',
    'History uses strictly earlier race dates, not verified historical publication timestamps; late corrections remain possible.',
    'Person identities use names scoped by track; transfers are split and same-name people may still collide.',
    'Histories update from earlier test dates; model weights stay fixed. Service histories are currently frozen instead.',
    'Scores are not calibrated probabilities; no profit claim, significance claim or automatic model promotion.',
]


def today():
    return datetime.now(ZoneInfo('Asia/Seoul')).date()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def code_hash():
    return digest({p: hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest()
                   for p in ('experiment.py', 'evaluate_tracks.py', 'evaluate_extended.py')})


def read(paths):
    hashes = {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    races = merge(paths)
    for key, rows in races.items():
        if len({(r['race_date'], r['distance']) for r in rows}) != 1:
            raise ValueError('Inconsistent date/distance in race: ' + key)
        if len({r['horse_id'] for r in rows}) != len(rows):
            raise ValueError('Duplicate starter: ' + key)
        if any(r['horse_id'] <= 0 or not 400 <= r['distance'] <= 10000 for r in rows):
            raise ValueError('Invalid identifier or distance: ' + key)
        parts = key.split(':')
        if len(parts) != 3 or parts[1] != rows[0]['race_date'].strftime('%Y%m%d') or not parts[2].isdigit():
            raise ValueError('Race ID/date mismatch: ' + key)
        rows.sort(key=lambda r: r['horse_id'])  # Never break score ties by finishing order in the CSV.
    if hashes != {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}:
        raise ValueError('CSV changed while reading; retry after collection')
    return races, hashes


def finite(value, fallback):
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


def features(races):
    by_date, horses, people = defaultdict(list), defaultdict(list), defaultdict(list)
    table, labels, groups, dates, market = [], [], [], [], []
    for key, rows in races.items():
        by_date[rows[0]['race_date']].append((key, rows))
    for day, day_races in sorted(by_date.items()):
        for key, rows in sorted(day_races):
            rows = sorted(rows, key=lambda r: r['horse_id'])
            odds = [finite(r.get('win_odds'), math.nan) for r in rows]
            complete_odds = all(math.isfinite(o) and o >= 1 for o in odds)
            for i, r in enumerate(sorted(rows, key=lambda r: r['horse_id'])):
                past = horses[r['horse_id']]
                recent = past[-5:]
                similar = [p for p in past if abs(p[1] - r['distance']) <= 200]
                f = {'priorMeanFinish': float(np.mean([p[2] for p in past])) if past else 12.5,
                     'starts': len(past), 'distance': r['distance'],
                     'recentMeanFinish': float(np.mean([p[2] for p in recent])) if recent else 12.5,
                     'recentTop3Rate': (sum(p[2] <= 3 for p in recent) + .84) / (len(recent) + 3),
                     'daysSinceLastStart': (day - past[-1][0]).days if past else 0,
                     'hasHistory': int(bool(past)),
                     'distanceTop3Rate': (sum(p[2] <= 3 for p in similar) + .84) / (len(similar) + 3),
                     'distanceStarts': len(similar)}
                for role, prefix in [('jockey', 'jockey'), ('trainer', 'trainer')]:
                    name = r.get(role, '').strip()
                    history = people[(key.split(':')[0], role, name)] if name else []
                    f[prefix + 'Top3Rate'] = (sum(history) + .84) / (len(history) + 3)
                    f[prefix + 'Starts'] = len(history)
                birth = date.fromisoformat(r['birth_date']) if r.get('birth_date') else None
                if birth and birth > day:
                    raise ValueError('Birth date after race date')
                f.update(carriedWeight=finite(r.get('carried_weight'), 56), horseWeight=finite(r.get('horse_weight'), 480),
                         gate=finite(r.get('gate'), 0), fieldSize=len(rows),
                         ageYears=(day-birth).days/365.25 if birth else 4,
                         sexCode={'수': 0, '거': 1, '암': 2}.get(r.get('sex'), 0))
                table.append(f); labels.append(int(r['finish_position'] <= 3)); groups.append(key); dates.append(day.isoformat())
                # Competition ranking: equal odds share a rank; missing odds exclude the entire race from comparison.
                market.append(1 / (1 + sum(o < odds[i] for o in odds)) if complete_odds else math.nan)
        for key, rows in sorted(day_races):
            for r in sorted(rows, key=lambda r: r['horse_id']):
                horses[r['horse_id']].append((day, r['distance'], r['finish_position']))
                for role in ('jockey', 'trainer'):
                    name = r.get(role, '').strip()
                    if name:
                        people[(key.split(':')[0], role, name)].append(int(r['finish_position'] <= 3))
    return table, np.array(labels), np.array(groups), np.array(dates), np.array(market)


def audit(races):
    tracks = {}
    for track in ('1', '2', '3'):
        rows = [r for k, rs in races.items() if k.startswith(track+':') for r in rs]
        days = sorted({r['race_date'].isoformat() for r in rows})
        tracks[track] = {'races': len({r['race_id'] for r in rows}), 'rows': len(rows), 'days': len(days),
                         'firstDate': days[0] if days else None, 'lastDate': days[-1] if days else None,
                         'missing': {col: sum(not r.get(col, '').strip() for r in rows)
                                     for col in ('jockey', 'trainer', 'horse_weight', 'carried_weight', 'gate', 'birth_date', 'win_odds')}}
    return {'status': 'retrospective_only', 'preRaceAvailabilityVerified': False,
            'target': 'finish_position <= 3', 'featureSets': SETS, 'tracks': tracks,
            'forbiddenInputs': ['finish_position', 'win_odds', 'place_odds', 'rating', 'current_race_time', 'current_sectionals'],
            'featureTiming': {'history': 'strictly earlier dates', 'distance': 'race metadata; no snapshot timestamp',
                             'connections': 'current identities from result CSV; history from earlier dates',
                             'physical': 'result CSV; publication time unknown; fieldSize is retained result count'},
            'limitations': LIMITS}


def ranking(y, scores, groups):
    if not len(y):
        return None
    recalls = []
    for group in np.unique(groups):
        mask = groups == group
        recalls.append(float(y[mask][np.argsort(-scores[mask], kind='stable')[:3]].sum() / y[mask].sum()))
    return {'rocAuc': float(roc_auc_score(y, scores)), 'averagePrecision': float(average_precision_score(y, scores)),
            'top3Recall': float(np.mean(recalls)), 'races': len(recalls)}


def paired_delta(y, scores, baseline, groups):
    differences = []
    for group in np.unique(groups):
        m = groups == group
        truth = y[m]
        differences.append(float((truth[np.argsort(-scores[m], kind='stable')[:3]].sum()
                                  - truth[np.argsort(-baseline[m], kind='stable')[:3]].sum()) / truth.sum()))
    if not differences:
        return None
    rng = np.random.default_rng(42)
    samples = rng.choice(differences, (1000, len(differences)), replace=True).mean(axis=1)
    return {'top3RecallDelta': float(np.mean(differences)), 'pairedRaceBootstrap95': np.quantile(samples, [.025, .975]).tolist(),
            'note': 'Descriptive race bootstrap; no multiple-comparison correction, temporal dependence not modeled.'}


def compare_window(races, start, end, sets, cohorts, train_end=None):
    report = {'start': start, 'endExclusive': end, 'cohorts': {}}
    for name in cohorts:
        tracks = COHORTS[name]
        subset = {k: rs for k, rs in races.items() if k.split(':')[0] in tracks and rs[0]['race_date'].isoformat() < end}
        if any(not any(k.startswith(t+':') for k in subset) for t in tracks):
            report['cohorts'][name] = {'status': 'missing_tracks'}
            continue
        table, y, groups, days, market = features(subset)
        train = days < (train_end or start)
        test = (days >= start) & (days < end)
        counts = {'trainingDays': len(set(days[train])), 'testDays': len(set(days[test])),
                  'trainingRaces': len(set(groups[train])), 'testRaces': len(set(groups[test])),
                  'trainingDaysByTrack': {t: len({d for d, g in zip(days[train], groups[train]) if g.startswith(t+':')}) for t in tracks},
                  'testDaysByTrack': {t: len({d for d, g in zip(days[test], groups[test]) if g.startswith(t+':')}) for t in tracks}}
        if counts['trainingDays'] < 20 or counts['testDays'] < 5 or len(set(y[train])) < 2:
            report['cohorts'][name] = {'status': 'insufficient_dates', **counts}
            continue
        result = {'status': 'evaluated', **counts, 'byTrack': {}}
        scores = {}
        for feature_set in sets:
            x = np.array([[r[c] for c in SETS[feature_set]] for r in table], dtype=float)
            model = RandomForestClassifier(**PARAMS).fit(x[train], y[train])
            scores[feature_set] = model.predict_proba(x)[:, 1]
        for track in tracks:
            mask = test & np.array([g.startswith(track+':') for g in groups])
            paired = mask & np.isfinite(market)
            result['byTrack'][track] = {'races': len(set(groups[mask])), 'marketRaces': len(set(groups[paired])),
                'market': ranking(y[paired], market[paired], groups[paired]), 'variants': {}}
            for feature_set, score in scores.items():
                result['byTrack'][track]['variants'][feature_set] = {
                    'allRaces': ranking(y[mask], score[mask], groups[mask]),
                    'matchedMarket': ranking(y[paired], score[paired], groups[paired]),
                    'deltaAgainstMarket': paired_delta(y[paired], score[paired], market[paired], groups[paired]),
                    'deltaAgainstBase': paired_delta(y[mask], score[mask], scores['base'][mask], groups[mask]) if 'base' in scores else None}
        report['cohorts'][name] = result
    return report


def develop(races, end, windows=3, days=30):
    if not 2 <= windows <= 12 or not 7 <= days <= 180:
        raise ValueError('windows must be 2..12 and test-days 7..180')
    finish = date.fromisoformat(end)
    if finish > today():
        raise ValueError('Development end must exclude today and future dates')
    subset = {k: rs for k, rs in races.items() if rs[0]['race_date'] < finish}
    return {'kind': 'development_ablation', 'audit': audit(subset), 'developmentEndExclusive': end,
            'excludedLaterRaces': len(races)-len(subset), 'modelParameters': PARAMS,
            'windows': [compare_window(subset, (finish-timedelta(days=(windows-i)*days)).isoformat(),
                         (finish-timedelta(days=(windows-i-1)*days)).isoformat(), list(SETS), list(COHORTS)) for i in range(windows)],
            'selection': 'No automatic winner; these windows are development data, not untouched final validation.', 'promoted': False}


def training_digest(races, end, cohort):
    return digest({k: rs for k, rs in races.items() if k.split(':')[0] in COHORTS[cohort] and rs[0]['race_date'].isoformat() < end})


def freeze(races, train_end, start, end, cohort, feature_set):
    training_end, first, last = map(date.fromisoformat, (train_end, start, end))
    if not training_end <= today() < first < last or training_end > first:
        raise ValueError('Freeze before a future final start; training end must be <= today and <= final start')
    eligible = {k: rs for k, rs in races.items() if k.split(':')[0] in COHORTS[cohort] and rs[0]['race_date'] < training_end}
    if any(not any(k.startswith(t+':') for k in eligible) for t in COHORTS[cohort]):
        raise ValueError('Missing training track')
    if len({rs[0]['race_date'] for rs in eligible.values()}) < 20:
        raise ValueError('Need at least 20 training dates before freeze')
    if any(rs[0]['race_date'] >= first for rs in races.values()):
        raise ValueError('Final-period rows already present; choose a genuinely unseen future period')
    plan = {'kind': 'frozen_final_plan', 'createdDateKST': today().isoformat(), 'trainingEndExclusive': train_end,
            'start': start, 'endExclusive': end, 'cohort': cohort, 'featureSet': feature_set,
            'features': SETS[feature_set], 'parameters': PARAMS, 'trainingDigest': training_digest(races, train_end, cohort),
            'codeHash': code_hash(), 'sklearnVersion': sklearn.__version__, 'numpyVersion': np.__version__,
            'historyPolicy': 'update from strictly earlier dates, including gap/test dates; model weights frozen',
            'primaryMetric': 'paired top3 recall delta against market; AUC/AP secondary',
            'limitations': LIMITS, 'promoted': False}
    plan['planDigest'] = digest(plan)
    return plan


def final(races, plan):
    if plan.get('kind') != 'frozen_final_plan' or plan.get('planDigest') != digest({k: v for k, v in plan.items() if k != 'planDigest'}):
        raise ValueError('Frozen plan changed or invalid')
    if plan['codeHash'] != code_hash() or plan['sklearnVersion'] != sklearn.__version__ or plan['numpyVersion'] != np.__version__:
        raise ValueError('Code or numerical library version differs from frozen plan')
    if today() < date.fromisoformat(plan['endExclusive']):
        raise ValueError('Final period has not ended; do not inspect interim outcomes')
    if training_digest(races, plan['trainingEndExclusive'], plan['cohort']) != plan['trainingDigest']:
        raise ValueError('Frozen training rows changed or are missing')
    window = compare_window(races, plan['start'], plan['endExclusive'], [plan['featureSet']], [plan['cohort']], plan['trainingEndExclusive'])
    if window['cohorts'][plan['cohort']]['status'] != 'evaluated':
        raise ValueError('Insufficient final-period data; complete collection before final evaluation')
    return {'kind': 'frozen_final_evaluation', 'plan': plan, 'window': window, 'audit': audit(races),
            'coverageVerified': False, 'coverageNote': 'Minimum date count does not verify complete collection; inspect provider collection status.',
            'promoted': False}


def save(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2, allow_nan=False)
        sink.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    for name in ('audit', 'compare', 'freeze', 'final'):
        parser = commands.add_parser(name)
        parser.add_argument('csv', nargs='+', type=Path)
        parser.add_argument('--output', required=True, type=Path)
        if name == 'compare':
            parser.add_argument('--development-end', required=True, help='YYYY-MM-DD, exclusive; never derived from latest CSV date')
            parser.add_argument('--windows', type=int, default=3)
            parser.add_argument('--test-days', type=int, default=30)
        if name == 'freeze':
            parser.add_argument('--training-end', required=True)
            parser.add_argument('--start', required=True); parser.add_argument('--end', required=True)
            parser.add_argument('--cohort', choices=COHORTS, required=True)
            parser.add_argument('--feature-set', choices=SETS, required=True)
        if name == 'final':
            parser.add_argument('--plan', required=True, type=Path)
    a = p.parse_args()
    try:
        if a.output.exists():
            raise ValueError('Output already exists; existing reports/plans are never overwritten')
        races, hashes = read(a.csv)
        if a.command == 'audit': report = audit(races)
        elif a.command == 'compare': report = develop(races, a.development_end, a.windows, a.test_days)
        elif a.command == 'freeze': report = freeze(races, a.training_end, a.start, a.end, a.cohort, a.feature_set)
        else: report = final(races, json.loads(a.plan.read_text(encoding='utf-8')))
        if a.command != 'freeze':
            report['inputHashes'] = hashes
        save(a.output, report)
        for window in report.get('windows', [report['window']] if 'window' in report else []):
            print(window['start'], '~', window['endExclusive'], '(끝 날짜 제외)')
            for name, cohort in window['cohorts'].items():
                print(name, cohort['status'], '학습/검증 날짜', cohort.get('trainingDays'), cohort.get('testDays'))
                for track, result in cohort.get('byTrack', {}).items():
                    print(' 경마장', track, '시장 비교', result['marketRaces'], '경주')
                    for variant, score in result['variants'].items():
                        matched = score['matchedMarket']; market = result['market']
                        print(' ', variant, 'AUC 모델/시장', f"{matched['rocAuc']:.3f}/{market['rocAuc']:.3f}" if matched else '미제공')
                        if matched:
                            delta = score['deltaAgainstMarket']
                            low, high = delta['pairedRaceBootstrap95']
                            print('   top3 recall 모델/시장', f"{matched['top3Recall']:.3f}/{market['top3Recall']:.3f}",
                                  '차이 95% 구간', f'[{low:.3f}, {high:.3f}]')
        print('보고서:', a.output, '/ API 호출·서비스 모델 변경 없음')
        return 0
    except (ValueError, KeyError, OSError) as exc:
        p.exit(1, f'실험 중단: {exc}\n')


if __name__ == '__main__':
    main()
