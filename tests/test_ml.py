import unittest,uuid,json,subprocess,sys
from pathlib import Path
from urllib.request import urlopen,Request
from test_catalog import request
class PredictionTests(unittest.TestCase):
 def test_authenticated_sorted_synthetic_scores(self):
  user={'email':uuid.uuid4().hex+'@example.test','password':'ML-test-password-123','nickname':'실험 회원'}
  self.assertEqual(request('/auth/register','POST',user)[0],201)
  _,auth=request('/auth/login','POST',user);token=auth['token']
  s,d=request('/races/8/prediction','POST',token=token);self.assertEqual(s,200)
  self.assertEqual(d['modelKind'],'synthetic_experiment');self.assertIn('합성',d['disclaimer']);self.assertEqual(len(d['scores']),12)
  scores=[s['score'] for s in d['scores']];self.assertEqual(scores,sorted(scores,reverse=True));self.assertTrue(all(0<=x<=1 for x in scores))
  self.assertEqual({s['horseId'] for s in d['scores']},set(range(22,34)))
  self.assertEqual(request('/races/99999/prediction','POST',token=token)[0],404)
  # Independently reconstruct historical inputs and compare FastAPI output.
  _,hist=request('/horses/22/history');past=[e['finishPosition'] for e in hist if e['raceDate']<'2026-11-01' and e['finishPosition'] is not None]
  body={'horses':[{'horseId':22,'priorMeanFinish':sum(past)/len(past),'starts':len(past),'distance':2000}]}
  with urlopen(Request('http://127.0.0.1:8000/predict',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})) as r: direct=json.load(r)
  self.assertAlmostEqual(next(x['score'] for x in d['scores'] if x['horseId']==22),direct['scores'][0]['score'])
 def test_real_race_uses_real_data_model_when_available(self):
  """한국마사회 경주(race.source KRA_*)는 /predict/real 로 가며, 모델이 없으면 준비 안내 503을 받습니다.
  DB에 실제 경주가 없으면(가상 샘플만 있는 개발·CI DB) 임시 KRA 형식 경주를 만들어 같은 경로를 검사하고 지웁니다."""
  user={'email':uuid.uuid4().hex+'@example.test','password':'ML-test-password-123','nickname':'실험 회원'}
  request('/auth/register','POST',user);_,auth=request('/auth/login','POST',user);token=auth['token']
  real=[]
  for page in range(10):
   s,races=request('/races?page=%d'%page);real+=[r for r in races.get('content',[]) if r['source'].startswith('KRA_') and r['status']=='OFFICIAL']
   if real or s!=200 or page+1>=races.get('totalPages',0): break
  if real:
   self.check_real_prediction(real[0]['id'],token);return
  fixture=Path(__file__).resolve().parent/'kra_browser_fixture.py'
  created=subprocess.run([sys.executable,str(fixture),'create'],capture_output=True,text=True)
  self.assertEqual(created.returncode,0,'임시 KRA 경주 생성 실패: '+created.stderr+created.stdout)
  race_id=json.loads(created.stdout)['raceId']
  try:
   self.check_real_prediction(race_id,token)
  finally:
   cleaned=subprocess.run([sys.executable,str(fixture),'clean',str(race_id)],capture_output=True,text=True)
   self.assertEqual(cleaned.returncode,0,'임시 KRA 경주 정리 실패: '+cleaned.stderr+cleaned.stdout)
 def check_real_prediction(self,race_id,token):
  with urlopen('http://127.0.0.1:8000/health') as r: health=json.load(r)
  s,d=request('/races/%d/prediction'%race_id,'POST',token=token)
  if health.get('realDataModel') is None:
   self.assertEqual(s,503);self.assertIn('실제 데이터 모델이 아직 준비되지 않았습니다',d['message'] if isinstance(d,dict) else str(d));return
  self.assertEqual(s,200);self.assertEqual(d['modelKind'],'real_data_experiment');self.assertIn('시장 정보',d['disclaimer'])
  self.assertEqual(d['info']['cutoffDate'],health['realDataModel']['cutoffDate']);self.assertIn('rocAuc',d['info']['holdoutMetrics'])
  _,detail=request('/races/%d'%race_id);self.assertEqual(len(d['scores']),len([e for e in detail['entries'] if e['status'] not in ('SCRATCHED','DISQUALIFIED','DNF','VOID')]))
  scores=[x['score'] for x in d['scores']];self.assertEqual(scores,sorted(scores,reverse=True));self.assertTrue(all(x['knownStarts'] is not None and x['knownStarts']>=0 for x in d['scores']))
