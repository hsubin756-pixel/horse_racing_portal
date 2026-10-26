"""Real MySQL/API tests with temporary, explicitly synthetic KRA-shaped records."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import random
import sys
import unittest
import uuid
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from backup import mysql
import kra_import as importer
from kra import KraError
from test_catalog import request
from test_kra_import import sample_rows, sectional_rows, archive, RETRIEVED
import kra_sync


class KraIntegrationTests(unittest.TestCase):
    def test_retry_archived_empty_weight_change_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = sample_rows(prefix=self.prefix)
            rows[0]['wgHr'] = '488()'
            rows[1]['wgHr'] = '502(0)'
            archive(Path(folder), rows)
            task = {'archive':folder, 'site':'보류 있음',
                    'races':{'91':{'status':'보류','error':'마체중·증감 표기를 확인하세요.'}}}
            budget = kra_sync.Budget(0)
            kra_sync.site_day(task,'1',date(2010,1,1),'unused',budget,True,True)
            rid = task['races']['91']['raceId']
            entries = request(f'/races/{rid}')[1]['entries']
            by_number = {entry['number']:entry for entry in entries}
            self.assertEqual(by_number[1]['bodyWeight'],488)
            self.assertIsNone(by_number[1]['weightChange'])
            self.assertEqual(by_number[2]['weightChange'],0)
            self.assertEqual(task['site'],'반영 완료')
            self.assertNotIn('error',task['races']['91'])
            self.assertEqual(budget.calls,0)
            kra_sync.site_day(task,'1',date(2010,1,1),'unused',budget,True,True)
            self.assertEqual(task['races']['91']['raceId'],rid)

    def test_sync_imports_valid_races_and_records_unsupported_race(self):
        with tempfile.TemporaryDirectory() as folder:
            good = sample_rows(prefix=self.prefix)
            bad = sample_rows(race_no=92, prefix=self.prefix)
            bad[0]['ordBigo'] = '주행중지'
            archive(Path(folder), good + bad)
            task = {'archive': folder}
            kra_sync.site_day(task, '1', date(2010, 1, 1), 'unused', kra_sync.Budget(1), True, False)
            self.assertEqual(task['races']['91']['status'], '반영 완료')
            self.assertEqual(task['races']['92']['status'], '보류')
            rid = task['races']['91']['raceId']
            self.assertEqual(request(f'/races/{rid}')[0], 200)
            self.assertEqual(mysql("SELECT COUNT(*) FROM race WHERE kra_id='1:20100101:92';", 'keiba').strip(), '0')
            kra_sync.site_day(task, '1', date(2010, 1, 1), 'unused', kra_sync.Budget(1), True, False)
            self.assertEqual(task['races']['91']['raceId'], rid)

    def setUp(self):
        self.prefix = '98' + str(random.randint(10000, 99999))
        self.rows = sample_rows(prefix=self.prefix)
        self.keys = ['1:20100101:91', '1:20100101:92', '1:20100101:93', '1:20100201:91']
        self.keys += ['2:20100101:91', '3:20100101:91']
        self.where = ','.join(importer.literal(k) for k in self.keys)
        self.assertEqual(mysql(f'SELECT COUNT(*) FROM race WHERE kra_id IN ({self.where});', 'keiba').strip(), '0')
        self.assertEqual(mysql(f"SELECT COUNT(*) FROM horse WHERE kra_id LIKE '{self.prefix}%';", 'keiba').strip(), '0')
        self.addCleanup(self.cleanup)

    def cleanup(self):
        ids = f'SELECT id FROM race WHERE kra_id IN ({self.where})'
        entries = f'SELECT id FROM entry WHERE race_id IN ({ids})'
        mysql(f'DELETE FROM sectional_marker WHERE entry_id IN ({entries});'
              f'DELETE FROM sectional WHERE entry_id IN ({entries});'
              f'DELETE FROM entry WHERE race_id IN ({ids});'
              f'DELETE FROM kra_race_import WHERE race_id IN ({ids});'
              f'DELETE FROM race WHERE kra_id IN ({self.where});'
              f"DELETE FROM horse WHERE kra_id LIKE '{self.prefix}%';"
              f"DELETE FROM person WHERE kra_id LIKE '{self.prefix}%';", 'keiba')

    def test_import_visible_api_duplicate_noop_and_original_values(self):
        plan = importer.prepare(self.rows, RETRIEVED)
        race_id, created = importer.apply(plan)[0]
        self.assertEqual(created, 1)
        self.assertEqual(importer.apply(plan), [(race_id, 0)])
        status, race = request(f'/races/{race_id}')
        self.assertEqual(status, 200)
        self.assertEqual(race['race']['source'], 'KRA_API214_1')
        self.assertEqual(len(race['entries']), 2)
        e = race['entries'][0]
        self.assertIsNone(e['popularityRank'])
        self.assertEqual(e['winOdds'], 4.6)
        # 두 출전마의 단승 배당이 같으므로 배당 기준 인기는 공동 1위, 계산 두수 2/2
        self.assertEqual([(x['oddsRank'], x['oddsRankShared'], x['oddsRankField'], x['oddsRankTotal']) for x in race['entries']], [(1, True, 2, 2)] * 2)
        self.assertIsNone(e['gate'])
        self.assertEqual(e['trainerName'], '가상 검증 조교사')
        self.assertEqual(request('/horses/' + str(e['horseId']))[1]['kraId'], self.rows[0]['hrNo'])
        _, runs = request(f'/races/{race_id}/sectionals')
        self.assertEqual(runs[0]['last600'], 39.3)
        self.assertEqual(runs[0]['style'], '선행')
        self.assertEqual([m['corner'] for m in runs[0]['markers']], [3, 4])
        self.assertEqual(len(runs[0]['points']), 4)
        self.assertEqual(request('/horses/' + str(e['horseId']) + '/running-style')[1]['style'], '판단 보류')
        self.assertEqual(request(f'/races/{race_id}/payouts')[1], [])
        raw = json.loads(mysql(f'SELECT raw_json FROM kra_race_import WHERE race_id={race_id};', 'keiba'))
        self.assertEqual(raw[0]['plcOdds'], '1.7')

    def test_other_tracks_persist_finish_without_inventing_sectionals(self):
        for meet, code in [('제주', '2'), ('부경', '3')]:
            with self.subTest(meet=meet):
                rows = sample_rows(meet=meet, prefix=self.prefix)
                for row in rows:
                    for key in list(row):
                        if key.startswith('sj'):
                            row[key] = '0'
                plan = importer.prepare(rows, RETRIEVED)
                race_id, created = importer.apply(plan)[0]
                self.assertEqual(created, 1)
                self.assertEqual(importer.apply(plan), [(race_id, 0)])
                status, race = request(f'/races/{race_id}')
                self.assertEqual(status, 200)
                self.assertEqual(race['race']['surface'], '미제공')
                self.assertEqual(len(race['entries']), 2)
                self.assertEqual(race['entries'][0]['oddsRank'], 1)
                _, runs = request(f'/races/{race_id}/sectionals')
                self.assertEqual(len(runs[0]['points']), 1)
                self.assertEqual(runs[0]['markers'], [])
                self.assertIsNone(runs[0]['last600'])
                self.assertEqual(mysql(f'SELECT kra_id FROM race WHERE id={race_id};', 'keiba').strip(), f'{code}:20100101:91')
                raw = json.loads(mysql(f'SELECT raw_json FROM kra_race_import WHERE race_id={race_id};', 'keiba'))
                self.assertEqual(raw[0]['meet'], meet)

    def test_refresh_sectionals_preserves_race_and_rejects_changed_source(self):
        for meet in ('제주', '부경'):
            with self.subTest(meet=meet):
                plan = importer.prepare(sectional_rows(meet, self.prefix), RETRIEVED)
                old = copy.deepcopy(plan)
                for entry in old[0]['entries']:
                    entry['points'] = {old[0]['distance']: (entry['finish'], entry['time'])}
                    entry['corners'] = []
                rid = importer.apply(old)[0][0]
                before = request(f'/races/{rid}')[1]
                self.assertEqual(importer.apply(plan, refresh_sectionals=True), [(rid, 0)])
                self.assertEqual(importer.apply(plan, refresh_sectionals=True), [(rid, 0)])
                self.assertEqual(request(f'/races/{rid}')[1], before)
                runs = request(f'/races/{rid}/sectionals')[1]
                self.assertEqual(runs[0]['style'], '선행')
                self.assertEqual(runs[0]['last600'], 50.3 if meet == '제주' else 38.1)
                self.assertEqual(len(runs[0]['points']), 3 if meet == '제주' else 6)
                self.assertEqual(len(runs[0]['markers']), 2 if meet == '제주' else 0)
                # Changed raw source cannot be silently reinterpreted.
                changed = sectional_rows(meet, self.prefix); changed[0]['winOdds'] = '5.0'
                with self.assertRaises(KraError):
                    importer.apply(importer.prepare(changed, RETRIEVED), refresh_sectionals=True)
                self.assertEqual(request(f'/races/{rid}/sectionals')[1], runs)
                # A foreign-source marker on the last horse rolls back changes to the first.
                eid = mysql(f'SELECT id FROM entry WHERE race_id={rid} ORDER BY number DESC LIMIT 1;', 'keiba').strip()
                mysql(f"UPDATE sectional SET source='manual_test' WHERE entry_id={eid};", 'keiba')
                snapshot = request(f'/races/{rid}/sectionals')[1]
                with self.assertRaises(KraError):
                    importer.apply(plan, refresh_sectionals=True)
                self.assertEqual(request(f'/races/{rid}/sectionals')[1], snapshot)

    def test_refresh_requires_an_existing_import(self):
        plan = importer.prepare(sectional_rows('부경', self.prefix), RETRIEVED)
        with self.assertRaises(KraError):
            importer.apply(plan, refresh_sectionals=True)
        self.assertEqual(mysql("SELECT COUNT(*) FROM race WHERE kra_id='3:20100101:91';", 'keiba').strip(), '0')

    def test_whole_batch_rolls_back_when_existing_source_changes(self):
        original = importer.prepare(self.rows, RETRIEVED)
        importer.apply(original)
        changed = copy.deepcopy(self.rows)
        changed[0]['winOdds'] = '5.0'
        new_rows = sample_rows(race_no=92, prefix=self.prefix)
        combined = importer.prepare(new_rows, RETRIEVED) + importer.prepare(changed, RETRIEVED)
        with self.assertRaises(KraError):
            importer.apply(combined)
        self.assertEqual(mysql("SELECT COUNT(*) FROM race WHERE kra_id='1:20100101:92';", 'keiba').strip(), '0')
        self.assertEqual(mysql("SELECT win_odds FROM entry e JOIN race r ON r.id=e.race_id WHERE r.kra_id='1:20100101:91' AND e.number=1;", 'keiba').strip(), '4.6')

    def test_concurrent_import_creates_one_race(self):
        plan = importer.prepare(self.rows, RETRIEVED)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outputs = list(pool.map(lambda _: importer.apply(plan), range(2)))
        self.assertEqual(sorted(output[0][1] for output in outputs), [0, 1])
        self.assertEqual(outputs[0][0][0], outputs[1][0][0])
        self.assertEqual(mysql(f"SELECT COUNT(*) FROM horse WHERE kra_id LIKE '{self.prefix}%';", 'keiba').strip(), '2')

    def test_trainer_is_recorded_at_race_time(self):
        race_id = importer.apply(importer.prepare(self.rows, RETRIEVED))[0][0]
        old_id = request(f'/races/{race_id}')[1]['entries'][0]['trainerId']
        later = sample_rows(race_date='20100201', prefix=self.prefix)
        for row in later:
            row['trNo'] = self.prefix + '5'
            row['trName'] = '가상 다음 조교사'
        later_id = importer.apply(importer.prepare(later, RETRIEVED))[0][0]
        new_id = request(f'/races/{later_id}')[1]['entries'][0]['trainerId']
        self.assertNotEqual(new_id, old_id)
        self.assertEqual(request('/people/' + str(old_id))[1]['totals']['starts'], 2)
        self.assertEqual(request('/people/' + str(new_id))[1]['totals']['starts'], 2)
        self.assertEqual(request('/people/' + str(old_id))[1]['recent'][0]['race_id'], race_id)

    def test_admin_cannot_edit_imported_source_or_run_synthetic_model(self):
        race_id = importer.apply(importer.prepare(self.rows, RETRIEVED))[0][0]
        email = 'kra-test-' + uuid.uuid4().hex + '@example.test'
        body = {'email': email, 'password': 'KraTest-password123', 'nickname': '검증 회원'}
        self.assertEqual(request('/auth/register', 'POST', body)[0], 201)
        token = request('/auth/login', 'POST', body)[1]['token']
        user_id = int(mysql('SELECT id FROM member WHERE email=' + importer.literal(email) + ';', 'keiba'))
        self.addCleanup(lambda: mysql(f'UPDATE member SET is_admin=FALSE WHERE id={user_id};', 'keiba'))
        mysql(f'UPDATE member SET is_admin=TRUE WHERE id={user_id};', 'keiba')
        prediction_status, prediction = request(f'/races/{race_id}/prediction', 'POST', token=token)
        self.assertIn(prediction_status, (200, 503))
        if prediction_status == 200:
            self.assertEqual(prediction['modelKind'], 'real_data_experiment')
        else:
            self.assertIn('실제 데이터 모델', prediction['message'])
        _, rows = request('/admin/races', token=token)
        row = next(row for row in rows if row['id'] == race_id)
        row['name'] = '수정 시도'
        status, _ = request('/admin/races/save', 'POST', {'rows': [row]}, token)
        self.assertEqual(status, 400)
        self.assertEqual(request(f'/races/{race_id}')[1]['race']['name'], '서울 91R · 가상 KRA 검증')


if __name__ == '__main__':
    unittest.main()
