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


def mixed_result_rows(prefix='99000', race_no=91):
    rows = sample_rows(prefix=prefix, race_no=race_no)
    for i, (code, remark) in enumerate([('92','주행중지'),('94','경주제외'),('95','출전취소')], 3):
        rows.append(dict(rows[0], chulNo=str(i), hrNo=prefix+str(i), hrName=f'가상 비완주말 {i}',
                         ord=code, ordBigo=remark, rcTime='0', winOdds='1.0'))
    return rows


def sample_rows(race_no=91, race_date='20100101', prefix='99000', meet='서울'):
    rows = []
    for i in range(1, 3):
        rows.append({'meet': meet, 'rcDate': race_date, 'rcNo': str(race_no), 'rcDist': '1200',
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


def sectional_rows(meet='제주', prefix='99000'):
    """Synthetic two-horse races using the user's first two time samples.

    Ranks/identities are synthetic; this is not a copy of the provider archive.
    """
    rows = sample_rows(meet=meet, prefix=prefix)
    for i, row in enumerate(rows):
        if meet == '제주':
            row.update(rcDist='800', rcTime=['67.4', '68.6'][i], jeS1fTime=['17.1', '17.4'][i],
                       jeG3fTime=['50.3', '51.2'][i], jeG1fTime=['18.1', '18.5'][i],
                       je_3cTime=['17.1', '17.4'][i], je_4cTime=['32.4', '32.8'][i], sjG3fOrd='0')
        else:
            row.update(rcTime=['75.3', '78.3'][i], buS1fAccTime=['13.7', '14.5'][i], buS1fOrd=str(i+1))
            for f, times in [(4, ['25.2','26.6']), (3, ['37.2','39.2']), (2, ['49.5','52']), (1, ['61.9','64.5'])]:
                row[f'buG{f}fAccTime'] = times[i]
                row[f'buG{f}fOrd'] = str(i+1)
            for f, times in [(3, ['38.1','39.1']), (2, ['25.8','26.3']), (1, ['13.4','13.8'])]:
                row[f'bu_{f}fGTime'] = times[i]
    return rows


def archive(folder, rows=None, meet='1'):
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
        'filters': {'meet': meet, 'rc_date': rows[0]['rcDate']}}
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

    def test_missing_other_track_sectionals_keep_finish_and_odds(self):
        for meet, code in (('제주', '2'), ('부산경남', '3')):
            rows = sample_rows(meet=meet)
            for row in rows:
                for key in list(row):
                    if key.startswith('sj'):
                        row[key] = '0'
            race = importer.prepare(rows, RETRIEVED)[0]
            e = race['entries'][0]
            with self.subTest(meet=meet):
                self.assertEqual((race['key'], race['venue'], race['surface']), (f'{code}:20100101:91', meet, '미제공'))
                self.assertTrue(race['name'].startswith(f'{meet} 91R'))
                self.assertEqual(sorted(e['points']), [1200])      # finish only
                self.assertEqual(e['corners'], [])
                self.assertEqual((e['finish'], e['odds'], e['body']), (1, Decimal('4.6'), 502))
                self.assertIn('"seG1fAccTime":"62.1"', race['raw'])  # full provider row stays in raw_json
                sql = importer.sql_plan([race])
                self.assertIn(importer.literal(meet), sql)
        seoul = importer.prepare(sample_rows(), RETRIEVED)[0]
        self.assertEqual((seoul['key'], seoul['surface']), ('1:20100101:91', '더트'))

    def test_jeju_remaining_times_merge_800m_marker_and_busan_accumulated_times(self):
        jeju = importer.prepare(sectional_rows(), RETRIEVED)[0]['entries'][0]
        self.assertEqual(jeju['points'], {200: (1, Decimal('17.1')), 600: (1, Decimal('49.3')), 800: (1, Decimal('67.4'))})
        self.assertEqual(jeju['corners'], [(3, 1, Decimal('17.1')), (4, 1, Decimal('32.4'))])
        busan = importer.prepare(sectional_rows('부경'), RETRIEVED)[0]['entries'][0]
        self.assertEqual(sorted(busan['points']), [200, 400, 600, 800, 1000, 1200])
        self.assertEqual(busan['points'][600], (1, Decimal('37.2')))
        self.assertEqual(busan['time'] - busan['points'][600][1], Decimal('38.1'))
        self.assertEqual(busan['corners'], [])

    def test_conflicting_or_impossible_track_sectionals_are_rejected(self):
        for meet, changes in [('제주', {'jeG3fTime':'50.0'}), ('제주', {'sjG3fOrd':'2'}),
                              ('제주', {'jeG1fTime':'67.4'}), ('제주', {'je_4cTime':'16'}),
                              ('부경', {'buG6fAccTime':'1'}), ('부경', {'bu_3fGTime':'39'}),
                              ('부경', {'buG3fAccTime':'24'})]:
            rows = sectional_rows(meet); rows[0].update(changes)
            with self.subTest(meet=meet, changes=changes), self.assertRaises(kra.KraError):
                importer.prepare(rows, RETRIEVED)

    def test_confirmed_non_finishers_preserved_with_null_results_and_raw(self):
        rows = mixed_result_rows()
        race = importer.prepare(rows, RETRIEVED)[0]
        self.assertEqual(len(race['entries']), 5)
        self.assertEqual([e['status'] for e in race['entries']], ['FINISHED','FINISHED','DNF','SCRATCHED','SCRATCHED'])
        for entry, note in zip(race['entries'][2:], ['주행중지','경주제외','출전취소']):
            self.assertEqual(entry['status_note'], note)
            self.assertIsNone(entry['finish']); self.assertIsNone(entry['time'])
            self.assertEqual(entry['points'], {}); self.assertEqual(entry['corners'], [])
        self.assertEqual(race['entries'][2]['odds'], Decimal('1.0'))
        self.assertIsNone(race['entries'][3]['odds']);self.assertIsNone(race['entries'][4]['odds'])
        self.assertEqual(json.loads(race['raw']), rows)
        self.assertIn('finish_position<=>NULL', importer.sql_plan([race], refresh_sectionals=True))

    def test_non_finisher_mismatch_unknown_results_and_rank_gaps_stay_held(self):
        for changes in [dict(ord='92',ordBigo='출전취소',rcTime='0'),
                        dict(ord='94',ordBigo='경주제외',rcTime='75'),
                        dict(ord='0',ordBigo='-',rcTime='0'),
                        dict(ord='98',ordBigo='경주불성립',rcTime='0'),
                        dict(ord='93',ordBigo='실격',rcTime='0')]:
            rows = mixed_result_rows();rows[2].update(changes)
            with self.subTest(changes=changes), self.assertRaises(kra.KraError):
                importer.prepare(rows, RETRIEVED)
        rows = mixed_result_rows();rows[1]['ord']='3'
        with self.assertRaises(kra.KraError):importer.prepare(rows, RETRIEVED)
        rows = mixed_result_rows()[2:]
        with self.assertRaises(kra.KraError):importer.prepare(rows, RETRIEVED)

    def test_empty_weight_change_preserves_body_and_raw(self):
        rows = sample_rows()
        rows[0]['wgHr'] = '488()'
        rows[1]['wgHr'] = '502(0)'
        plan = importer.prepare(rows, RETRIEVED)[0]
        self.assertEqual((plan['entries'][0]['body'], plan['entries'][0]['change']), (488, None))
        self.assertEqual((plan['entries'][1]['body'], plan['entries'][1]['change']), (502, 0))
        self.assertEqual(json.loads(plan['raw'])[0]['wgHr'], '488()')

    def test_empty_weight_and_observed_jockey_id_preserve_missingness_and_identity(self):
        rows = mixed_result_rows()
        rows[0]['jkNo'] = '01Z234'
        rows[3]['wgHr'] = '()'
        plan = importer.prepare(rows, RETRIEVED)[0]
        self.assertEqual(plan['entries'][0]['jockey'], '01Z234')
        self.assertEqual((plan['entries'][3]['body'],plan['entries'][3]['change']), (None,None))
        self.assertEqual(json.loads(plan['raw'])[3]['wgHr'], '()')
        for key, value in [('jkNo','01z234'),('jkNo','01ZZ34'),('jkNo','01Z2345'),('jkNo','000000'),
                           ('hrNo','01Z234'),('trNo','01Z234')]:
            with self.subTest(key=key,value=value), self.assertRaises(kra.KraError):
                importer.identifier({key:value},key)

    def test_missing_trainer_preserves_name_without_inventing_identity(self):
        rows = mixed_result_rows()
        rows[3].update(trNo='',trName='이름만 제공된 조교사')
        rows[4].pop('trNo');rows[4].pop('trName')
        plan = importer.prepare(rows, RETRIEVED)[0]
        self.assertEqual((plan['entries'][3]['trainer'],plan['entries'][3]['trainer_name']), (None,'이름만 제공된 조교사'))
        self.assertEqual((plan['entries'][4]['trainer'],plan['entries'][4]['trainer_name']), (None,None))
        self.assertEqual(importer.sql_plan([plan]).count('SET @tid=NULL;'),2)
        self.assertEqual(json.loads(plan['raw']),rows)
        for value in ('0','ABC','1'*17,'123\n456'):
            rows[3]['trNo']=value
            with self.subTest(value=value),self.assertRaises(kra.KraError):
                importer.prepare(rows, RETRIEVED)

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
            for meet, name in (('2', '제주'), ('3', '부산경남'), ('3', '부경')):
                with self.subTest(meet=meet):
                    archive(folder, sample_rows(meet=name), meet)
                    plan = importer.load_archive(folder)[0]
                    self.assertEqual(plan['venue'], importer.MEETS[meet])
                    self.assertEqual(plan['key'], f'{meet}:20100101:91')
                    self.assertEqual(json.loads(plan['raw'])[0]['meet'], name)
                    meta_wrong = json.loads((folder / 'summary.json').read_text())
                    meta_wrong['filters']['meet'] = '1'      # archive says Seoul but rows say Jeju/Busan
                    (folder / 'summary.json').write_text(json.dumps(meta_wrong))
                    with self.assertRaises(kra.KraError):
                        importer.load_archive(folder)
            meta = archive(folder)
            (folder / 'summary.json').write_text(json.dumps({**meta, 'filters': {'meet': '4', 'rc_date': '20100101'}}))
            with self.assertRaises(kra.KraError):
                importer.load_archive(folder)
            meta = archive(folder)
            for changes in [{'complete': False}, {'receivedCount': 1}, {'totalCount': 0}, {'pages': 2},
                    {'filters': {'meet': '2', 'rc_date': '20100101'}},   # Seoul rows under a Jeju request
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
