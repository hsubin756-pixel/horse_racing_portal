"""Offline evaluation of owner-supplied CSV. Never downloads data or promotes a model.
CSV: race_id,race_date,horse_id,distance,finish_position (one complete result per starter).
Only completed races with unique ranks 1..field size are accepted. Excludes ties/withdrawals.
"""
import argparse,csv,hashlib,json
from collections import defaultdict
from datetime import date
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,average_precision_score,brier_score_loss,roc_auc_score

def features(rows):
 races=defaultdict(list);horse_races=set()
 for row in rows:
  row=dict(row)
  row['race_date']=date.fromisoformat(row['race_date'])
  for key in ('horse_id','distance','finish_position'): row[key]=int(row[key])
  if not row['race_id'] or row['horse_id']<=0 or not 400<=row['distance']<=10000: raise ValueError('Invalid identifier or distance')
  pair=(row['race_id'],row['horse_id'])
  if pair in horse_races: raise ValueError('Duplicate starter')
  horse_races.add(pair);races[row['race_id']].append(row)
 for race in races.values():
  if len({(r['race_date'],r['distance']) for r in race})!=1: raise ValueError('Inconsistent race metadata')
  if not 4<=len(race)<=100 or sorted(r['finish_position'] for r in race)!=list(range(1,len(race)+1)):
   raise ValueError('Require complete races of 4..100 starters with unique ranks 1..N')
 by_date=defaultdict(list)
 for race in races.values(): by_date[race[0]['race_date']].extend(race)
 history=defaultdict(list);x=[];y=[];groups=[];dates=[]
 for day,starters in sorted(by_date.items()):
  # Update only after the whole date, matching the backend strict raceDate < targetDate.
  for row in sorted(starters,key=lambda r:(r['race_id'],r['horse_id'])):
   past=history[row['horse_id']]
   x.append([float(np.mean(past)) if past else 12.5,len(past),row['distance']])
   y.append(int(row['finish_position']<=3));groups.append(row['race_id']);dates.append(day.isoformat())
  for row in starters: history[row['horse_id']].append(row['finish_position'])
 return np.array(x),np.array(y),np.array(groups),np.array(dates)

def metrics(y,scores,groups,baseline):
 recalls=[]
 for race in np.unique(groups):
  mask=groups==race;truth=y[mask];ranked=np.argsort(-scores[mask],kind='stable')[:3]
  recalls.append(float(truth[ranked].sum()/truth.sum()))
 # Race-level bootstrap keeps correlated starters together. Descriptive, not a guarantee.
 rng=np.random.default_rng(42)
 means=[float(np.mean(rng.choice(recalls,len(recalls),replace=True))) for _ in range(500)]
 return {'accuracy':float(accuracy_score(y,scores>=.5)),
  'rocAuc':float(roc_auc_score(y,scores)),'averagePrecision':float(average_precision_score(y,scores)),
  'brierScore':float(brier_score_loss(y,scores)),
  'trainingPrevalenceBaselineBrier':float(brier_score_loss(y,np.full(len(y),baseline))),
  'testPositiveRate':float(y.mean()),'majorityBaselineAccuracy':float(max(y.mean(),1-y.mean())),
  'top3Recall':float(np.mean(recalls)), 'top3RecallBootstrap95':np.quantile(means,[.025,.975]).tolist()}

def evaluate(path,provenance):
 data=Path(path).read_bytes()
 with Path(path).open(newline='',encoding='utf-8-sig') as source: rows=list(csv.DictReader(source))
 x,y,groups,dates=features(rows);days=np.unique(dates)
 if len(days)<30: raise ValueError('At least 30 distinct completed race dates required')
 cutoff=days[int(len(days)*.8)];train=dates<cutoff;test=~train
 model=RandomForestClassifier(n_estimators=120,max_depth=5,min_samples_leaf=8,random_state=42,n_jobs=1)
 model.fit(x[train],y[train]);scores=model.predict_proba(x[test])[:,1]
 return {'modelKind':'offline_user_dataset_experiment','dataSha256':hashlib.sha256(data).hexdigest(),
  'provenanceDeclaredByOperator':provenance,'rightsVerifiedByTool':False,'seed':42,
  'trainingRows':int(train.sum()),'testRows':int(test.sum()),'trainingRaces':len(np.unique(groups[train])),
  'testRaces':len(np.unique(groups[test])),'holdoutStartDate':str(cutoff),
  'split':'First 80% of distinct dates train, remaining dates holdout; same-day results excluded from features',
  'metrics':metrics(y[test],scores,groups[test],float(y[train].mean())),
  'limitations':'Offline fixed-model evaluation only. No tuning on holdout, calibration, external validation, profitability claim or automatic production promotion. Cold-start mean 12.5 matches current API; field-size shift remains possible.'}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('csv');parser.add_argument('--provenance',required=True)
 parser.add_argument('--output',required=True);args=parser.parse_args()
 report=evaluate(args.csv,args.provenance)
 Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
