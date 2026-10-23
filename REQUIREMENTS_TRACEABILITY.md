# 요구사항 추적표

원본 SRS의 전체 32개 ID(기능 25개, 비기능 7개). 테스트 세부 결과는 TEST_REPORT.md를 참조하세요.

| ID | 우선순위 | 요구사항 | 구현 위치 | 상태 |
|---|---|---|---|---|
| FR-HORSE-01 | Must | 말 이름 부분 일치 | CatalogService.horses | 구현·검증 |
| FR-HORSE-02 | Must | 말 상세/부모/조교사 | CatalogService.horse | 구현·검증 |
| FR-HORSE-03 | Must | 최신 전적 순 | CatalogService.history | 구현·검증 |
| FR-HORSE-04 | Should | 검색 결과 없음 안내 | HorseList | 구현·검증 |
| FR-HORSE-05 | Could | 성별/생년 정렬 | CatalogService.horses | 구현·검증 |
| FR-RACE-01 | Must | 이름/일자 검색 | CatalogService.races | 구현·검증 |
| FR-RACE-02 | Must | 출주마와 착순 | CatalogService.race | 구현·검증 |
| FR-AUTH-01 | Must | 회원가입 | AuthService.register | 구현·검증 |
| FR-AUTH-02 | Must | 이메일 중복 거부 | AuthService.register | 구현·검증 |
| FR-AUTH-03 | Must | 로그인/JWT | AuthService.login | 구현·검증 |
| FR-AUTH-04 | Must | 인증 실패 안내 | AuthService.login | 구현·검증 |
| FR-AUTH-05 | Should | 로그아웃/철회 | AuthService.logout | 구현·검증 |
| FR-FAV-01 | Must | 즐겨찾기 추가 | FavoriteService.add | 구현·검증 |
| FR-FAV-02 | Must | 본인 목록 | FavoriteService.list | 구현·검증 |
| FR-FAV-03 | Must | 본인 삭제 | FavoriteService.remove | 구현·검증 |
| FR-FAV-04 | Should | 중복 거부 | FavoriteService.add | 구현·검증 |
| FR-PED-01 | Should | 부모 조회 | CatalogService.pedigree | 구현·검증 |
| FR-PED-02 | Should | 3대 조상 | CatalogService.pedigree | 구현·검증 |
| FR-PED-03 | Could | 트리 시각화 | Pedigree | 구현·검증 |
| FR-PED-04 | Should | 누락 정보 없음 | Pedigree | 구현·검증 |
| FR-ML-01 | Could | 회원 예측 요청 | PredictService.predict | 구현·검증 |
| FR-ML-02 | Could | 점수 반환 | ml/app.py | 구현·검증 |
| FR-ML-03 | Could | 점수 정렬 | PredictService.predict | 구현·검증 |
| FR-ML-04 | Could | 면책 안내 | Prediction | 구현·검증 |
| FR-ML-05 | Won’t | 정확도 보장 | 제외 | 제외 |
| NFR-PERF-01 | Should | 검색 3초 이내 | tests/performance.py / portal.spec.ts | 개발 데이터 검증, 운영 미검증 |
| NFR-PERF-02 | Could | 동시 50명 | tests/performance.py | 확장 합성 DB 동시 50명·30초 통과, 운영 미검증 |
| NFR-SEC-01 | Must | 비밀번호 해시 | BCryptPasswordEncoder | 구현·검증 |
| NFR-SEC-02 | Must | 회원 API 서버 인증 | SecurityConfig / JwtFilter | 구현·검증 |
| NFR-SEC-03 | Should | 토큰 만료 | JwtService | 구현·검증 |
| NFR-ETC-01 | Should | 이해 가능한 안내 | ApiExceptionHandler / UI | 구현·검증 |
| NFR-ETC-02 | Could | 모바일 대응 | style.css | 구현·검증 |

## 검증 연결
| ID 그룹 | 실행한 검증 |
|---|---|
| FR-HORSE-01~05, FR-RACE-01~02 | tests/test_catalog.py, frontend/e2e/portal.spec.ts 공개 탐색 |
| FR-AUTH-01~05, FR-FAV-01~04 | tests/test_auth.py, tests/test_token_claims.py, JwtServiceTest, 브라우저 가입/로그인/즐겨찾기/로그아웃, check_restart.py |
| FR-PED-01~04 | tests/test_pedigree.py, 브라우저 혈통/모바일 검사 |
| FR-ML-01~04 | tests/test_ml.py, ml/test_model.py, PredictServiceTest, check_outage.py, 브라우저 회원 예측 |
| NFR-SEC-01~03 | DB 해시 형식, 토큰 위변조·만료·철회, 소유권 분리, UTF-8 길이, 유효하지 않은 요청 검사 |
| NFR-PERF-01~02 | 10,040두/1,008경주/20,096출전에서 동시 50명·30초 조회, 브라우저 검색 표시 시간. 로컬 환경 한정 |
| NFR-ETC-01~02 | 한국어 오류/빈 결과/누락 표시, 375px 7개 화면 가로 넘침 검사 |

Must 14개는 실제 구현 및 위 검증으로 확인했습니다. Should 9개와 Could 8개도 구현했으며 성능은 측정 환경에 한정됩니다. Won't 1개(FR-ML-05 정확도 보장)는 제외했습니다. 실시간 오즈 수집/커뮤니티는 구현하지 않았습니다. 후속 사용자 요청으로 가상 인기·단승 배당 스냅샷 표시를 추가했습니다. 외부 배포/새 task 복원은 검증 범위에 포함하지 않습니다.

## 검증 상태 해석
위의 “구현·검증”은 연결된 대표 인수 시나리오가 통과했다는 뜻이며 모든 입력·운영 상황에 대한 완전성 보장이 아닙니다. 인증 claims 누락/만료/위변조, 즐겨찾기 동시 중복, ML 잘못된 응답/시간초과, 검색 특수문자, 브라우저 네트워크 오류를 추가 검사했습니다. 보안·성능·브라우저 결과의 범위는 TEST_REPORT.md의 최신 개선 기록을 따릅니다. 공개 배포·실데이터 평가·다른 브라우저·장기 부하는 아직 미검증입니다.

## 후속 사용자 요청 — 인기와 단승 배당
원본 32개 ID와 별개로 출주마 및 과거 전적의 인기·단승 배당·출처·기준 시각, 인기/배당 정렬, null 미제공 처리를 추가했습니다. `V4__entry_odds.sql`, Entry/CatalogService, EntryTable/RacePage에 구현했으며 `tests/test_odds.py`와 브라우저의 배당 시나리오로 검증합니다. 실시간 데이터 공급원과 확정 환급표는 아직 없습니다.


## 후속 사용자 요청 — 비교·통계·관심 일정
원본 SRS의 ID를 변경하지 않고 아래 추가 기능을 추적합니다.

| 추가 요청 | 구현 | 검증 |
|---|---|---|
| 최대 4두 비교, 최근 5경주·거리/주로별 기록 | AnalyticsService/Controller, analytics.tsx `/compare` | AnalyticsServiceTest, test_analytics.py, 브라우저 비교/모바일 |
| 말·기수 조건별 성적, 기간/거리/주로 필터 | AnalyticsService/Controller, analytics.tsx `/statistics` | 같은 통계 단위/API 검사, 브라우저 기수 변경·필터·빈 전적 |
| 관심 경주 저장/목록/삭제와 회원별 분리 | V5, RaceFavorite*, WatchlistService/Controller, watchlist.tsx | test_watchlist.py 소유권/중복/인증/동시 요청, 브라우저 저장·삭제 |
| 관심 말 출전과 저장 경주의 예정 일정 병합 | Entry/RaceRepository, WatchlistService, `/watchlist` | WatchlistServiceTest 시간대/병합, test_watchlist.py, 브라우저 일정 |
| 넷케이바와 기능 차이 확인 | docs/NETKEIBA_COMPARISON.md | 현재 포털 구현은 코드/실행으로 확인. 넷케이바 최신 화면은 프록시 403으로 미확인 |

가상 데이터 기반 기능 검증입니다. 실시간 인기·배당/조합별 환급·상세 출마표·뉴스/영상/커뮤니티·외부 알림은 이번 추가 기능에 포함되지 않습니다.


## 후속 사용자 요청 — 제안 8개 전체와 구간 기록
아래가 2026-10-23 확장 후의 상태이며 앞 절의 미구현 기록은 당시 시점의 범위입니다.

| 추가 기능 | 구현 근거 | 검증 |
|---|---|---|
| 출마표 상세·경주/출전 상태 | V6, Race/Entry, CatalogService, RaceFacts/EntryTable | 기존 API 회귀 + test_extensions, 브라우저 출마표 |
| 관리자 입력·CSV·미리보기·이력 | CatalogAdmin, admin.tsx, scripts/admin.py | 권한/회수·CSV·원자성·동시 수정 API, CSV 단위, 관리자 브라우저 |
| 조합별 예상/확정/환불 | payout, V8, CatalogAdmin.validateRace, Payouts | 착순/조합·NULL DB 제약·삭제 권한·브라우저 금액 |
| 전체 개최 캘린더 | RacingInsights.calendar, Calendar | 월/경마장 API·브라우저 이동·모바일 |
| 개인 메모·태그 | personal_note, MemberTools, Notes | 소유권·검색·정정 충돌·삭제 API, 메모 브라우저 |
| 기수·조교사 프로필/순위 | person/FK, PeopleController, People/PersonProfile | ID·조건 집계 API·프로필 브라우저 |
| 성적 추이 | HorseRunningStyle의 경주 선택 막대 | 날짜/착순 선택과 구간 표 전환 브라우저 |
| 사이트 내 알림 | site_notification, MemberTools, Inbox | 7일 일정 생성·중복·읽음 소유권·취소 상태, 브라우저 알림함 |
| 구간 통과/시간·주행 스타일 | sectional, RacingInsights, RunDetail | 위치 분류 경계 단위·실제 시간 차 API·누락·미확정·표본 수·그래프/표 브라우저 |

기본 합성 데이터와 관리자 등록 기능의 검증입니다. 각질은 공식 판정이 아닌 명시적인 초반 위치 규칙입니다. 실제 데이터 공급/갱신, 외부 알림 발송, 뉴스/영상/커뮤니티, 수득상금·과거 담당 조교사 이력은 여전히 별도 범위입니다.
