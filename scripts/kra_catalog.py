#!/usr/bin/env python3
"""승인된 한국마사회 공공데이터 API 공통 호출 도구 (표준 라이브러리 전용).

docs/KRA_API_CATALOG.md의 명세를 코드로 옮긴 레지스트리와, 한 페이지를 호출해 원본을 보존하고
항목 요약을 출력하는 probe / 여러 페이지를 내려받는 fetch 명령을 제공합니다. DB는 변경하지 않습니다.
인증키는 scripts/kra.py와 같은 .runtime/kra/service-key 를 사용합니다.
"""
import argparse
import json
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kra import ERRORS, MAX_BYTES, STATE, KraError, NoRedirect, load_key, private_write, redact  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://apis.data.go.kr/B551015/'
MEET_PARAMS = {'meet', 'rccrs_cd'}
# name -> (path, key parameter name, allowed query parameters, required parameters, portal ID)
REGISTRY = {
    'horse-info': ('API8_2/raceHorseInfo_2', 'ServiceKey', ('hr_name', 'hr_no', 'meet', 'act_gubun'), (), 15058115),
    'horse-total': ('API42_1/totalHorseInfo_1', 'ServiceKey', ('hr_eng_name', 'hr_name', 'hr_no'), (), 15057985),
    'horse-list': ('racehorselist/getracehorselist', 'ServiceKey', ('meet', 'rank'), (), 15089503),
    'horse-identity': ('horseinfohi/gethorseinfohi', 'serviceKey', ('hrname', 'hrno', 'reg_dt_fr', 'reg_dt_to'), (), 15105155),
    'horse-result': ('API15_2/raceHorseResult_2', 'ServiceKey', ('hr_name', 'hr_no'), (), 15058779),
    'pedigree-5gen': ('API47/rchrBldlnInfo', 'serviceKey', ('hr_no', 'hr_name'), ('hr_no',), 15173126),
    'pedigree-basic': ('API284/HorseBloodBasicInfo', 'serviceKey', ('hrno', 'kor_hrnm', 'foalg_dt_fr', 'foalg_dt_to'), (), 15109000),
    'stallion': ('API79_1/stallionInfo_1', 'ServiceKey', (), (), 15059488),
    'cross': ('API192/Cross', 'ServiceKey', ('cross_date_fr', 'cross_date_to'), (), 15063956),
    'jockey-info': ('API12_1/jockeyInfo_1', 'ServiceKey', ('jk_name', 'jk_no', 'meet'), (), 15056828),
    'jockey-current': ('currentjockeyInfo/getcurrentjockeyinfo', 'ServiceKey', ('jk_name', 'jk_no', 'meet'), (), 15086329),
    'jockey-result': ('API11_1/jockeyResult_1', 'ServiceKey', ('jk_name', 'jk_no', 'meet'), (), 15056591),
    'trainer-info': ('API19_1/trainerInfo_1', 'ServiceKey', ('meet', 'tr_name', 'tr_no'), (), 15057915),
    'total-record': ('API27_1/totalRecord_1', 'ServiceKey', ('meet', 'pr_gubun', 'pr_name', 'pr_no'), (), 15058399),
    'race-plan': ('API72_2/racePlan_2', 'ServiceKey', ('meet', 'rc_date', 'rc_month', 'rc_year'), (), 15056499),
    'race-plan-info': ('API45/rcplnInfo', 'serviceKey', ('meet', 'pg_date'), ('meet', 'pg_date'), 15173122),
    'ai-race-plan': ('API154/racePlan', 'serviceKey', ('rccrs_cd', 'race_dt'), ('rccrs_cd', 'race_dt'), 15143802),
    'ai-race-result': ('API155/raceResult', 'serviceKey', ('rccrs_cd', 'race_dt'), ('rccrs_cd', 'race_dt'), 15143803),
    'ai-race-detail': ('API156/raceRsutDtl', 'serviceKey', ('rccrs_cd', 'race_dt', 'race_no'), (), 15150068),
    'race-result-3': ('API4_3/raceResult_3', 'ServiceKey', ('meet', 'rc_date', 'rc_month', 'rc_no', 'rc_year'), (), 15058305),
    'race-result-detail': ('racedetailresult/getracedetailresult', 'ServiceKey', ('meet', 'rc_date', 'rc_no'), ('meet', 'rc_date'), 15089492),
    'race-result-total': ('API299/Race_Result_total', 'serviceKey', ('meet', 'rc_year', 'rc_month', 'rc_date', 'rc_no'), (), 15119524),
    'race-summary': ('API34_1/raceSummaryResult_1', 'ServiceKey', ('meet', 'rc_date', 'rc_month', 'rc_year'), (), 15057579),
    'race-performance': ('API44/rcpfmcInfo', 'serviceKey', ('meet', 'rc_date', 'rc_no'), ('meet', 'rc_date'), 15173120),
    'race-info': ('API3_1/raceInfo_1', 'ServiceKey', ('meet', 'rc_date', 'rc_month', 'rc_no', 'rc_year'), (), 15059144),
    'prize': ('horseraceprizeinfo/gethorseraceprizeinfo', 'ServiceKey', ('meet', 'hr_name', 'rc_date_fr', 'rc_date_to'), (), 15086325),
    'section-race': ('API6_1/raceDetailSectionRecord_1', 'ServiceKey', ('meet', 'rc_date', 'rc_month', 'rc_no', 'rc_year'), (), 15057847),
    'section-horse': ('API37_1/sectionRecord_1', 'ServiceKey', ('hr_name', 'hr_no', 'meet', 'rc_date', 'rc_month', 'rc_year'), ('rc_date',), 15057859),
    'section-acc': ('API46/sectAcumRcd', 'serviceKey', ('meet', 'rc_date', 'rc_no'), ('meet', 'rc_date'), 15173124),
    'corner-rank': ('API303/corner_rank', 'serviceKey', ('meet', 'rc_year', 'rc_month', 'rc_date', 'rc_no'), (), 15119851),
    'track': ('API189_1/Track_1', 'ServiceKey', ('meet', 'rc_date_fr', 'rc_date_to'), (), 15063953),
    'top-record': ('API32_1/topRecordByCondition_1', 'ServiceKey', (), (), 15057344),
    'jockey-change': ('API48/jksubtInfo', 'serviceKey', ('meet', 'rc_date'), ('meet', 'rc_date'), 15173128),
    'starting-test': ('API21_1/startingTestResult_1', 'ServiceKey', ('meet', 'tr_date', 'tr_month', 'tr_year'), (), 15057405),
    'sanction': ('API180_1/sanctionHistory_1', 'ServiceKey', ('meet', 'rc_date', 'rc_month', 'rc_no', 'rc_year'), (), 15037098),
    'race-result': ('API214_1/RaceDetailResult_1', 'serviceKey', ('meet', 'rc_year', 'rc_month', 'rc_date', 'rc_no'), (), 15063979),
}
# 포털 한글 페이지의 Swagger 명세는 네 API(API27_1, API72_2, API155, API299)의 폴더를 비워 두므로 영문 페이지의 주소를 사용했습니다.
MASKED = {'birthday'}


def request_page(key, api, params, page, size):
    path, key_name, allowed, required, _ = REGISTRY[api]
    unknown = sorted(set(params) - set(allowed))
    if unknown:
        raise KraError('이 API가 받지 않는 조건입니다: ' + ', '.join(unknown))
    missing = [name for name in required if name not in params]
    if missing:
        raise KraError('필수 조건이 빠졌습니다: ' + ', '.join(missing))
    query = urlencode({key_name: key, 'numOfRows': size, 'pageNo': page, **params})
    req = Request(BASE + path + '?' + query, headers={'Accept': 'application/xml'})
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            data = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        raise KraError(f'API HTTP 오류 {exc.code}. 신청 상태·제공기관 상태·네트워크를 확인하세요.') from None
    except (URLError, TimeoutError, OSError):
        raise KraError('API에 연결하지 못했습니다. 네트워크 또는 제공기관 상태를 확인하세요.') from None
    if len(data) > MAX_BYTES:
        raise KraError('API 응답이 허용 크기를 초과했습니다.')
    return redact(data.decode('utf-8-sig', errors='strict'), key)


def parse_page(text):
    """items/item 구조와 body 직하 평면 구조를 모두 읽습니다. (total, rows, page, size)"""
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
        code = root.findtext('.//returnReasonCode') or root.findtext('./resultCode')
    if code != '00':
        safe = str(int(code)) if code and re.fullmatch(r'\d{1,3}', code) else '?'
        raise KraError('API 오류 ' + safe + ': ' + ERRORS.get(safe, '제공기관 응답 코드를 확인하세요.'))
    body = root.find('./body')
    scope = body if body is not None else root
    try:
        total = int(scope.findtext('./totalCount', '0') or 0)
        page = int(scope.findtext('./pageNo', '1') or 1)
        size = int(scope.findtext('./numOfRows', '0') or 0)
    except ValueError:
        raise KraError('응답의 페이지 정보가 올바르지 않습니다.') from None
    items = scope.findall('./items/item')
    if items:
        rows = [{c.tag: (c.text or '').strip() for c in item} for item in items]
    else:
        meta = {'totalCount', 'pageNo', 'numOfRows', 'resultCode', 'resultMsg', 'items', 'header'}
        flat = {c.tag: (c.text or '').strip() for c in scope if c.tag not in meta and len(c) == 0}
        rows = [flat] if flat else []
    return total, rows, page, size


def summarize(rows):
    if not rows:
        return '응답 항목이 없습니다(0건).'
    first = rows[0]
    lines = []
    for field in sorted(first):
        value = first[field]
        if field in MASKED and value and set(value) == {'*'}:
            value = '(마스킹)'
        lines.append(f'  {field} = {value[:60]}')
    fields = sorted({f for row in rows for f in row})
    empty = [f for f in fields if all(not row.get(f) for row in rows)]
    text = f'첫 행 {len(first)}개 항목:\n' + '\n'.join(lines)
    if empty:
        text += '\n수신 행 전체에서 비어 있는 항목: ' + ', '.join(empty)
    return text


def save(api, params, pages, rows, total, complete):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix=api + '-', dir=STATE))
    for index, raw in enumerate(pages, 1):
        private_write(folder / f'page-{index}.xml', raw)
    metadata = {'api': api, 'portalId': REGISTRY[api][4], 'endpoint': BASE + REGISTRY[api][0],
                'retrievedAt': datetime.now(timezone.utc).isoformat(), 'filters': params,
                'totalCount': total, 'receivedCount': len(rows), 'complete': complete, 'pages': len(pages),
                'availableFields': sorted({f for row in rows for f in row})}
    private_write(folder / 'summary.json', json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    private_write(folder / 'rows.json', json.dumps(rows, ensure_ascii=False, indent=1) + '\n')
    return folder


def run(api, params, max_pages, size):
    key = load_key()
    pages, rows, total = [], [], None
    for page in range(1, max_pages + 1):
        if page > 1:
            time.sleep(0.25)
        raw = request_page(key, api, params, page, size)
        current_total, batch, actual_page, _ = parse_page(raw)
        if total is not None and total != current_total:
            raise KraError('조회 중 전체 건수가 변경됐습니다. 잠시 후 다시 시도하세요.')
        total = current_total
        if actual_page != page:
            raise KraError('응답의 페이지 번호가 요청과 다릅니다.')
        pages.append(raw)
        rows.extend(batch)
        if not batch or len(rows) >= total:
            break
    complete = total is not None and len(rows) >= total
    folder = save(api, params, pages, rows, total, complete)
    print(f'{api}: 전체 {total}건 / 수신 {len(rows)}건 / 호출 {len(pages)}회 / {"전체 수신" if complete else "일부 수신"}')
    print(summarize(rows))
    print('저장 위치: ' + str(folder.relative_to(ROOT)))
    return rows


def parse_params(items):
    params = {}
    for item in items:
        if '=' not in item:
            raise KraError('조건은 이름=값 형식으로 입력하세요. 예: hr_no=039092')
        name, value = item.split('=', 1)
        if not re.fullmatch(r'[a-z_]{2,20}', name) or not re.fullmatch(r'[\w가-힣.\-]{1,40}', value):
            raise KraError('조건 이름 또는 값의 형식을 확인하세요: ' + name)
        params[name] = value
    return params


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='등록된 API 이름과 조건 목록')
    for command in ('probe', 'fetch'):
        p = sub.add_parser(command, help='첫 페이지 호출·요약' if command == 'probe' else '최대 --pages 페이지 다운로드')
        p.add_argument('api', choices=sorted(REGISTRY))
        p.add_argument('params', nargs='*', help='조건 이름=값 (예: meet=1 hr_no=039092)')
        p.add_argument('--rows', type=int, default=100, help='페이지당 건수 (기본 100)')
        if command == 'fetch':
            p.add_argument('--pages', type=int, default=10, help='최대 호출 페이지 수 (기본 10)')
    args = parser.parse_args()
    try:
        if args.command == 'list':
            for name, (path, _, allowed, required, pid) in sorted(REGISTRY.items()):
                print(f'{name:20s} {path:45s} 조건: {", ".join(allowed) or "-"}' + (f'  필수: {", ".join(required)}' if required else '') + f'  (포털 {pid})')
            return 0
        if not 1 <= args.rows <= 1000:
            raise KraError('--rows 는 1~1000 사이여야 합니다.')
        pages = 1 if args.command == 'probe' else max(1, min(args.pages, 50))
        run(args.api, parse_params(args.params), pages, args.rows)
    except (KraError, UnicodeError) as exc:
        print(str(exc) if isinstance(exc, KraError) else '응답의 문자 인코딩을 확인하세요.', file=sys.stderr)
        return 1
    except OSError:
        print('로컬 파일을 읽거나 저장하지 못했습니다. 폴더 권한과 여유 공간을 확인하세요.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\n작업을 취소했습니다.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
