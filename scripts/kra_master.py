#!/usr/bin/env python3
"""한국마사회 기준 자료(말 프로필·3대 혈통·기수/조교사·예정 경주)를 받아 미리보기하거나 로컬 DB에 반영합니다.

  python3 scripts/kra_master.py horses [--hr-no 0038599 ...] [--apply]   # 기본: DB에 있는 한국마사회 말 전체
  python3 scripts/kra_master.py people --meet 1 [--apply]
  python3 scripts/kra_master.py plans --meet 1 [--apply]

API 호출은 사용자 PC에서 이루어지며 원본은 .runtime/kra/ 아래에 보존됩니다. --apply 없이 실행하면 DB를 바꾸지 않습니다.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kra_catalog as kc  # noqa: E402
from kra import KraError, load_key  # noqa: E402
from kra_import import day, identifier, insert, literal, number, text  # noqa: E402

SOURCES = {'horses': 'KRA_API8_2', 'pedigree': 'KRA_API47', 'JOCKEY': 'KRA_API12_1', 'TRAINER': 'KRA_API19_1', 'plans': 'KRA_API72_2'}
MEETS = {'1': '서울', '2': '제주', '3': '부산경남'}
KST = timezone(timedelta(hours=9))
# Generation paths of the pedigree API: f = sire line, m = dam line (confirmed against API8_2 faHrName/moHrName).
PATHS = [p for gen in ((('f1', ''), ('m1', '')),
                       (('f1f2', 'f1'), ('f1m2', 'f1'), ('m1f2', 'm1'), ('m1m2', 'm1')),
                       (('f1f2f3', 'f1f2'), ('f1f2m3', 'f1f2'), ('f1m2f3', 'f1m2'), ('f1m2m3', 'f1m2'),
                        ('m1f2f3', 'm1f2'), ('m1f2m3', 'm1f2'), ('m1m2f3', 'm1m2'), ('m1m2m3', 'm1m2'))) for p in gen]


def collect(api, params, pages=10):
    """한 API를 호출해 원본을 보존하고 (rows, retrieved UTC naive ISO) 를 돌려줍니다."""
    key = load_key()
    rows, pages_raw, total = [], [], None
    for page in range(1, pages + 1):
        raw = kc.request_page(key, api, params, page, 100)
        current_total, batch, actual_page, _ = kc.parse_page(raw)
        if total is not None and total != current_total:
            raise KraError(api + ': 조회 중 전체 건수가 변경됐습니다.')
        total = current_total
        if actual_page != page:
            raise KraError(api + ': 응답 페이지 번호가 다릅니다.')
        pages_raw.append(raw)
        rows.extend(batch)
        if not batch or len(rows) >= total:
            break
    if total is not None and len(rows) < total:
        raise KraError(f'{api}: 전체 {total}건 중 {len(rows)}건만 받았습니다. --pages 한도를 확인하세요.')
    kc.save(api, params, pages_raw, rows, total, True)
    retrieved = datetime.now(timezone.utc)
    return rows, retrieved.replace(tzinfo=None).isoformat(sep=' ')


def kra_num(value):
    return int(identifier({'v': value}, 'v'))


def optional_day(value):
    value = (value or '').strip()
    if value in ('', '-', '0', '00000000') or set(value) == {'*'}:
        return None
    return day(value).isoformat()


def fingerprint(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def clean_name(value):
    value = (value or '').strip()
    return '' if value in ('-', '') or len(value) > 100 or any(ord(c) < 32 for c in value) else value


def profile(row, keys):
    out = {}
    for key in keys:
        value = (row.get(key) or '').strip()
        if value not in ('', '-'):
            out[key] = value
    return out


def tx(statements):
    return '\n'.join(["SET SESSION time_zone='+00:00';",
                      "CREATE TEMPORARY TABLE kra_assertion (ok INT NOT NULL CHECK(ok=1));",
                      "INSERT INTO kra_assertion VALUES (COALESCE(GET_LOCK('kra_master_import',10),0));",
                      'START TRANSACTION;'] + statements + ['COMMIT;', "DO RELEASE_LOCK('kra_master_import');"])


def record(kind, subject, raw, digest, retrieved):
    return ('INSERT INTO kra_master_import(kind,subject,fingerprint,raw_json,retrieved_at) VALUES(' + ','.join(literal(v) for v in (kind, subject, digest, raw, retrieved)) +
            ') AS new ON DUPLICATE KEY UPDATE fingerprint=new.fingerprint,raw_json=new.raw_json,retrieved_at=new.retrieved_at,imported_at=CURRENT_TIMESTAMP(6);')


def run_sql(sql):
    from backup import mysql
    try:
        return mysql(sql, 'keiba')
    except subprocess.CalledProcessError:
        raise KraError('DB 반영을 취소했습니다(전체 롤백). V10 적용 여부와 DB 상태를 확인하세요.') from None


# ---------------------------------------------------------------- horses + pedigree
def db_kra_horses():
    from backup import mysql
    return [line.strip() for line in mysql('SELECT kra_id FROM horse WHERE kra_id IS NOT NULL ORDER BY id;', 'keiba').splitlines() if line.strip()]


def prepare_horse(info, total, pedigree):
    kra = identifier(info, 'hrNo')
    birthday = optional_day(info.get('birthday'))
    sex = text(info, 'sex', 8)
    if sex not in ('수', '암', '거'):
        raise KraError(kra + ': 지원하지 않는 성별 표기입니다.')
    plan = {'kra': kra, 'name': text(info, 'hrName'), 'sex': sex, 'birth': birthday,
            'color': clean_name(total.get('color')) or '미제공', 'origin': clean_name(info.get('name')) or clean_name(total.get('prdCty')) or None,
            'breed': clean_name(total.get('breed')) or None, 'rank': clean_name(info.get('rank')) or None,
            'owner': clean_name(info.get('owName')) or None, 'name_en': clean_name(total.get('hrEngNm')) or None,
            'trainer_name': clean_name(info.get('trName')), 'trainer_no': None,
            'profile': profile(info, ('rcCntT', 'ord1CntT', 'ord2CntT', 'ord3CntT', 'rcCntY', 'ord1CntY', 'ord2CntY', 'ord3CntY', 'chaksunT', 'rating')),
            'parents': {}, 'ancestors': []}
    if clean_name(info.get('trNo')):
        plan['trainer_no'] = identifier(info, 'trNo')
    for field in ('winRate', 'quinRate', 'lchulDt', 'fdebutDt', 'useNm'):
        if clean_name(total.get(field)):
            plan['profile'][field] = total[field].strip()
    for role, no_key, name_key, path in (('sire', 'faHrNo', 'faHrName', 'f1'), ('dam', 'moHrNo', 'moHrName', 'm1')):
        name = clean_name(info.get(name_key)) or clean_name(pedigree.get(path))
        if name:
            plan['parents'][role] = {'kra': identifier(info, no_key) if clean_name(info.get(no_key)) else None, 'name': name}
    present = {'': True, 'f1': 'sire' in plan['parents'], 'm1': 'dam' in plan['parents']}
    for path, parent in PATHS[2:]:
        name = clean_name(pedigree.get(path))
        ok = present.get(parent, False) and bool(name)
        present[path] = ok
        if ok:
            plan['ancestors'].append({'path': path, 'parent': parent, 'name': name})
    raw, digest = fingerprint({'info': info, 'total': {k: total[k] for k in ('color', 'breed', 'hrEngNm', 'prdCty', 'winRate', 'quinRate', 'lchulDt', 'fdebutDt', 'useNm') if k in total}, 'pedigree': pedigree})
    plan['raw'], plan['fingerprint'] = raw, digest
    return plan


def fetch_horse(kra):
    info_rows, retrieved = collect('horse-info', {'hr_no': kra, 'act_gubun': 'n'}, 1)
    info = next((r for r in info_rows if (r.get('hrNo') or '').strip().lstrip('0') == kra.lstrip('0')), None)
    if info is None:
        return None, retrieved
    total_rows, _ = collect('horse-total', {'hr_no': kra}, 1)
    total = total_rows[0] if total_rows else {}
    ped_rows, _ = collect('pedigree-5gen', {'hr_no': kra}, 1)
    pedigree = ped_rows[0] if ped_rows else {}
    return prepare_horse(info, total, pedigree), retrieved


def horse_var(path):
    return '@n_' + (path or 'self')


def ancestor_statements(var, name, sex, source):
    key = literal('KRA:' + name.upper())
    return [f'SET {var}=(SELECT id FROM horse WHERE ancestor_key={key} LIMIT 1);',
            insert('horse', {'name': name, 'sex': sex, 'color': '미제공', 'trainer': '미제공', 'source': source, 'ancestor_key': 'KRA:' + name.upper()}, f'{var} IS NULL'),
            f'SET {var}=(SELECT id FROM horse WHERE ancestor_key={key} LIMIT 1);']


def kra_horse_statements(var, kra, name, sex, source, track=False):
    """제공기관 번호로 말을 찾고, 없으면 같은 이름의 이름 전용 조상 행을 승격하거나 새로 만듭니다."""
    n, key = literal(kra_num(kra)), literal('KRA:' + name.upper())
    return [f'SET {var}=(SELECT id FROM horse WHERE kra_id IS NOT NULL AND CAST(kra_id AS UNSIGNED)={n} LIMIT 1);',
            f'SET {var}=COALESCE({var},(SELECT id FROM horse WHERE ancestor_key={key} LIMIT 1));'] + ([f'SET @created=({var} IS NULL);'] if track else []) + [
            insert('horse', {'name': name, 'sex': sex, 'color': '미제공', 'trainer': '미제공', 'kra_id': kra, 'source': source}, f'{var} IS NULL'),
            f'SET {var}=COALESCE({var},(SELECT id FROM horse WHERE kra_id={literal(kra)} LIMIT 1));',
            f'UPDATE horse SET kra_id={literal(kra)},ancestor_key=NULL WHERE id={var} AND kra_id IS NULL;']


def sql_horses(plans, retrieved):
    statements = []
    for plan in plans:
        self_var = horse_var('')
        statements += kra_horse_statements(self_var, plan['kra'], plan['name'], plan['sex'], SOURCES['horses'], track=True)
        if plan['trainer_no']:
            statements += [insert('person', {'kind': 'TRAINER', 'name': plan['trainer_name'] or '조교사', 'source': SOURCES['horses'], 'kra_id': plan['trainer_no']},
                                  f"NOT EXISTS(SELECT 1 FROM person WHERE kind='TRAINER' AND kra_id IS NOT NULL AND CAST(kra_id AS UNSIGNED)={literal(kra_num(plan['trainer_no']))})"),
                           f"SET @tid=(SELECT id FROM person WHERE kind='TRAINER' AND kra_id IS NOT NULL AND CAST(kra_id AS UNSIGNED)={literal(kra_num(plan['trainer_no']))} LIMIT 1);"]
        else:
            statements.append('SET @tid=NULL;')
        fields = {'name': plan['name'], 'sex': plan['sex'], 'birth_date': plan['birth'], 'color': plan['color'],
                  'trainer': plan['trainer_name'] or '미제공', 'source': SOURCES['horses'], 'name_en': plan['name_en'],
                  'origin': plan['origin'], 'breed': plan['breed'], 'kra_rank': plan['rank'], 'owner_name': plan['owner'],
                  'profile_json': json.dumps(plan['profile'], ensure_ascii=False), 'profile_as_of': retrieved}
        statements.append('UPDATE horse SET ' + ','.join(f'{k}={literal(v)}' for k, v in fields.items()) + f',trainer_id=@tid WHERE id={self_var};')
        for role, path in (('sire', 'f1'), ('dam', 'm1')):
            parent = plan['parents'].get(role)
            var = horse_var(path)
            if not parent:
                statements.append(f'SET {var}=NULL;')
                continue
            sex = '수' if role == 'sire' else '암'
            if parent['kra']:
                statements += kra_horse_statements(var, parent['kra'], parent['name'], sex, SOURCES['pedigree'])
            else:
                statements += ancestor_statements(var, parent['name'], sex, SOURCES['pedigree'])
            statements.append(f'UPDATE horse SET {role}_id={var} WHERE id={self_var};')
        for node in plan['ancestors']:
            var, parent_var = horse_var(node['path']), horse_var(node['parent'])
            sex = '수' if node['path'][-2] == 'f' else '암'
            statements += ancestor_statements(var, node['name'], sex, SOURCES['pedigree'])
            column = 'sire_id' if node['path'][-2] == 'f' else 'dam_id'
            statements.append(f'UPDATE horse SET {column}=COALESCE({column},{var}) WHERE id={parent_var} AND id<>{var};')
        statements += [record('HORSE', plan['kra'], plan['raw'], plan['fingerprint'], retrieved),
                       f"SELECT 'KRA_HORSE',{self_var},COALESCE(@created,1);"]
    return tx(statements)


def command_horses(args):
    targets = [identifier({'v': v}, 'v') for v in args.hr_no] if args.hr_no else db_kra_horses()
    if not targets:
        raise KraError('대상 말이 없습니다. --hr-no 로 마번을 지정하거나 먼저 경주 결과를 반영하세요.')
    if len(targets) > 200:
        raise KraError('한 번에 200두까지만 처리합니다(말당 API 3회 호출).')
    plans, missing, retrieved = [], [], None
    for kra in targets:
        plan, retrieved = fetch_horse(kra)
        (plans if plan else missing).append(plan or kra)
    print(f'말 프로필 {len(plans)}두 준비 (API 호출 {len(plans) * 3 + len(missing)}회), 제공기관에 없는 마번 {len(missing)}건' + (': ' + ', '.join(missing) if missing else ''))
    for plan in plans:
        parents = ' / '.join(f"{role} {p['name']}{' (' + p['kra'] + ')' if p['kra'] else ''}" for role, p in plan['parents'].items())
        print(f"  {plan['kra']} {plan['name']} · {plan['sex']} · {plan['birth'] or '생년월일 미제공'} · {plan['color']} · 조교사 {plan['trainer_name'] or '미제공'} · 조상 {len(plan['ancestors']) + len(plan['parents'])}두 [{parents}]")
    if not plans:
        return
    if not args.apply:
        print('미리보기입니다. DB에 반영하려면 --apply 를 붙이세요.')
        return
    for line in run_sql(sql_horses(plans, retrieved)).splitlines():
        if line.startswith('KRA_HORSE\t'):
            _, hid, created = line.split('\t')
            print(('새 말 등록' if created == '1' else '기존 말 갱신') + f': http://localhost:5173/horses/{hid}')


# ---------------------------------------------------------------- people
def prepare_person(kind, row):
    no_key, name_key = ('jkNo', 'jkName') if kind == 'JOCKEY' else ('trNo', 'trName')
    kra = identifier(row, no_key)
    stats = ('rcCntT', 'ord1CntT', 'ord2CntT', 'ord3CntT', 'rcCntY', 'ord1CntY', 'ord2CntY', 'ord3CntY',
             'winRateT', 'qnlRateT', 'plcRateT', 'winRateY', 'qnlRateY', 'plcRateY', 'wgPart', 'wgOther', 'age')
    plan = {'kind': kind, 'kra': kra, 'name': text(row, name_key), 'meet': clean_name(row.get('meet')) or None,
            'debut': optional_day(row.get('debut') or row.get('stDate')), 'retired': optional_day(row.get('spDate')),
            'affiliation': clean_name(row.get('part'))[:60] or None, 'profile': profile(row, stats)}
    if plan['meet']:
        plan['profile']['meet'] = plan['meet']
    plan['raw'], plan['fingerprint'] = fingerprint(row)
    return plan


def sql_people(plans, retrieved):
    statements = []
    for plan in plans:
        n = literal(kra_num(plan['kra']))
        source = SOURCES[plan['kind']]
        statements += [f"SET @pid=(SELECT id FROM person WHERE kind={literal(plan['kind'])} AND kra_id IS NOT NULL AND CAST(kra_id AS UNSIGNED)={n} LIMIT 1);",
                       'SET @created=(@pid IS NULL);',
                       insert('person', {'kind': plan['kind'], 'name': plan['name'], 'source': source, 'kra_id': plan['kra']}, '@pid IS NULL'),
                       f"SET @pid=COALESCE(@pid,(SELECT id FROM person WHERE kind={literal(plan['kind'])} AND kra_id={literal(plan['kra'])} LIMIT 1));",
                       'UPDATE person SET ' + ','.join(f'{k}={literal(v)}' for k, v in {'name': plan['name'], 'source': source, 'debut_date': plan['debut'], 'retired_date': plan['retired'], 'affiliation': plan['affiliation'], 'profile_json': json.dumps(plan['profile'], ensure_ascii=False), 'profile_as_of': retrieved}.items()) + ' WHERE id=@pid;',
                       record(plan['kind'], plan['kra'], plan['raw'], plan['fingerprint'], retrieved),
                       "SELECT 'KRA_PERSON',@pid,@created;"]
    return tx(statements)


def command_people(args):
    plans, seen, skipped = [], set(), []
    for kind, api in (('JOCKEY', 'jockey-info'), ('TRAINER', 'trainer-info')):
        rows, retrieved = collect(api, {'meet': args.meet}, 20)
        for row in rows:
            try:
                plan = prepare_person(kind, row)
            except KraError as exc:
                # Rows without a usable provider number (blank or non-numeric) cannot be matched, so they are reported and skipped.
                skipped.append(f"{kind} {clean_name(row.get('jkName') or row.get('trName')) or '(이름 없음)'}: {exc}")
                continue
            if (kind, kra_num(plan['kra'])) in seen:
                raise KraError(f'{kind} {plan["kra"]}: 응답에 같은 번호가 두 번 있습니다.')
            seen.add((kind, kra_num(plan['kra'])))
            plans.append(plan)
    jockeys = sum(p['kind'] == 'JOCKEY' for p in plans)
    print(f'{MEETS[args.meet]} 기수 {jockeys}명 · 조교사 {len(plans) - jockeys}명 준비, 번호가 없어 건너뜀 {len(skipped)}건')
    for line in skipped[:10]:
        print('  건너뜀: ' + line)
    if not plans:
        raise KraError('반영할 인물이 없습니다.')
    for plan in plans[:5]:
        print(f"  {plan['kind']} {plan['kra']} {plan['name']} · 데뷔 {plan['debut'] or '미제공'} · 소속 {plan['affiliation'] or '미제공'}")
    if not args.apply:
        print('미리보기입니다. DB에 반영하려면 --apply 를 붙이세요.')
        return
    created = updated = 0
    for line in run_sql(sql_people(plans, retrieved)).splitlines():
        if line.startswith('KRA_PERSON\t'):
            created += line.endswith('\t1'); updated += line.endswith('\t0')
    print(f'반영 완료: 신규 {created}명, 갱신 {updated}명 → http://localhost:5173/people')


# ---------------------------------------------------------------- plans
def prepare_plan(meet, row, today):
    meet_name = MEETS[meet]
    if text(row, 'meet') != meet_name:
        raise KraError('요청한 경마장과 다른 자료가 섞여 있습니다.')
    race_date = day(text(row, 'rcDate', 8))
    race_no = number(row, 'rcNo', 1, 99)
    if race_date < today:
        return None
    start = clean_name(row.get('schStTime'))
    start_time = None
    if re.fullmatch(r'\d{4}', start) and start[:2] < '24' and start[2:] < '60':
        start_time = f'{start[:2]}:{start[2:]}:00'
    prize = profile(row, ('chaksun1', 'chaksun2', 'chaksun3', 'chaksun4', 'chaksun5', 'buga1', 'buga2', 'buga3', 'budam', 'ageCond', 'sexCond', 'ilsu', 'stRating', 'spRating'))
    plan = {'key': f'{meet}:{race_date:%Y%m%d}:{race_no}', 'date': race_date.isoformat(), 'venue': meet_name, 'surface': '더트' if meet == '1' else '미제공',
            'name': f"{meet_name} {race_no}R · {text(row, 'rcName', 120)}", 'distance': number(row, 'rcDist', 800, 4000),
            'class': text(row, 'rank', 60, True) or None, 'start': start_time, 'prize': prize}
    plan['raw'], plan['fingerprint'] = fingerprint(row)
    return plan


def sql_plans(meet, plans, retrieved):
    statements = []
    for plan in plans:
        key = literal(plan['key'])
        statements += [f'SET @rid=(SELECT id FROM race WHERE kra_id={key});', 'SET @created=(@rid IS NULL);',
                       insert('race', {'name': plan['name'], 'race_date': plan['date'], 'venue': plan['venue'], 'distance': plan['distance'],
                                       'surface': plan['surface'], 'start_time': plan['start'], 'race_class': plan['class'], 'status': 'SCHEDULED',
                                       'source': SOURCES['plans'], 'kra_id': plan['key'], 'prize_json': json.dumps(plan['prize'], ensure_ascii=False)}, '@rid IS NULL'),
                       f'SET @rid=(SELECT id FROM race WHERE kra_id={key});',
                       "SET @updated=(SELECT status='SCHEDULED' FROM race WHERE id=@rid);",
                       'UPDATE race SET ' + ','.join(f'{k}={literal(v)}' for k, v in {'name': plan['name'], 'distance': plan['distance'], 'start_time': plan['start'], 'race_class': plan['class'], 'prize_json': json.dumps(plan['prize'], ensure_ascii=False)}.items()) + " WHERE id=@rid AND status='SCHEDULED';",
                       record('PLAN', plan['key'], plan['raw'], plan['fingerprint'], retrieved),
                       "SELECT 'KRA_PLAN',@rid,@created,COALESCE(@updated,0);"]
    return tx(statements)


def command_plans(args):
    rows, retrieved = collect('race-plan', {'meet': args.meet}, 5)
    today = datetime.now(KST).date()
    plans = [p for p in (prepare_plan(args.meet, row, today) for row in rows) if p]
    keys = [p['key'] for p in plans]
    if len(keys) != len(set(keys)):
        raise KraError('응답에 같은 경주가 두 번 있습니다.')
    print(f'{MEETS[args.meet]} 예정 경주 {len(plans)}건 (오늘 이전 {len(rows) - len(plans)}건 제외)')
    for plan in plans[:8]:
        print(f"  {plan['date']} {plan['name']} · {plan['distance']}m · 발주 {plan['start'] or '미제공'} · {plan['class'] or '등급 미제공'}")
    if not args.apply:
        print('미리보기입니다. DB에 반영하려면 --apply 를 붙이세요.')
        return
    created = updated = kept = 0
    for line in run_sql(sql_plans(args.meet, plans, retrieved)).splitlines():
        if line.startswith('KRA_PLAN\t'):
            _, _, c, u = line.split('\t')
            created += c == '1'; updated += c == '0' and u == '1'; kept += c == '0' and u == '0'
    print(f'반영 완료: 신규 {created}건, 갱신 {updated}건, 확정 경주라 유지 {kept}건 → http://localhost:5173/calendar')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('horses', help='말 프로필·모색·부모·3대 혈통 (말당 3회 호출)')
    p.add_argument('--hr-no', nargs='*', default=[], help='마번 (생략하면 DB의 한국마사회 말 전체)')
    for name, help_text in (('people', '기수·조교사 프로필'), ('plans', '한 달 예정 경주')):
        q = sub.add_parser(name, help=help_text)
        q.add_argument('--meet', required=True, choices=sorted(MEETS), help='1 서울 / 2 제주 / 3 부산경남')
    for q in sub.choices.values():
        q.add_argument('--apply', action='store_true', help='검증 후 로컬 DB에 반영 (생략하면 미리보기)')
    args = parser.parse_args()
    try:
        {'horses': command_horses, 'people': command_people, 'plans': command_plans}[args.command](args)
    except (KraError, UnicodeError) as exc:
        print(str(exc) if isinstance(exc, KraError) else '응답 문자 인코딩을 확인하세요.', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'처리 중 오류({type(exc).__name__}). 원본 폴더·DB 상태를 확인하세요.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\n작업을 취소했습니다.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
