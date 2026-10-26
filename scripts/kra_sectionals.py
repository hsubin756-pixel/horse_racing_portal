#!/usr/bin/env python3
"""저장된 API214_1 원본의 구간 필드 요약. API 호출·DB 변경 없이 숫자만 출력합니다."""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys

from kra import KraError
from kra_import import load_archive

FIELD = re.compile(r'(?:se|sj|je|bu)[A-Za-z0-9_]*(?:Time|Ord)\Z')


def numeric(value):
    if value is None or str(value).strip() in ('', '-'):
        return '없음'
    value = str(value).strip()
    if not re.fullmatch(r'\d{1,6}(?:\.\d{1,3})?', value):
        return '비숫자'
    try:
        return str(Decimal(value))
    except InvalidOperation:
        return '비숫자'


def report(folder):
    races = load_archive(Path(folder))
    for race in races:
        rows = json.loads(race['raw'])
        print(f"{race['key']} · {race['venue']} · {race['distance']}m · {len(rows)}두")
        keys = ['rcTime'] + sorted({k for row in rows for k in row if FIELD.fullmatch(k)})
        print('필드 | 양수/0/없음/비숫자 | 양수 범위 | 첫 2행 값')
        for key in keys:
            values = [numeric(row.get(key)) for row in rows]
            nums = [Decimal(v) for v in values if v not in ('없음', '비숫자')]
            positive = [v for v in nums if v > 0]
            # 다른 경마장 전용 0 필드는 생략. 해당 경마장 필드는 0/누락도 표시.
            prefixes = {'1': ('se', 'sj'), '2': ('je', 'sj'), '3': ('bu',)}[race['meet']]
            if key != 'rcTime' and not key.startswith(prefixes) and not positive:
                continue
            bounds = f'{min(positive)}~{max(positive)}' if positive else '-'
            counts = f"{len(positive)}/{sum(v == 0 for v in nums)}/{values.count('없음')}/{values.count('비숫자')}"
            print(f"{key} | {counts} | {bounds} | {', '.join(values[:2])}")
        print('첫 2행 출전번호: ' + ', '.join(numeric(r.get('chulNo')) for r in rows[:2]))
        print('원본 진단용 요약입니다. 누적/구간 시간 해석이나 DB 반영을 수행하지 않았습니다.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', help='kra.py로 받은 results-... 폴더')
    args = parser.parse_args()
    try:
        for folder in args.directories:
            report(folder)
    except KraError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print('보관 폴더의 파일·형식·권한을 확인하세요.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
