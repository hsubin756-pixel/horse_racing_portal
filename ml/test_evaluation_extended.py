import unittest
from datetime import date, timedelta
from collections import defaultdict
from evaluate_extended import build


def rows(days=4, races=2, field=6):
    out = defaultdict(list)
    for d in range(days):
        day = date(2025, 1, 4) + timedelta(days=d)
        for r in range(races):
            for h in range(field):
                out[f'1:{day:%Y%m%d}:{r+1}'].append({'race_id': f'1:{day:%Y%m%d}:{r+1}', 'race_date': day, 'horse_id': h + 1, 'distance': 1200,
                    'finish_position': (h + d + r) % field + 1, 'jockey': f'J{h}', 'trainer': 'T0', 'carried_weight': '56', 'win_odds': str(h + 2),
                    'place_odds': '', 'gate': str(h + 1), 'horse_weight': '480', 'rating': '0', 'sex': '수', 'birth_date': '2020-04-01'})
    return out


class ExtendedEvaluationTests(unittest.TestCase):
    def test_connection_rates_use_only_earlier_dates(self):
        table, y, groups, dates, market = build(rows())
        first_day = [t for t, d in zip(table, dates) if d == '2025-01-04']
        self.assertTrue(all(t['jockeyStarts'] == 0 and abs(t['jockeyTop3Rate'] - 0.28) < 1e-9 for t in first_day))
        second_day = [t for t, d in zip(table, dates) if d == '2025-01-05']
        self.assertTrue(all(t['jockeyStarts'] == 2 and t['trainerStarts'] == 12 for t in second_day))
        self.assertEqual(len(table), 48)

    def test_market_rank_puts_favourite_first_and_missing_odds_last(self):
        data = rows(days=1, races=1)
        data['1:20250104:1'][0]['win_odds'] = ''
        table, y, groups, dates, market = build(data)
        self.assertEqual(list(market), [7.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(table[1]['oddsRankInRace'], 1)
        self.assertEqual(table[0]['oddsRankInRace'], 6)


if __name__ == '__main__':
    unittest.main()
