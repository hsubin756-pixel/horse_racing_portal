"""Offline checks for the multi-API KRA probe tool; no provider calls, no key."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kra_catalog as kc  # noqa: E402
from kra import KraError  # noqa: E402

ITEMS = ('<response><header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header><body><items>'
         '<item><hrNo>039092</hrNo><hrName>눈빛언약</hrName><birthday>********</birthday><rating></rating></item>'
         '<item><hrNo>039093</hrNo><hrName>둘째</hrName><birthday>20160101</birthday><rating></rating></item>'
         '</items><numOfRows>100</numOfRows><pageNo>1</pageNo><totalCount>2</totalCount></body></response>')
FLAT = ('<response><resultCode>00</resultCode><resultMsg>OK</resultMsg><numOfRows>10</numOfRows><pageNo>1</pageNo>'
        '<totalCount>1</totalCount><hrNo>039092</hrNo><hrNm>눈빛언약</hrNm><color>갈색</color></response>')
ERROR = '<response><header><resultCode>30</resultCode><resultMsg>KEY</resultMsg></header></response>'


class CatalogTests(unittest.TestCase):
    def test_registry_matches_portal_catalog(self):
        self.assertEqual(len(kc.REGISTRY), 36)
        for name, (path, key_name, allowed, required, pid) in kc.REGISTRY.items():
            self.assertTrue(path and not path.startswith('/'), name)
            self.assertIn(key_name, ('ServiceKey', 'serviceKey'), name)
            self.assertTrue(set(required) <= set(allowed), name)
            self.assertTrue(15000000 < pid < 16000000, name)
        self.assertEqual(kc.REGISTRY['race-result'][0], 'API214_1/RaceDetailResult_1')

    def test_parses_item_list_and_flat_body(self):
        total, rows, page, size = kc.parse_page(ITEMS)
        self.assertEqual((total, page, size, len(rows)), (2, 1, 100, 2))
        self.assertEqual(rows[0]['hrNo'], '039092')
        self.assertEqual(rows[1]['rating'], '')
        total, rows, page, size = kc.parse_page(FLAT)
        self.assertEqual((total, len(rows)), (1, 1))
        self.assertEqual(rows[0], {'hrNo': '039092', 'hrNm': '눈빛언약', 'color': '갈색'})

    def test_rejects_provider_error_and_doctype(self):
        with self.assertRaises(KraError) as ctx:
            kc.parse_page(ERROR)
        self.assertIn('30', str(ctx.exception))
        with self.assertRaises(KraError):
            kc.parse_page('<!DOCTYPE x>' + ITEMS)

    def test_summary_masks_birthday_and_reports_empty_fields(self):
        _, rows, _, _ = kc.parse_page(ITEMS)
        text = kc.summarize(rows)
        self.assertIn('birthday = (마스킹)', text)
        self.assertIn('비어 있는 항목: rating', text)
        self.assertEqual(kc.summarize([]), '응답 항목이 없습니다(0건).')

    def test_param_validation_before_any_request(self):
        key = 'A' * 32
        with self.assertRaises(KraError):
            kc.request_page(key, 'horse-info', {'password': 'x'}, 1, 100)
        with self.assertRaises(KraError):
            kc.request_page(key, 'pedigree-5gen', {}, 1, 100)
        with self.assertRaises(KraError):
            kc.parse_params(['hr_no'])
        with self.assertRaises(KraError):
            kc.parse_params(['hr_no=; DROP'])
        self.assertEqual(kc.parse_params(['meet=1', 'hr_no=039092']), {'meet': '1', 'hr_no': '039092'})

    def test_run_saves_rows_without_key_and_stops_when_complete(self):
        calls = []

        def fake_request(key, api, params, page, size):
            calls.append(page)
            return ITEMS.replace('[KEY]', '')
        with mock.patch.object(kc, 'load_key', return_value='SECRETKEY1234567890'), \
                mock.patch.object(kc, 'request_page', side_effect=fake_request), \
                mock.patch.object(kc, 'STATE', Path(__file__).resolve().parent / '.tmp-catalog'), \
                mock.patch('builtins.print'):
            rows = kc.run('horse-info', {'hr_no': '039092'}, 10, 100)
        self.assertEqual(calls, [1])
        self.assertEqual(len(rows), 2)
        folder = next((Path(__file__).resolve().parent / '.tmp-catalog').glob('horse-info-*'))
        saved = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
        self.assertTrue(saved['complete'])
        self.assertEqual(saved['portalId'], 15058115)
        self.assertNotIn('SECRETKEY', (folder / 'page-1.xml').read_text(encoding='utf-8'))
        for path in sorted(folder.glob('*')):
            path.unlink()
        folder.rmdir()
        (Path(__file__).resolve().parent / '.tmp-catalog').rmdir()


if __name__ == '__main__':
    unittest.main()
