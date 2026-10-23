"""Offline checks for the API155 dataset builder: race validation and CSV export, no provider calls."""
import csv
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kra_ml_dataset as ds  # noqa: E402
from kra import KraError  # noqa: E402


def starter(race_no, gate, hrno, rank, dist='1200'):
    return {'raceDt': '20220220', 'raceNo': str(race_no), 'gtno': str(gate), 'hrno': hrno, 'rk': rank, 'raceDs': dist, 'hrnm': '말' + hrno, 'winPrice': '4.6'}


def day(date_text, rows):
    return {'meet': '1', 'date': date_text, 'api': 'KRA_API155', 'rows': rows}


class DatasetTests(unittest.TestCase):
    def test_keeps_complete_races_and_reports_dropped_ones(self):
        good = [starter(1, g, f'004423{g}', str(g)) for g in range(1, 6)]
        tie = [starter(2, g, f'004424{g}', '1' if g < 3 else str(g)) for g in range(1, 6)]
        scratched = [starter(3, g, f'004425{g}', str(g) if g < 5 else '') for g in range(1, 6)]
        small = [starter(4, g, f'004426{g}', str(g)) for g in range(1, 4)]
        mixed_distance = [starter(5, g, f'004427{g}', str(g), '1200' if g < 5 else '1400') for g in range(1, 6)]
        rows, dropped = ds.build_rows([day('2022-02-20', good + tie + scratched + small + mixed_distance)], '1')
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0], {'race_id': '1:20220220:1', 'race_date': '2022-02-20', 'horse_id': 44231, 'distance': 1200, 'finish_position': 1})
        self.assertEqual(dropped, {'착순 불완전(동착·4두 미만)': 2, '순위 없음·취소·실격 포함': 1, '거리 불일치': 1})

    def test_export_writes_csv_and_warns_below_thirty_dates(self):
        days = [day(f'2022-02-{d:02d}', [starter(1, g, f'00442{d:02d}{g}', str(g)) for g in range(1, 7)]) for d in (5, 6, 12)]
        out = Path(__file__).resolve().parent / '.tmp-ml.csv'
        with mock.patch.object(ds, 'load_days', return_value=days), mock.patch('builtins.print') as printed:
            ds.export('1', str(out))
        with out.open(newline='', encoding='utf-8') as source:
            written = list(csv.DictReader(source))
        out.unlink()
        self.assertEqual(len(written), 18)
        self.assertEqual(written[-1]['race_id'], '1:20220212:1')
        text = ' '.join(str(c.args[0]) for c in printed.call_args_list)
        self.assertIn('날짜 3개, 경주 3개, 출전 18건', text)
        self.assertIn('30일 이상', text)

    def test_collect_only_calls_race_days_and_caches_results(self):
        page = ('<response><header><resultCode>00</resultCode></header><body><items><item><raceNo>1</raceNo><hrno>0044233</hrno><rk>1</rk><raceDs>1200</raceDs></item></items>'
                '<numOfRows>100</numOfRows><pageNo>1</pageNo><totalCount>1</totalCount></body></response>')
        root = Path(__file__).resolve().parent / '.tmp-ml-dir'
        calls = []

        def fake(key, api, params, page_no, size):
            calls.append(params['race_dt'])
            return page
        with mock.patch.object(ds, 'ML_DIR', root), mock.patch.object(ds, 'load_key', return_value='K' * 32), \
                mock.patch.object(ds.kc, 'request_page', side_effect=fake), mock.patch('builtins.print'):
            ds.collect('1', date(2022, 2, 14), date(2022, 2, 20), 100, False)   # Mon..Sun: only Sat 19 and Sun 20
            ds.collect('1', date(2022, 2, 14), date(2022, 2, 20), 100, False)   # cached: no new calls
            ds.collect('1', date(2022, 2, 14), date(2022, 2, 20), 1, True)      # all days but one call budget
        self.assertEqual(calls, ['20220219', '20220220', '20220214'])
        saved = json.loads((root / 'meet-1' / '20220219.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['rows'][0]['hrno'], '0044233')
        for path in sorted((root / 'meet-1').glob('*')):
            path.unlink()
        (root / 'meet-1').rmdir(); root.rmdir()
        with self.assertRaises(KraError):
            ds.collect('1', date(2022, 2, 20), date(2022, 2, 14), 10, False)


if __name__ == '__main__':
    unittest.main()
