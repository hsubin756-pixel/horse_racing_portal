import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from kra_status import publish


class StatusTests(unittest.TestCase):
 def test_only_sanitized_state_is_published_without_secrets_or_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'20260726-20261025-123.json'
   state={'calls':602,'evaluation':'/private/eval.json','service-key':'SECRET',
    'tasks':{'1:20260824':{'archive':'/private/archive','site':'보류 있음','training':'수집 완료',
      'races':{'1':{'error':'ord: 미제공','recheckArchive':'/private/new'},'2':{'error':'https://provider?key=SECRET'}}}}}
   publish(path,state)
   target=root/'dashboard'/path.name;raw=target.read_text()
   self.assertNotIn('SECRET',raw);self.assertNotIn('/private',raw);self.assertNotIn('archive',raw)
   self.assertEqual(json.loads(raw)['calls'],602)
   self.assertEqual(target.stat().st_mode&0o777,0o644)
   self.assertFalse(path.exists())
