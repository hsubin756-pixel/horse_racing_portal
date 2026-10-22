from pathlib import Path
from contextlib import asynccontextmanager
import json,joblib
from fastapi import FastAPI
from pydantic import BaseModel,Field
ROOT=Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app):
 # Only load our locally generated trusted artifact, never an uploaded pickle.
 app.state.model=joblib.load(ROOT/'model.joblib')
 app.state.report=json.loads((ROOT/'model-report.json').read_text())
 yield
app=FastAPI(title='Keiba synthetic experiment',version='0.1.0',lifespan=lifespan)
class HorseFeatures(BaseModel):
 horseId:int=Field(gt=0)
 priorMeanFinish:float=Field(ge=1,le=100)
 starts:int=Field(ge=0,le=100000)
 distance:int=Field(ge=400,le=10000)
class PredictRequest(BaseModel):
 horses:list[HorseFeatures]=Field(min_length=1,max_length=100)
@app.get('/health')
def health():return {'status':'ok','modelKind':'synthetic_experiment'}
@app.post('/predict')
def predict(body:PredictRequest):
 x=[[h.priorMeanFinish,h.starts,h.distance] for h in body.horses]
 scores=app.state.model.predict_proba(x)[:,1]
 return {'modelKind':'synthetic_experiment','scores':sorted([{'horseId':h.horseId,'score':float(s)} for h,s in zip(body.horses,scores)],key=lambda x:(-x['score'],x['horseId']))}
