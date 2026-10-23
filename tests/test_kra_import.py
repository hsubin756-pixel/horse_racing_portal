"""Offline validation of KRA archive conversion. All records below are synthetic."""
import copy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kra
import kra_import as importer

RETRIEVED = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)


def sample_rows(race_no=91, race_date='20100101', prefix='99000'):
    rows = []
    for i in range(1, 3):
        rows.append({'meet': '서울', 'rcDate': race_date, 'rcNo': str(race_no), 'rcDist': '1200',
            'rcName': '가상 KRA 검증', 'rank': '국6등급', 'weather': '맑음', 'track': '건조 (2%)',
            'hrNo': prefix + str(i), 'hrName': f'가상 KRA 검증말 {i}', 'sex': '수', 'birthday': '20070407',
            'chulNo': str(i), 'ord': str(i), 'ordBigo': '-', 'rcTime': str(Decimal('75.9') + i - 1),
            'jkNo': prefix + '3', 'jkName': '가상 검증 기수', 'trNo': prefix + '4', 'trName': '가상 검증 조교사',
            'wgBudam': '56', 'wgHr': '502(-2)', 'winOdds': '4.6', 'plcOdds': '1.7',
            'seS1fAccTime': '13.6', 'sjS1fOrd': str(i), 'seG3fAccTime': '36.6', 'sjG3fOrd': str(i),
            'seG1fAccTime': '62.1', 'sjG1fOrd': str(i), 'se_1cAccTime': '0', 'sj_1cOrd': '0',
            'se_2cAccTime': '0', 'sj_2cOrd': '0', 'se_3cAccTime': '24.3', 'sj_3cOrd': str(i),
            'se_4cAccTime': '43', 'sj_4cOrd': str(i)})
    return rows


def archive(folder, rows=None):
    rows = rows or sample_rows()
    root = ET.Element('response')
    ET.SubElement(ET.SubElement(root, 'header'), 'resultCode').text = '00'
    body = ET.SubElement(root, 'body')
    items = ET.SubElement(body, 'items')
    for row in rows:
        item = ET.SubElement(items, 'item')
        for key, value in row.items():
            ET.SubElement(item, key).text = value
    for key, value in {'numOfRows': '100', 'pageNo': '1', 'totalCount': str(len(rows))}.items():
        ET.SubElement(body, key).text = value
    (folder / 'page-1.xml').write_text(ET.tostring(root, encoding='unicode'))
    metadata = {'source': importer.SOURCE, 'endpoint': kra.ENDPOINT, 'complete': True, 'pages': 1,
        'totalCount': len(rows), 'receivedCount': len(rows), 'retrievedAt': RETRIEVED.isoformat(),
        'filters': {'meet': '1', 'rc_date': rows[0]['rcDate']}}
    (folder / 'summary.json').write_text(json.dumps(metadata))
    return metadata


class KraImportTests(unittest.TestCase):
    def test_converts_seoul_without_inventing_popularity_or_corner_distances(self):
        race = importer.prepare(sample_rows(), RETRIEVED)[0]
        e = race['entries'][0]
        self.assertEqual(e['horse'], '990001')
        self.assertEqual(e['body'], 502)
        self.assertEqual(e['change'], -2)
        self.assertEqual(sorted(e['points']), [200, 600, 1000, 1200])
        self.assertEqual(e['points'][1200][1] - e['points'][600][1], Decimal('39.3'))
        self.assertEqual(e['corners'], [(3, 1, Decimal('24.3')), (4, 1, Decimal('43'))])
        self.assertNotIn('popularity', e)
        self.assertNotIn('plcOdds', e)
        self.assertIn('"plcOdds":"1.7"', race['raw'])

    def test_rejects_ambiguous_results_and_invalid_sectionals(self):
        for updates in [
            {'ordBigo': '주행중지'}, {'ord': '99'}, {'rcTime': '0'}, {'hrNo': ''},
            {'sjS1fOrd': '3'}, {'seG3fAccTime': '12'}, {'se_4cAccTime': '20'},
            {'wgHr': 'NaN'}, {'winOdds': 'NaN'}, {'winOdds': '4.65'}, {'sex': '?'},
            {'birthday': '20200407'}, {'rcDist': '1300'},
        ]:
            rows = sample_rows(); rows[0].update(updates)
            with self.subTest(updates=updates), self.assertRaises(kra.KraError):
                importer.prepare(rows, RETRIEVED)
        for key in ['hrNo', 'chulNo']:
            rows = sample_rows(); rows[1][key] = rows[0][key]
            with self.assertRaises(kra.KraError):
                importer.prepare(rows, RETRIEVED)

    def test_missing_times_and_odds_are_not_zero_records(self):
        rows = sample_rows()
        rows[0].update({'winOdds': '0', 'seS1fAccTime': '0', 'sjS1fOrd': '0', 'seG3fAccTime': ''})
        e = importer.prepare(rows, RETRIEVED)[0]['entries'][0]
        self.assertIsNone(e['odds'])
        self.assertNotIn(200, e['points'])
        self.assertIsNone(e['points'][600][1])

    def test_tied_ranks_and_stable_fingerprint(self):
        rows = sample_rows(); rows[1]['ord'] = '1'
        race = importer.prepare(rows, RETRIEVED)[0]
        self.assertEqual(race['fingerprint'], importer.prepare(list(reversed(rows)), RETRIEVED)[0]['fingerprint'])
        rows[1]['ord'] = '3'
        with self.assertRaises(kra.KraError):
            importer.prepare(rows, RETRIEVED)

    def test_archive_completeness_and_wrong_scope(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            meta = archive(folder)
            self.assertEqual(len(importer.load_archive(folder)[0]['entries']), 2)
            for changes in [{'complete': False}, {'receivedCount': 1}, {'totalCount': 0}, {'pages': 2},
                    {'filters': {'meet': '2', 'rc_date': '20100101'}},
                    {'filters': {'meet': '1', 'rc_date': '20100102'}},
                    {'retrievedAt': '2026-01-01T00:00:00'}]:
                (folder / 'summary.json').write_text(json.dumps({**meta, **changes}))
                with self.subTest(changes=changes), self.assertRaises(kra.KraError):
                    importer.load_archive(folder)

    def test_sql_values_are_encoded_and_archive_has_no_payout_invention(self):
        rows = sample_rows(); rows[0]['hrName'] = "가상말'); DROP TABLE horse; --"
        sql = importer.sql_plan(importer.prepare(rows, RETRIEVED))
        self.assertNotIn('DROP TABLE horse', sql)
        self.assertNotIn('INSERT INTO payout', sql)
        self.assertIn('START TRANSACTION', sql)
        self.assertIn('COMMIT', sql)
        self.assertIn('GET_LOCK', sql)


if __name__ == '__main__':
    unittest.main()
