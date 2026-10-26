"""Archive diagnostics use synthetic records, never provider calls."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import kra_sectionals as diagnostic
from test_kra_import import archive, sample_rows


class SectionalDiagnosticsTests(unittest.TestCase):
    def test_alias_archive_reports_numeric_fields_without_echoing_other_values(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = sample_rows(meet='부경')
            rows[0].update(buG1fAccTime='62.1', buS1fTime='13.6', buG1fOrd='1', buG8fAccTime='0')
            rows[1].update(buG1fAccTime='63.2', buS1fTime='secret-do-not-print', buG1fOrd='2', buG8fAccTime='0')
            archive(Path(folder), rows, '3')
            output = io.StringIO()
            with redirect_stdout(output):
                diagnostic.report(folder)
            text = output.getvalue()
            self.assertIn('부산경남 · 1200m · 2두', text)
            self.assertIn('buG1fAccTime | 2/0/0/0 | 62.1~63.2 | 62.1, 63.2', text)
            self.assertIn('buS1fTime | 1/0/0/1', text)
            self.assertIn('buG8fAccTime | 0/2/0/0', text)
            self.assertNotIn('secret-do-not-print', text)
            self.assertNotIn(rows[0]['hrName'], text)

    def test_missing_zero_and_non_numeric_are_distinct(self):
        self.assertEqual([diagnostic.numeric(v) for v in (None, '', '-', '0', '13.60', 'NaN', '-1', 'a\nb')],
                         ['없음', '없음', '없음', '0', '13.60', '비숫자', '비숫자', '비숫자'])


if __name__ == '__main__':
    unittest.main()
