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
