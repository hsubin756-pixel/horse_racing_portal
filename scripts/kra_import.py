#!/usr/bin/env python3
"""검증된 완료 경주 원본(서울·제주·부산경남)을 미리보기 또는 로컬 DB에 최초 반영합니다."""
import argparse
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from kra import ENDPOINT, MAX_BYTES, PAGE_SIZE, MEETS, MEET_CODES, KraError, parse_page

SOURCE = 'KRA_API214_1'


def sectionals(row, meet, distance, field, finish, finish_time):
    """Store elapsed time from start; Jeju G times are remaining section times.

    Shared distances (e.g. Jeju 800m S1F/G3F) merge missing values, never
    discard a conflicting rank/time. Zero is unavailable, not a recorded time.
    """
    points = {}

    def add(where, time_key, rank_key, remaining=False):
        seconds = number(row, time_key, Decimal('.01'), finish_time, True, 2)
        position = number(row, rank_key, 1, field, True)
        if seconds is None and position is None:
            return
        if not 0 < where < distance:
            raise KraError(f'{time_key}: 경주 거리 밖의 구간 기록입니다.')
        if remaining and seconds is not None:
            seconds = finish_time - seconds
        if seconds is not None and not 0 < seconds < finish_time:
            raise KraError(f'{time_key}: 누적 시간이 올바르지 않습니다.')
        old_position, old_seconds = points.get(where, (None, None))
        if any(a is not None and b is not None and a != b for a, b in ((old_position, position), (old_seconds, seconds))):
            raise KraError('동일 거리의 구간 기록이 충돌합니다.')
        points[where] = (old_position if old_position is not None else position,
                         old_seconds if old_seconds is not None else seconds)

    if meet == '1':
        add(200, 'seS1fAccTime', 'sjS1fOrd')
        for furlongs in (3, 1):
            add(distance - furlongs * 200, f'seG{furlongs}fAccTime', f'sjG{furlongs}fOrd')
    elif meet == '2':
        add(200, 'jeS1fTime', 'sjS1fOrd')
        for furlongs in (3, 1):
            add(distance - furlongs * 200, f'jeG{furlongs}fTime', f'sjG{furlongs}fOrd', remaining=True)
    elif meet == '3':
        add(200, 'buS1fAccTime', 'buS1fOrd')
        for furlongs in (8, 6, 4, 3, 2, 1):
            add(distance - furlongs * 200, f'buG{furlongs}fAccTime', f'buG{furlongs}fOrd')
        for furlongs in (3, 2, 1):
            remaining = number(row, f'bu_{furlongs}fGTime', Decimal('.01'), finish_time, True, 2)
            elapsed = points.get(distance - furlongs * 200, (None, None))[1]
            if remaining is not None and elapsed is not None and remaining + elapsed != finish_time:
                raise KraError('부산경남 구간 시간과 누적 시간이 일치하지 않습니다.')
    points[distance] = (finish, finish_time)
    previous = Decimal('0')
    for _, (_, seconds) in sorted(points.items()):
        if seconds is not None:
            if seconds <= previous:
                raise KraError('거리별 누적 시간이 증가하지 않습니다.')
            previous = seconds
    corners = []
    previous = Decimal('0')
    # Jeju 3C/4C elapsed times verified against 800m response. Nonzero
    # Jeju 1C/2C times remain in raw_json pending evidence from longer races.
    for corner in (range(1, 5) if meet == '1' else (3, 4) if meet == '2' else ()):
        key = f'se_{corner}cAccTime' if meet == '1' else f'je_{corner}cTime'
        seconds = number(row, key, Decimal('.01'), finish_time, True, 2)
        position = number(row, f'sj_{corner}cOrd', 1, field, True)
        if seconds is not None:
            if seconds <= previous or seconds >= finish_time:
                raise KraError('코너 누적 시간이 올바르지 않습니다.')
            previous = seconds
        if seconds is not None or position is not None:
            corners.append((corner, position, seconds))
    return points, corners


def text(row, key, max_length=100, optional=False):
    value = row.get(key, '').strip()
    if (not value and not optional) or len(value) > max_length or any(ord(c) < 32 for c in value):
        raise KraError(f'{key}: 필수값·길이·문자 형식을 확인하세요.')
    return value


def number(row, key, low, high, optional=False, places=0):
    value = row.get(key, '').strip()
    if optional and value in ('', '-', '0', '0.0', '0.00'):
        return None
    try:
        result = Decimal(value)
        if not result.is_finite() or not low <= result <= high or result != result.quantize(Decimal(10) ** -places):
            raise ValueError()
        return int(result) if places == 0 else result
    except (InvalidOperation, ValueError):
        raise KraError(f'{key}: 지원 범위를 벗어나거나 해석할 수 없는 숫자입니다.') from None


def identifier(row, key):
    value = text(row, key, 16)
    if not re.fullmatch(r'\d{1,16}', value) or int(value) == 0:
        raise KraError(f'{key}: 제공기관 식별번호를 확인하세요.')
    return value


def day(value):
    try:
        if not re.fullmatch(r'\d{8}', value):
            raise ValueError()
        return datetime.strptime(value, '%Y%m%d').date()
    except ValueError:
        raise KraError('경주일 또는 생년월일 형식을 확인하세요.') from None


def load_archive(folder):
    folder = Path(folder)
    meta_path = folder / 'summary.json'
    if meta_path.stat().st_size > MAX_BYTES:
        raise KraError('요약 파일이 너무 큽니다.')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    if meta.get('source') != SOURCE or meta.get('endpoint') != ENDPOINT or meta.get('complete') is not True:
        raise KraError('완료된 API214_1 다운로드만 반영할 수 있습니다.')
    filters = meta.get('filters', {})
    if filters.get('meet') not in MEETS:
        raise KraError('지원하는 경마장은 서울(1)·제주(2)·부산경남(3)입니다.')
    if day(filters.get('rc_date', '')) >= datetime.now(timezone(timedelta(hours=9))).date():
        raise KraError('완료 여부 검증을 위해 오늘 이전 경주만 반영합니다.')
    try:
        retrieved = datetime.fromisoformat(meta['retrievedAt'])
        if retrieved.tzinfo is None or retrieved > datetime.now(timezone.utc):
            raise ValueError()
    except (KeyError, ValueError):
        raise KraError('수집 시각에 시간대 정보가 없거나 올바르지 않습니다.') from None
    pages, total = meta.get('pages'), meta.get('totalCount')
    if type(pages) is not int or not 1 <= pages <= 10 or type(total) is not int or not 1 <= total <= 1000:
        raise KraError('반영할 자료가 없거나 페이지·전체 건수가 올바르지 않습니다.')
    if meta.get('receivedCount') != total or pages != (total + PAGE_SIZE - 1) // PAGE_SIZE:
        raise KraError('전체 다운로드 건수가 맞지 않습니다.')
    rows = []
    for page in range(1, pages + 1):
        path = folder / f'page-{page}.xml'
        if path.stat().st_size > MAX_BYTES:
            raise KraError('원본 파일이 너무 큽니다.')
        count, batch = parse_page(path.read_text(encoding='utf-8'), page)
        if count != total or len(batch) != min(PAGE_SIZE, total - len(rows)):
            raise KraError('원본 페이지의 전체 건수가 맞지 않습니다.')
        rows.extend(batch)
    for row in rows:
        if MEET_CODES.get(row.get('meet')) != filters['meet'] or row.get('rcDate') != filters['rc_date']:
            raise KraError('요청한 경마장·날짜와 원본이 다릅니다.')
        if 'rc_no' in filters and str(number(row, 'rcNo', 1, 99)) != str(filters['rc_no']):
            raise KraError('요청한 경주번호와 원본이 다릅니다.')
    return prepare(rows, retrieved)


def prepare(rows, retrieved):
    groups = defaultdict(list)
    for row in rows:
        if text(row, 'meet') not in MEET_CODES:
            raise KraError('서울·제주·부산경남 원본만 지원합니다.')
        groups[(MEET_CODES[row['meet']], text(row, 'rcDate'), number(row, 'rcNo', 1, 99))].append(row)
    races = []
    for (meet, race_day, race_no), raw in sorted(groups.items()):
        first, field = raw[0], len(raw)
        if not 2 <= field <= 30:
            raise KraError('한 경주의 전체 출전 자료(2~30두)가 필요합니다.')
        race_date = day(race_day)
        distance = number(first, 'rcDist', 800, 4000)
        common = ('rcDist', 'rcName', 'rank', 'weather', 'track')
        if any(any(r.get(k, '') != first.get(k, '') for k in common) for r in raw):
            raise KraError('같은 경주의 거리·등급·날씨 정보가 일치하지 않습니다.')
        race = {'key': f'{meet}:{race_day}:{race_no}', 'date': race_date.isoformat(), 'meet': meet, 'venue': MEETS[meet],
                'surface': '더트' if meet == '1' else '미제공',
                'name': f"{MEETS[meet]} {race_no}R · {text(first, 'rcName', 120)}", 'distance': distance,
                'class': text(first, 'rank', 60, True), 'weather': text(first, 'weather', 30, True),
                'going': text(first, 'track', 30, True), 'entries': []}
        horses, numbers = set(), set()
        for r in raw:
            horse = identifier(r, 'hrNo')
            num = number(r, 'chulNo', 1, 30)
            if horse in horses or num in numbers:
                raise KraError('동일 경주에서 말 또는 출전번호가 중복됐습니다.')
            horses.add(horse); numbers.add(num)
            finish = number(r, 'ord', 1, field)
            if text(r, 'ordBigo', 30, True) not in ('', '-'):
                raise KraError('순위비고가 있는 경주입니다. 취소·중지·실격 등의 의미 확인 후 반영해야 합니다.')
            birthday = day(text(r, 'birthday', 8))
            if not date(1980, 1, 1) <= birthday < race_date:
                raise KraError('말의 생년월일과 경주일을 확인하세요.')
            sex = text(r, 'sex', 8)
            if sex not in ('수', '암', '거'):
                raise KraError('지원하지 않는 성별 표기입니다.')
            finish_time = number(r, 'rcTime', 1, 1000, places=2)
            weight = text(r, 'wgHr', 30, True)
            body = change = None
            if weight not in ('', '-', '0'):
                match = re.fullmatch(r'(\d+)\s*\(\s*([+-]?\d+)\s*\)', weight)
                if not match:
                    raise KraError('마체중·증감 표기를 확인하세요.')
                body, change = map(int, match.groups())
                if not 200 <= body <= 800 or not -100 <= change <= 100:
                    raise KraError('마체중·증감이 지원 범위를 벗어났습니다.')
            points, corners = sectionals(r, meet, distance, field, finish, finish_time)
            race['entries'].append({'horse': horse, 'name': text(r, 'hrName'), 'sex': sex,
                'birth': birthday.isoformat(), 'number': num, 'finish': finish, 'time': finish_time,
                'jockey': identifier(r, 'jkNo'), 'jockey_name': text(r, 'jkName'),
                'trainer': identifier(r, 'trNo'), 'trainer_name': text(r, 'trName'),
                'carried': number(r, 'wgBudam', 30, 80, True, 1), 'body': body, 'change': change,
                'odds': number(r, 'winOdds', 1, 999999, True, 1), 'points': points, 'corners': corners})
        # Competition ranks allow ties (1,1,3), but reject a missing winner/finisher.
        finishes = sorted(e['finish'] for e in race['entries'])
        for index, finish in enumerate(finishes):
            if finish != index + 1 and (index == 0 or finish != finishes[index - 1]):
                raise KraError('착순이 완전하지 않습니다. 전체 경주 결과를 다시 받아 확인하세요.')
        race['entries'].sort(key=lambda e: e['number'])
        race['raw'] = json.dumps(sorted(raw, key=lambda r: int(r['chulNo'])), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        race['fingerprint'] = hashlib.sha256(race['raw'].encode()).hexdigest()
        race['retrieved'] = retrieved.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=' ')
        races.append(race)
    return races


def literal(value):
    if value is None:
        return 'NULL'
    if isinstance(value, (int, Decimal)):
        return str(value)
    return "CONVERT(0x" + str(value).encode().hex() + " USING utf8mb4)" if str(value) else "''"


def insert(table, data, condition='@new_race=1'):
    # Table/column identifiers are code constants. Values are UTF-8 hex or validated numbers.
    return f"INSERT INTO {table} ({','.join(data)}) SELECT {','.join(literal(v) for v in data.values())} WHERE {condition};"


def sql_plan(races, refresh_sectionals=False):
    statements = ["SET SESSION time_zone='+00:00';",
        "CREATE TEMPORARY TABLE kra_assertion (ok INT NOT NULL CHECK(ok=1));",
        "INSERT INTO kra_assertion VALUES (COALESCE(GET_LOCK('kra_result_import',10),0));",
        'START TRANSACTION;']
    for race in races:
        key, fingerprint = literal(race['key']), literal(race['fingerprint'])
        # A race pre-registered from the plan API (SCHEDULED, no entries, no result import) is upgraded in place so saved
        # favorites keep their id; any other existing race must carry the identical result fingerprint.
        statements += [f'SET @rid=(SELECT id FROM race WHERE kra_id={key});',
            "SET @planned=(SELECT COUNT(*) FROM race r WHERE r.id=@rid AND r.status='SCHEDULED' AND NOT EXISTS(SELECT 1 FROM entry e WHERE e.race_id=r.id) AND NOT EXISTS(SELECT 1 FROM kra_race_import k WHERE k.race_id=r.id));",
            'SET @new_race=(@rid IS NULL OR @planned=1);',
            f'INSERT INTO kra_assertion VALUES (IF(@new_race=1,1,EXISTS(SELECT 1 FROM kra_race_import WHERE race_id=@rid AND fingerprint={fingerprint})));',
            insert('race', {'name': race['name'], 'race_date': race['date'], 'venue': race['venue'],
                'distance': race['distance'], 'surface': race['surface'], 'race_class': race['class'],
                'weather': race['weather'], 'going': race['going'], 'status': 'OFFICIAL',
                'source': SOURCE, 'kra_id': race['key']}, '@rid IS NULL'),
            'UPDATE race SET ' + ','.join(f'{k}={literal(v)}' for k, v in {'name': race['name'], 'race_date': race['date'], 'distance': race['distance'],
                'venue': race['venue'], 'surface': race['surface'], 'race_class': race['class'], 'weather': race['weather'], 'going': race['going'], 'status': 'OFFICIAL', 'source': SOURCE}.items()) + ' WHERE id=@rid AND @planned=1;',
            f'SET @rid=(SELECT id FROM race WHERE kra_id={key});']
        if refresh_sectionals:
            statements += [f'INSERT INTO kra_assertion VALUES (IF(@new_race=0 AND (SELECT COUNT(*) FROM entry WHERE race_id=@rid)={len(race["entries"])},1,0));']
            statements += [f"INSERT INTO kra_assertion VALUES (EXISTS(SELECT 1 FROM race WHERE id=@rid AND source={literal(SOURCE)} AND distance={race['distance']} AND race_date={literal(race['date'])} AND status='OFFICIAL'));" ]
        for entry in race['entries']:
            for kind, role, var in [('JOCKEY', 'jockey', '@jid'), ('TRAINER', 'trainer', '@tid')]:
                source_id = literal(entry[role])
                statements += [insert('person', {'kind': kind, 'name': entry[role + '_name'], 'source': SOURCE, 'kra_id': entry[role]},
                    f"@new_race=1 AND NOT EXISTS(SELECT 1 FROM person WHERE kind='{kind}' AND kra_id={source_id})"),
                    f"SET {var}=(SELECT id FROM person WHERE kind='{kind}' AND kra_id={source_id});"]
            horse_id = literal(entry['horse'])
            statements += [insert('horse', {'name': entry['name'], 'sex': entry['sex'], 'birth_date': entry['birth'],
                    'color': '미제공', 'trainer': '경주별 조교사 참조', 'kra_id': entry['horse']},
                    f'@new_race=1 AND NOT EXISTS(SELECT 1 FROM horse WHERE kra_id={horse_id})'),
                f'SET @hid=(SELECT id FROM horse WHERE kra_id={horse_id});']
            values = {'number': entry['number'], 'jockey': entry['jockey_name'], 'trainer_name': entry['trainer_name'],
                'finish_position': entry['finish'], 'time_seconds': entry['time'], 'status': 'FINISHED',
                'carried_weight': entry['carried'], 'body_weight': entry['body'], 'weight_change': entry['change'],
                'win_odds': entry['odds'], 'odds_source': SOURCE if entry['odds'] is not None else None,
                'odds_as_of': race['retrieved'] if entry['odds'] is not None else None}
            statements += [f"INSERT INTO entry(race_id,horse_id,jockey_id,trainer_id,{','.join(values)}) SELECT @rid,@hid,@jid,@tid,{','.join(literal(v) for v in values.values())} WHERE @new_race=1;",
                'SET @eid=(SELECT id FROM entry WHERE race_id=@rid AND horse_id=@hid);']
            if refresh_sectionals:
                statements += [f'INSERT INTO kra_assertion VALUES (EXISTS(SELECT 1 FROM entry WHERE id=@eid AND number={entry["number"]} AND finish_position={entry["finish"]} AND time_seconds={literal(entry["time"])}));']
                for table in ('sectional', 'sectional_marker'):
                    statements += [f'INSERT INTO kra_assertion VALUES (NOT EXISTS(SELECT 1 FROM {table} WHERE entry_id=@eid AND source<>{literal(SOURCE)}));',
                                   f'DELETE FROM {table} WHERE entry_id=@eid;']
            condition = '1=1' if refresh_sectionals else '@new_race=1'
            for distance, (position, seconds) in sorted(entry['points'].items()):
                statements.append('INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT @eid,' + ','.join(literal(v) for v in (distance, position, seconds, SOURCE)) + f' WHERE {condition};')
            for corner, position, seconds in entry['corners']:
                statements.append('INSERT INTO sectional_marker(entry_id,marker,position,cumulative_seconds,source) SELECT @eid,' + ','.join(literal(v) for v in (corner, position, seconds, SOURCE)) + f' WHERE {condition};')
        statements += ['INSERT INTO kra_race_import(race_id,fingerprint,raw_json,retrieved_at) SELECT @rid,' + ','.join(literal(race[k]) for k in ('fingerprint', 'raw', 'retrieved')) + ' WHERE @new_race=1;',
            "SELECT 'KRA_RESULT',@rid,@new_race;"]
    statements += ['COMMIT;', "DO RELEASE_LOCK('kra_result_import');"]
    return '\n'.join(statements)


def apply(races, database='keiba', refresh_sectionals=False):
    from backup import mysql
    try:
        output = mysql(sql_plan(races, refresh_sectionals), database)
    except subprocess.CalledProcessError:
        raise KraError('DB 반영을 취소했습니다. 최신 버전 실행 여부, 기존 경주와 원본 변경 여부, DB 상태를 확인하세요. 부분 변경은 롤백됩니다.') from None
    return [tuple(map(int, line.split('\t')[1:])) for line in output.splitlines() if line.startswith('KRA_RESULT\t')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='kra.py로 받은 results-... 폴더')
    parser.add_argument('--apply', action='store_true', help='검증 후 로컬 DB에 반영 (생략하면 미리보기)')
    parser.add_argument('--refresh-sectionals', action='store_true', help='동일 원본으로 이미 반영된 경주의 구간 자료만 갱신 (--apply와 함께 실행)')
    args = parser.parse_args()
    try:
        races = load_archive(args.directory)
        print(f"검증 완료: {', '.join(sorted({r['venue'] for r in races}))} {len(races)}경주 / {sum(len(r['entries']) for r in races)}두 출전")
        for race in races:
            print(f"{race['date']} · {race['name']} · {len(race['entries'])}두")
        print('단승 배당·경마장별 구간 기록을 반영합니다(제주 코너는 3·4코너). 공식 인기 순위는 미제공, plcOdds는 원본에 보관합니다.')
        if args.refresh_sectionals:
            print('구간 갱신 모드: 기존 경주·출전 정보와 원본이 일치할 때 구간·코너만 갱신합니다.')
        if not args.apply:
            print('미리보기입니다. DB에 반영하려면 같은 명령 끝에 --apply를 붙이세요.')
            return 0
        for race_id, created in apply(races, refresh_sectionals=args.refresh_sectionals):
            print(('구간 자료 갱신' if args.refresh_sectionals else '새 경주 반영' if created else '동일 원본: 중복 반영 생략') + f': http://localhost:5173/races/{race_id}')
    except (KraError, OSError, ValueError, TypeError, KeyError) as exc:
        print(str(exc) if isinstance(exc, KraError) else '다운로드 파일 형식·경로·권한을 확인하세요. DB에 반영하지 못했습니다.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
