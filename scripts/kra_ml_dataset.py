#!/usr/bin/env python3
"""한국마사회 AI학습용 경주결과(API155)를 날짜별로 수집해 ml/evaluate.py 입력 CSV를 만듭니다.

  python3 scripts/kra_ml_dataset.py collect --meet 1 --from 20250104 --to 20251228 --max-calls 100
  python3 scripts/kra_ml_dataset.py export --meet 1 --output .runtime/kra/ml/seoul-2025.csv

collect 는 경마 시행 요일(서울 토·일, 제주 금·토, 부산경남 금·일; --all-days 로 전체)만 호출하고, 받은 날짜는
.runtime/kra/ml/meet-<번호>/<날짜>.json 에 보존해 다시 호출하지 않습니다. export 는 보존된 자료만 사용합니다.
CSV 계약(docs/ML_DATA.md): race_id,race_date,horse_id,distance,finish_position 뒤에 확장 열(기수·조교사·부담중량·배당 등)이 붙습니다.
취소·실격 등 순위 없는 출전만 제외하고 나머지 순위가 1..N으로 이어지는 경주를 유지합니다. 기존 ml/evaluate.py 는 앞 5열만 읽습니다.
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kra_catalog as kc  # noqa: E402
from kra import KraError, STATE, load_key, private_write  # noqa: E402

MEETS = {'1': '서울', '2': '제주', '3': '부산경남'}
RACE_DAYS = {'1': (5, 6), '2': (4, 5), '3': (4, 6)}
ML_DIR = STATE / 'ml'


def parse_day(value):
    try:
        return datetime.strptime(value, '%Y%m%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError('날짜는 YYYYMMDD 형식입니다.') from None


def day_file(meet, day):
    return ML_DIR / f'meet-{meet}' / f'{day:%Y%m%d}.json'


def fetch_day(key, meet, day):
    """하루치 전체 행을 받아 돌려줍니다(최대 3페이지). 0건이면 빈 목록."""
    rows, total = [], None
    for page in range(1, 4):
        raw = kc.request_page(key, 'ai-race-result', {'rccrs_cd': meet, 'race_dt': f'{day:%Y%m%d}'}, page, 100)
        current, batch, actual, _ = kc.parse_page(raw)
        if actual != page or (total is not None and total != current):
            raise KraError(f'{day}: 응답 페이지 정보가 일치하지 않습니다.')
        total = current
        rows.extend(batch)
        if not batch or len(rows) >= total:
            break
    if total is not None and len(rows) < total:
        raise KraError(f'{day}: 전체 {total}건 중 {len(rows)}건만 받았습니다.')
    return rows


def collect(meet, start, end, max_calls, all_days):
    if end < start or (end - start).days > 400:
        raise KraError('기간은 시작일 이후 400일 이내여야 합니다.')
    key = load_key()
    calls = fetched = skipped = 0
    day = start
    pending = []
    while day <= end:
        if (all_days or day.weekday() in RACE_DAYS[meet]) and day < date.today():
            if day_file(meet, day).exists():
                skipped += 1
            else:
                pending.append(day)
        day += timedelta(days=1)
    for day in pending:
        if calls >= max_calls:
            break
        rows = fetch_day(key, meet, day)
        calls += 1
        private_write(day_file(meet, day), json.dumps({'meet': meet, 'date': day.isoformat(), 'api': 'KRA_API155',
                      'retrievedAt': datetime.now(timezone.utc).isoformat(), 'rows': rows}, ensure_ascii=False) + '\n')
        fetched += 1
        print(f'{day} {MEETS[meet]}: {len(rows)}건')
    remaining = len(pending) - fetched
    print(f'수집 완료: 새로 받은 날짜 {fetched}개 (호출 {calls}회), 이미 보존된 날짜 {skipped}개, 남은 날짜 {remaining}개')
    if remaining:
        print('남은 날짜는 같은 명령을 다시 실행하면 이어서 받습니다(개발계정 호출 한도 주의).')
    return {'fetched': fetched, 'skipped': skipped, 'remaining': remaining, 'calls': calls}


def load_days(meet):
    folder = ML_DIR / f'meet-{meet}'
    if not folder.is_dir():
        return []
    days = []
    for path in sorted(folder.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('meet') != meet or data.get('api') != 'KRA_API155':
            raise KraError(f'{path.name}: 보존 파일의 형식이 다릅니다.')
        days.append(data)
    return days


EXTRA = ['jockey', 'trainer', 'carried_weight', 'win_odds', 'place_odds', 'gate', 'horse_weight', 'rating', 'sex', 'birth_date']


def weight_of(value):
    match = re.fullmatch(r'(\d{3})\s*\(\s*[+-]?\d+\s*\)', (value or '').strip())
    return int(match.group(1)) if match else ''


def decimal_or_blank(value, low, high):
    value = (value or '').strip()
    try:
        number = float(value)
    except ValueError:
        return ''
    return value if low <= number <= high else ''


def build_rows(days, meet, drop_scratched=True):
    """날짜별 원본을 경주 단위로 검증해 CSV 행과 제외 사유 집계를 돌려줍니다.

    drop_scratched=True 이면 순위가 없는 출전(취소·실격 등)만 제외하고 나머지 순위가 1..N으로 이어지면 경주를 유지합니다.
    """
    races = defaultdict(list)
    for data in days:
        for row in data['rows']:
            races[(data['date'], (row.get('raceNo') or '').strip())].append(row)
    out, dropped = [], defaultdict(int)
    kept_after_scratch = 0
    for (race_day, race_no), starters in sorted(races.items(), key=lambda kv: (kv[0][0], int(kv[0][1]) if kv[0][1].isdigit() else 0)):
        if not race_no.isdigit():
            dropped['경주번호 없음'] += 1
            continue
        ranked, horses, distance = [], set(), None
        ok, scratched = True, 0
        for row in starters:
            rank, hrno, dist = (row.get('rk') or '').strip(), (row.get('hrno') or '').strip(), (row.get('raceDs') or '').strip()
            if not re.fullmatch(r'\d{1,2}', rank) or int(rank) == 0:
                if drop_scratched:
                    scratched += 1
                    continue
                ok = False; dropped['순위 없음·취소·실격 포함'] += 1; break
            if not re.fullmatch(r'\d{1,16}', hrno) or int(hrno) == 0 or int(hrno) in horses:
                ok = False; dropped['마번 누락·중복'] += 1; break
            if not dist.isdigit() or not 400 <= int(dist) <= 10000 or (distance is not None and distance != int(dist)):
                ok = False; dropped['거리 불일치'] += 1; break
            distance = int(dist)
            horses.add(int(hrno)); ranked.append(row)
        if not ok:
            continue
        if not 4 <= len(ranked) <= 100 or sorted(int(r['rk']) for r in ranked) != list(range(1, len(ranked) + 1)):
            dropped['착순 불완전(동착·4두 미만·취소 후 순위 공백)'] += 1
            continue
        kept_after_scratch += scratched > 0
        for row in ranked:
            out.append({'race_id': f'{meet}:{race_day.replace("-", "")}:{race_no}', 'race_date': race_day,
                        'horse_id': int(row['hrno']), 'distance': distance, 'finish_position': int(row['rk']),
                        'jockey': (row.get('jckyNm') or '').strip(), 'trainer': (row.get('trarNm') or '').strip(),
                        'carried_weight': decimal_or_blank(row.get('burdWgt'), 30, 80), 'win_odds': decimal_or_blank(row.get('winPrice'), 1, 9999),
                        'place_odds': decimal_or_blank(row.get('placePrice'), 1, 9999), 'gate': (row.get('gtno') or '').strip() if (row.get('gtno') or '').strip().isdigit() else '',
                        'horse_weight': weight_of(row.get('rchrWeg')), 'rating': decimal_or_blank(row.get('ratgSo'), 0, 200),
                        'sex': (row.get('gndrNm') or '').strip(), 'birth_date': (row.get('bthd') or '').strip()})
    if kept_after_scratch:
        dropped['(참고) 취소마만 제외하고 유지한 경주'] = kept_after_scratch
    return out, dict(dropped)


def export(meet, output, start=None, end=None):
    if start and end and end < start:
        raise KraError('종료일은 시작일 이후여야 합니다.')
    days = load_days(meet)
    if start or end:
        days = [d for d in days if (not start or date.fromisoformat(d['date']) >= start)
                and (not end or date.fromisoformat(d['date']) <= end)]
    if not days:
        raise KraError('보존된 날짜가 없습니다. 먼저 collect 를 실행하세요.')
    rows, dropped = build_rows(days, meet)
    if not rows:
        raise KraError('CSV로 내보낼 완전한 경주가 없습니다.')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as sink:
        writer = csv.DictWriter(sink, fieldnames=['race_id', 'race_date', 'horse_id', 'distance', 'finish_position'] + EXTRA)
        writer.writeheader()
        writer.writerows(rows)
    dates = sorted({r['race_date'] for r in rows})
    races = len({r['race_id'] for r in rows})
    print(f'{MEETS[meet]}: 보존 날짜 {len(days)}개 중 자료 있는 날짜 {len(dates)}개, 경주 {races}개, 출전 {len(rows)}건 → {output}')
    for reason, count in sorted(dropped.items()):
        print(f'  {"" if reason.startswith("(참고)") else "제외 "}{reason}: {count}경주')
    if len(dates) < 30:
        print('주의: evaluate.py 는 서로 다른 개최일 30일 이상을 요구합니다. 기간을 넓혀 collect 를 더 실행하세요.')
    else:
        print(f'다음: .runtime/ml-venv/bin/python ml/evaluate.py {output} --provenance "한국마사회 공공데이터포털 API155(AI학습용 경주결과), 개발계정, {dates[0]}~{dates[-1]}" --output .runtime/kra/ml/report-meet{meet}.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect', help='날짜별 원본 수집')
    c.add_argument('--meet', required=True, choices=sorted(MEETS))
    c.add_argument('--from', dest='start', required=True, type=parse_day)
    c.add_argument('--to', dest='end', required=True, type=parse_day)
    c.add_argument('--max-calls', type=int, default=100, help='이번 실행의 최대 호출 수 (기본 100)')
    c.add_argument('--all-days', action='store_true', help='시행 요일 추정 없이 모든 날짜 호출')
    e = sub.add_parser('export', help='보존 자료를 CSV로')
    e.add_argument('--meet', required=True, choices=sorted(MEETS))
    e.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'collect':
            if not 1 <= args.max_calls <= 1000:
                raise KraError('--max-calls 는 1~1000 입니다.')
            collect(args.meet, args.start, args.end, args.max_calls, args.all_days)
        else:
            export(args.meet, args.output)
    except (KraError, UnicodeError, ValueError) as exc:
        print(str(exc) if isinstance(exc, KraError) else '보존 파일 또는 응답 형식을 확인하세요.', file=sys.stderr)
        return 1
    except OSError:
        print('로컬 파일을 읽거나 저장하지 못했습니다. 폴더 권한과 여유 공간을 확인하세요.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\n작업을 취소했습니다. 받은 날짜는 보존되어 있습니다.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
