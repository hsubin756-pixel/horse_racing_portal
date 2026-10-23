"""Real MySQL/API contract checks for synthetic win-odds snapshots."""
import subprocess,unittest
from datetime import datetime,timezone
from test_catalog import request
class OddsTests(unittest.TestCase):
 def test_popularity_odds_and_provenance(self):
  status,race=request('/races/1');self.assertEqual(status,200)
  ordered=sorted(race['entries'],key=lambda entry:entry['popularityRank'])
  self.assertEqual([e['popularityRank'] for e in ordered],list(range(1,13)))
  odds=[e['winOdds'] for e in ordered]
  self.assertEqual(odds,sorted(odds));self.assertEqual(odds[0],2.4)
  self.assertTrue(all(e['winOdds']>=1 and e['oddsSource']=='synthetic_fixture' for e in ordered))
  self.assertTrue(any(e['popularityRank']!=e['finishPosition'] for e in ordered))
  for entry in ordered:
   stamp=datetime.fromisoformat(entry['oddsAsOf'].replace('Z','+00:00'))
   self.assertEqual(stamp.tzinfo,timezone.utc)
  _,history=request('/horses/22/history')
  snapshot=next(e for e in history if e['raceId']==1)
  race_entry=next(e for e in ordered if e['horseId']==22)
  for key in ('popularityRank','winOdds','oddsSource','oddsAsOf'):
   self.assertEqual(snapshot[key],race_entry[key])
 def test_missing_upcoming_snapshot(self):
  status,race=request('/races/8');self.assertEqual(status,200)
  self.assertTrue(all(e['finishPosition'] is None for e in race['entries']))
  missing=[e for e in race['entries'] if e['winOdds'] is None]
  self.assertEqual(len(missing),1)
  for key in ('popularityRank','winOdds','oddsSource','oddsAsOf'):self.assertIsNone(missing[0][key])
  self.assertEqual(sorted(e['popularityRank'] for e in race['entries'] if e['popularityRank'] is not None),list(range(1,12)))
 def test_odds_rank_is_computed_from_stored_win_odds(self):
  """배당 기준 인기: 저장된 단승 배당이 낮은 순서, 같은 배당은 공동 순위, 배당이 없으면 비움."""
  status,race=request('/races/1');self.assertEqual(status,200)
  entries=race['entries']
  for e in entries:
   expected=1+sum(1 for o in entries if o['winOdds']<e['winOdds'])
   self.assertEqual(e['oddsRank'],expected);self.assertEqual(e['oddsRankShared'],sum(1 for o in entries if o['winOdds']==e['winOdds'])>1)
   self.assertEqual(e['oddsRankField'],12);self.assertEqual(e['oddsRankTotal'],12)
  self.assertEqual(min(e['oddsRank'] for e in entries),1)
  by_odds=sorted(entries,key=lambda e:e['winOdds']);self.assertEqual([e['oddsRank'] for e in by_odds],sorted(e['oddsRank'] for e in entries))
  _,history=request('/horses/22/history')
  snapshot=next(e for e in history if e['raceId']==1);race_entry=next(e for e in entries if e['horseId']==22)
  for key in ('oddsRank','oddsRankShared','oddsRankField','oddsRankTotal'):self.assertEqual(snapshot[key],race_entry[key])
  _,upcoming=request('/races/8');missing=next(e for e in upcoming['entries'] if e['winOdds'] is None)
  self.assertIsNone(missing['oddsRank']);self.assertIsNone(missing['oddsRankShared']);self.assertEqual(missing['oddsRankField'],11);self.assertEqual(missing['oddsRankTotal'],12)
  ranked=[e for e in upcoming['entries'] if e['oddsRank'] is not None];self.assertEqual(len(ranked),11)
  self.assertTrue(all(e['oddsRankField']==11 and e['oddsRankTotal']==12 for e in ranked))
 def test_database_rejects_invalid_or_incomplete_snapshot(self):
  for assignment,constraint in (("win_odds=0",'ck_win_odds'),("popularity_rank=0",'ck_popularity'),
   ("win_odds=NULL,popularity_rank=NULL",'ck_odds_snapshot'),("odds_as_of=NULL",'ck_odds_snapshot'),("odds_source=' '",'ck_odds_snapshot')):
   # Each connection rolls back on disconnect; committed fixture data is never changed.
   result=subprocess.run(['docker','compose','exec','-T','db','sh','-c',
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot keiba'],
    input='START TRANSACTION; UPDATE entry SET '+assignment+' WHERE race_id=1 AND number=1; ROLLBACK;',
    capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn(constraint,result.stderr)
  # Popularity and win odds are independently optional, but provenance is still mandatory.
  for assignment in ('win_odds=NULL', 'popularity_rank=NULL'):
   result=subprocess.run(['docker','compose','exec','-T','db','sh','-c',
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot keiba'],
    input='START TRANSACTION; UPDATE entry SET '+assignment+' WHERE race_id=1 AND number=1; ROLLBACK;',
    capture_output=True,text=True)
   self.assertEqual(result.returncode,0)
