#!/usr/bin/env python3
"""최근 3개월 사이트 전적/API155 학습 자료 수집과 재개. --status로 진행표 확인."""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
import contextlib
import fcntl
import html
import io
import json
import re
from pathlib import Path
import sys
import time
import subprocess

import kra
import kra_import as imp
import kra_ml_dataset as ds

STATE = kra.STATE / 'sync'


class BudgetReached(Exception):
    pass


class Budget:
    def __init__(self, limit):
        self.limit, self.calls = limit, 0

    def take(self):
        if self.calls >= self.limit:
            raise BudgetReached()
        if self.calls:
            time.sleep(.25)
        self.calls += 1


def default_period():
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    month = today.year * 12 + today.month - 1 - 3
    year, m = divmod(month, 12)
    start = date(year, m + 1, min(today.day, calendar.monthrange(year, m + 1)[1]))
    return start, today - timedelta(days=1)


def job_path(start, end, meets):
    return STATE / f'{start:%Y%m%d}-{end:%Y%m%d}-{"".join(sorted(meets))}.json'


def jobs(start, end, meets):
    # Include every date: special weekday meetings must not be silently missed.
    for offset in range((end-start).days+1):
        day = start + timedelta(days=offset)
        for meet in meets:
            yield f'{meet}:{day:%Y%m%d}', meet, day


def save(path, state):
    state['updatedAt'] = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    kra.private_write(path, json.dumps(state, ensure_ascii=False, indent=2))
    lines = ['<!doctype html><html lang="ko"><meta charset="utf-8"><title>경마 자료 수집 현황</title>',
             '<style>body{font:16px sans-serif;max-width:1100px;margin:2rem auto;padding:1rem}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.5rem;text-align:left}pre{white-space:pre-wrap}</style>',
             '<h1>경마 자료 수집 현황</h1><p>사이트 전적과 학습 자료는 별도입니다. 이 파일은 마지막 실행 시점의 기록입니다.</p>',
             '<p>'+html.escape(summary(state))+'</p><p>갱신: '+html.escape(state['updatedAt'])+'</p><table><tr><th>날짜·경마장</th><th>사이트 DB</th><th>학습 원본</th><th>실패·보류</th></tr>']
    for key, task in state['tasks'].items():
        failures = [f"{n}R: {v['error']}" for n,v in task.get('races',{}).items() if v.get('error')]
        failures += [task[k] for k in ('site_error','training_error') if task.get(k)]
        count = sum(v.get('status') == '반영 완료' for v in task.get('races',{}).values())
        cells = [key, task.get('site','대기')+f' ({count}경주 반영)', task.get('training','대기'), ' / '.join(failures)]
        lines.append('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in cells)+'</tr>')
    lines.append('</table><h2>학습 CSV</h2><pre>'+html.escape(json.dumps(state.get('exports',{}),ensure_ascii=False,indent=2))+'</pre><h2>경마장별 평가</h2><p>'+html.escape(state.get('evaluation','평가 실행 전'))+'</p></html>')
    kra.private_write(path.with_suffix('.html'), '\n'.join(lines))


def summary(state):
    tasks = list(state['tasks'].values())
    return (f"날짜×경마장 {len(tasks)}개 / 사이트 완료 {sum(t.get('site') in ('반영 완료','자료 없음') for t in tasks)} / "
            f"학습 수집 완료 {sum(t.get('training') == '수집 완료' for t in tasks)} / "
            f"실패·보류 {sum(t.get('site') in ('실패','보류 있음') or t.get('training') == '실패' for t in tasks)} / "
            f"API 누적 {state.get('calls',0)}회")


def print_issues(state):
    found = False
    for ident, task in state['tasks'].items():
        meet, day = ident.split(':', 1)
        label = f'{day} {kra.MEETS.get(meet, meet)}'
        for kind, title in [('site', '사이트 전적'), ('training', '학습 자료')]:
            if task.get(kind+'_error'):
                print(f"- {label} / {title}: {task[kind+'_error']}")
                found = True
        for race_no, result in task.get('races', {}).items():
            if result.get('error'):
                print(f"- {label} {race_no}R / 보류: {result['error']}")
                field = 'wgHr' if '마체중' in result['error'] else result['error'].split(':', 1)[0]
                if field in ('wgHr', 'ord', 'jkNo', 'trNo', 'rcDist') and task.get('archive'):
                    print_archived_issues(task['archive'], meet, day, race_no, field)
                found = True
    if not found:
        print('기록된 실패·보류 사유가 없습니다.')


def diagnostic_value(value):
    """Only short numeric/Korean field values; exclude keys, URLs and control codes."""
    return repr(value) if re.fullmatch(r'[0-9가-힣()\[\] .,+−–—?/\-]{0,40}', value) else '(비표준 문자 포함: 원문 미출력)'


def identifier_shape(value):
    # Identify foreign-ID formats without printing an unverified identifier or secret.
    if re.fullmatch(r'[A-Za-z0-9]{1,16}', value):
        return ''.join('9' if c.isdigit() else 'A' if c.isupper() else 'a' for c in value)
    return '길이·문자 형식 추가 확인 필요'


def print_archived_issues(directory, meet, day, race_no, field):
    """Inspect allowlisted fields without interpreting non-finisher codes or writing data."""
    try:
        folder = Path(directory)
        if (folder/'summary.json').stat().st_size > kra.MAX_BYTES:
            raise ValueError()
        meta = json.loads((folder/'summary.json').read_text())
        if meta.get('source') != 'KRA_API214_1' or meta.get('filters',{}).get('meet') != meet or meta.get('filters',{}).get('rc_date') != day:
            raise ValueError()
        pages = meta['pages']
        if type(pages) is not int or not 1 <= pages <= 10:
            raise ValueError()
        selected = []
        for page in range(1, pages+1):
            path = folder/f'page-{page}.xml'
            if path.stat().st_size > kra.MAX_BYTES:
                raise ValueError()
            _, rows = kra.parse_page(path.read_text(),page)
            for row in rows:
                if kra.MEET_CODES.get(row.get('meet')) != meet or row.get('rcDate') != day:
                    raise ValueError()
                if row.get('rcNo') != race_no:
                    continue
                selected.append(row)
        if not selected:
            raise ValueError()
        invalid = []
        for row in selected:
            try:
                if field == 'wgHr':
                    kra.parse_body_weight(row.get(field, '').strip())
                elif field == 'ord':
                    imp.result_state(row, len(selected))
                elif field == 'rcDist':
                    imp.number(row, field, 800, 4000)
                elif field in ('jkNo', 'trNo'):
                    imp.identifier(row, field)
                else:
                    raise ValueError()
            except kra.KraError:
                invalid.append(row)
        print(f'  {field} 검증 불통과 {len(invalid)}/{len(selected)}두 (최대 3두 표시)')
        for row in invalid[:3]:
            number = row.get('chulNo','')
            number = number if re.fullmatch(r'[0-9]{1,2}',number) else '?'
            fields = (field, 'ordBigo', 'rcTime') if field == 'ord' else (field,)
            values = ' / '.join(f'{name}={diagnostic_value(row.get(name, ""))}' for name in fields)
            if field in ('jkNo', 'trNo'):
                values += f' / 형식={identifier_shape(row.get(field, ""))} (A=영문 대문자, a=소문자, 9=숫자)'
            print(f'  출전번호 {number} / {values}')
    except (OSError,ValueError,KeyError,kra.KraError):
        print('  원본 필드 확인 불가: 보관 폴더·형식을 확인하세요.')


def site_day(task, meet, day, key, budget, apply, retry):
    if task.get('site') in ('반영 완료','자료 없음'):
        return
    if task.get('site_error') and not retry:
        return
    if not task.get('archive'):
        with contextlib.redirect_stdout(io.StringIO()):
            meta = kra.download(key, {'meet':meet,'rc_date':f'{day:%Y%m%d}'}, 10, before_request=budget.take,
                                page_cache=STATE/'pages'/f'214-{meet}-{day:%Y%m%d}')
        task['archive'] = meta['directory']
    folder = Path(task['archive'])
    meta = json.loads((folder/'summary.json').read_text())
    if meta['filters'] != {'meet':meet,'rc_date':f'{day:%Y%m%d}'} or not meta['complete'] or meta.get('source') != 'KRA_API214_1' or meta.get('endpoint') != kra.ENDPOINT:
        raise kra.KraError('보관 원본의 조회 조건이 다릅니다.')
    if not meta['receivedCount']:
        task['site'] = '자료 없음'; task.pop('site_error',None); return
    grouped = defaultdict(list)
    received = 0
    for page in range(1, meta['pages']+1):
        total, rows = kra.parse_page((folder/f'page-{page}.xml').read_text(), page)
        if total != meta['totalCount'] or len(rows) != min(kra.PAGE_SIZE,max(0,total-received)):
            raise kra.KraError('보관 원본의 페이지 건수가 다릅니다.')
        received += len(rows)
        for row in rows:
            if kra.MEET_CODES.get(row.get('meet')) != meet or row.get('rcDate') != f'{day:%Y%m%d}':
                raise kra.KraError('보관 원본의 경마장·날짜 불일치')
            grouped[row.get('rcNo','')].append(row)
    if received != meta['receivedCount'] or received != meta['totalCount']:
        raise kra.KraError('보관 원본의 전체 건수가 다릅니다.')
    statuses = task.setdefault('races',{})
    for race_no, rows in grouped.items():
        old = statuses.get(race_no,{})
        if old.get('status') == '반영 완료' or (old.get('error') and not retry):
            continue
        try:
            plan = imp.prepare(rows, datetime.fromisoformat(meta['retrievedAt']))
            if apply:
                result = imp.apply(plan)
                statuses[race_no] = {'status':'반영 완료','raceId':result[0][0]}
            else:
                statuses[race_no] = {'status':'검증 완료'}
        except kra.KraError as exc:
            statuses[race_no] = {'status':'보류','error':str(exc)}
    task['site'] = '보류 있음' if any(v.get('error') for v in statuses.values()) else '반영 완료' if apply else '검증 완료(DB 미반영)'
    task.pop('site_error',None)


def training_day(task, meet, day, key, budget, retry):
    if task.get('training_error') and not retry:
        return
    path = ds.day_file(meet,day)
    if not path.exists():
        rows = ds.fetch_day(key,meet,day,before_request=budget.take,page_cache=STATE/'pages'/f'155-{meet}-{day:%Y%m%d}')
        kra.private_write(path,json.dumps({'meet':meet,'date':day.isoformat(),'api':'KRA_API155',
            'retrievedAt':datetime.now(ZoneInfo('UTC')).isoformat(),'rows':rows},ensure_ascii=False))
    cached = json.loads(path.read_text())
    if cached.get('meet') != meet or cached.get('date') != day.isoformat() or cached.get('api') != 'KRA_API155':
        raise kra.KraError('학습 캐시 조회 조건이 다릅니다.')
    task['training'] = '수집 완료'; task['trainingRows'] = len(cached['rows']); task.pop('training_error',None)


def run(args):
    path = job_path(args.start,args.end,args.meets)
    state = json.loads(path.read_text()) if path.exists() else {'tasks':{k:{} for k,_,_ in jobs(args.start,args.end,args.meets)},'calls':0}
    if args.status or args.dry_run:
        print(summary(state)); print('진행표:',path.with_suffix('.html'))
        print('학습 CSV:',json.dumps(state.get('exports',{}),ensure_ascii=False))
        if state.get('evaluation'): print('경마장별 평가:',state['evaluation'])
        print('기간:',args.start,'~',args.end,'/ 경마장:',','.join(args.meets))
        if args.status:
            print_issues(state)
        if args.dry_run: print('계획만 확인했습니다. 호출·DB 변경 없음.')
        return 0
    key = kra.load_key() if args.max_calls else ''
    budget = Budget(args.max_calls)
    previous_calls = state['calls']
    try:
        for ident,meet,day in jobs(args.start,args.end,args.meets):
            task = state['tasks'][ident]
            for kind, action in [('site',site_day),('training',training_day)]:
                try:
                    if kind == 'site': action(task,meet,day,key,budget,args.apply,args.retry_failed)
                    else: action(task,meet,day,key,budget,args.retry_failed)
                except kra.KraError as exc:
                    task[kind] = '실패'; task[kind+'_error'] = str(exc)
                    # API/network errors need operator review, not repeated calls in a loop.
                    raise
                finally:
                    state['lastRunCalls'] = budget.calls
                    state['calls'] = previous_calls + budget.calls
                    save(path,state)
    except BudgetReached:
        print('보관 자료가 없어 중단했습니다. --max-calls 0은 API를 호출하지 않습니다.' if not args.max_calls else
              '이번 실행의 API 호출 한도에 도달했습니다. 같은 명령으로 이어서 받으세요.')
    finally:
        save(path,state)
        print(summary(state)); print('진행표:',path.with_suffix('.html'))
    exports = state.setdefault('exports',{})
    for meet in args.meets:
        tasks = [state['tasks'][ident] for ident,m,_ in jobs(args.start,args.end,args.meets) if m==meet]
        if all(t.get('training') == '수집 완료' for t in tasks):
            target = STATE / 'training' / f'{meet}-{args.start:%Y%m%d}-{args.end:%Y%m%d}.csv'
            try:
                with contextlib.redirect_stdout(io.StringIO()): ds.export(meet,target,start=args.start,end=args.end)
                exports[meet] = {'status':'CSV 준비','path':str(target)}
            except kra.KraError as exc: exports[meet] = {'status':'자료 부족','error':str(exc)}
    save(path,state)
    if args.evaluate:
        files = [exports[m]['path'] for m in args.meets if exports.get(m,{}).get('status') == 'CSV 준비']
        if len(files) != len(args.meets):
            state['evaluation'] = '학습 자료 수집 완료 대기'
        else:
            from refresh_training import python_for_ml
            output = path.with_name(path.stem+'-evaluation.json')
            result = subprocess.run([python_for_ml(),str(kra.ROOT/'ml'/'evaluate_tracks.py'),*files,'--output',str(output)],cwd=kra.ROOT)
            state['evaluation'] = str(output) if result.returncode == 0 else '평가 미완료: 날짜 수·자료 형식을 확인하세요.'
        save(path,state)
    return 0


def main():
    start,end = default_period()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--from',dest='start',type=ds.parse_day,default=start)
    p.add_argument('--to',dest='end',type=ds.parse_day,default=end)
    p.add_argument('--meets',nargs='+',choices=['1','2','3'],default=['1','2','3'])
    p.add_argument('--max-calls',type=int,default=25,help='두 API의 페이지 호출 합계 한도')
    p.add_argument('--apply',action='store_true',help='검증된 경주를 사이트 DB에 반영')
    p.add_argument('--status',action='store_true'); p.add_argument('--dry-run',action='store_true')
    p.add_argument('--retry-failed',action='store_true',help='기록된 실패/보류 재시도')
    p.add_argument('--evaluate',action='store_true',help='학습 수집 완료 시 경마장별 비교 평가 (모델 교체 없음)')
    a=p.parse_args(); a.meets=sorted(set(a.meets))
    if not 0<=a.max_calls<=1000 or a.end<a.start or (a.end-a.start).days>400 or a.end>end:
        p.error('기간은 어제까지, 400일 이내이며 호출 한도는 0~1000입니다(0은 보관 자료만 사용).')
    try:
        if a.status or a.dry_run: return run(a)
        STATE.mkdir(parents=True,exist_ok=True)
        with (STATE/'sync.lock').open('w') as lock:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise kra.KraError('다른 수집 작업이 실행 중입니다.')
            return run(a)
    except (kra.KraError,OSError,ValueError,KeyError) as exc:
        print(str(exc) if isinstance(exc,kra.KraError) else '로컬 상태/원본 파일을 확인하세요.',file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('중단했습니다. 같은 기간 명령으로 보존된 자료부터 재개할 수 있습니다.',file=sys.stderr)
        return 130


if __name__=='__main__': sys.exit(main())
