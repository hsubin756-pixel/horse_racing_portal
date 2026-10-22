# 요구사항 추적표

원본 SRS의 전체 ID. 상태는 실제 검증 후 갱신합니다. 테스트 세부 결과는 TEST_REPORT.md를 참조하세요.

| ID | 우선순위 | 요구사항 | 구현 위치(계획) | 상태 |
|---|---|---|---|---|
| FR-HORSE-01 | Must | 말 이름 부분 일치 | CatalogService.horses | 계획 |
| FR-HORSE-02 | Must | 말 상세/부모/조교사 | CatalogService.horse | 계획 |
| FR-HORSE-03 | Must | 최신 전적 순 | CatalogService.history | 계획 |
| FR-HORSE-04 | Should | 검색 결과 없음 안내 | HorseList | 계획 |
| FR-HORSE-05 | Could | 성별/생년 정렬 | CatalogService.horses | 계획 |
| FR-RACE-01 | Must | 이름/일자 검색 | CatalogService.races | 계획 |
| FR-RACE-02 | Must | 출주마와 착순 | CatalogService.race | 계획 |
| FR-AUTH-01 | Must | 회원가입 | AuthService.register | 계획 |
| FR-AUTH-02 | Must | 이메일 중복 거부 | AuthService.register | 계획 |
| FR-AUTH-03 | Must | 로그인/JWT | AuthService.login | 계획 |
| FR-AUTH-04 | Must | 인증 실패 안내 | AuthService.login | 계획 |
| FR-AUTH-05 | Should | 로그아웃/철회 | AuthService.logout | 계획 |
| FR-FAV-01 | Must | 즐겨찾기 추가 | FavoriteService.add | 계획 |
| FR-FAV-02 | Must | 본인 목록 | FavoriteService.list | 계획 |
| FR-FAV-03 | Must | 본인 삭제 | FavoriteService.remove | 계획 |
| FR-FAV-04 | Should | 중복 거부 | FavoriteService.add | 계획 |
| FR-PED-01 | Should | 부모 조회 | CatalogService.pedigree | 계획 |
| FR-PED-02 | Should | 3대 조상 | CatalogService.pedigree | 계획 |
| FR-PED-03 | Could | 트리 시각화 | Pedigree | 계획 |
| FR-PED-04 | Should | 누락 정보 없음 | Pedigree | 계획 |
| FR-ML-01 | Could | 회원 예측 요청 | PredictService.predict | 계획 |
| FR-ML-02 | Could | 점수 반환 | ml/app.py | 계획 |
| FR-ML-03 | Could | 점수 정렬 | PredictService.predict | 계획 |
| FR-ML-04 | Could | 면책 안내 | Prediction | 계획 |
| FR-ML-05 | Won’t | 정확도 보장 | 제외 | 제외 |
| NFR-PERF-01 | Should | 검색 3초 이내 | 검색 지연 측정 | 계획 |
| NFR-PERF-02 | Could | 동시 50명 | 부하 검증 | 계획 |
| NFR-SEC-01 | Must | 비밀번호 해시 | BCryptPasswordEncoder | 계획 |
| NFR-SEC-02 | Must | 회원 API 서버 인증 | SecurityConfig / JwtFilter | 계획 |
| NFR-SEC-03 | Should | 토큰 만료 | JwtService | 계획 |
| NFR-ETC-01 | Should | 이해 가능한 안내 | ApiExceptionHandler / UI | 계획 |
| NFR-ETC-02 | Could | 모바일 대응 | style.css | 계획 |
