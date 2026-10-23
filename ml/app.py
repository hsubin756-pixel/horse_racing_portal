from pathlib import Path
from contextlib import asynccontextmanager
import json,joblib
from fastapi import FastAPI
from pydantic import BaseModel,Field,model_validator
from datetime import date
import math
from fastapi import HTTPException
from evaluate_extended import SETS, SEX, PRIOR_TOP3
ROOT=Path(__file__).resolve().parent
REAL_FILES=('real-model.joblib','real-history.json','real-model-report.json')
def load_real(root):
 # Optional real-data experiment artifacts produced by train_real.py from ml/data/; absent means synthetic only.
 if not all((root/name).exists() for name in REAL_FILES): return None
 history=json.loads((root/'real-history.json').read_text(encoding='utf-8'))
 return {'model':joblib.load(root/'real-model.joblib'),'history':history,'report':json.loads((root/'real-model-report.json').read_text(encoding='utf-8'))}
@asynccontextmanager
async def lifespan(app):
 # Only load our locally generated trusted artifacts, never an uploaded pickle.
 app.state.model=joblib.load(ROOT/'model.joblib')
 app.state.report=json.loads((ROOT/'model-report.json').read_text())
 app.state.real=load_real(ROOT)
 yield
app=FastAPI(title='Keiba prediction experiments',version='0.2.0',lifespan=lifespan)
class HorseFeatures(BaseModel):
 horseId:int=Field(gt=0)
 priorMeanFinish:float=Field(ge=1,le=100)
 starts:int=Field(ge=0,le=100000)
 distance:int=Field(ge=400,le=10000)
class PredictRequest(BaseModel):
 horses:list[HorseFeatures]=Field(min_length=1,max_length=100)
 @model_validator(mode='after')
 def unique_horses(self):
  if len({h.horseId for h in self.horses})!=len(self.horses):
   raise ValueError('horseId must be unique within a race')
  return self
@app.get('/health')
def health():
 real=app.state.real
 return {'status':'ok','modelKind':'synthetic_experiment','realDataModel':None if real is None else {'modelKind':'real_data_experiment','cutoffDate':real['history']['cutoffDate']}}
class RealHorse(BaseModel):
 horseId:int=Field(gt=0)
 kraId:str=Field(pattern=r'^\d{1,16}$')
 carriedWeight:float|None=Field(default=None,ge=30,le=80)
 bodyWeight:int|None=Field(default=None,ge=200,le=800)
 gate:int|None=Field(default=None,ge=1,le=30)
 birthDate:date|None=None
 sex:str|None=Field(default=None,max_length=8)
 jockey:str|None=Field(default=None,max_length=100)
 trainer:str|None=Field(default=None,max_length=100)
class RealRequest(BaseModel):
 raceDate:date
 distance:int=Field(ge=400,le=10000)
 horses:list[RealHorse]=Field(min_length=1,max_length=100)
 @model_validator(mode='after')
 def unique_horses(self):
  if len({h.horseId for h in self.horses})!=len(self.horses): raise ValueError('horseId must be unique within a race')
  return self
def before(records,day):
 return [value for stamp,value in records if stamp<day]
def real_features(real,body):
 day=body.raceDate.isoformat();history=real['history'];rows=[];known=[]
 for h in body.horses:
  past=before(history['horses'].get(str(int(h.kraId)),[]),day)
  jk=before(history['people'].get('J:'+(h.jockey or ''),[]),day);tr=before(history['people'].get('T:'+(h.trainer or ''),[]),day)
  age=(body.raceDate-h.birthDate).days/365.25 if h.birthDate else 4.0
  feature={'priorMeanFinish':float(sum(past)/len(past)) if past else 12.5,'starts':len(past),'distance':body.distance,
   'jockeyTop3Rate':(sum(jk)+3*PRIOR_TOP3)/(len(jk)+3),'jockeyStarts':len(jk),'trainerTop3Rate':(sum(tr)+3*PRIOR_TOP3)/(len(tr)+3),'trainerStarts':len(tr),
   'carriedWeight':h.carriedWeight if h.carriedWeight is not None else 56.0,'horseWeight':float(h.bodyWeight) if h.bodyWeight is not None else 480.0,
   'gate':float(h.gate) if h.gate is not None else 0.0,'fieldSize':len(body.horses),'ageYears':age,'sexCode':SEX.get(h.sex or '',0.0)}
  rows.append([feature[c] for c in real['report']['features']]);known.append(len(past))
 return rows,known
@app.post('/predict/real')
def predict_real(body:RealRequest):
 real=app.state.real
 if real is None: raise HTTPException(status_code=503,detail='real data model not available')
 x,known=real_features(real,body)
 scores=real['model'].predict_proba(x)[:,1]
 report=real['report']
 return {'modelKind':'real_data_experiment','cutoffDate':real['history']['cutoffDate'],'firstDate':report.get('firstDate'),'trainingRaces':report.get('trainingRaces'),
  'holdoutMetrics':report.get('holdoutMetrics'),'marketBaselineMetrics':report.get('marketBaselineMetrics'),
  'scores':sorted([{'horseId':h.horseId,'score':float(s),'knownStarts':k} for h,s,k in zip(body.horses,scores,known)],key=lambda r:(-r['score'],r['horseId']))}
@app.post('/predict')
def predict(body:PredictRequest):
 x=[[h.priorMeanFinish,h.starts,h.distance] for h in body.horses]
 scores=app.state.model.predict_proba(x)[:,1]
 return {'modelKind':'synthetic_experiment','scores':sorted([{'horseId':h.horseId,'score':float(s)} for h,s in zip(body.horses,scores)],key=lambda x:(-x['score'],x['horseId']))}
