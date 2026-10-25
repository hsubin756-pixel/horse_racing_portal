"""Train the real-data experiment on a generated fixture and exercise /predict/real (no real data, no network)."""
import csv, json, random, tempfile, unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock
from fastapi.testclient import TestClient
import app as service
from train_real import train


def fixture(path, meet='1', seed=7):
    random.seed(seed)
    skill = {h: random.gauss(0, 1) for h in range(1, 120)}
    rows = []
    for d in range(70):
        day = date(2025, 1, 4) + timedelta(days=7 * (d // 2) + d % 2)
        for r in range(1, 4):
            field = random.sample(range(1, 120), 8)
            order = sorted(field, key=lambda h: -(skill[h] + random.gauss(0, 1.5)))
            for rank, h in enumerate(order, 1):
                rows.append({'race_id': f'{meet}:{day:%Y%m%d}:{r}', 'race_date': day.isoformat(), 'horse_id': h, 'distance': 1200, 'finish_position': rank,
                             'jockey': f'J{h % 9}', 'trainer': f'T{h % 5}', 'carried_weight': '56', 'win_odds': str(round(random.uniform(1.5, 40), 1)),
                             'place_odds': '', 'gate': str(rank), 'horse_weight': '480', 'rating': '0', 'sex': '수', 'birth_date': '2020-04-01'})
    with path.open('w', newline='', encoding='utf-8') as sink:
        writer = csv.DictWriter(sink, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


class RealModelTests(unittest.TestCase):
    def test_training_artifacts_and_real_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture(root / 'fixture.csv')
            report = train([str(root / 'fixture.csv')], 'generated fixture; no real racing data', output=root)
            self.assertEqual(report['modelKind'], 'real_data_experiment')
            self.assertEqual(report['cutoffDate'], '2025-08-31')
            self.assertIn('rocAuc', report['holdoutMetrics'])
            history = json.loads((root / 'real-history.json').read_text(encoding='utf-8'))
            self.assertEqual(history['cutoffDate'], report['cutoffDate'])
            self.assertTrue(all(h.startswith(('J:', 'T:')) for h in history['people']))
            real = service.load_real(root)
            with mock.patch.object(service, 'load_real', return_value=real), TestClient(service.app) as client:
                self.assertEqual(client.get('/health').json()['realDataModel']['cutoffDate'], '2025-08-31')
                body = {'raceDate': '2025-10-01', 'distance': 1400, 'horses': [
                    {'horseId': 41, 'kraId': '0000001', 'jockey': 'J1', 'trainer': 'T1', 'carriedWeight': 55.5, 'bodyWeight': 500, 'gate': 2, 'birthDate': '2020-04-01', 'sex': '수'},
                    {'horseId': 42, 'kraId': '9999999'}]}
                result = client.post('/predict/real', json=body).json()
                self.assertEqual(result['modelKind'], 'real_data_experiment')
                self.assertEqual(len(result['scores']), 2)
                known = {s['horseId']: s['knownStarts'] for s in result['scores']}
                self.assertGreater(known[41], 0); self.assertEqual(known[42], 0)
                self.assertTrue(all(0 <= s['score'] <= 1 for s in result['scores']))
                # Histories only count results strictly before the race date.
                earlier = client.post('/predict/real', json=dict(body, raceDate='2025-01-04')).json()
                self.assertEqual({s['horseId']: s['knownStarts'] for s in earlier['scores']}[41], 0)
                self.assertEqual(client.post('/predict/real', json=dict(body, horses=[body['horses'][0]] * 2)).status_code, 422)
                self.assertEqual(client.post('/predict/real', json=dict(body, horses=[{'horseId': 1, 'kraId': 'abc'}])).status_code, 422)
            with mock.patch.object(service, 'load_real', return_value=None), TestClient(service.app) as client:
                self.assertIsNone(client.get('/health').json()['realDataModel'])
                self.assertEqual(client.post('/predict/real', json=body).status_code, 503)

    def test_several_files_are_merged_for_one_holdout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture(root / 'a.csv', '1', 7); fixture(root / 'b.csv', '2', 8)
            report = train([str(root / 'a.csv'), str(root / 'b.csv')], 'generated fixtures; no real racing data', output=root)
            self.assertEqual(report['trainingRaces'], 420)
            self.assertEqual([f['path'] for f in report['dataFiles']], ['a.csv', 'b.csv'])
            self.assertIn('rocAuc', report['holdoutMetrics'])
            fixture(root / 'c.csv', '1', 9)   # same race ids as a.csv
            with self.assertRaises(ValueError):
                train([str(root / 'a.csv'), str(root / 'c.csv')], 'x', output=root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
