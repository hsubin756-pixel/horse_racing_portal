#!/usr/bin/env python3
"""PC 실행용 증분 갱신. 한국 날짜별 호출 상한, 기존 기간 작업 재사용, 모델 자동 교체 없음."""
import argparse
import copy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import fcntl
import json
import re
from types import SimpleNamespace
import sys

import kra
import kra_sync as sync


def seed_known_tasks(start,end,meets):
    state={'tasks':{k:{} for k,_,_ in sync.jobs(start,end,meets)},'calls':0}
    paths=sorted((p for p in sync.STATE.glob('*.json') if re.fullmatch(r'\d{8}-\d{8}-[123]{1,3}\.json',p.name)),
                 key=lambda p:p.stat().st_mtime)
    for path in paths:
        saved=json.loads(path.read_text())
        for key,task in saved.get('tasks',{}).items():
            if key in state['tasks']:state['tasks'][key]=copy.deepcopy(task)
    return state


def run(today,lookback,max_calls,apply=False,dry_run=False):
    start,end=today-timedelta(days=lookback),today-timedelta(days=1)
    path=sync.job_path(start,end,['1','2','3'])
    ledger=sync.STATE/f'daily-{today:%Y%m%d}.json'
    if dry_run:
        state=json.loads(path.read_text()) if path.exists() else seed_known_tasks(start,end,['1','2','3'])
        print('예정 기간:',start,'~',end,'/ 하루 최대 호출:',max_calls)
        print(sync.summary(state));print('계획만 확인했습니다. API 호출·DB·상태 변경 없음.');return 0
    if not path.exists():sync.save(path,seed_known_tasks(start,end,['1','2','3']))
    state=json.loads(path.read_text())
    record=json.loads(ledger.read_text()) if ledger.exists() else {'job':str(path.resolve()),'baselineCalls':state.get('calls',0),'limit':max_calls}
    if record['job']!=str(path.resolve()) or record['limit']!=max_calls:
        raise kra.KraError('오늘 실행한 기간·상한과 다릅니다. 같은 설정으로 재개하세요.')
    used=state.get('calls',0)-record['baselineCalls']
    if used < record.get('usedCalls',0):
        raise kra.KraError('호출 기록이 이전 실행보다 줄었습니다. 상태 파일을 초기화하지 말고 확인하세요.')
    remaining=max(0,max_calls-used)
    kra.private_write(ledger,json.dumps(record,ensure_ascii=False,indent=2))
    if not remaining:
        print('오늘의 자동 갱신 호출 상한에 도달했습니다. 다음 한국 날짜에 다시 실행됩니다.');return 0
    args=SimpleNamespace(start=start,end=end,meets=['1','2','3'],max_calls=remaining,apply=apply,
                         retry_failed=False,status=False,dry_run=False,evaluate=False)
    try:
        result=sync.run(args);record['result']='완료 또는 호출 상한 도달';return result
    except Exception:
        record['result']='실패: 원인 확인 후 재시도 필요';raise
    finally:
        latest=json.loads(path.read_text())
        record['usedCalls']=latest.get('calls',0)-record['baselineCalls']
        record['lastRunAt']=datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
        kra.private_write(ledger,json.dumps(record,ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lookback',type=int,default=7);p.add_argument('--max-calls',type=int,default=25)
    p.add_argument('--apply',action='store_true');p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    if not 1<=args.lookback<=31 or not 1<=args.max_calls<=1000:p.error('기간 1~31일, 호출 상한 1~1000을 사용하세요.')
    try:
        today=datetime.now(ZoneInfo('Asia/Seoul')).date()
        if args.dry_run:return run(today,args.lookback,args.max_calls,args.apply,True)
        sync.STATE.mkdir(parents=True,exist_ok=True)
        with (sync.STATE/'sync.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise kra.KraError('수집·재조회·백업 작업 실행 중입니다. 다음 실행에서 재개하세요.') from None
            return run(today,args.lookback,args.max_calls,args.apply)
    except (kra.KraError,OSError,ValueError,KeyError) as exc:
        print(str(exc) if isinstance(exc,kra.KraError) else '자동 갱신의 상태·경로를 확인하세요.',file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
