import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_evaluation_extended import rows
from evaluate_tracks import compare


def write(path, track):
    data=[]
    for race in rows(days=35,races=1).values():
        for row in race:
            row=dict(row);row['race_id']=track+row['race_id'][1:];data.append(row)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)


class TrackEvaluationTests(unittest.TestCase):
    def test_cohorts_share_cutoff_and_combined_reports_each_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[Path(tmp)/f'{i}.csv' for i in ('1','2','3')]
            for i,p in zip(('1','2','3'),paths):write(p,i)
            report=compare(paths)
            self.assertFalse(report['promoted'])
            self.assertEqual(set(report['cohorts']['seoul_busan']['byTrack']),{'1','3'})
            self.assertEqual(report['cohorts']['seoul']['testRaces'],report['cohorts']['seoul_busan']['byTrack']['1']['races'])
            self.assertEqual(set(report['cohorts']['jeju']['byTrack']),{'2'})
            self.assertTrue(all(c['status']=='evaluated' for c in report['cohorts'].values()))

    def test_missing_tracks_and_duplicate_races_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'seoul.csv';write(p,'1')
            report=compare([p,p])
            self.assertEqual(report['cohorts']['seoul_busan']['status'],'missing_tracks')
            self.assertEqual(report['cohorts']['jeju']['status'],'missing_tracks')
            self.assertEqual(report['cohorts']['seoul']['trainingRaces'],28)

    def test_absent_odds_do_not_create_a_market_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'seoul.csv';write(p,'1')
            with p.open() as f: data=list(csv.DictReader(f))
            for row in data: row['win_odds']=''
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
            report=compare([p])
            track=report['cohorts']['seoul']['byTrack']['1']
            self.assertEqual(track['marketRaces'],0)
            self.assertIsNone(track['market'])
            self.assertIsNone(track['modelOnMarketSubset'])

if __name__=='__main__':unittest.main()
