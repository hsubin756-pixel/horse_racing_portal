import contextlib
from datetime import date
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import kra_sync as sync
import kra
from test_kra_import import archive, sample_rows
from test_kra import response, KEY
from test_kra_ml_dataset import starter


class SyncTests(unittest.TestCase):
    def test_page_budget_resumes_without_redownloading_first_page(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(kra,'ROOT',Path(tmp)), patch.object(kra,'STATE',Path(tmp)/'archives'), patch.object(sync.time,'sleep'):
            cache=Path(tmp)/'pages'; filters={'meet':'1','rc_date':'20220220'}
            with patch.object(kra,'request_page',side_effect=[response(total=101,count=100)]) as request:
                with self.assertRaises(sync.BudgetReached):
                    kra.download(KEY,filters,10,before_request=sync.Budget(1).take,page_cache=cache)
                self.assertEqual(request.call_count,1)
            with patch.object(kra,'request_page',return_value=response(page=2,total=101,start=101)) as request, contextlib.redirect_stdout(io.StringIO()):
                result=kra.download(KEY,filters,10,before_request=sync.Budget(1).take,page_cache=cache)
                self.assertEqual(request.call_count,1);self.assertEqual(result['receivedCount'],101)

    def test_site_import_is_per_race_and_bad_race_is_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);bad=sample_rows(race_no=92);bad[0]['ordBigo']='주행중지'
            archive(folder,sample_rows()+bad)
            task={'archive':str(folder)}
            with patch.object(sync.imp,'apply',return_value=[(123,1)]) as apply:
                sync.site_day(task,'1',date(2010,1,1),KEY,sync.Budget(1),True,False)
                self.assertEqual(apply.call_count,1)
                self.assertEqual(task['races']['91']['raceId'],123)
                self.assertIn('error',task['races']['92'])
                sync.site_day(task,'1',date(2010,1,1),KEY,sync.Budget(1),True,False)
                self.assertEqual(apply.call_count,1)

    def test_run_resumes_training_and_counts_actual_calls(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);folder=root/'archive';folder.mkdir();archive(folder)
            args=SimpleNamespace(start=date(2010,1,1),end=date(2010,1,1),meets=['1'],max_calls=1,apply=True,retry_failed=False,status=False,dry_run=False,evaluate=False)
            def download(*a,**kw): kw['before_request']();return {'directory':str(folder)}
            def fetch(*a,**kw): kw['before_request']();return [starter(1,g,str(100+g),str(g)) for g in range(1,5)]
            with patch.object(sync,'STATE',root/'sync'),patch.object(sync.ds,'ML_DIR',root/'ml'),patch.object(kra,'load_key',return_value=KEY),patch.object(kra,'download',side_effect=download) as get,patch.object(sync.ds,'fetch_day',side_effect=fetch),patch.object(sync.imp,'apply',return_value=[(123,1)]):
                sync.run(args);sync.run(args)
                state=json.loads(sync.job_path(args.start,args.end,args.meets).read_text())
                self.assertEqual(state['calls'],2);self.assertEqual(get.call_count,1)
                self.assertEqual(state['tasks']['1:20100101']['site'],'반영 완료')
                self.assertEqual(state['tasks']['1:20100101']['training'],'수집 완료')
                self.assertEqual(state['exports']['1']['status'],'CSV 준비')
                self.assertNotIn(KEY,sync.job_path(args.start,args.end,args.meets).with_suffix('.html').read_text())

    def test_dry_run_needs_no_key_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sync,'STATE',Path(tmp)/'state'), patch.object(kra,'load_key') as key, contextlib.redirect_stdout(io.StringIO()):
            args=SimpleNamespace(start=date(2025,1,1),end=date(2025,1,3),meets=['1','2','3'],status=False,dry_run=True)
            sync.run(args);key.assert_not_called();self.assertFalse(sync.STATE.exists())

    def test_status_prints_stage_and_race_errors_without_loading_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sync,'STATE',Path(tmp)), patch.object(kra,'load_key') as key:
            args=SimpleNamespace(start=date(2025,1,1),end=date(2025,1,1),meets=['3'],status=True,dry_run=False)
            path=sync.job_path(args.start,args.end,args.meets)
            state={'calls':25,'tasks':{'3:20250101':{'site':'보류 있음','training':'실패','training_error':'API 호출 실패',
                   'races':{'2':{'error':'착순 불완전'}}}}}
            path.write_text(json.dumps(state))
            before=path.read_bytes();output=io.StringIO()
            with contextlib.redirect_stdout(output):sync.run(args)
            self.assertIn('20250101 부산경남 / 학습 자료: API 호출 실패',output.getvalue())
            self.assertIn('20250101 부산경남 2R / 보류: 착순 불완전',output.getvalue())
            self.assertEqual(path.read_bytes(),before);key.assert_not_called()

    def test_weight_diagnostic_shows_only_invalid_archived_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=sample_rows();rows[0]['wgHr']='480(-)';rows[1]['wgHr']=KEY
            archive(Path(tmp),rows)
            task={'archive':tmp,'races':{'91':{'error':'마체중·증감 표기를 확인하세요.'}}}
            output=io.StringIO()
            with contextlib.redirect_stdout(output):sync.print_issues({'tasks':{'1:20100101':task}})
            self.assertIn("출전번호 1 / wgHr='480(-)'",output.getvalue())
            self.assertIn('원문 미출력',output.getvalue())
            self.assertNotIn(KEY,output.getvalue())
            self.assertNotIn(rows[0]['hrName'],output.getvalue())

    def test_status_diagnoses_rank_distance_and_jockey_without_api_or_writes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sync,'STATE',Path(tmp)/'sync'), patch.object(kra,'load_key') as key, patch.object(kra,'request_page') as request, patch.object(sync.imp,'apply') as apply:
            folder=Path(tmp)/'archive';folder.mkdir()
            rows=sample_rows();rows[0].update(ord='99',ordBigo='주행중지',rcTime='0')
            distance=sample_rows(race_no=92);distance[0]['rcDist']='0'
            jockey=sample_rows(race_no=93);jockey[0]['jkNo']='000000';jockey[1]['jkNo']=KEY
            archive(folder,rows+distance+jockey)
            task={'archive':str(folder),'races':{str(n):{'error':f'{field}: 검증 오류'} for n,field in [(91,'ord'),(92,'rcDist'),(93,'jkNo')]}}
            args=SimpleNamespace(start=date(2010,1,1),end=date(2010,1,1),meets=['1'],status=True,dry_run=False)
            sync.STATE.mkdir();path=sync.job_path(args.start,args.end,args.meets)
            path.write_text(json.dumps({'tasks':{'1:20100101':task}}))
            before={p:p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            output=io.StringIO()
            with contextlib.redirect_stdout(output):sync.run(args)
            text=output.getvalue()
            self.assertIn('ord 검증 불통과 1/2두',text)
            self.assertIn("ord='99' / ordBigo='주행중지' / rcTime='0'",text)
            self.assertIn("rcDist='0'",text);self.assertIn("jkNo='000000'",text)
            self.assertIn('원문 미출력',text);self.assertNotIn(KEY,text)
            self.assertNotIn(rows[0]['hrName'],text)
            self.assertEqual(before,{p:p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()})
            key.assert_not_called();request.assert_not_called();apply.assert_not_called()

    def test_rank_diagnostics_bound_output_and_count_entire_race(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=[dict(sample_rows()[0],chulNo=str(i),ord='0') for i in range(1,7)]
            archive(Path(tmp),rows)
            output=io.StringIO()
            with contextlib.redirect_stdout(output):sync.print_archived_issues(tmp,'1','20100101','91','ord')
            self.assertIn('검증 불통과 6/6두',output.getvalue())
            self.assertEqual(output.getvalue().count('출전번호'),3)

    def test_diagnostics_reject_wrong_row_date_and_missing_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=sample_rows();rows[0].update(rcDate='20100102',ord='99')
            archive(Path(tmp),rows)
            for folder in (tmp,str(Path(tmp)/'missing')):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):sync.print_archived_issues(folder,'1','20100101','91','ord')
                self.assertIn('원본 필드 확인 불가',output.getvalue())
                self.assertNotIn("ord='99'",output.getvalue())


class FailureAndTrainingBudgetTests(unittest.TestCase):
    def test_api155_page_budget_counts_pages_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sync.time,'sleep'):
            cache=Path(tmp)/'pages'
            with patch.object(sync.ds.kc,'request_page',return_value=response(total=101,count=100)) as request:
                with self.assertRaises(sync.BudgetReached):
                    sync.ds.fetch_day(KEY,'1',date(2022,2,20),before_request=sync.Budget(1).take,page_cache=cache)
                self.assertEqual(request.call_count,1)
            with patch.object(sync.ds.kc,'request_page',return_value=response(page=2,total=101,start=101)) as request:
                rows=sync.ds.fetch_day(KEY,'1',date(2022,2,20),before_request=sync.Budget(1).take,page_cache=cache)
                self.assertEqual(len(rows),101);self.assertEqual(request.call_count,1)

    def test_failure_is_saved_and_requires_explicit_retry(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);args=SimpleNamespace(start=date(2010,1,1),end=date(2010,1,1),meets=['1'],max_calls=1,apply=True,retry_failed=False,status=False,dry_run=False,evaluate=False)
            with patch.object(sync,'STATE',root),patch.object(kra,'load_key',return_value=KEY),patch.object(sync,'site_day',side_effect=kra.KraError('API 호출 실패')),patch.object(sync,'training_day') as training:
                with self.assertRaises(kra.KraError):sync.run(args)
                state=json.loads(sync.job_path(args.start,args.end,args.meets).read_text())
                self.assertEqual(state['tasks']['1:20100101']['site_error'],'API 호출 실패')
                training.assert_not_called()
            folder=root/'archive';folder.mkdir();archive(folder)
            task={'archive':str(folder),'site_error':'API 호출 실패'}
            with patch.object(sync.imp,'apply',return_value=[(123,1)]) as apply:
                sync.site_day(task,'1',date(2010,1,1),KEY,sync.Budget(1),True,False);apply.assert_not_called()
                sync.site_day(task,'1',date(2010,1,1),KEY,sync.Budget(1),True,True)
                apply.assert_called_once();self.assertNotIn('site_error',task)

if __name__=='__main__':unittest.main()
