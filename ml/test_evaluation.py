import csv,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from evaluate import features,evaluate
class EvaluationTests(unittest.TestCase):
 def rows(self):
  return [dict(race_id=str(r),race_date=(date(2020,1,1)+timedelta(days=r//2)).isoformat(),
   horse_id=h+1,distance=1600,finish_position=(h+r)%8+1) for r in range(80) for h in range(8)]
 def test_same_day_and_current_results_cannot_leak(self):
  rows=self.rows();x,y,g,d=features(rows)
  self.assertTrue((x[:16,1]==0).all());self.assertTrue((x[16:32,1]==2).all())
  changed=[dict(r,finish_position=9-r['finish_position']) if r['race_id'] in ('2','3') else r for r in rows]
  other,*_=features(changed)
  self.assertTrue((x[:32]==other[:32]).all())
 def test_rejects_duplicate_and_incomplete_results(self):
  rows=self.rows()
  with self.assertRaises(ValueError): features(rows+[rows[0]])
  with self.assertRaises(ValueError): features(rows[1:])
 def test_temporal_report_records_provenance(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'synthetic.csv';rows=self.rows()
   with path.open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
   report=evaluate(path,'Generated test fixture; no real racing data')
   self.assertEqual(report['trainingRaces'],64);self.assertEqual(report['testRaces'],16)
   self.assertEqual(len(report['dataSha256']),64);self.assertFalse(report['rightsVerifiedByTool'])
   self.assertIn('top3RecallBootstrap95',report['metrics'])
