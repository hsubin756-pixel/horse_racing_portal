# REST API v1
기본 경로 /api. JSON. 오류는 {message}. 인증은 Authorization: Bearer <token>.
| 메서드 / 경로 | 입력 / 결과 | 인증 |
|---|---|---|
| GET /horses | q, page(0부터), sort(name/sex/birthDate), direction(asc/desc). 20건 Page | 공개 |
| GET /horses/{id} | 이름/성별/생일/모색/부모/조교사 | 공개 |
| GET /horses/{id}/history | 최근 경주 먼저, 경주 링크 ID | 공개 |
| GET /horses/{id}/pedigree | 루트 + 양쪽 조상 3단계, null은 정보 없음 | 공개 |
| GET /races | q, date(YYYY-MM-DD), page. 20건 Page | 공개 |
| GET /races/{id} | 경주와 출전 기록 | 공개 |
| POST /auth/register | email, password(10~72자, UTF-8 72바이트 이하), nickname. 201 | 공개 |
| POST /auth/login | email, password → token, nickname, expiresIn | 공개 |
| POST /auth/logout | 현재 JWT 철회. 204 | 회원 |
| GET /favorites | 현재 회원의 경주마 목록 | 회원 |
| POST /favorites/{horseId} | 추가. 201 / 중복 409 | 회원 |
| DELETE /favorites/{horseId} | 자신의 항목 삭제. 204 | 회원 |
| POST /races/{id}/prediction | 예측 점수 내림차순, 모델 종류와 면책 문구 | 회원 |
| GET /health | 상태 | 공개 |
400 잘못된 입력, 401 인증 실패/만료/철회, 404 대상 없음, 409 중복, 503 ML 장애. OpenAPI: /v3/api-docs, Swagger UI: /swagger-ui/index.html.

## 추가 실패 응답과 운영 프록시
- `GET /api/health`는 실제 DB에 `SELECT 1`을 실행합니다. 연결 불가 시 한국어 메시지와 503을 반환합니다. ML 장애 여부는 이 endpoint에 포함하지 않습니다.
- JWT는 서명/issuer/만료와 함께 `exp`, `iat`, UUID 형식 `jti`, 양수 회원 ID `sub`를 요구합니다. 누락·잘못된 claims는 401입니다.
- 예측 서버의 timeout, 응답 항목 누락/null, 알 수 없는 말, 중복 말, 범위 밖 점수는 503으로 처리합니다.
- Nginx의 로그인/가입 요청 제한 초과는 429와 한국어 JSON 메시지를 반환합니다. 개발용 8080 포트 직접 호출에는 프록시 제한이 적용되지 않습니다.

## 출주마 인기 및 단승 배당
`GET /api/races/{id}`의 `entries`와 `GET /api/horses/{id}/history`의 각 항목에 아래 필드를 추가했습니다. 기존 필드는 유지합니다.

| 필드 | 타입 | 의미 |
|---|---|---|
| popularityRank | integer 또는 null | 해당 경주의 인기 순위. 착순·모델 점수와 별도 |
| winOdds | decimal 또는 null | 원금을 포함하는 단승 배수. 1.0 이상, 소수점 한 자리 |
| oddsSource | string 또는 null | 현재는 `synthetic_fixture`(가상 샘플) |
| oddsAsOf | ISO 8601 UTC 또는 null | 해당 스냅샷의 자료 기준 시각. 화면은 KST로 표시 |

네 값은 동일한 스냅샷으로 함께 저장되며 미제공 항목은 모두 null입니다. 숫자 0으로 대체하지 않습니다. 완료/예정 경주의 샘플 96건 중 95건을 제공하며, 예정 경주 8에는 미제공 예시 1건이 있습니다. 응답은 마번 순서를 유지하며, 화면에서 착순·마번·인기·배당 오름차순으로 정렬합니다. null은 화면 정렬의 끝으로 보냅니다.

### 배당 기준 인기 (조회 시 계산) — 2026-10-23

같은 두 응답의 각 항목에 저장하지 않고 조회할 때 계산하는 필드를 추가했습니다. 공식 인기 순위(`popularityRank`)가 없는 한국마사회 자료에도 적용됩니다.

| 필드 | 타입 | 의미 |
|---|---|---|
| oddsRank | integer 또는 null | 같은 경주에서 저장된 `winOdds`가 낮은 순서의 순위. 같은 배당은 같은 순위이며 다음 순위는 건너뜁니다(2.4·4.6·4.6·9.0 → 1·2·2·4). 배당이 없거나 취소(SCRATCHED) 출전이면 null |
| oddsRankShared | boolean 또는 null | 같은 배당의 말이 둘 이상이면 true(공동 순위). `oddsRank`가 null이면 null |
| oddsRankField | integer 또는 null | 순위 계산에 사용한 두수(배당이 있고 취소되지 않은 출전 수). 취소 출전 항목은 null |
| oddsRankTotal | integer | 취소를 제외한 해당 경주 출전 두수. `oddsRankField`보다 크면 일부 말의 배당이 빠진 것 |

계산 규칙은 `CatalogService.oddsRank`(순수 함수)에 있으며 `withOddsRanks`가 조회된 경주들의 배당을 `EntryRepository.oddsByRace` 한 번으로 읽어 채웁니다. 다른 응답(비교·통계·일정 등)의 EntryView에는 이 필드가 null입니다. 공식 인기 순위를 대체하거나 추정하지 않습니다.

기본 스냅샷은 고정된 가상 데이터입니다. 실제 배당 API 연동·실시간 갱신은 없으며, 후속 확장의 조합별 환급표와 관리자 등록 API는 아래에 설명합니다. 실제 자료 연동 시 공급자의 사용 허가, 시장 종류, 마감 여부와 기준 시각을 확인하고 인기·배당·출처·시각을 원자적으로 갱신해야 합니다.

## 비교·조건별 성적·관심 일정

| 메서드/경로 | 인증 | 내용 |
|---|---|---|
| GET /api/horses/compare?ids=22,32 | 공개 | 중복 없는 1~4두, 요청 순서대로 비교 |
| GET /api/horses/{id}/stats | 공개 | 1두 비교 응답과 같은 구조의 성적 |
| GET /api/jockeys?q=이름 | 공개 | 가상 기수 이름 부분 검색, 최대 50개 |
| GET /api/jockeys/stats?name=기수명 | 공개 | 해당 가상 기수의 조건별 성적 |
| GET /api/race-favorites | 회원 | 본인 관심 경주 목록, 개최일/ID 순 |
| POST /api/race-favorites/{id} | 회원 | 저장 201, 중복 409, 없는 경주 404 |
| DELETE /api/race-favorites/{id} | 회원 | 본인 저장만 삭제, 204 |
| GET /api/my-schedule | 회원 | 오늘~90일 뒤의 관심 경주·관심 말 출전, 경주별 병합 |

성적 필터는 선택적인 `distance`(400~10000), `surface`(잔디/더트/장애), `from`, `to`(ISO 날짜, 양끝 포함)입니다. 잘못된 조건은 한국어 400, 없는 말·기수는 404입니다. 기수는 현재 가상 데이터의 이름으로 식별하며 실제 공급원 연결 시 고유 기수 ID를 도입해야 합니다.

비교 응답은 `asOfDate`, `dataKind=synthetic_fixture`, `filter`, `horses[{horse,statistics}]`입니다. 기수 응답은 `asOfDate`, `dataKind`, `jockey`, `filter`, `statistics`입니다. `statistics`는 `totals`, `byDistance`, `bySurface`, `recent`(최신 5개)를 포함합니다. `totals`는 `starts`, `wins`, `top3`, `winRate`, `top3Rate`, `averageFinish`, `bestFinish`입니다. 비율은 0~100 단위이며, 표본 0이면 비율/평균/최고 착순은 null입니다. 완료 착순이 있고 개최일이 한국·일본 기준 오늘 이하인 전적만 집계합니다. 미래/미완료 전적은 제외하며 필터를 적용한 표본 안에서 조건별 성적과 최근 5경주를 계산합니다.

일정 응답은 `asOfDate`, `through`, `races[{race,savedRace,favoriteHorses}]`입니다. 예정일 범위에 있고 결과가 아직 하나도 기록되지 않은 경주만 표시합니다. 관심 말 출전과 관심 경주가 겹치면 경주 하나로 합칩니다. 지난 경주도 관심 목록에 저장할 수 있지만 앞으로의 일정에는 표시하지 않습니다. 외부 메시지를 발송하는 알림 기능은 없습니다.


## 출마표 확장·구간 분석·캘린더
`RaceView`는 `startTime`(한국/일본 현지 시각), `raceClass`, `weather`, `going`, `status`, `source`를 추가합니다. `EntryView`는 `gate`, `carriedWeight`, `bodyWeight`, `weightChange`, `status`, `jockeyId`를 추가합니다. `HorseView.trainerId`는 인물 상세 링크입니다. 기존 필드는 유지합니다. 미제공 정보는 null입니다.

| 요청 | 인증 | 응답/규칙 |
|---|---|---|
| GET /api/races/{id}/sectionals | 공개 | 출주별 구간, 통과 순위, 누적 시간·구간 시간, 마지막 600m, 초반 스타일 |
| GET /api/horses/{id}/running-style | 공개 | 최근 확정 완료 10경주, 유효 표본 수·유형 분포·대표 스타일·판정 설명 |
| GET /api/races/{id}/payouts | 공개 | 승식·조합·OPEN/FINAL/REFUND·배수/100엔당 금액·출처·시각 |
| GET /api/races/calendar?month=2025-01&venue=이름 | 공개 | 월 범위 경주, 경마장은 정확한 이름 필터, 날짜/시각 순 |
| GET /api/people?kind=JOCKEY&year=2025&venue=이름&q=부분이름 | 공개 | JOCKEY/TRAINER, 우승/출전/ID 순 최대 100명 |
| GET /api/people/{id}?year=2025&venue=이름 | 공개 | 고유 ID 인물 프로필·집계·최근 출전 20건 |

구간 `Run`은 `raceId,raceName,raceDate,distance,horseId,horseName,number,fieldSize,finishPosition,style,last600,points`입니다. `points`는 `distance,position,cumulativeSeconds,segmentSeconds,source`를 포함합니다. 시각이 부족하면 계산값은 null입니다. 상세 판정 규칙은 docs/RACE_FEATURES.md를 따릅니다. 인물·캘린더·환급의 JDBC 응답 필드 이름은 DB의 snake_case(`race_date`, `amount_yen` 등)입니다.

통계/전적/모델 과거 입력은 `OFFICIAL` 경주의 `FINISHED` 착순만 포함합니다. 비교/기수 통계의 `dataKind`는 입력 경주의 출처가 모두 기본 가상 fixture이면 `synthetic_fixture`, 그 외 `admin_catalog`입니다. 기수 이름 기반 기존 API는 호환용이며 ID 프로필은 별도입니다.

## 개인 메모와 사이트 내 알림

| 요청 | 인증 | 동작 |
|---|---|---|
| GET /api/notes?q=문자 | 회원 | 본인 메모/태그 문자 검색, 최근 수정 순 최대 200개 |
| POST /api/notes | 회원 | `{id?,revision?,horseId?,raceId?,body,tags}` 저장; 대상은 말 또는 경주 하나, 대상별 메모 하나 |
| DELETE /api/notes/{id} | 회원 | 본인 메모만 삭제, 204 |
| POST /api/notifications/refresh | 회원 | 7일 내 관심 예정 출전 알림 생성/중복 제거 후 본인 최근 100개 반환 |
| POST /api/notifications/{id}/read | 회원 | 본인 알림 읽음 표시, 204 |

메모는 1~2000자, 태그는 200자 이하입니다. 수정에는 현재 revision이 필요하고 다른 회원/오래된 버전은 409입니다. 알림은 회원·경주·개최일 UNIQUE이며 읽음 상태를 보존합니다. 신규 자료 생성이므로 알림 갱신은 POST를 사용합니다. 외부 발송 API는 없습니다.

## 관리자 API
일반 회원은 403, 미인증은 401입니다. 권한은 DB `member.is_admin`을 확인하며 공개 가입 요청으로 설정할 수 없습니다. 종류(kind)는 `horses,races,entries,sectionals,payouts,people`만 허용합니다.

| 요청 | 동작 |
|---|---|
| GET /api/admin/access | 관리자 여부 확인 |
| GET /api/admin/{kind}?page=0 | 최신 ID 순 50개, 페이지 0~10000 |
| POST /api/admin/{kind}/preview | `{rows:[...]}` 형식/참조 검사, 저장 없음 |
| POST /api/admin/{kind}/csv-preview | `{csv:"헤더\n행"}` CSV 파싱·검사, 저장 없음 |
| POST /api/admin/{kind}/save | `{rows:[...]}` 검증 후 원자적 저장 |
| POST /api/admin/changes | `[{kind,rows},...]` 최대 10묶음·묶음당 100행, 여러 자료 종류를 한 transaction으로 저장 |
| DELETE /api/admin/{kind}/{id}?revision=0 | sectionals/payouts만 삭제, 변경 이력 저장, 204 |
| GET /api/admin/audit | 최근 100개 변경 전후 값·작성자·시각 |

입력 필드는 각 자료의 DB 열 이름을 사용합니다. `id`가 없으면 새 자료, 있으면 해당 행의 `revision`을 반드시 보내야 합니다. 오래된 버전은 409이며 연관 자료의 정합성 실패는 400으로 전체 롤백합니다. CSV는 UTF-8 200KB/100행 제한, 따옴표·쉼표·줄바꿈을 지원합니다. 출처/시각과 지원 필드 목록은 관리자 화면 및 docs/RACE_FEATURES.md에 있습니다. DB 충돌(예: 중복 조합·같은 말 출전)은 409입니다.

## 한국마사회 서울 결과 최초 반영
웹 API에 새 쓰기 엔드포인트를 공개하지 않습니다. 로컬 소유자가 `scripts/kra_import.py`로 검증/반영합니다. 사용법과 지원 범위는 [KRA_API.md](docs/KRA_API.md)를 참고하세요.

- HorseView: `kraId`(문자열 또는 null) 추가.
- EntryView: `trainerId`, `trainerName`(경주 당시 조교사, 없으면 null) 추가. `popularityRank`와 `winOdds`는 독립적으로 null일 수 있으며 하나라도 있으면 출처·시각은 필수입니다.
- 구간 API Run: `markers` 배열 추가. 각 항목은 `corner`, `position`, `cumulativeSeconds`, `source`입니다. 거리 좌표를 갖는 `points`와 구분합니다.
- 한국마사회 실제 경주의 합성 모델 예측 요청은 400입니다. 가져온 원본 레코드의 관리자 수정/삭제도 400으로 거부합니다.
