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

현재 값은 고정된 가상 데이터입니다. 실제 배당 API 연동·실시간 갱신·복승/삼복승 등 조합별 확정 환급표는 구현 범위에 포함하지 않습니다. 실제 자료 연동 시 공급자의 사용 허가, 시장 종류, 마감 여부와 기준 시각을 확인하고 인기·배당·출처·시각을 원자적으로 갱신해야 합니다.
