#!/usr/bin/env python3
"""보류 경주 재조회 → 원본 비교 → 미반영 경주만 명시적 반영. 기존 원본/DB 정정 덮어쓰기 없음."""
import argparse
from collections import defaultdict
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
from pathlib import Path
import sys
import uuid
from zoneinfo import ZoneInfo

import kra
import kra_import as imp
import kra_sync as sync


def read_rows(folder, meet, day, race=None):
    folder = Path(folder)
    meta = json.loads((folder/'summary.json').read_text())
    filters = meta.get('filters', {})
    if (meta.get('source') != imp.SOURCE or meta.get('endpoint') != kra.ENDPOINT or
            meta.get('complete') is not True or filters.get('meet') != meet or filters.get('rc_date') != day):
        raise kra.KraError('원본의 출처·완료 여부·조회 조건이 일치하지 않습니다.')
    retrieved=datetime.fromisoformat(meta['retrievedAt'])
    if retrieved.tzinfo is None or retrieved>datetime.now(timezone.utc) or imp.day(day)>=datetime.now(ZoneInfo('Asia/Seoul')).date():
        raise kra.KraError('원본의 수집 시각·경주일을 확인하세요.')
    total, pages = meta.get('totalCount'), meta.get('pages')
    if (type(total) is not int or not 0 <= total <= 1000 or type(pages) is not int or
            pages != max(1, (total+kra.PAGE_SIZE-1)//kra.PAGE_SIZE) or meta.get('receivedCount') != total):
        raise kra.KraError('원본의 페이지·전체 건수가 맞지 않습니다.')
    rows = []
    for page in range(1, pages+1):
        path = folder/f'page-{page}.xml'
        if path.stat().st_size > kra.MAX_BYTES:
            raise kra.KraError('원본 페이지가 너무 큽니다.')
        count, batch = kra.parse_page(path.read_text(), page)
        if count != total or len(batch) != min(kra.PAGE_SIZE, total-len(rows)):
            raise kra.KraError('원본 페이지 건수가 다릅니다.')
        rows.extend(batch)
    for row in rows:
        if kra.MEET_CODES.get(row.get('meet')) != meet or row.get('rcDate') != day:
            raise kra.KraError('원본의 경마장·날짜가 다릅니다.')
        if filters.get('rc_no') is not None and row.get('rcNo') != str(filters['rc_no']):
            raise kra.KraError('조회 경주번호와 원본이 다릅니다.')
    return meta, [r for r in rows if race is None or r.get('rcNo') == str(race)]


def fingerprint(rows):
    return hashlib.sha256(json.dumps(sorted(rows, key=lambda r:json.dumps(r, sort_keys=True)),
        sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def difference(old, new):
    def values(rows):
        grouped = defaultdict(list)
        for row in rows:
            for field, value in row.items(): grouped[field].append((row.get('chulNo',''),value))
        return {field:sorted(values) for field,values in grouped.items()}
    a,b=values(old),values(new)
    return {'oldRows':len(old),'newRows':len(new),
            'changedFields':sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k))}


def targets(state):
    return [{'task':key,'race':race} for key,task in state['tasks'].items()
            for race,result in task.get('races',{}).items() if result.get('error')]


def check_plan(rows, retrieved):
    if not rows: return '자료 없음', None
    try:
        plan=imp.prepare(rows,datetime.fromisoformat(retrieved))
        if len(plan)!=1: raise kra.KraError('단일 경주가 아닙니다.')
        return '검증 통과',plan
    except kra.KraError as exc:
        return str(exc),None


def fetch(state_path, report_path, max_calls):
    state=json.loads(state_path.read_text())
    if report_path.exists():
        report=json.loads(report_path.read_text())
        if report.get('state')!=str(state_path.resolve()):raise kra.KraError('재조회 보고서의 기간 작업이 다릅니다.')
    else:
        report={'version':1,'state':str(state_path.resolve()),'targets':targets(state),'records':{},'calls':0}
    budget=sync.Budget(max_calls); key=kra.load_key() if max_calls else ''
    def save(): kra.private_write(report_path,json.dumps(report,ensure_ascii=False,indent=2))
    def before_request():
        budget.take();report['calls']+=1;state['calls']=state.get('calls',0)+1
        save();sync.save(state_path,state)
    save()
    try:
        for target in report['targets']:
            ident,race=target['task'],target['race'];token=ident+':'+race
            if token in report['records']:continue
            task=state['tasks'][ident]
            if not task.get('races',{}).get(race,{}).get('error'):continue
            meet,day=ident.split(':')
            old_folder=task['archive']
            _,old=read_rows(old_folder,meet,day,race)
            with contextlib.redirect_stdout(io.StringIO()):
                meta=kra.download(key,{'meet':meet,'rc_date':day,'rc_no':race},10,
                    before_request=before_request,page_cache=report_path.parent/(report_path.stem+'-pages')/token.replace(':','-'))
            new_meta,new=read_rows(meta['directory'],meet,day,race)
            validation,plan=check_plan(new,new_meta['retrievedAt'])
            record={'task':ident,'race':race,'oldArchive':str(old_folder),'newArchive':meta['directory'],
                    'oldHash':fingerprint(old),'newHash':fingerprint(new),'validation':validation,
                    'canApply':plan is not None,'checkedAt':datetime.now(timezone.utc).isoformat(),**difference(old,new)}
            report['records'][token]=record;save()
            print(token,validation,'/ 변경 필드:',', '.join(record['changedFields']) or '없음')
    except sync.BudgetReached:
        print('호출 한도 도달. 같은 --report 경로로 재개하세요.')
    finally:
        save()
        print('비교 보고서:',report_path,'/ 재조회 누적 호출:',report['calls'])
    return report


def apply_report(report_path):
    report=json.loads(report_path.read_text());state_path=Path(report['state']);state=json.loads(state_path.read_text())
    applied=0
    for rec in report['records'].values():
        if not rec.get('canApply'):continue
        task=state['tasks'][rec['task']];current=task['races'][rec['race']]
        if current.get('status')=='반영 완료':
            if current.get('recheckArchive')==rec['newArchive']:continue
            raise kra.KraError('이미 반영된 경주입니다. 재조회로 기존 결과를 덮어쓰지 않습니다.')
        if not current.get('error') or task['archive']!=rec['oldArchive']:
            raise kra.KraError('기존 보류 상태가 변경됐습니다. 다시 비교하세요.')
        meet,day=rec['task'].split(':')
        _,old=read_rows(rec['oldArchive'],meet,day,rec['race'])
        meta,new=read_rows(rec['newArchive'],meet,day,rec['race'])
        if fingerprint(old)!=rec['oldHash'] or fingerprint(new)!=rec['newHash']:
            raise kra.KraError('비교 이후 원본이 변경됐습니다. 반영하지 않습니다.')
        validation,plan=check_plan(new,meta['retrievedAt'])
        if plan is None:raise kra.KraError(validation)
        rid,created=imp.apply(plan)[0]
        task['races'][rec['race']]={'status':'반영 완료','raceId':rid,'recheckArchive':rec['newArchive']}
        task['site']='보류 있음' if any(r.get('error') for r in task['races'].values()) else '반영 완료'
        sync.save(state_path,state);applied+=1
        print(rec['task']+':'+rec['race'],'/ 반영 경주 ID:',rid)
    print('재조회 자료 반영:',applied,'경주 / 기존 원본 보존')


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('plan');p.add_argument('state',type=Path)
    p=commands.add_parser('fetch');p.add_argument('state',type=Path);p.add_argument('--report',type=Path);p.add_argument('--max-calls',type=int,default=5)
    p=commands.add_parser('apply');p.add_argument('report',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='plan':
            selected=targets(json.loads(args.state.read_text()))
            for item in selected:print(item['task']+':'+item['race'])
            print('재조회 대상:',len(selected),'경주 / API 호출·DB 변경 없음');return 0
        sync.STATE.mkdir(parents=True,exist_ok=True)
        with (sync.STATE/'sync.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise kra.KraError('다른 수집/백업 작업이 실행 중입니다.') from None
            if args.command=='apply':apply_report(args.report)
            else:
                if not 0<=args.max_calls<=1000:raise kra.KraError('호출 한도는 0~1000입니다.')
                report=args.report or kra.STATE/'rechecks'/('review-'+uuid.uuid4().hex[:12]+'.json')
                fetch(args.state,report,args.max_calls)
        return 0
    except (kra.KraError,OSError,ValueError,KeyError,TypeError) as exc:
        print(str(exc) if isinstance(exc,kra.KraError) else '재조회 상태·원본·경로를 확인하세요.',file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
