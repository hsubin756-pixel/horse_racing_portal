"""Offline checks for the KRA master-data importer: planning and SQL generation from fixture rows shaped like real probes."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kra_master as km  # noqa: E402
import kra_import as importer  # noqa: E402
from kra import KraError  # noqa: E402

INFO = {'hrNo': '0038599', 'hrName': '허쉬대보', 'sex': '수', 'birthday': '20160322', 'name': '한국', 'rank': '국3', 'rating': '0',
        'trName': '전승규', 'trNo': '070182', 'owName': '박철근', 'owNo': '111042', 'faHrName': '테스타마타', 'faHrNo': '0034428',
        'moHrName': '허쉬틸드', 'moHrNo': '0022400', 'rcCntT': '38', 'ord1CntT': '7', 'ord2CntT': '2', 'ord3CntT': '1',
        'rcCntY': '13', 'ord1CntY': '0', 'ord2CntY': '0', 'ord3CntY': '1', 'chaksunT': '330830000', 'meet': '서울', 'hrLastAmt': '-'}
TOTAL = {'color': '갈색', 'breed': '더러브렛', 'hrEngNm': 'HUSH DAEBO', 'prdCty': '한국', 'winRate': '18.4', 'quinRate': '23.7', 'lchulDt': '20261003', 'useNm': '경주용'}
PEDIGREE = {'hrNo': '0038599', 'hrName': '허쉬대보', 'f1': '테스타마타', 'm1': '허쉬틸드', 'f1f2': 'TAPIT', 'f1m2': 'DIFFICULT',
            'm1f2': '디스틸드', 'm1m2': '미스알루허쉬', 'f1f2f3': 'PULPIT', 'f1f2m3': 'TAP YOUR HEELS', 'f1m2f3': 'CONCERN',
            'f1m2m3': 'WINGS OF JOVE', 'm1f2f3': 'HENNESSY', 'm1f2m3': 'WOOD OF BINN', 'm1m2f3': 'ALWUHUSH', 'm1m2m3': '',
            'f1f2f3f4': 'A.P. INDY'}
JOCKEY = {'jkNo': '080618', 'jkName': '권중석', 'meet': '서울', 'part': '프리기수', 'birthday': '19940704', 'age': '32', 'debut': '20250625',
          'spDate': '-', 'wgPart': '50', 'wgOther': '50', 'rcCntT': '331', 'ord1CntT': '22', 'ord2CntT': '18', 'ord3CntT': '21',
          'rcCntY': '322', 'ord1CntY': '22', 'ord2CntY': '18', 'ord3CntY': '20'}
TRAINER = {'trNo': '070174', 'trName': '강성오', 'meet': '서울', 'part': '9', 'birthday': '19660820', 'age': '60', 'stDate': '20180701',
           'rcCntT': '1905', 'ord1CntT': '233', 'winRateT': '12', 'qnlRateT': '21', 'plcRateT': '31'}
PLAN = {'meet': '서울', 'rcDate': '20261025', 'rcNo': '1', 'ilsu': '83', 'rcDist': '1400', 'rank': '국6등급', 'budam': '별정A', 'rcName': '일반',
        'schStTime': '1035', 'ageCond': '연령오픈', 'sexCond': '성별오픈', 'chaksun1': '16500000', 'chaksun2': '6600000', 'chaksun3': '4200000',
        'chaksun4': '1500000', 'chaksun5': '1200000', 'buga1': '0', 'buga2': '0', 'buga3': '0', 'stRating': '0', 'spRating': '0'}


class HorsePlanTests(unittest.TestCase):
    def test_profile_parents_and_three_generations(self):
        plan = km.prepare_horse(INFO, TOTAL, PEDIGREE)
        self.assertEqual((plan['kra'], plan['name'], plan['birth'], plan['color'], plan['breed'], plan['name_en']),
                         ('0038599', '허쉬대보', '2016-03-22', '갈색', '더러브렛', 'HUSH DAEBO'))
        self.assertEqual(plan['trainer_no'], '070182')
        self.assertEqual(plan['parents']['sire'], {'kra': '0034428', 'name': '테스타마타'})
        self.assertEqual(plan['parents']['dam'], {'kra': '0022400', 'name': '허쉬틸드'})
        paths = [a['path'] for a in plan['ancestors']]
        # 2nd and 3rd generation only; m1m2m3 is blank and 4th generation is not imported.
        self.assertEqual(paths, ['f1f2', 'f1m2', 'm1f2', 'm1m2', 'f1f2f3', 'f1f2m3', 'f1m2f3', 'f1m2m3', 'm1f2f3', 'm1f2m3', 'm1m2f3'])
        self.assertEqual(plan['profile']['rcCntT'], '38')
        self.assertEqual(plan['profile']['winRate'], '18.4')
        self.assertNotIn('hrLastAmt', plan['profile'])

    def test_missing_parent_prunes_its_line_and_masked_birthday_stays_empty(self):
        info = dict(INFO, moHrName='', moHrNo='', birthday='********')
        pedigree = dict(PEDIGREE, m1='')
        plan = km.prepare_horse(info, TOTAL, pedigree)
        self.assertIsNone(plan['birth'])
        self.assertNotIn('dam', plan['parents'])
        self.assertTrue(all(a['path'].startswith('f1') for a in plan['ancestors']))

    def test_rejects_unknown_sex_or_bad_identifier(self):
        with self.assertRaises(KraError):
            km.prepare_horse(dict(INFO, sex='?'), TOTAL, PEDIGREE)
        with self.assertRaises(KraError):
            km.prepare_horse(dict(INFO, hrNo='abc'), TOTAL, PEDIGREE)

    def test_sql_links_parents_by_number_and_ancestors_by_name_without_overwriting(self):
        sql = km.sql_horses([km.prepare_horse(INFO, TOTAL, PEDIGREE)], '2026-10-23 03:00:00')
        self.assertIn("GET_LOCK('kra_master_import'", sql)
        self.assertIn('CAST(kra_id AS UNSIGNED)=38599', sql)
        self.assertIn('CAST(kra_id AS UNSIGNED)=34428', sql)
        self.assertIn('UPDATE horse SET sire_id=@n_f1 WHERE id=@n_self;', sql)
        self.assertIn('UPDATE horse SET dam_id=@n_m1 WHERE id=@n_self;', sql)
        self.assertIn('UPDATE horse SET sire_id=COALESCE(sire_id,@n_f1f2) WHERE id=@n_f1 AND id<>@n_f1f2;', sql)
        self.assertIn('UPDATE horse SET sire_id=COALESCE(sire_id,@n_m1m2f3) WHERE id=@n_m1m2 AND id<>@n_m1m2f3;', sql)
        self.assertNotIn('@n_m1m2m3', sql)
        self.assertIn(importer.literal('KRA:TAPIT'), sql)
        self.assertIn("kind='TRAINER' AND kra_id IS NOT NULL AND CAST(kra_id AS UNSIGNED)=70182", sql)
        self.assertIn("INSERT INTO kra_master_import(kind,subject,fingerprint,raw_json,retrieved_at)", sql)
        self.assertIn("SELECT 'KRA_HORSE',@n_self", sql)
        self.assertTrue(sql.rstrip().endswith("DO RELEASE_LOCK('kra_master_import');"))


class PeopleAndPlanTests(unittest.TestCase):
    def test_person_plan_and_sql(self):
        jockey = km.prepare_person('JOCKEY', JOCKEY)
        self.assertEqual((jockey['kra'], jockey['name'], jockey['debut'], jockey['retired'], jockey['affiliation']), ('080618', '권중석', '2025-06-25', None, '프리기수'))
        self.assertEqual(jockey['profile']['rcCntT'], '331')
        trainer = km.prepare_person('TRAINER', TRAINER)
        self.assertEqual((trainer['debut'], trainer['profile']['winRateT']), ('2018-07-01', '12'))
        sql = km.sql_people([jockey, trainer], '2026-10-23 03:00:00')
        self.assertIn("kind=CONVERT(0x4a4f434b4559 USING utf8mb4) AND kra_id IS NOT NULL AND CAST(kra_id AS UNSIGNED)=80618", sql)
        self.assertIn('debut_date=', sql)
        self.assertEqual(sql.count("SELECT 'KRA_PERSON'"), 2)

    def test_plan_skips_past_days_and_formats_start_time(self):
        today = date(2026, 10, 23)
        plan = km.prepare_plan('1', PLAN, today)
        self.assertEqual((plan['key'], plan['name'], plan['distance'], plan['start'], plan['class']), ('1:20261025:1', '서울 1R · 일반', 1400, '10:35:00', '국6등급'))
        self.assertEqual(plan['prize']['chaksun1'], '16500000')
        self.assertIsNone(km.prepare_plan('1', dict(PLAN, rcDate='20261001'), today))
        self.assertIsNone(km.prepare_plan('1', dict(PLAN, schStTime='-'), today)['start'])
        with self.assertRaises(KraError):
            km.prepare_plan('2', PLAN, today)
        sql = km.sql_plans('1', [plan], '2026-10-23 03:00:00')
        self.assertIn("status='SCHEDULED'", sql)
        self.assertIn('prize_json', sql)
        self.assertIn("SELECT 'KRA_PLAN',@rid,@created", sql)

    def test_result_import_upgrades_planned_race_only_when_untouched(self):
        from test_kra_import import sample_rows, RETRIEVED
        sql = importer.sql_plan(importer.prepare(sample_rows(), RETRIEVED))
        self.assertIn("SET @planned=(SELECT COUNT(*) FROM race r WHERE r.id=@rid AND r.status='SCHEDULED' AND NOT EXISTS(SELECT 1 FROM entry e WHERE e.race_id=r.id) AND NOT EXISTS(SELECT 1 FROM kra_race_import k WHERE k.race_id=r.id));", sql)
        self.assertIn('SET @new_race=(@rid IS NULL OR @planned=1);', sql)
        self.assertIn("WHERE id=@rid AND @planned=1;", sql)
        self.assertIn('WHERE @rid IS NULL;', sql)

    def test_collect_archives_only_complete_downloads(self):
        def page(total, n):
            return ('<response><header><resultCode>00</resultCode></header><body><items><item><jkNo>08061' + str(n) + '</jkNo><jkName>기수</jkName></item></items>'
                    f'<numOfRows>100</numOfRows><pageNo>{n}</pageNo><totalCount>{total}</totalCount></body></response>')
        with mock.patch.object(km, 'load_key', return_value='K' * 32), mock.patch.object(km.kc, 'save') as save:
            with mock.patch.object(km.kc, 'request_page', side_effect=lambda key, api, params, n, size: page(250, n)):
                with self.assertRaises(KraError):
                    km.collect('jockey-info', {'meet': '1'}, 1)
            save.assert_not_called()
            with mock.patch.object(km.kc, 'request_page', side_effect=lambda key, api, params, n, size: page(2, n)):
                rows, retrieved = km.collect('jockey-info', {'meet': '1'}, 5)
        self.assertEqual([r['jkNo'] for r in rows], ['080611', '080612'])
        self.assertRegex(retrieved, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
        save.assert_called_once()

if __name__ == '__main__':
    unittest.main()
