"""Offline API client tests. No service key, Docker, or network required."""
import contextlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kra

KEY = 'TestOnlyKey1234567890+/='
FILTERS = {'meet': '1', 'rc_date': '20220220'}


def response(page=1, total=1, start=1, count=1):
    items = ''.join(f'<item><meet>서울</meet><rcDate>20220220</rcDate>'
                    f'<rcNo>1</rcNo><hrNo>{n:07}</hrNo><winOdds>4.6</winOdds>'
                    '<plcOdds>1.7</plcOdds><seG3fAccTime>36.6</seG3fAccTime>'
                    '<rcTime>75.9</rcTime></item>' for n in range(start, start + count))
    return ('<response><header><resultCode>00</resultCode></header><body>'
            f'<items>{items}</items><pageNo>{page}</pageNo><numOfRows>100</numOfRows>'
            f'<totalCount>{total}</totalCount></body></response>')


class KraTests(unittest.TestCase):
    def test_body_weight_preserves_unknown_change_and_checks_bounds(self):
        for value, expected in [('488()', (488, None)), ('446( )', (446, None)),
                                ('502(0)', (502, 0)), ('502(-2)', (502, -2)), ('502(+2)', (502, 2)),
                                ('', (None, None)), ('-', (None, None)), ('0', (None, None)), ('()', (None, None))]:
            with self.subTest(value=value):
                self.assertEqual(kra.parse_body_weight(value), expected)
        for value in ['488(-)', '488(+)', '488', 'abc', '199()', '801()', '500(+101)', '500(-101)', '(+2)', '(-)', '0()']:
            with self.subTest(value=value), self.assertRaises(kra.KraError):
                kra.parse_body_weight(value)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, value in [('ROOT', self.root), ('STATE', self.root / '.runtime' / 'kra')]:
            p = patch.object(kra, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_encoded_key_and_secure_replacement(self):
        self.assertEqual(kra.normalize_key('  ' + kra.quote(KEY, safe='') + '\n'), KEY)
        target = kra.STATE / 'service-key'
        kra.private_write(target, KEY)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        kra.private_write(target, KEY + 'X')
        self.assertEqual(target.read_text(), KEY + 'X')
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        for invalid in ['', 'https://example.com/?ServiceKey=' + KEY, 'key with spaces']:
            with self.assertRaises(kra.KraError):
                kra.normalize_key(invalid)

    def test_https_request_encodes_key_once_and_redacts_echo(self):
        with patch.object(kra, 'build_opener') as factory:
            reply = factory.return_value.open.return_value.__enter__.return_value
            reply.read.return_value = ('<echo>' + KEY + ' ' + kra.quote(KEY, safe='') + '</echo>').encode()
            raw = kra.request_page(KEY, FILTERS, 1)
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(urlsplit(request.full_url).scheme, 'https')
            params = parse_qs(urlsplit(request.full_url).query)
            self.assertEqual(params['ServiceKey'], [KEY])
            self.assertEqual(params['rc_date'], ['20220220'])
            self.assertNotIn(KEY, raw)
            self.assertNotIn(kra.quote(KEY, safe=''), raw)

    def test_transport_errors_do_not_expose_key(self):
        for error in [URLError(KEY), HTTPError('https://example.com/?key=' + KEY, 403, KEY, {}, None)]:
            with patch.object(kra, 'build_opener') as factory:
                factory.return_value.open.side_effect = error
                with self.assertRaises(kra.KraError) as caught:
                    kra.request_page(KEY, FILTERS, 1)
                self.assertNotIn(KEY, str(caught.exception))
        with self.assertRaises(kra.KraError):
            kra.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://elsewhere/')

    def test_provider_errors_invalid_xml_and_entities(self):
        for xml in [
            '<response><header><resultCode>22</resultCode><resultMsg>' + KEY + '</resultMsg></header></response>',
            '<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>',
            '<html>unavailable</html>', 'not XML', '<!DOCTYPE x [<!ENTITY a "x">]><x>&a;</x>',
        ]:
            with self.assertRaises(kra.KraError) as caught:
                kra.parse_page(xml, 1)
            self.assertNotIn(KEY, str(caught.exception))

    def test_two_pages_preserve_source_fields_and_identifiers(self):
        with patch.object(kra, 'request_page', side_effect=[response(total=101, count=100), response(page=2, total=101, start=101)]), patch.object(kra.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            summary = kra.download(KEY, FILTERS, 10)
        self.assertTrue(summary['complete'])
        self.assertFalse(summary['importedIntoSite'])
        self.assertEqual(summary['receivedCount'], 101)
        folder = next(kra.STATE.glob('results-*'))
        self.assertEqual(len(list(folder.glob('page-*.xml'))), 2)
        total, rows = kra.parse_page((folder / 'page-1.xml').read_text(), 1)
        self.assertEqual(rows[0]['hrNo'], '0000001')
        self.assertEqual(rows[0]['plcOdds'], '1.7')  # No unsupported market interpretation.
        self.assertEqual(rows[0]['seG3fAccTime'], '36.6')
        self.assertNotIn(KEY, (folder / 'summary.json').read_text())
        self.assertEqual(json.loads((folder / 'summary.json').read_text())['totalCount'], total)

    def test_empty_success_and_incomplete_preview_are_explicit(self):
        for total, count, complete in [(0, 0, True), (101, 100, False)]:
            with patch.object(kra, 'request_page', return_value=response(total=total, count=count)), contextlib.redirect_stdout(io.StringIO()):
                summary = kra.download(KEY, FILTERS, 1, preview=True)
            self.assertEqual(summary['complete'], complete)
            self.assertEqual(summary['receivedCount'], count)

    def test_incomplete_changed_duplicate_and_wrong_filter_fail_without_archive(self):
        cases = [
            [response(total=101, count=100)],  # Request budget exhausted.
            [response(total=101, count=100), response(page=2, total=102, start=101, count=2)],
            [response(total=101, count=100), response(page=2, total=101, start=1)],
            [response(total=2, count=1)],
            [response().replace('20220220', '20220221')],
            [response().replace('서울', '제주')],
            [response().replace('<hrNo>0000001</hrNo>', '<hrNo/>')],
            [response(page=2)],
        ]
        for pages in cases:
            with patch.object(kra, 'request_page', side_effect=pages), patch.object(kra.time, 'sleep'):
                with self.assertRaises(kra.KraError):
                    kra.download(KEY, FILTERS, len(pages))
            self.assertFalse(kra.STATE.exists())

    def test_configure_requires_interactive_terminal(self):
        with patch.object(kra.sys.stdin, 'isatty', return_value=False), patch.object(kra.getpass, 'getpass') as prompt:
            with self.assertRaises(kra.KraError):
                kra.configure()
            prompt.assert_not_called()
        with patch.object(kra.sys.stdin, 'isatty', return_value=True), patch.object(kra.getpass, 'getpass', side_effect=kra.getpass.GetPassWarning):
            with self.assertRaises(kra.KraError):
                kra.configure()
        self.assertFalse(kra.STATE.exists())

    def test_mismatched_meet_reports_label_without_saving_or_echoing_secrets(self):
        for label in ['영남', '부산경남 ', '서울', KEY, 'https://example.com/' + KEY, '부산\n경남']:
            with self.subTest(label=label), patch.object(kra, 'request_page', return_value=response().replace('서울', label)):
                with self.assertRaises(kra.KraError) as caught:
                    kra.download(KEY, {**FILTERS, 'meet': '3'}, 1)
                message = str(caught.exception)
                self.assertIn('요청: 3 (부산경남)', message)
                self.assertIn('응답 meet:', message)
                if label in ['영남', '부산경남 ', '서울']:
                    self.assertIn(repr(label), message)
                else:
                    self.assertIn('(미인식 표기)', message)
                self.assertNotIn(KEY, message)
                self.assertFalse(kra.STATE.exists())

    def test_busan_alias_download_preserves_raw_and_rejects_wrong_request(self):
        raw = response().replace('서울', '부경')
        with patch.object(kra, 'request_page', return_value=raw), contextlib.redirect_stdout(io.StringIO()):
            summary = kra.download(KEY, {**FILTERS, 'meet': '3'}, 1)
            self.assertTrue(summary['complete'])
            folder = next(kra.STATE.glob('results-*'))
            self.assertIn('<meet>부경</meet>', (folder / 'page-1.xml').read_text())
            for code in ('1', '2'):
                with self.assertRaises(kra.KraError):
                    kra.download(KEY, {**FILTERS, 'meet': code}, 1)
        duplicate = response(total=2, count=2).replace('서울', '부산경남', 1).replace('서울', '부경').replace('0000002', '0000001')
        with patch.object(kra, 'request_page', return_value=duplicate), self.assertRaisesRegex(kra.KraError, '중복'):
            kra.download(KEY, {**FILTERS, 'meet': '3'}, 1)


if __name__ == '__main__':
    unittest.main()
