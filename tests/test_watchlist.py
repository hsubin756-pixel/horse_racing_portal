import unittest,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from test_catalog import request
class WatchlistTests(unittest.TestCase):
 def user(self):
  body={'email':'watch-'+uuid.uuid4().hex+'@example.test','password':'Watch-test-123456','nickname':'일정 회원'}
  self.assertEqual(request('/auth/register','POST',body)[0],201)
  return request('/auth/login','POST',body)[1]['token']
 def test_private_save_delete_and_schedule_merge(self):
  a,b=self.user(),self.user()
  self.assertEqual(request('/race-favorites')[0],401);self.assertEqual(request('/my-schedule')[0],401)
  self.assertEqual(request('/race-favorites/8','POST')[0],401)
  self.assertEqual(request('/race-favorites/8','POST',token=a)[0],201)
  self.assertEqual(request('/race-favorites/8','POST',token=a)[0],409)
  self.assertEqual(request('/race-favorites/99999','POST',token=a)[0],404)
  self.assertEqual(request('/race-favorites',token=b)[1],[])
  self.assertEqual(request('/race-favorites/8','DELETE',token=b)[0],204)
  self.assertEqual([r['id'] for r in request('/race-favorites',token=a)[1]],[8])
  self.assertEqual(request('/favorites/22','POST',token=a)[0],201)
  self.assertEqual(request('/race-favorites/1','POST',token=a)[0],201)
  _,schedule=request('/my-schedule',token=a)
  # Fixture date is fixed; API correctness remains testable after the sample expires.
  active=schedule['asOfDate']<='2026-11-01'<=schedule['through']
  self.assertEqual([r['race']['id'] for r in schedule['races']],[8] if active else [])
  if active:
   self.assertTrue(schedule['races'][0]['savedRace']);self.assertEqual([h['id'] for h in schedule['races'][0]['favoriteHorses']],[22])
  self.assertEqual(request('/my-schedule',token=b)[1]['races'],[])
  self.assertEqual(request('/race-favorites/8','DELETE',token=a)[0],204)
  _,schedule=request('/my-schedule',token=a)
  if active:self.assertFalse(schedule['races'][0]['savedRace'])
  self.assertEqual(request('/favorites/22','DELETE',token=a)[0],204)
  self.assertEqual(request('/my-schedule',token=a)[1]['races'],[])
  self.assertEqual([r['id'] for r in request('/race-favorites',token=a)[1]],[1])
 def test_concurrent_duplicate_and_revoked_token(self):
  token=self.user()
  with ThreadPoolExecutor(max_workers=2) as pool:
   statuses=list(pool.map(lambda _:request('/race-favorites/8','POST',token=token)[0],range(2)))
  self.assertEqual(sorted(statuses),[201,409]);self.assertEqual(len(request('/race-favorites',token=token)[1]),1)
  self.assertEqual(request('/auth/logout','POST',token=token)[0],204)
  self.assertEqual(request('/race-favorites',token=token)[0],401)
  self.assertEqual(request('/my-schedule',token=token)[0],401)
