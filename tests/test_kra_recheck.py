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
import kra_recheck as r
from test_kra_import import archive,sample_rows


class RecheckTests(unittest.TestCase):
 def fixture(self,root):
  old=root/'old';new=root/'new';old.mkdir();new.mkdir()
  rows=sample_rows();rows[0].update(ord='0',rcTime='0');archive(old,rows);archive(new,sample_rows())
  state=root/'state.json';state.write_text(json.dumps({'calls':602,'tasks':{'1:20100101':{'archive':str(old),'site':'보류 있음','races':{'91':{'error':'ord: 미제공'}}}}}))
  return state,old,new
 def fetch(self,state,new,report):
  def download(*a,**kw):kw['before_request']();return {'directory':str(new)}
  with patch.object(r.kra,'load_key',return_value='unused'),patch.object(r.kra,'download',side_effect=download),contextlib.redirect_stdout(io.StringIO()):
   return r.fetch(state,report,1)
 def test_requery_preserves_old_source_and_applies_only_reviewed_held_race(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);state,old,new=self.fixture(root);before=(old/'page-1.xml').read_bytes();report=root/'review.json'
   result=self.fetch(state,new,report);rec=next(iter(result['records'].values()))
   self.assertTrue(rec['canApply']);self.assertEqual(rec['changedFields'],['ord','rcTime'])
   self.assertEqual((old/'page-1.xml').read_bytes(),before);self.assertEqual(json.loads(state.read_text())['calls'],603)
   with patch.object(r.imp,'apply',return_value=[(123,1)]) as apply,contextlib.redirect_stdout(io.StringIO()):
    r.apply_report(report);r.apply_report(report);apply.assert_called_once()
   self.assertEqual(json.loads(state.read_text())['tasks']['1:20100101']['site'],'반영 완료')
 def test_modified_reviewed_archive_and_already_applied_race_are_rejected(self):
  for change in ('archive','state'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);state,old,new=self.fixture(root);report=root/'review.json';self.fetch(state,new,report)
    if change=='archive':
     rows=sample_rows();rows[0]['winOdds']='8.0';archive(new,rows)
    else:
     data=json.loads(state.read_text());data['tasks']['1:20100101']['races']['91']={'status':'반영 완료','raceId':1};state.write_text(json.dumps(data))
    with patch.object(r.imp,'apply') as apply,self.assertRaises(r.kra.KraError):r.apply_report(report)
    apply.assert_not_called()
 def test_zero_budget_resumes_same_report_without_duplicate_downloads(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);state,old,new=self.fixture(root);report=root/'review.json'
   def blocked(*a,**kw):kw['before_request']();self.fail('budget did not stop')
   with patch.object(r.kra,'download',side_effect=blocked),contextlib.redirect_stdout(io.StringIO()):
    r.fetch(state,report,0)
   self.fetch(state,new,report)
   with patch.object(r.kra,'download') as download,contextlib.redirect_stdout(io.StringIO()):r.fetch(state,report,0)
   download.assert_not_called();self.assertEqual(json.loads(report.read_text())['calls'],1)
 def test_incomplete_or_wrong_scope_archives_cannot_pass(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);state,old,new=self.fixture(root)
   with self.assertRaises(r.kra.KraError):r.read_rows(new,'2','20100101','91')
   meta=json.loads((new/'summary.json').read_text());meta['receivedCount']=1;(new/'summary.json').write_text(json.dumps(meta))
   with self.assertRaises(r.kra.KraError):r.read_rows(new,'1','20100101','91')
