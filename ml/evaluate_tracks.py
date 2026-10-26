"""Market-free track comparison with one shared chronological cutoff; never replaces the service model."""
import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from evaluate_extended import load, build, SETS
from evaluate import metrics

COHORTS = {'seoul': ('1',), 'seoul_busan': ('1','3'), 'jeju': ('2',)}


def merge(paths):
    races = {}
    for path in paths:
        for key, rows in load(path).items():
            if key.split(':')[0] not in ('1','2','3'):
                raise ValueError('race_id must start with KRA meet code 1/2/3')
            if key in races and races[key] != rows:
                raise ValueError('Overlapping race has different contents: '+key)
            races[key] = rows
    return races


def compare(paths, cutoff=None):
    races = merge(paths)
    days = sorted({r[0]['race_date'].isoformat() for r in races.values()})
    if len(days) < 30:
        raise ValueError('At least 30 distinct dates required')
    cutoff = cutoff or days[int(len(days)*.8)]
    date.fromisoformat(cutoff)
    result = {'cutoff':cutoff,'dataFiles':[{'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths],
              'cohorts':{},'promoted':False,'limitations':['Single temporal split; scores are not calibrated probabilities.',
              'Compare seoul and seoul_busan on the Seoul test subset with the same cutoff.',
              'Jockey/trainer identities use names; cross-track names may be ambiguous.',
              'Jeju is evaluated separately; no automatic service model replacement.']}
    for name, tracks in COHORTS.items():
        subset = {k:v for k,v in races.items() if k.split(':')[0] in tracks}
        missing = [t for t in tracks if not any(k.startswith(t+':') for k in subset)]
        if missing:
            result['cohorts'][name] = {'status':'missing_tracks','missing':missing}; continue
        table,y,groups,dates,market = build(subset)
        train,test = dates<cutoff,dates>=cutoff
        if len(set(dates[train]))<20 or len(set(dates[test]))<5 or len(set(y[train]))<2:
            result['cohorts'][name] = {'status':'insufficient_dates','trainingDays':len(set(dates[train])),'testDays':len(set(dates[test]))}; continue
        x=np.array([[row[c] for c in SETS['base+connections+physical']] for row in table])
        model=RandomForestClassifier(n_estimators=120,max_depth=5,min_samples_leaf=8,random_state=42,n_jobs=1)
        model.fit(x[train],y[train]); scores=model.predict_proba(x)[:,1]
        track_metrics={}
        for track in tracks:
            mask=test & np.array([g.startswith(track+':') for g in groups])
            if not mask.any(): continue
            market_races = set()
            for key, race in subset.items():
                try:
                    odds = [float(r.get('win_odds','')) for r in race]
                    if all(math.isfinite(o) and o >= 1 for o in odds): market_races.add(key)
                except (TypeError, ValueError):
                    pass
            market_mask = mask & np.array([g in market_races for g in groups])
            track_metrics[track]={'races':len(set(groups[mask])), 'rows':int(mask.sum()),
                'model':metrics(y[mask],scores[mask],groups[mask],float(y[train].mean())),
                'marketRaces':len(set(groups[market_mask])),
                'market':metrics(y[market_mask],1/market[market_mask],groups[market_mask],float(y[train].mean())) if market_mask.any() else None,
                'modelOnMarketSubset':metrics(y[market_mask],scores[market_mask],groups[market_mask],float(y[train].mean())) if market_mask.any() else None}
        result['cohorts'][name]={'status':'evaluated','trainingRaces':len(set(groups[train])),
                                'testRaces':len(set(groups[test])),'byTrack':track_metrics}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv',nargs='+');p.add_argument('--cutoff');p.add_argument('--output',default='.runtime/kra/track-evaluation.json')
    a=p.parse_args()
    try:
        result=compare(a.csv,a.cutoff)
        path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        for name,c in result['cohorts'].items():
            print(name, c['status'])
            for track,m in c.get('byTrack',{}).items():
                baseline = f"{m['market']['rocAuc']:.3f}" if m['market'] else '자료 없음'
                print(f"  경마장 {track}: {m['races']}경주 / AUC {m['model']['rocAuc']:.3f} / top3 recall {m['model']['top3Recall']:.3f} / 시장 {baseline} ({m['marketRaces']}경주)")
        print('보고서:',path,'/ 서비스 모델 교체 없음')
        return 0
    except (ValueError,OSError,KeyError) as exc:
        print('평가 실패:',str(exc));return 1

if __name__=='__main__': raise SystemExit(main())
