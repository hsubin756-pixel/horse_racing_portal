import unittest,uuid,json
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
  """한국마사회 경주(race.source KRA_*)는 /predict/real 로 가며, 모델이 없으면 준비 안내 503을 받습니다."""
  user={'email':uuid.uuid4().hex+'@example.test','password':'ML-test-password-123','nickname':'실험 회원'}
  request('/auth/register','POST',user);_,auth=request('/auth/login','POST',user);token=auth['token']
  _,races=request('/races?page=0');real=[r for r in races['content'] if r['source'].startswith('KRA_') and r['status']=='OFFICIAL']
  if not real: self.skipTest('실제 경주가 DB에 없음')
  with urlopen('http://127.0.0.1:8000/health') as r: health=json.load(r)
  s,d=request('/races/%d/prediction'%real[0]['id'],'POST',token=token)
  if health.get('realDataModel') is None:
   self.assertEqual(s,503);self.assertIn('실제 데이터 모델이 아직 준비되지 않았습니다',d['message'] if isinstance(d,dict) else str(d));return
  self.assertEqual(s,200);self.assertEqual(d['modelKind'],'real_data_experiment');self.assertIn('시장 정보',d['disclaimer'])
  self.assertEqual(d['info']['cutoffDate'],health['realDataModel']['cutoffDate']);self.assertIn('rocAuc',d['info']['holdoutMetrics'])
  _,detail=request('/races/%d'%real[0]['id']);self.assertEqual(len(d['scores']),len([e for e in detail['entries'] if e['status'] not in ('SCRATCHED','DISQUALIFIED','DNF')]))
  scores=[x['score'] for x in d['scores']];self.assertEqual(scores,sorted(scores,reverse=True));self.assertTrue(all(x['knownStarts'] is not None and x['knownStarts']>=0 for x in d['scores']))
