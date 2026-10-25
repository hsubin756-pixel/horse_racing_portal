"""Train the real-data experiment model from the KRA CSV files in ml/data/ (market-free feature set).

Artifacts: real-model.joblib, real-history.json (per-horse finishes and per-person top-3 records up to the data cutoff),
real-model-report.json (temporal holdout metrics of this feature set plus the market-only baseline). Nothing is promoted
automatically: app.py serves this model only through /predict/real and labels it real_data_experiment.
Run with --if-present to exit quietly when ml/data/ holds no CSV (used by the Docker build).
"""
import argparse, csv, hashlib, json, sys, tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from evaluate_extended import SETS, build, evaluate, load

ROOT = Path(__file__).resolve().parent
FEATURE_SET = 'base+connections+physical'


def history(races):
    horses, people = defaultdict(list), defaultdict(list)
    for race in races.values():
        for r in race:
            day = r['race_date'].isoformat()
            horses[str(r['horse_id'])].append([day, r['finish_position']])
            for kind, key in (('J', r.get('jockey', '')), ('T', r.get('trainer', ''))):
                if key:
                    people[kind + ':' + key].append([day, int(r['finish_position'] <= 3)])
    return {k: sorted(v) for k, v in horses.items()}, {k: sorted(v) for k, v in people.items()}


def evaluate_files(paths, provenance):
    """Temporal holdout of the same feature set; several CSVs (tracks/periods) are merged first so one split covers them all."""
    if len(paths) == 1:
        return evaluate(paths[0], provenance)
    with tempfile.TemporaryDirectory() as folder:
        merged = Path(folder) / 'merged.csv'
        with merged.open('w', newline='', encoding='utf-8') as sink:
            writer = None
            for path in paths:
                with Path(path).open(newline='', encoding='utf-8-sig') as source:
                    reader = csv.DictReader(source)
                    if writer is None:
                        writer = csv.DictWriter(sink, fieldnames=reader.fieldnames); writer.writeheader()
                    elif reader.fieldnames != writer.fieldnames:
                        raise ValueError(f'{path}: CSV columns differ from the first file')
                    writer.writerows(reader)
        return evaluate(str(merged), provenance)


def train(paths, provenance, output=ROOT):
    rows_all, races = [], {}
    for path in paths:
        part = load(path)
        if set(part) & set(races):
            raise ValueError(f'{path}: race ids overlap another file')
        races.update(part)
    table, y, groups, dates, _ = build(races)
    columns = SETS[FEATURE_SET]
    x = np.array([[row[c] for c in columns] for row in table], dtype=float)
    model = RandomForestClassifier(n_estimators=120, max_depth=5, min_samples_leaf=8, random_state=42, n_jobs=1)
    model.fit(x, y)
    holdout = evaluate_files(paths, provenance)
    horses, people = history(races)
    cutoff = str(max(dates))
    report = {'modelKind': 'real_data_experiment', 'features': columns, 'provenanceDeclaredByOperator': provenance, 'rightsVerifiedByTool': False,
              'dataFiles': [{'path': Path(p).name, 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths],
              'trainingRows': int(len(y)), 'trainingRaces': len(races), 'firstDate': str(min(dates)), 'cutoffDate': cutoff, 'seed': 42,
              'holdoutMetrics': holdout['results'][FEATURE_SET]['metrics'] if holdout else None,
              'marketBaselineMetrics': holdout['results']['market_only_rank_by_win_odds']['metrics'] if holdout else None,
              'holdoutStartDate': holdout['holdoutStartDate'] if holdout else None,
              'limitations': 'Experimental model trained on provider open data for the tracks and periods listed in dataFiles; holdout metrics come from a single temporal split '
                             'before retraining on all rows. Histories are frozen at cutoffDate until retrained. No calibration, no profitability claim, '
                             'no market inputs. Scores are not probabilities of placing.'}
    joblib.dump(model, output / 'real-model.joblib')
    (output / 'real-history.json').write_text(json.dumps({'cutoffDate': cutoff, 'horses': horses, 'people': people}, ensure_ascii=False) + '\n')
    (output / 'real-model-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='*', help='CSV files (default: ml/data/*.csv)')
    parser.add_argument('--provenance', default=None)
    parser.add_argument('--if-present', action='store_true')
    args = parser.parse_args()
    files = [Path(p) for p in args.csv] or sorted((ROOT / 'data').glob('*.csv'))
    if not files:
        if args.if_present:
            print('ml/data 에 CSV가 없어 실제 데이터 모델을 만들지 않았습니다 (합성 실험 모델만 제공).')
            sys.exit(0)
        sys.exit('CSV 경로를 지정하거나 ml/data/ 에 두세요.')
    provenance = args.provenance or ((ROOT / 'data' / 'PROVENANCE.md').read_text(encoding='utf-8').strip() if (ROOT / 'data' / 'PROVENANCE.md').exists() else 'provenance not declared')
    result = train([str(f) for f in files], provenance)
    print(json.dumps({k: result[k] for k in ('trainingRaces', 'firstDate', 'cutoffDate', 'holdoutMetrics')}, ensure_ascii=False, indent=2))
