from pathlib import Path
import tempfile
import unittest
from test_evaluate_tracks import write
from evaluate_windows import evaluate


class WindowsTests(unittest.TestCase):
 def test_disjoint_windows_use_only_earlier_training_and_matched_market_races(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'seoul.csv';write(path,'1');report=evaluate([path],2,7)
   first,last=report['windows']
   self.assertEqual(first['testEndExclusive'],last['cutoff'])
   self.assertEqual(first['cohorts']['seoul']['trainingRaces'],21)
   self.assertEqual(last['cohorts']['seoul']['trainingRaces'],28)
   for window in report['windows']:
    cohort=window['cohorts']['seoul'];self.assertEqual(cohort['testRaces'],7)
    self.assertEqual(cohort['byTrack']['1']['marketRaces'],7)
    self.assertEqual(window['cohorts']['jeju']['status'],'missing_tracks')
   self.assertFalse(report['promoted'])
