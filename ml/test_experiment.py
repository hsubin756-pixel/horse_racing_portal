import copy
import csv
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import experiment as exp
from test_evaluation_extended import rows


class ExperimentTests(unittest.TestCase):
    def test_current_same_day_and_future_outcomes_cannot_change_past_features(self):
        original = rows(days=4, races=2)
        modified = copy.deepcopy(original)
        for race in modified.values():
            if race[0]['race_date'] >= date(2025, 1, 5):
                for r in race:
                    r['finish_position'] = 7-r['finish_position']
        a, _, _, dates, _ = exp.features(original)
        b, _, _, _, _ = exp.features(modified)
        for index, day in enumerate(dates):
            if day <= '2025-01-05':
                self.assertEqual(a[index], b[index])
        self.assertTrue(any(a[i] != b[i] for i, day in enumerate(dates) if day > '2025-01-05'))
        self.assertEqual(a[12]['starts'], 2)
        self.assertEqual(a[12]['daysSinceLastStart'], 1)

    def test_recent_five_distance_and_missing_connections(self):
        data = rows(days=8, races=1)
        for race in data.values():
            for r in race:
                r['jockey'] = ''; r['trainer'] = ''
                if r['race_date'] == date(2025, 1, 10): r['distance'] = 1800
        table, _, _, _, _ = exp.features(data)
        last = table[-6]
        self.assertEqual(last['starts'], 7)
        self.assertEqual(last['distanceStarts'], 6)
        self.assertEqual(last['jockeyStarts'], 0)
        expected = np.mean([race[0]['finish_position'] for race in list(data.values())[2:7]])
        self.assertEqual(last['recentMeanFinish'], expected)

    def test_odds_and_row_order_do_not_change_model_features_and_ties_share_rank(self):
        original = rows(days=2, races=1)
        for race in original.values():
            race[0]['win_odds'] = race[1]['win_odds'] = '2'
        a = exp.features(original)
        shuffled = {k: list(reversed(v)) for k, v in reversed(list(original.items()))}
        b = exp.features(shuffled)
        self.assertEqual(a[0], b[0])
        np.testing.assert_array_equal(a[4], b[4])
        self.assertEqual(list(a[4][:3]), [1, 1, 1/3])
        altered = copy.deepcopy(original)
        for race in altered.values():
            for r in race: r['win_odds'] = ''; r['rating'] = '999'; r['place_odds'] = '88'
        c = exp.features(altered)
        self.assertEqual(a[0], c[0])
        self.assertTrue(np.isnan(c[4]).all())
        for cols in exp.SETS.values():
            self.assertFalse(set(cols) & {'logWinOdds', 'oddsRankInRace', 'rating', 'finish_position'})

    def test_missing_market_excludes_whole_race_and_paired_bootstrap_is_zero_for_equal_scores(self):
        data = rows(days=35, races=1)
        data['1:20250207:1'][0]['win_odds'] = ''
        report = exp.compare_window(data, '2025-02-01', '2025-02-08', ['base', 'recent'], ['seoul'])
        track = report['cohorts']['seoul']['byTrack']['1']
        self.assertEqual(track['races'], 7)
        self.assertEqual(track['marketRaces'], 6)
        self.assertEqual(track['variants']['base']['deltaAgainstBase']['pairedRaceBootstrap95'], [0, 0])
        self.assertEqual(track['variants']['recent']['matchedMarket']['races'], 6)

    def test_loader_rejects_duplicate_starters_and_mixed_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'data.csv'
            original = list(rows(days=1, races=1).values())[0]
            for kind in ('duplicate', 'distance', 'date'):
                data = copy.deepcopy(original)
                if kind == 'duplicate': data[1]['horse_id'] = data[0]['horse_id']
                elif kind == 'distance': data[1]['distance'] = 1800
                else:
                    for r in data: r['race_id'] = '1:20250105:1'
                with path.open('w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
                with self.assertRaises(ValueError): exp.read([path])

    def test_development_end_does_not_move_with_new_rows(self):
        data = rows(days=45, races=1)
        with patch.object(exp, 'compare_window', return_value={}) as run:
            result = exp.develop(data, '2025-02-08', 2, 7)
        self.assertEqual(result['excludedLaterRaces'], 10)
        calls = run.call_args_list
        self.assertEqual(calls[0].args[1:3], ('2025-01-25', '2025-02-01'))
        self.assertEqual(calls[1].args[1:3], ('2025-02-01', '2025-02-08'))
        self.assertTrue(all(rs[0]['race_date'] < date(2025, 2, 8) for rs in calls[0].args[0].values()))

    def test_final_plan_freezes_training_and_rejects_peeking_edits_and_new_training_rows(self):
        data = rows(days=35, races=1)
        with patch.object(exp, 'today', return_value=date(2025, 2, 10)):
            plan = exp.freeze(data, '2025-02-08', '2025-03-01', '2025-04-01', 'seoul', 'recent')
            with self.assertRaisesRegex(ValueError, 'not ended'): exp.final(data, plan)
            with self.assertRaises(ValueError): exp.freeze(data, '2025-02-08', '2025-02-10', '2025-04-01', 'seoul', 'recent')
        changed = copy.deepcopy(plan); changed['featureSet'] = 'combined'
        with self.assertRaisesRegex(ValueError, 'changed or invalid'): exp.final(data, changed)
        changed = copy.deepcopy(data); next(iter(changed.values()))[0]['horse_weight'] = '555'
        with patch.object(exp, 'today', return_value=date(2025, 4, 2)):
            with self.assertRaisesRegex(ValueError, 'training rows'): exp.final(changed, plan)
            with self.assertRaisesRegex(ValueError, 'Insufficient final-period'): exp.final(data, plan)
            all_data = rows(days=90, races=1)
            result = exp.final(all_data, plan)
        cohort = result['window']['cohorts']['seoul']
        self.assertEqual(cohort['trainingRaces'], 35)
        self.assertEqual(cohort['testRaces'], 31)
        self.assertEqual(set(cohort['byTrack']['1']['variants']), {'recent'})
        self.assertFalse(result['promoted'])

    def test_blank_and_cross_track_person_names_do_not_share_history(self):
        data = rows(days=2, races=1)
        day2 = data.pop('1:20250105:1')
        for r in day2: r['race_id'] = '3:20250105:1'
        data['3:20250105:1'] = day2
        table, _, _, _, _ = exp.features(data)
        self.assertEqual(table[-1]['jockeyStarts'], 0)
        self.assertEqual(table[-1]['trainerStarts'], 0)
        self.assertEqual(table[-1]['starts'], 1)  # National horse ID keeps history across tracks.

    def test_audit_is_explicit_and_output_never_overwrites(self):
        report = exp.audit(rows())
        self.assertFalse(report['preRaceAvailabilityVerified'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            exp.save(path, report)
            with self.assertRaises(FileExistsError): exp.save(path, {})
            self.assertEqual(json.loads(path.read_text()), report)


if __name__ == '__main__':
    unittest.main()
