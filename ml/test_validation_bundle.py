import copy
import csv
from datetime import date
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import experiment as exp
import validation_bundle as vb
from test_evaluation_extended import rows


def write(path, data):
    flat = [r for race in data.values() for r in race]
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)


class ValidationBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = rows(days=35, races=1)
        cls.report = exp.develop(cls.data, '2025-02-08', 2, 7)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.csv = self.root/'source.csv'; write(self.csv, self.data)
        report = copy.deepcopy(self.report); report['inputHashes'] = {str(self.csv): vb.sha(self.csv)}
        self.report_path = self.root/'report.json'; exp.save(self.report_path, report)
        self.bundle = self.root/'bundle'

    def prepare(self):
        with patch.object(exp, 'today', return_value=date(2025, 2, 10)):
            return vb.prepare(self.report_path, self.bundle, '2025-03-01', '2025-04-01', 'seoul', 'combined')

    def test_snapshot_preserves_training_code_evidence_and_rejects_overwrite(self):
        plan = self.prepare()
        self.assertEqual(vb.verify(self.bundle)['planDigest'], plan['planDigest'])
        saved, _ = exp.read([self.bundle/'training.csv'])
        self.assertEqual(exp.training_digest(saved, '2025-02-08', 'seoul'), plan['trainingDigest'])
        self.csv.unlink()  # Original export can disappear; the bundle stays independently verifiable.
        self.assertEqual(vb.verify(self.bundle)['featureSet'], 'combined')
        self.assertTrue((self.bundle/'code/validation_bundle.py').is_file())
        self.assertFalse(json.loads((self.bundle/'decision.json').read_text())['criteria']['automaticPromotion'])
        before = (self.bundle/'manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'): self.prepare()
        self.assertEqual((self.bundle/'manifest.json').read_bytes(), before)

    def test_changed_source_or_incompatible_report_is_rejected_before_creation(self):
        self.csv.write_text(self.csv.read_text()+'\n')
        with self.assertRaisesRegex(ValueError, 'source CSV changed'): self.prepare()
        self.assertFalse(self.bundle.exists())
        report = json.loads(self.report_path.read_text()); report['modelParameters']['max_depth'] = 99
        self.report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'matching configuration'): self.prepare()

    def test_failed_copy_cleans_only_new_destination(self):
        sentinel = self.root/'keep.txt'; sentinel.write_text('keep')
        with patch.object(vb.shutil, 'copyfile', side_effect=OSError('copy failure')):
            with self.assertRaises(OSError): self.prepare()
        self.assertFalse(self.bundle.exists())
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_verify_rejects_changed_payload_symlink_and_manifest_paths(self):
        self.prepare()
        path = self.bundle/'training.csv'; original = path.read_bytes()
        path.write_bytes(original+b'\n')
        with self.assertRaisesRegex(ValueError, 'payload changed'): vb.verify(self.bundle)
        path.unlink(); path.symlink_to(self.csv)
        with self.assertRaisesRegex(ValueError, 'symlink'): vb.verify(self.bundle)
        path.unlink(); path.write_bytes(original)
        manifest = json.loads((self.bundle/'manifest.json').read_text())
        manifest['files']['../escape'] = '0'*64
        (self.bundle/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'payload list'): vb.verify(self.bundle)

    def test_final_rejects_early_execution_environment_change_and_concurrent_run(self):
        self.prepare()
        with patch.object(exp, 'today', return_value=date(2025, 3, 31)):
            with self.assertRaisesRegex(ValueError, 'not ended'): vb.run_final(self.bundle, [self.csv])
        with patch.object(vb, 'environment', return_value={}):
            with self.assertRaisesRegex(ValueError, 'Environment changed'): vb.run_final(self.bundle, [self.csv])
        lock = self.bundle/'.final-lock'; lock.mkdir()
        with self.assertRaises(FileExistsError): vb.run_final(self.bundle, [self.csv])
        self.assertTrue(lock.exists())
        self.assertFalse((self.bundle/'results').exists())

    def test_final_runs_preserved_code_and_produces_no_promotion(self):
        self.prepare()
        later = self.root/'later.csv'
        write(later, {k: r for k, r in rows(days=90, races=1).items() if r[0]['race_date'] >= date(2025, 2, 8)})
        self.csv.unlink()
        with patch.object(exp, 'final', side_effect=AssertionError('Do not use checkout evaluator')):
            verdict = vb.run_final(self.bundle, [later])
        self.assertFalse(verdict['promoted'])
        result = json.loads((self.bundle/'results/evaluation.json').read_text())
        self.assertEqual(result['window']['cohorts']['seoul']['trainingRaces'], 35)
        self.assertEqual(result['window']['cohorts']['seoul']['testRaces'], 31)
        self.assertFalse((self.bundle/'.final-lock').exists())
        with self.assertRaisesRegex(ValueError, 'already exist'): vb.run_final(self.bundle, [later])
        vb.verify(self.bundle)
        (self.bundle/'results/decision.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Final results changed'): vb.verify(self.bundle)

    def test_failed_final_cleans_partial_outputs_but_preserves_bundle(self):
        self.prepare()
        with patch.object(vb.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'evaluator')):
            with self.assertRaises(subprocess.CalledProcessError): vb.run_final(self.bundle, [self.csv])
        self.assertFalse((self.bundle/'results').exists())
        self.assertFalse((self.bundle/'.final-lock').exists())
        self.assertEqual(list(self.bundle.glob('.final-*')), [])
        vb.verify(self.bundle)

    def test_decision_never_treats_crossing_zero_as_equivalence_or_promotes(self):
        result = {'plan': {'cohort': 'jeju', 'featureSet': 'combined'}, 'window': {'cohorts': {'jeju': {'byTrack': {
            '2': {'variants': {'combined': {'deltaAgainstMarket': {'top3RecallDelta': -.01, 'pairedRaceBootstrap95': [-.08, .02]}}}}
        }}}}}
        self.assertEqual(vb.decision(result, vb.CRITERIA)['decision'], 'do_not_promote')
        delta = result['window']['cohorts']['jeju']['byTrack']['2']['variants']['combined']['deltaAgainstMarket']
        delta.update(top3RecallDelta=.05, pairedRaceBootstrap95=[.01, .09])
        verdict = vb.decision(result, vb.CRITERIA)
        self.assertEqual(verdict['decision'], 'review_only')
        self.assertFalse(verdict['promoted'])


if __name__ == '__main__':
    unittest.main()
