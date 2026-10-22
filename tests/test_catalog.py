"""Black-box tests against running Spring + real MySQL, no mock API."""
import json, os, unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE=os.environ.get('TEST_BASE_URL','http://127.0.0.1:8080/api')
def request(path, method='GET', body=None, token=None):
 headers={'Content-Type':'application/json'}
 if token: headers['Authorization']='Bearer '+token
 req=Request(BASE+path,data=None if body is None else json.dumps(body).encode(),method=method,headers=headers)
 try:
  with urlopen(req,timeout=8) as r: return r.status,json.loads(r.read() or b'null')
 except HTTPError as r: return r.code,json.loads(r.read() or b'null')
class CatalogTests(unittest.TestCase):
 def test_pagination_search_sort(self):
  s,p=request('/horses'); self.assertEqual(s,200);self.assertEqual(p['totalElements'],40);self.assertEqual(len(p['content']),20)
  _,p2=request('/horses?page=1');self.assertFalse({h['id'] for h in p['content']}&{h['id'] for h in p2['content']})
  _,p=request('/horses?q=%EC%82%AC%EC%BF%A0%EB%9D%BC');self.assertEqual(p['totalElements'],1)
  _,p=request('/horses?q=not-existing');self.assertEqual(p['content'],[])
  _,p=request('/horses?sort=birthDate&direction=desc');self.assertEqual(p['content'][0]['birthDate'][:4],'2021')
  self.assertEqual(request('/horses?page=-1')[0],400);self.assertEqual(request('/horses?sort=password')[0],400)
 def test_details_and_history(self):
  s,h=request('/horses/22');self.assertEqual(s,200);self.assertIsNotNone(h['sire']['id']);self.assertTrue(h['sire']['name']);self.assertTrue(h['trainer'])
  _,hist=request('/horses/22/history');self.assertEqual(len(hist),7);self.assertEqual(hist[0]['raceId'],7)
  dates=[e['raceDate'] for e in hist];self.assertEqual(dates,sorted(dates,reverse=True));self.assertIsNotNone(hist[-1]['timeSeconds'])
  self.assertEqual(request('/horses/9999')[0],404)
 def test_literal_wildcards_and_invalid_queries(self):
  for resource in ('horses','races'):
   for query in ('%25','_','%27%20OR%201%3D1'):
    status,data=request('/'+resource+'?q='+query)
    self.assertEqual(status,200);self.assertEqual(data['totalElements'],0)
  self.assertEqual(request('/horses?q='+'a'*101)[0],400)
  self.assertEqual(request('/races?page=-1')[0],400)
 def test_races(self):
  _,p=request('/races?date=2025-01-15');self.assertEqual(p['totalElements'],1)
  _,p=request('/races?q=not-existing');self.assertEqual(p['totalElements'],0)
  s,r=request('/races/1');self.assertEqual(s,200);self.assertEqual(len(r['entries']),12)
  self.assertEqual(sorted(e['finishPosition'] for e in r['entries']),list(range(1,13)))
  self.assertEqual(request('/races?date=wrong')[0],400)
if __name__=='__main__': unittest.main(verbosity=2)
