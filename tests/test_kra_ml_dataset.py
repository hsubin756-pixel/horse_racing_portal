"""Offline checks for the API155 dataset builder: race validation and CSV export, no provider calls."""
import csv
import json
import sys
import tempfile
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
    def test_export_limits_cached_days_to_requested_period(self):
        days = [day(d, [starter(1, g, f'004423{g}', str(g)) for g in range(1, 5)])
                for d in ('2024-12-31', '2025-01-04', '2025-12-28', '2026-01-01')]
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(ds, 'load_days', return_value=days), mock.patch('builtins.print'):
            out = Path(folder) / 'seoul-2025.csv'
            ds.export('1', out, start=date(2025, 1, 4), end=date(2025, 12, 28))
            with out.open() as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 8)
            self.assertEqual({r['race_date'] for r in rows}, {'2025-01-04', '2025-12-28'})
            before = out.read_bytes()
            with self.assertRaises(KraError):
                ds.export('1', out, start=date(2023, 1, 1), end=date(2023, 12, 31))
            self.assertEqual(out.read_bytes(), before)

    def test_keeps_complete_races_and_reports_dropped_ones(self):
        good = [starter(1, g, f'004423{g}', str(g)) for g in range(1, 6)]
        tie = [starter(2, g, f'004424{g}', '1' if g < 3 else str(g)) for g in range(1, 6)]
        scratched = [starter(3, g, f'004425{g}', str(g) if g < 5 else '') for g in range(1, 6)]
        small = [starter(4, g, f'004426{g}', str(g)) for g in range(1, 4)]
        mixed_distance = [starter(5, g, f'004427{g}', str(g), '1200' if g < 5 else '1400') for g in range(1, 6)]
        rows, dropped = ds.build_rows([day('2022-02-20', good + tie + scratched + small + mixed_distance)], '1', drop_scratched=False)
        self.assertEqual(len(rows), 5)
        self.assertEqual({k: rows[0][k] for k in ('race_id', 'race_date', 'horse_id', 'distance', 'finish_position')},
                         {'race_id': '1:20220220:1', 'race_date': '2022-02-20', 'horse_id': 44231, 'distance': 1200, 'finish_position': 1})
        self.assertEqual(dropped, {'착순 불완전(동착·4두 미만·취소 후 순위 공백)': 2, '순위 없음·취소·실격 포함': 1, '거리 불일치': 1})
        # Relaxed rule: a scratched starter (blank rank) is dropped and the race kept when the remaining ranks are 1..N.
        rows, dropped = ds.build_rows([day('2022-02-20', good + scratched)], '1')
        self.assertEqual(len(rows), 9)
        self.assertEqual(dropped, {'(참고) 취소마만 제외하고 유지한 경주': 1})
        gap = [starter(6, g, f'004428{g}', str(g) if g != 3 else '') for g in range(1, 6)]   # rank 3 missing after scratch
        rows, dropped = ds.build_rows([day('2022-02-20', gap)], '1')
        self.assertEqual((rows, dropped), ([], {'착순 불완전(동착·4두 미만·취소 후 순위 공백)': 1}))

    def test_extended_columns_are_parsed_and_blank_when_invalid(self):
        row = dict(starter(1, 1, '0044233', '1'), jckyNm='안토니오', trarNm='최용구', burdWgt='56', winPrice='4.6', placePrice='1.7', rchrWeg='502(-2)', ratgSo='0', gndrNm='수', bthd='2019-04-07')
        bad = dict(starter(1, 2, '0044234', '2'), burdWgt='-', winPrice='NaN', rchrWeg='?', gtno='x')
        rows, _ = ds.build_rows([day('2022-02-20', [row, bad] + [starter(1, g, f'004423{g+4}', str(g)) for g in range(3, 5)])], '1')
        self.assertEqual({k: rows[0][k] for k in ds.EXTRA}, {'jockey': '안토니오', 'trainer': '최용구', 'carried_weight': '56', 'win_odds': '4.6', 'place_odds': '1.7', 'gate': '1', 'horse_weight': 502, 'rating': '0', 'sex': '수', 'birth_date': '2019-04-07'})
        self.assertEqual({k: rows[1][k] for k in ('carried_weight', 'win_odds', 'horse_weight', 'gate')}, {'carried_weight': '', 'win_odds': '', 'horse_weight': '', 'gate': ''})

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
