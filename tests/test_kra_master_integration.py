"""Real MySQL/API checks for the master-data importer using fixture plans (no provider calls)."""
import json
import random
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from backup import mysql
import kra_master as km
import kra_import as importer
from test_catalog import request
from test_kra_import import sample_rows, RETRIEVED
from test_kra_master import INFO, TOTAL, PEDIGREE, JOCKEY, TRAINER, PLAN

RETRIEVED_SQL = '2026-10-23 03:00:00'


class MasterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.prefix = '96' + str(random.randint(10000, 99999))
        self.names = [f'가상 조상 {self.prefix} {i}' for i in range(16)]
        self.addCleanup(self.cleanup)

    def cleanup(self):
        keys = ','.join(importer.literal('KRA:' + n.upper()) for n in self.names)
        ids = f"SELECT id FROM horse WHERE kra_id LIKE '{self.prefix}%' OR ancestor_key IN ({keys})"
        mysql(f'UPDATE horse SET sire_id=NULL,dam_id=NULL WHERE sire_id IN ({ids}) OR dam_id IN ({ids});'
              f"DELETE FROM kra_master_import WHERE subject LIKE '{self.prefix}%' OR subject LIKE '1:2099%';"
              f'DELETE FROM sectional_marker WHERE entry_id IN (SELECT id FROM entry WHERE horse_id IN ({ids}));'
              f'DELETE FROM sectional WHERE entry_id IN (SELECT id FROM entry WHERE horse_id IN ({ids}));'
              f'DELETE FROM entry WHERE horse_id IN ({ids});'
              f"DELETE FROM horse WHERE kra_id LIKE '{self.prefix}%' OR ancestor_key IN ({keys});"
              f"DELETE FROM person WHERE kra_id LIKE '{self.prefix}%';"
              f"DELETE FROM race_favorite WHERE race_id IN (SELECT id FROM race WHERE kra_id LIKE '1:2099%');"
              f"DELETE FROM kra_race_import WHERE race_id IN (SELECT id FROM race WHERE kra_id LIKE '1:2099%');"
              f"DELETE FROM sectional_marker WHERE entry_id IN (SELECT e.id FROM entry e JOIN race r ON r.id=e.race_id WHERE r.kra_id LIKE '1:2099%');"
              f"DELETE FROM sectional WHERE entry_id IN (SELECT e.id FROM entry e JOIN race r ON r.id=e.race_id WHERE r.kra_id LIKE '1:2099%');"
              f"DELETE FROM entry WHERE race_id IN (SELECT id FROM race WHERE kra_id LIKE '1:2099%');"
              f"DELETE FROM race WHERE kra_id LIKE '1:2099%';", 'keiba')

    def fixture_horse(self):
        info = dict(INFO, hrNo=self.prefix + '1', hrName=self.names[0], faHrNo=self.prefix + '2', faHrName=self.names[1],
                    moHrNo=self.prefix + '3', moHrName=self.names[2], trNo=self.prefix + '9', trName='가상 마스터 조교사')
        pedigree = {'f1': self.names[1], 'm1': self.names[2], 'f1f2': self.names[3], 'f1m2': self.names[4], 'm1f2': self.names[5], 'm1m2': self.names[6],
                    'f1f2f3': self.names[7], 'f1f2m3': self.names[8], 'f1m2f3': self.names[9], 'f1m2m3': self.names[10],
                    'm1f2f3': self.names[11], 'm1f2m3': self.names[12], 'm1m2f3': self.names[13], 'm1m2m3': self.names[14]}
        return km.prepare_horse(info, TOTAL, pedigree)

    def test_horse_profile_parents_and_three_generations_are_visible(self):
        plan = self.fixture_horse()
        out = mysql(km.sql_horses([plan], RETRIEVED_SQL), 'keiba')
        line = next(l for l in out.splitlines() if l.startswith('KRA_HORSE\t'))
        horse_id, created = line.split('\t')[1:]
        self.assertEqual(created, '1')
        status, horse = request('/horses/' + horse_id)
        self.assertEqual(status, 200)
        self.assertEqual((horse['color'], horse['breed'], horse['nameEn'], horse['kraRank'], horse['ownerName'], horse['source']), ('갈색', '더러브렛', 'HUSH DAEBO', '국3', '박철근', 'KRA_API8_2'))
        self.assertEqual(horse['sire']['name'], self.names[1])
        self.assertEqual(horse['dam']['name'], self.names[2])
        self.assertEqual(horse['profile']['rcCntT'], '38')
        self.assertFalse(horse['ancestorOnly'])
        _, tree = request('/horses/' + horse_id + '/pedigree')
        self.assertEqual(tree['sire']['sire']['sire']['name'], self.names[7])
        self.assertEqual(tree['dam']['dam']['dam']['name'], self.names[14])
        self.assertIsNone(tree['sire']['sire']['sire']['sire'])
        _, grand = request('/horses/' + str(tree['sire']['sire']['id']))
        self.assertTrue(grand['ancestorOnly'])
        self.assertIsNone(grand['birthDate'])
        # Re-running the same plan updates in place: no duplicate rows, same ids, nothing re-created.
        out = mysql(km.sql_horses([plan], RETRIEVED_SQL), 'keiba')
        self.assertIn(f'KRA_HORSE\t{horse_id}\t0', out)
        count = mysql(f"SELECT COUNT(*) FROM horse WHERE kra_id LIKE '{self.prefix}%' OR ancestor_key LIKE '%{self.prefix}%';", 'keiba').strip()
        self.assertEqual(count, '15')
        # Importing the dam by her own number promotes the number-keyed row and keeps the existing link.
        dam_info = dict(INFO, hrNo=self.prefix + '3', hrName=self.names[2], sex='암', faHrNo='', faHrName=self.names[5], moHrNo='', moHrName=self.names[6], trNo='', trName='')
        out = mysql(km.sql_horses([km.prepare_horse(dam_info, TOTAL, {})], RETRIEVED_SQL), 'keiba')
        dam_id = next(l for l in out.splitlines() if l.startswith('KRA_HORSE\t')).split('\t')[1]
        self.assertEqual(int(dam_id), horse['dam']['id'])
        self.assertEqual(mysql(f"SELECT COUNT(*) FROM horse WHERE kra_id LIKE '{self.prefix}%' OR ancestor_key LIKE '%{self.prefix}%';", 'keiba').strip(), '15')
        # Imported rows are locked for the web admin like other provider data.
        self.assertEqual(mysql(f"SELECT COUNT(*) FROM horse WHERE id={tree['sire']['sire']['id']} AND (kra_id IS NOT NULL OR source LIKE 'KRA_%');", 'keiba').strip(), '1')

    def test_people_profiles_are_upserted_and_visible(self):
        jockey = km.prepare_person('JOCKEY', dict(JOCKEY, jkNo=self.prefix + '5', jkName='가상 마스터 기수'))
        trainer = km.prepare_person('TRAINER', dict(TRAINER, trNo=self.prefix + '6', trName='가상 마스터 조교사'))
        out = mysql(km.sql_people([jockey, trainer], RETRIEVED_SQL), 'keiba')
        lines = [l.split('\t') for l in out.splitlines() if l.startswith('KRA_PERSON\t')]
        self.assertEqual([l[2] for l in lines], ['1', '1'])
        status, profile = request('/people/' + lines[0][1])
        self.assertEqual(status, 200)
        person = profile['person']
        self.assertEqual((person['name'], person['affiliation'], str(person['debut_date'])[:10], person['source']), ('가상 마스터 기수', '프리기수', '2025-06-25', 'KRA_API12_1'))
        self.assertEqual(json.loads(person['profile_json'])['rcCntT'], '331')
        out = mysql(km.sql_people([jockey], RETRIEVED_SQL), 'keiba')
        self.assertIn(f'KRA_PERSON\t{lines[0][1]}\t0', out)

    def test_planned_race_is_upgraded_by_the_result_import_keeping_its_id(self):
        plan = km.prepare_plan('1', dict(PLAN, rcDate='20990101', rcNo='91'), date(2026, 1, 1))
        out = mysql(km.sql_plans('1', [plan], RETRIEVED_SQL), 'keiba')
        race_id = next(l for l in out.splitlines() if l.startswith('KRA_PLAN\t')).split('\t')[1]
        status, detail = request('/races/' + race_id)
        self.assertEqual(status, 200)
        self.assertEqual((detail['race']['status'], detail['race']['source'], detail['race']['startTime'], detail['entries']), ('SCHEDULED', 'KRA_API72_2', '10:35:00', []))
        # Second plan run only updates the scheduled race.
        out = mysql(km.sql_plans('1', [km.prepare_plan('1', dict(PLAN, rcDate='20990101', rcNo='91', rcDist='1800'), date(2026, 1, 1))], RETRIEVED_SQL), 'keiba')
        self.assertIn(f'KRA_PLAN\t{race_id}\t0\t1', out)
        self.assertEqual(request('/races/' + race_id)[1]['race']['distance'], 1800)
        # Results for the same race key upgrade the planned row instead of rejecting it.
        rows = sample_rows(race_no=91, race_date='20990101', prefix=self.prefix)
        races = importer.prepare(rows, RETRIEVED)
        self.assertEqual(races[0]['key'], '1:20990101:91')
        result_id, created = importer.apply(races)[0]
        self.assertEqual((str(result_id), created), (race_id, 1))
        _, detail = request('/races/' + race_id)
        self.assertEqual((detail['race']['status'], detail['race']['source'], len(detail['entries'])), ('OFFICIAL', 'KRA_API214_1', 2))
        self.assertEqual(importer.apply(races), [(result_id, 0)])
        # A later plan run must not touch the official race.
        out = mysql(km.sql_plans('1', [plan], RETRIEVED_SQL), 'keiba')
        self.assertIn(f'KRA_PLAN\t{race_id}\t0\t0', out)


if __name__ == '__main__':
    unittest.main()
