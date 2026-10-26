"""Offline checks for scripts/refresh_training.py: planning, export targets, stop-on-partial, retraining call. No provider calls."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import refresh_training as rt  # noqa: E402
from kra import KraError  # noqa: E402


def args(**kw):
    base = dict(meets=['1', '2'], start=date(2025, 1, 4), end=date(2025, 12, 28), max_calls=100, skip_train=False, dry_run=False)
    return type('A', (), {**base, **kw})


class RefreshTests(unittest.TestCase):
    def test_target_names_and_overlap_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            self.assertEqual(rt.target('2', date(2025, 1, 3), date(2025, 12, 26), data).name, 'jeju-2025.csv')
            self.assertEqual(rt.target('3', date(2025, 1, 3), date(2026, 3, 1), data).name, 'busan-20250103-20260301.csv')
            (data / 'seoul-2024.csv').write_text('x')
            with self.assertRaises(KraError):
                rt.target('1', date(2025, 1, 4), date(2025, 12, 28), data)
            (data / 'seoul-2025.csv').write_text('x')   # same target name only → allowed to refresh in place
            self.assertEqual(rt.target('2', date(2025, 1, 3), date(2025, 12, 26), data).name, 'jeju-2025.csv')

    def test_dry_run_does_nothing(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(rt.ds, 'collect') as collect, \
                mock.patch.object(rt.subprocess, 'run') as run, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rt.run(args(dry_run=True), Path(folder)), 0)
        collect.assert_not_called(); run.assert_not_called()
        self.assertIn('서울→seoul-2025.csv · 제주→jeju-2025.csv', out.getvalue())

    def test_collects_exports_each_meet_then_trains(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); (data / 'PROVENANCE.md').write_text('서울 자료')
            done = mock.Mock(returncode=0)
            with mock.patch.object(rt.ds, 'collect', return_value={'remaining': 0}) as collect, mock.patch.object(rt.ds, 'export') as export, \
                    mock.patch.object(rt.subprocess, 'run', return_value=done) as run, redirect_stdout(io.StringIO()) as out:
                self.assertEqual(rt.run(args(), data), 0)
            self.assertEqual([c.args[0] for c in collect.call_args_list], ['1', '2'])
            self.assertEqual([(c.args[0], Path(c.args[1]).name) for c in export.call_args_list], [('1', 'seoul-2025.csv'), ('2', 'jeju-2025.csv')])
            for call in export.call_args_list:
                self.assertEqual(call.kwargs, {'start': date(2025, 1, 4), 'end': date(2025, 12, 28)})
            self.assertTrue(run.call_args.args[0][1].endswith('train_real.py'))
            self.assertIn('제주 자료 출처', out.getvalue())     # provenance warning for the meet missing in PROVENANCE.md
            self.assertNotIn('서울 자료 출처', out.getvalue())

    def test_partial_collection_stops_before_export_and_training(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(rt.ds, 'collect', return_value={'remaining': 12}), \
                mock.patch.object(rt.ds, 'export') as export, mock.patch.object(rt.subprocess, 'run') as run:
            with self.assertRaises(KraError):
                rt.run(args(), Path(folder))
        export.assert_not_called(); run.assert_not_called()

    def test_skip_train_and_training_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            with mock.patch.object(rt.ds, 'collect', return_value={'remaining': 0}), mock.patch.object(rt.ds, 'export'), \
                    mock.patch.object(rt.subprocess, 'run') as run, redirect_stdout(io.StringIO()):
                self.assertEqual(rt.run(args(meets=['1'], skip_train=True), data), 0)
                run.assert_not_called()
            with mock.patch.object(rt.ds, 'collect', return_value={'remaining': 0}), mock.patch.object(rt.ds, 'export'), \
                    mock.patch.object(rt.subprocess, 'run', return_value=mock.Mock(returncode=1)), redirect_stdout(io.StringIO()):
                with self.assertRaises(KraError):
                    rt.run(args(meets=['1']), data)

    def test_main_reports_errors_without_traceback(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(rt.main(['--from', '20250104', '--to', '20250101', '--dry-run', '--max-calls', '0']), 1)
        self.assertIn('--max-calls', err.getvalue())
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rt.main(['--meets', '3', '3', '--from', '20250103', '--to', '20251226', '--dry-run']), 0)
        self.assertEqual(out.getvalue().count('busan-2025.csv'), 1)   # duplicate meets collapsed

    def test_invalid_period_rejected_even_in_dry_run(self):
        with mock.patch.object(rt.ds, 'collect') as collect:
            for start, end in [(date(2025, 2, 1), date(2025, 1, 1)), (date(2024, 1, 1), date(2025, 12, 31))]:
                with self.assertRaises(KraError):
                    rt.run(args(start=start, end=end, dry_run=True))
            collect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
