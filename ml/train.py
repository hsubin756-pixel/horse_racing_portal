"""Reproducible synthetic-only experiment. Never trained on netkeiba or real results."""
from pathlib import Path
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,roc_auc_score,brier_score_loss
from evaluate import metrics
ROOT=Path(__file__).resolve().parent
FEATURES=['priorMeanFinish','starts','distance']
def dataset(seed=42):
 rng=np.random.default_rng(seed)
 # Independent fictional cohort, 24 horses x 100 sequential races, before catalog dates.
 skills=rng.normal(size=24);history=[[] for _ in skills];rows=[];labels=[];rounds=[]
 for race in range(100):
  distance=int(rng.choice([1600,1800,2000]))
  performance=skills+rng.normal(0,1.8,24)
  ranks=np.argsort(np.argsort(-performance))+1
  for h in range(24):
   # Features use only earlier races; current race's finish is never an input.
   rows.append([float(np.mean(history[h])) if history[h] else 12.5,len(history[h]),distance])
   labels.append(int(ranks[h]<=3));rounds.append(race)
  for h in range(24): history[h].append(int(ranks[h]))
 return np.array(rows),np.array(labels),np.array(rounds)
def train():
 x,y,rounds=dataset();train_mask=rounds<80
 model=RandomForestClassifier(n_estimators=120,max_depth=5,min_samples_leaf=8,random_state=42,n_jobs=1)
 model.fit(x[train_mask],y[train_mask]);score=model.predict_proba(x[~train_mask])[:,1]
 report={'modelKind':'synthetic_experiment','seed':42,'features':FEATURES,'trainingRows':int(train_mask.sum()),'testRows':int((~train_mask).sum()),'split':'temporal: first 80 races train, last 20 test; independent fictional cohort',
 'accuracy':float(accuracy_score(y[~train_mask],score>=.5)),'majorityBaselineAccuracy':float((y[~train_mask]==0).mean()),'rocAuc':float(roc_auc_score(y[~train_mask],score)),'brierScore':float(brier_score_loss(y[~train_mask],score)),
 'rankingAndBaselineMetrics':metrics(y[~train_mask],score,rounds[~train_mask],float(y[train_mask].mean())),
 'limitations':'SYNTHETIC ONLY. No real-world predictive ability evaluated. Scores are uncalibrated model outputs, not guaranteed probabilities. Catalog cohort differs from training population.'}
 joblib.dump(model,ROOT/'model.joblib');(ROOT/'model-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False))
 return model,report
if __name__=='__main__':train()
