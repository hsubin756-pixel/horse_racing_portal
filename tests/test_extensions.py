import unittest,uuid,sys
from pathlib import Path
from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from backup import mysql
from test_catalog import request

class ExtensionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.members=[]
  def account(admin=False):
   email='extended-'+uuid.uuid4().hex+'@example.test';body={'email':email,'password':'Extension-test-12345','nickname':'검증 회원'}
   assert request('/auth/register','POST',body)[0]==201
   id=int(mysql("SELECT id FROM member WHERE email='"+email+"';",'keiba'));cls.members.append(id)
   if admin:mysql('UPDATE member SET is_admin=TRUE WHERE id='+str(id)+';','keiba')
   return request('/auth/login','POST',body)[1]['token'],id
  cls.admin,cls.admin_id=account(True);cls.user,cls.user_id=account();cls.other,cls.other_id=account()
 @classmethod
 def tearDownClass(cls):
  mysql('UPDATE member SET is_admin=FALSE WHERE id='+str(cls.admin_id)+';','keiba')
 def save(self,kind,rows,token=None):return request('/admin/'+kind+'/save','POST',{'rows':rows},token or self.admin)
 def new_race(self):
  today=request('/my-schedule',token=self.user)[1]['asOfDate']
  r={'name':'검증 경주 '+uuid.uuid4().hex[:8],'race_date':str(date.fromisoformat(today)+timedelta(days=2)),'start_time':'15:30','venue':'검증 경마장','distance':1600,'surface':'잔디','status':'SCHEDULED','source':'synthetic_test'}
  s,b=self.save('races',[r]);self.assertEqual(s,200,b);return b['batches'][0]['ids'][0]
 def row(self,kind,id):return next(x for x in request('/admin/'+kind,token=self.admin)[1] if x['id']==id)
 def clean_race(self,id):
  mysql(f'DELETE FROM site_notification WHERE race_id={id};DELETE FROM personal_note WHERE race_id={id};DELETE FROM race_favorite WHERE race_id={id};DELETE FROM sectional WHERE entry_id IN (SELECT id FROM entry WHERE race_id={id});DELETE FROM payout WHERE race_id={id};DELETE FROM entry WHERE race_id={id};DELETE FROM race WHERE id={id};','keiba')
 def test_public_details_sectionals_styles_calendar_people(self):
  s,r=request('/races/1');self.assertEqual(s,200);self.assertEqual(r['race']['status'],'OFFICIAL');self.assertEqual(r['entries'][0]['gate'],1)
  s,r=request('/races/1/sectionals');self.assertEqual(s,200);self.assertEqual(len(r),12)
  first=r[0];self.assertEqual(first['style'],'선행');self.assertEqual([p['distance'] for p in first['points']],[400,1000,1200,1600]);self.assertAlmostEqual(sum(p['segmentSeconds'] for p in first['points']),96.96)
  self.assertAlmostEqual(first['last600'],96.96-first['points'][1]['cumulativeSeconds'])
  _,style=request('/horses/22/running-style');self.assertEqual(style['style'],'선행');self.assertEqual(style['samples'],7)
  _,style=request('/horses/33/running-style');self.assertEqual(style['style'],'판단 보류');self.assertEqual(style['samples'],0)
  self.assertEqual(request('/horses/99999/running-style')[0],404)
  self.assertEqual(request('/races/calendar?month=wrong')[0],400)
  s,c=request('/races/calendar?month=2025-01');self.assertEqual(s,200);self.assertEqual([r['id'] for r in c],[1])
  self.assertEqual(request('/races/calendar?month=2025-01&venue=missing')[1],[])
  s,people=request('/people?kind=JOCKEY&year=2025');self.assertEqual(s,200);self.assertEqual(len(people),12);self.assertEqual(sum(p['starts'] for p in people),84)
  _,profile=request('/people/'+str(people[0]['id'])+'?year=2025');self.assertEqual(profile['totals']['starts'],7)
  s,trainers=request('/people?kind=TRAINER');self.assertEqual(s,200);self.assertEqual(sum(p['starts'] for p in trainers),84)
  self.assertEqual(request('/people?kind=invalid')[0],400)
  s,payout=request('/races/1/payouts');self.assertEqual(s,200);self.assertEqual(len(payout),5);self.assertTrue(all(p['status']=='FINAL' for p in payout))
 def test_admin_authorization_preview_csv_and_atomicity(self):
  self.assertEqual(request('/admin/access')[0],401);self.assertEqual(request('/admin/access',token=self.user)[0],403)
  self.assertEqual(request('/admin/people/save','POST',{'rows':[]},self.user)[0],403)
  before=mysql('SELECT COUNT(*) FROM person;','keiba')
  csv='kind,name,biography,source\r\nJOCKEY,"테스트, 이름","소개\n둘째 줄",synthetic_test\r\n'
  s,preview=request('/admin/people/csv-preview','POST',{'csv':csv},self.admin);self.assertEqual(s,200,preview);self.assertEqual(preview[0]['name'],'테스트, 이름');self.assertEqual(mysql('SELECT COUNT(*) FROM person;','keiba'),before)
  s,saved=self.save('people',preview);self.assertEqual(s,200,saved);id=saved['batches'][0]['ids'][0]
  try:
   row=self.row('people',id);row['biography']='정정한 소개';self.assertEqual(self.save('people',[row])[0],200)
   self.assertEqual(self.save('people',[row])[0],409)
   self.assertEqual(request('/people/'+str(id))[1]['person']['biography'],'정정한 소개')
  finally:mysql('DELETE FROM person WHERE id='+str(id)+';','keiba')
  old=mysql('SELECT COUNT(*) FROM person;SELECT COUNT(*) FROM catalog_audit;','keiba')
  changes=[{'kind':'people','rows':[{'kind':'TRAINER','name':'롤백 대상','source':'synthetic_test'}]},{'kind':'races','rows':[{'name':'필수값 누락'}]}]
  self.assertEqual(request('/admin/changes','POST',changes,self.admin)[0],400)
  self.assertEqual(mysql('SELECT COUNT(*) FROM person;SELECT COUNT(*) FROM catalog_audit;','keiba'),old)
  self.assertEqual(request('/admin/people/csv-preview','POST',{'csv':'name,name\na,b'},self.admin)[0],400)
  try:
   mysql('UPDATE member SET is_admin=FALSE WHERE id='+str(self.admin_id)+';','keiba')
   self.assertEqual(request('/admin/access',token=self.admin)[0],403)
  finally:mysql('UPDATE member SET is_admin=TRUE WHERE id='+str(self.admin_id)+';','keiba')
 def test_personal_notes_ownership_revision_search_and_delete(self):
  note={'horseId':22,'body':'중간에서 전진, <script>는 문자입니다','tags':'관찰,선행'}
  self.assertEqual(request('/notes','POST',note,self.user)[0],200)
  rows=request('/notes?'+urlencode({'q':'관찰'}),token=self.user)[1];self.assertEqual(len(rows),1)
  self.assertEqual(request('/notes',token=self.other)[1],[])
  n=rows[0];edit={**note,'id':n['id'],'revision':n['revision'],'body':'수정 기록'}
  self.assertEqual(request('/notes','POST',edit,self.other)[0],409)
  self.assertEqual(request('/notes/'+str(n['id']),'DELETE',token=self.other)[0],204)
  self.assertEqual(len(request('/notes',token=self.user)[1]),1)
  self.assertEqual(request('/notes','POST',edit,self.user)[0],200);self.assertEqual(request('/notes','POST',edit,self.user)[0],409)
  self.assertEqual(request('/notes/'+str(n['id']),'DELETE',token=self.user)[0],204)
  self.assertEqual(request('/notes',token=self.user)[1],[])
 def test_schedule_notifications_cancellation_and_revision_conflict(self):
  id=self.new_race()
  try:
   self.assertEqual(self.save('entries',[{'race_id':id,'horse_id':22,'number':1,'jockey':'검증 기수','status':'DECLARED'}])[0],200)
   self.assertEqual(request('/race-favorites/'+str(id),'POST',token=self.user)[0],201)
   s,rows=request('/notifications/refresh','POST',token=self.user);self.assertEqual(s,200);own=[n for n in rows if n['race_id']==id];self.assertEqual(len(own),1)
   self.assertEqual(len([n for n in request('/notifications/refresh','POST',token=self.user)[1] if n['race_id']==id]),1)
   nid=own[0]['id'];request('/notifications/'+str(nid)+'/read','POST',token=self.other)
   self.assertFalse(next(n for n in request('/notifications/refresh','POST',token=self.user)[1] if n['id']==nid)['is_read'])
   request('/notifications/'+str(nid)+'/read','POST',token=self.user)
   self.assertTrue(next(n for n in request('/notifications/refresh','POST',token=self.user)[1] if n['id']==nid)['is_read'])
   row=self.row('races',id);row['status']='CANCELLED'
   with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(lambda _:self.save('races',[row])[0],range(2)))
   self.assertEqual(sorted(statuses),[200,409])
   self.assertNotIn(id,[r['race']['id'] for r in request('/my-schedule',token=self.user)[1]['races']])
   self.assertEqual(request('/races/'+str(id)+'/prediction','POST',token=self.user)[0],400)
  finally:self.clean_race(id)
 def test_sectional_consistency_and_full_batch_rollback(self):
  id=self.new_race()
  try:
   race=self.row('races',id);race['status']='RUNNING';self.assertEqual(self.save('races',[race])[0],200)
   s,b=self.save('entries',[{'race_id':id,'horse_id':22,'number':1,'jockey':'검증 기수','status':'FINISHED','finish_position':1,'time_seconds':100},{'race_id':id,'horse_id':23,'number':2,'jockey':'검증 기수','status':'FINISHED','finish_position':2,'time_seconds':101}]);self.assertEqual(s,200,b);eid=b['batches'][0]['ids'][0]
   base={'entry_id':eid,'source':'synthetic_test'}
   s,b=self.save('sectionals',[{**base,'distance':400,'position':1,'cumulative_seconds':25},{**base,'distance':1000,'position':1,'cumulative_seconds':65},{**base,'distance':1600,'position':1,'cumulative_seconds':100}]);self.assertEqual(s,200,b)
   self.assertEqual(request('/races/'+str(id)+'/sectionals')[1][0]['style'],'판단 보류')
   race=self.row('races',id);race['status']='OFFICIAL';self.assertEqual(self.save('races',[race])[0],200)
   self.assertEqual(self.save('sectionals',[{**base,'distance':1200,'position':1,'cumulative_seconds':60}])[0],400)
   self.assertEqual(len(request('/races/'+str(id)+'/sectionals')[1][0]['points']),3)
   bad={'race_id':id,'market':'EXACTA','combination':'1-9','status':'FINAL','amount_yen':500,'source':'synthetic_test','as_of':'2026-10-23T03:00:00Z'}
   self.assertEqual(self.save('payouts',[bad])[0],400)
   bad['combination']='2-1';self.assertEqual(self.save('payouts',[bad])[0],400)
   bad['combination']='1-2';s,preview=request('/admin/payouts/preview','POST',{'rows':[bad]},self.admin);self.assertEqual(s,200,preview)
   s,b=self.save('payouts',preview);self.assertEqual(s,200,b)
   self.assertEqual(request('/races/'+str(id)+'/payouts')[1][0]['amount_yen'],500)
   payout=self.row('payouts',b['batches'][0]['ids'][0])
   self.assertEqual(request('/admin/payouts/'+str(payout['id'])+'?revision=1','DELETE',token=self.admin)[0],409)
   self.assertEqual(request('/admin/payouts/'+str(payout['id'])+'?revision=0','DELETE',token=self.user)[0],403)
   self.assertEqual(request('/admin/payouts/'+str(payout['id'])+'?revision=0','DELETE',token=self.admin)[0],204)
   self.assertEqual(request('/races/'+str(id)+'/payouts')[1],[])
  finally:self.clean_race(id)
