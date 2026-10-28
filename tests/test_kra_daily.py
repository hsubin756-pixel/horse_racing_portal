import contextlib
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import kra_daily as daily


class DailyTests(unittest.TestCase):
 def test_existing_task_reuse_and_daily_call_limit_survive_repeated_runs(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(daily.sync,'STATE',Path(tmp)),contextlib.redirect_stdout(io.StringIO()):
   root=Path(tmp);old=root/'20260726-20261025-123.json'
   old.write_text(json.dumps({'calls':602,'tasks':{'1:20261025':{'site':'반영 완료','races':{'1':{'status':'반영 완료'}}}}}))
   def run(args):
    path=daily.sync.job_path(args.start,args.end,args.meets);state=json.loads(path.read_text())
    self.assertEqual(state['tasks']['1:20261025']['site'],'반영 완료')
    state['calls']+=args.max_calls;path.write_text(json.dumps(state));return 0
   with patch.object(daily.sync,'run',side_effect=run) as sync:
    daily.run(date(2026,10,26),7,25,True);daily.run(date(2026,10,26),7,25,True)
    self.assertEqual(sync.call_count,1)
   self.assertEqual(json.loads((root/'daily-20261026.json').read_text())['usedCalls'],25)
   with self.assertRaises(daily.kra.KraError):daily.run(date(2026,10,26),7,100,True)
   job=daily.sync.job_path(date(2026,10,19),date(2026,10,25),['1','2','3'])
   state=json.loads(job.read_text());state['calls']=0;job.write_text(json.dumps(state))
   with self.assertRaises(daily.kra.KraError):daily.run(date(2026,10,26),7,25,True)
 def test_dry_run_does_not_write_or_load_credentials(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(daily.sync,'STATE',Path(tmp)),patch.object(daily.kra,'load_key') as key,contextlib.redirect_stdout(io.StringIO()):
   daily.run(date(2026,10,26),7,25,dry_run=True)
   self.assertEqual(list(Path(tmp).iterdir()),[]);key.assert_not_called()
 def test_failed_run_consumption_counts_toward_next_run(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(daily.sync,'STATE',Path(tmp)),contextlib.redirect_stdout(io.StringIO()):
   def fail(args):
    path=daily.sync.job_path(args.start,args.end,args.meets);state=json.loads(path.read_text());state['calls']=3;path.write_text(json.dumps(state));raise daily.kra.KraError('API 오류')
   with patch.object(daily.sync,'run',side_effect=fail),self.assertRaises(daily.kra.KraError):daily.run(date(2026,10,26),7,5)
   with patch.object(daily.sync,'run',return_value=0) as run:daily.run(date(2026,10,26),7,5)
   self.assertEqual(run.call_args.args[0].max_calls,2)
