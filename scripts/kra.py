#!/usr/bin/env python3
"""한국마사회 API214_1 연결 확인 및 원본 다운로드 (Python 표준 라이브러리 전용)."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import warnings
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.runtime' / 'kra'
ENDPOINT = 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1'
PAGE_SIZE = 100
MAX_BYTES = 4 * 1024 * 1024
MEETS = {'1': '서울', '2': '제주', '3': '부산경남'}
# API214_1 실제 응답에서 확인한 약칭. 원본 행은 변경하지 않습니다.
MEET_CODES = {name: code for code, name in MEETS.items()} | {'부경': '3'}
ERRORS = {
    '1': '제공기관의 처리 오류입니다. 잠시 후 다시 시도하세요.',
    '10': '조회 조건이 올바르지 않습니다.',
    '12': 'API 경로 또는 서비스 제공 상태를 확인하세요.',
    '20': '이 API의 활용 승인 및 키 사용 권한을 확인하세요.',
    '22': 'API 요청 한도를 초과했습니다. 반복 실행을 멈춰 주세요.',
    '30': '인증키가 등록되지 않았습니다. 키와 신청 내역을 확인하세요.',
    '31': '인증키의 사용 기간이 만료되었습니다.',
    '32': '허용된 IP 주소를 확인하세요.',
    '99': '제공기관에서 기타 오류를 반환했습니다.',
}


class KraError(Exception):
    pass


def normalize_key(value):
    # Accept either portal encoding; urlencode below performs the one URL encoding.
    key = unquote(value.strip())
    if not re.fullmatch(r'[A-Za-z0-9+/=]{16,512}', key):
        raise KraError('인증키 형식을 확인하세요. 주소 전체가 아닌 인증키만 입력하세요.')
    return key


def parse_body_weight(value):
    """Return kg and optional change; an empty change is unknown, never zero."""
    value = (value or '').strip()
    if value in ('', '-', '0'):
        return None, None
    match = re.fullmatch(r'(\d+)\s*\(\s*([+-]?\d+)?\s*\)', value)
    if not match or len(value) > 30:
        raise KraError('마체중·증감 표기를 확인하세요.')
    body = int(match[1])
    change = int(match[2]) if match[2] is not None else None
    if not 200 <= body <= 800 or (change is not None and not -100 <= change <= 100):
        raise KraError('마체중·증감이 지원 범위를 벗어났습니다.')
    return body, change


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.kra-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def configure():
    if not sys.stdin.isatty():
        raise KraError('WSL 터미널에서 configure를 직접 실행하세요. 입력은 화면에 표시되지 않습니다.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            value = getpass.getpass('공공데이터포털 인증키를 붙여넣고 Enter (화면에 표시되지 않음): ')
    except getpass.GetPassWarning:
        raise KraError('이 터미널에서는 숨김 입력을 사용할 수 없습니다. WSL 터미널에서 다시 실행하세요.') from None
    key = normalize_key(value)
    private_write(STATE / 'service-key', key + '\n')
    print('인증키를 로컬 .runtime/kra/service-key에 저장했습니다. 값은 표시하지 않습니다.')


def load_key():
    if os.environ.get('KRA_SERVICE_KEY'):
        return normalize_key(os.environ['KRA_SERVICE_KEY'])
    path = STATE / 'service-key'
    if not path.is_file():
        raise KraError('먼저 python3 scripts/kra.py configure를 실행하세요.')
    return normalize_key(path.read_text(encoding='utf-8'))


def redact(text, key):
    for value in (key, quote(key, safe='')):
        text = re.sub(re.escape(value), '[REDACTED]', text, flags=re.IGNORECASE)
    return text


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise KraError('API 주소가 리디렉션되었습니다. 인증키 전달을 중단했습니다.')


def request_page(key, filters, page):
    query = urlencode({'ServiceKey': key, 'numOfRows': PAGE_SIZE, 'pageNo': page, **filters})
    req = Request(ENDPOINT + '?' + query, headers={'Accept': 'application/xml'})
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            data = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        raise KraError(f'API HTTP 오류 {exc.code}. 신청 상태·제공기관 상태·네트워크를 확인하세요.') from None
    except (URLError, TimeoutError, OSError):
        raise KraError('API에 연결하지 못했습니다. 네트워크 또는 제공기관 상태를 확인하세요.') from None
    if len(data) > MAX_BYTES:
        raise KraError('API 응답이 허용 크기를 초과했습니다.')
    # Never persist an echoed credential, including in a nominally successful response.
    return redact(data.decode('utf-8-sig', errors='strict'), key)


def parse_page(text, page):
    if re.search(r'<!\s*(DOCTYPE|ENTITY)', text, re.I):
        raise KraError('지원하지 않는 XML 선언입니다.')
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise KraError('XML 응답을 읽을 수 없습니다. 제공기관 응답 형식을 확인하세요.') from None
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    code = root.findtext('./header/resultCode')
    if code is None:
        code = root.findtext('.//returnReasonCode')
    if code != '00':
        safe_code = str(int(code)) if code and re.fullmatch(r'\d{1,3}', code) else '?'
        raise KraError('API 오류 ' + safe_code + ': ' + ERRORS.get(safe_code, '제공기관 응답 코드를 확인하세요.'))
    try:
        total = int(root.findtext('./body/totalCount', ''))
        actual_page = int(root.findtext('./body/pageNo', ''))
        size = int(root.findtext('./body/numOfRows', ''))
    except ValueError:
        raise KraError('응답의 페이지 정보가 올바르지 않습니다.') from None
    rows = [{child.tag: child.text or '' for child in item}
            for item in root.findall('./body/items/item')]
    if total < 0 or actual_page != page or size != PAGE_SIZE or len(rows) > PAGE_SIZE:
        raise KraError('응답의 페이지 정보가 요청과 일치하지 않습니다.')
    return total, rows


def validate_date(value):
    try:
        if not re.fullmatch(r'\d{8}', value):
            raise ValueError()
        datetime.strptime(value, '%Y%m%d')
    except ValueError:
        raise argparse.ArgumentTypeError('날짜를 YYYYMMDD 형식으로 입력하세요. 예: 20220220') from None
    return value


def bounded_race(value):
    value = int(value)
    if not 1 <= value <= 99:
        raise argparse.ArgumentTypeError('경주번호는 1~99입니다.')
    return value


def meet_mismatch(requested, observed):
    # Only short Korean venue labels or venue codes are safe to echo. Never
    # print an arbitrary provider field that could contain an echoed key/URL.
    safe = observed if re.fullmatch(r'[가-힣 ]{1,20}|[1-4]', observed or '') else '(미인식 표기)'
    expected = MEETS[requested]
    return (f'요청한 경마장과 다른 자료가 반환되었습니다. 요청: {requested} ({expected}), '
            f'응답 meet: {safe!r}. 표기 확인 전에는 저장·DB 반영하지 않습니다.')


def download(key, filters, max_pages, preview=False, before_request=None, page_cache=None):
    pages, rows, seen = [], [], set()
    total = None
    for page in range(1, max_pages + 1):
        if page > 1:
            time.sleep(0.25)
        cached = Path(page_cache) / f'{page}.xml' if page_cache else None
        if cached and cached.exists():
            raw = cached.read_text(encoding='utf-8')
        else:
            if before_request:
                before_request()
            raw = request_page(key, filters, page)
        current_total, batch = parse_page(raw, page)
        if total is not None and total != current_total:
            raise KraError('조회 중 전체 건수가 변경됐습니다. 잠시 후 다시 시도하세요.')
        total = current_total
        expected = min(PAGE_SIZE, max(0, total - len(rows)))
        if len(batch) != expected:
            raise KraError('응답 건수가 전체 건수와 일치하지 않습니다. 불완전한 다운로드를 중단했습니다.')
        for row in batch:
            identity = (MEET_CODES.get(row.get('meet')), *(row.get(k, '') for k in ('rcDate', 'rcNo', 'hrNo')))
            if MEET_CODES.get(row.get('meet')) != filters['meet']:
                raise KraError(meet_mismatch(filters['meet'], row.get('meet', '')))
            if not all(identity) or identity in seen:
                raise KraError('경주·말 식별번호가 누락되거나 중복됐습니다.')
            if row['rcDate'] != filters['rc_date']:
                raise KraError('요청한 날짜와 다른 자료가 반환되었습니다.')
            if 'rc_no' in filters and row['rcNo'] != str(filters['rc_no']):
                raise KraError('요청한 경주번호와 다른 자료가 반환되었습니다.')
            seen.add(identity)
        if cached:
            private_write(cached, raw)
        pages.append(raw)
        rows.extend(batch)
        if len(rows) == total or preview:
            break
    complete = len(rows) == total
    if not complete and not preview:
        raise KraError('최대 10페이지를 초과합니다. --race로 경주를 지정해 조회 범위를 줄이세요.')
    # No archive is created on a failure. Unique directories never overwrite a prior run.
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix='results-', dir=STATE))
    for index, raw in enumerate(pages, 1):
        private_write(folder / f'page-{index}.xml', raw)
    metadata = {'source': 'KRA_API214_1', 'endpoint': ENDPOINT,
                'retrievedAt': datetime.now(timezone.utc).isoformat(),
                'filters': filters, 'totalCount': total, 'receivedCount': len(rows),
                'complete': complete, 'pages': len(pages), 'importedIntoSite': False,
                'availableFields': sorted({field for row in rows for field in row})}
    private_write(folder / 'summary.json', json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(f'API 연결 성공: 전체 {total}건 / 수신 {len(rows)}건 / 호출 {len(pages)}회')
    print('전체 조회 완료' if complete else '첫 페이지 확인 완료 (전체 다운로드는 fetch 명령 사용)')
    if not rows:
        print('해당 조건의 자료가 없습니다. 경주일·경마장·경주번호를 확인하세요.')
    print('저장 위치: ' + str(folder.relative_to(ROOT)))
    print('인증키는 출력·응답 파일에 포함하지 않습니다. 사이트 DB 반영은 별도 단계입니다.')
    return {**metadata, 'directory': str(folder)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('configure', help='인증키를 숨김 입력으로 로컬 저장')
    for command in ('check', 'fetch'):
        p = sub.add_parser(command, help='첫 페이지 연결 확인' if command == 'check' else '지정 일자 원본 다운로드 (최대 10회 호출)')
        p.add_argument('--date', required=True, type=validate_date, help='경주일 YYYYMMDD')
        p.add_argument('--meet', required=True, choices=['1', '2', '3'], help='1 서울 / 2 제주 / 3 부산경남')
        p.add_argument('--race', type=bounded_race, help='특정 경주번호 (생략하면 해당 날짜 전체)')
    args = parser.parse_args()
    try:
        if args.command == 'configure':
            configure()
        else:
            filters = {'meet': args.meet, 'rc_date': args.date}
            if args.race is not None:
                filters['rc_no'] = args.race
            download(load_key(), filters, 1 if args.command == 'check' else 10, args.command == 'check')
    except (KraError, UnicodeError) as exc:
        print(str(exc) if isinstance(exc, KraError) else '파일 또는 응답의 문자 인코딩을 확인하세요.', file=sys.stderr)
        return 1
    except OSError:
        print('로컬 파일을 읽거나 저장하지 못했습니다. 폴더 권한과 여유 공간을 확인하세요.', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\n작업을 취소했습니다.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
