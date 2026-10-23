"""Offline comparison of feature sets on the extended KRA CSV (scripts/kra_ml_dataset.py export).
Same temporal split and fixed RandomForest as evaluate.py; adds connection, physical and market inputs step by step,
plus a no-model market baseline (rank by lowest win odds). Never promotes a model or downloads data.
"""
import argparse, csv, hashlib, json, math
from collections import defaultdict
from datetime import date
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from evaluate import metrics

PRIOR_TOP3 = 0.28   # smoothing prior for jockey/trainer rates before any history (≈ 3 / average field of ~10.6)
SETS = {
 'base': ['priorMeanFinish', 'starts', 'distance'],
 'base+connections': ['priorMeanFinish', 'starts', 'distance', 'jockeyTop3Rate', 'jockeyStarts', 'trainerTop3Rate', 'trainerStarts'],
 'base+connections+physical': ['priorMeanFinish', 'starts', 'distance', 'jockeyTop3Rate', 'jockeyStarts', 'trainerTop3Rate', 'trainerStarts',
                               'carriedWeight', 'horseWeight', 'gate', 'fieldSize', 'ageYears', 'sexCode'],
 'all+market': ['priorMeanFinish', 'starts', 'distance', 'jockeyTop3Rate', 'jockeyStarts', 'trainerTop3Rate', 'trainerStarts',
                'carriedWeight', 'horseWeight', 'gate', 'fieldSize', 'ageYears', 'sexCode', 'logWinOdds', 'oddsRankInRace'],
}
SEX = {'수': 0.0, '거': 1.0, '암': 2.0}


def number(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as source:
        rows = list(csv.DictReader(source))
    races = defaultdict(list)
    for row in rows:
        row['race_date'] = date.fromisoformat(row['race_date'])
        row['horse_id'] = int(row['horse_id']); row['distance'] = int(row['distance']); row['finish_position'] = int(row['finish_position'])
        races[row['race_id']].append(row)
    for race in races.values():
        if sorted(r['finish_position'] for r in race) != list(range(1, len(race) + 1)) or not 4 <= len(race) <= 100:
            raise ValueError('Require complete races of 4..100 starters with unique ranks 1..N')
    return races


def build(races):
    """Temporal features: every input uses only results from earlier dates (same-day results excluded)."""
    by_date = defaultdict(list)
    for race in races.values():
        by_date[race[0]['race_date']].append(race)
    horse_hist, person_hist = defaultdict(list), defaultdict(lambda: [0, 0])
    table, y, groups, dates, market_rank = [], [], [], [], []
    for day, day_races in sorted(by_date.items()):
        for race in sorted(day_races, key=lambda r: r[0]['race_id']):
            odds = [number(r.get('win_odds'), math.nan) for r in race]
            order = sorted(range(len(race)), key=lambda i: (math.isnan(odds[i]), odds[i]))
            rank_by_odds = {i: k + 1 for k, i in enumerate(order)}
            for i, r in enumerate(race):
                past = horse_hist[r['horse_id']]
                jk, tr = person_hist[('J', r.get('jockey', ''))], person_hist[('T', r.get('trainer', ''))]
                age = (day - date.fromisoformat(r['birth_date'])).days / 365.25 if r.get('birth_date') else 4.0
                table.append({'priorMeanFinish': float(np.mean(past)) if past else 12.5, 'starts': len(past), 'distance': r['distance'],
                              'jockeyTop3Rate': (jk[0] + 3 * PRIOR_TOP3) / (jk[1] + 3), 'jockeyStarts': jk[1],
                              'trainerTop3Rate': (tr[0] + 3 * PRIOR_TOP3) / (tr[1] + 3), 'trainerStarts': tr[1],
                              'carriedWeight': number(r.get('carried_weight'), 56.0), 'horseWeight': number(r.get('horse_weight'), 480.0),
                              'gate': number(r.get('gate'), 0.0), 'fieldSize': len(race), 'ageYears': age, 'sexCode': SEX.get(r.get('sex', ''), 0.0),
                              'logWinOdds': math.log(odds[i]) if not math.isnan(odds[i]) else math.log(20.0),
                              'oddsRankInRace': rank_by_odds[i] if not math.isnan(odds[i]) else len(race)})
                y.append(int(r['finish_position'] <= 3)); groups.append(r['race_id']); dates.append(day.isoformat())
                market_rank.append(rank_by_odds[i] if not math.isnan(odds[i]) else len(race) + 1)
        for race in day_races:
            for r in race:
                horse_hist[r['horse_id']].append(r['finish_position'])
                for key in (('J', r.get('jockey', '')), ('T', r.get('trainer', ''))):
                    person_hist[key][0] += r['finish_position'] <= 3; person_hist[key][1] += 1
    return table, np.array(y), np.array(groups), np.array(dates), np.array(market_rank, dtype=float)


def evaluate(path, provenance):
    data = Path(path).read_bytes()
    table, y, groups, dates, market_rank = build(load(path))
    days = np.unique(dates)
    if len(days) < 30:
        raise ValueError('At least 30 distinct completed race dates required')
    cutoff = days[int(len(days) * .8)]; train = dates < cutoff; test = ~train
    results = {}
    for name, columns in SETS.items():
        x = np.array([[row[c] for c in columns] for row in table], dtype=float)
        model = RandomForestClassifier(n_estimators=120, max_depth=5, min_samples_leaf=8, random_state=42, n_jobs=1)
        model.fit(x[train], y[train])
        results[name] = {'features': columns, 'metrics': metrics(y[test], model.predict_proba(x[test])[:, 1], groups[test], float(y[train].mean())),
                         'featureImportances': {c: round(float(v), 4) for c, v in zip(columns, model.feature_importances_)}}
    # Market-only ranking (no model): score = -odds rank, so the favourite is ranked first.
    results['market_only_rank_by_win_odds'] = {'features': ['win_odds'], 'metrics': metrics(y[test], 1.0 / market_rank[test], groups[test], float(y[train].mean())),
                                               'note': 'Scores are 1/odds-rank, not probabilities: AUC, AP and top-3 recall are meaningful; accuracy and Brier are not.'}
    return {'modelKind': 'offline_user_dataset_feature_comparison', 'dataSha256': hashlib.sha256(data).hexdigest(),
            'provenanceDeclaredByOperator': provenance, 'rightsVerifiedByTool': False, 'seed': 42,
            'trainingRows': int(train.sum()), 'testRows': int(test.sum()), 'trainingRaces': len(np.unique(groups[train])), 'testRaces': len(np.unique(groups[test])),
            'holdoutStartDate': str(cutoff), 'split': 'First 80% of distinct dates train, remaining dates holdout; same-day results excluded from features',
            'results': results,
            'limitations': 'Fixed model per feature set, no tuning on holdout, no calibration. Jockey/trainer rates use names from the provider dataset. Market inputs are post-close odds and must not be presented as a prediction independent of the betting market.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv'); parser.add_argument('--provenance', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = evaluate(args.csv, args.provenance)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    summary = {k: {m: round(v['metrics'][m], 3) for m in ('rocAuc', 'averagePrecision', 'top3Recall')} for k, v in report['results'].items()}
    print(json.dumps({'holdoutStartDate': report['holdoutStartDate'], 'testRaces': report['testRaces'], 'summary': summary}, ensure_ascii=False, indent=2))
