import unittest
from urllib.parse import urlencode
from test_catalog import request
class AnalyticsTests(unittest.TestCase):
 def test_comparison_known_totals_and_empty_horse(self):
  status,data=request('/horses/compare?ids=22,32,1');self.assertEqual(status,200)
  self.assertEqual(data['dataKind'],'synthetic_fixture')
  self.assertEqual([row['horse']['id'] for row in data['horses']],[22,32,1])
  first,second,empty=[row['statistics'] for row in data['horses']]
  self.assertEqual(first['totals']['starts'],7);self.assertEqual(first['totals']['wins'],0)
  self.assertEqual(first['totals']['averageFinish'],6);self.assertEqual(first['totals']['top3'],1)
  self.assertEqual(second['totals']['wins'],1);self.assertAlmostEqual(second['totals']['winRate'],100/7)
  self.assertEqual([e['raceId'] for e in first['recent']],[7,6,5,4,3])
  self.assertEqual([g['totals']['starts'] for g in first['byDistance']],[4,3])
  self.assertEqual(empty['totals']['starts'],0);self.assertIsNone(empty['totals']['winRate']);self.assertEqual(empty['recent'],[])
 def test_horse_and_jockey_filters(self):
  status,data=request('/horses/22/stats?'+urlencode({'distance':1600,'surface':'잔디','from':'2025-03-15','to':'2025-05-15'}))
  self.assertEqual(status,200);stats=data['horses'][0]['statistics']
  self.assertEqual(stats['totals']['starts'],2);self.assertEqual(stats['totals']['averageFinish'],6)
  _,data=request('/jockeys/stats?'+urlencode({'name':'가상 기수 1','distance':2000}))
  self.assertEqual(data['statistics']['totals']['starts'],3);self.assertEqual(data['statistics']['totals']['top3'],0)
  _,names=request('/jockeys?'+urlencode({'q':'가상 기수 1'}));self.assertIn('가상 기수 1',names)
  self.assertEqual(request('/jockeys?'+urlencode({'q':'%'}))[1],[])
 def test_validation_and_unknown_entities(self):
  for path in ('/horses/compare?ids=22,22','/horses/compare?ids=1,2,3,4,5','/horses/compare?ids=0',
   '/horses/compare?ids=hello','/horses/22/stats?distance=0','/horses/22/stats?from=2025-12-01&to=2025-01-01',
   '/horses/22/stats?surface=unknown'):
   self.assertEqual(request(path)[0],400,path)
  self.assertEqual(request('/horses/compare?ids=99999')[0],404)
  self.assertEqual(request('/jockeys/stats?name=not-existing')[0],404)
