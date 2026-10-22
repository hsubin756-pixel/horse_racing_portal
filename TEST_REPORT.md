# 실제 검증 기록
2026-10-22, Codex cloud Linux. 합성 데이터 전용.

## Phase 1
- Gradle 8.14.3 / JDK 21: bootJar 성공.
- React / Vite / TypeScript: npm run build 성공.
- MySQL 8.4 Docker healthy, Spring datasource/Hibernate 초기화 성공.
- Vite 프록시 GET /api/health → 200, {status:ok} 확인.
- 초기 npm 캐시 권한 오류: .runtime/npm으로 변경.
- 초기 Gradle TLS 오류: 제공된 프록시 CA를 전용 truststore에 추가. 검증 비활성화 없음.

기능 검증은 후속 단계에서 기록합니다.

## Phase 2
- bootJar / React production build 성공.
- real MySQL HTTP black-box 테스트 3개 통과 (검색, 20건 페이지 분리, 생년 정렬, 빈 결과, 부모 상세, 역순 전적, 경주 일자 검색, 12개 착순 및 입력 오류).
- Vite /api 프록시 경주 상세 조회에서 출주마 12건 확인.
- 초기 SQL CHECK의 MySQL auto_increment 제약과 JPA lazy proxy 필드 접근으로 null 응답되는 결함을 수정하고 동일 테스트 재실행 통과.

## Phase 3
- Gradle build 성공, JWT 단위 테스트 4개 통과 (서명/claims, 만료 거부, 다른 키 거부, 약한 키 설정 거부).
- 실제 MySQL API 테스트 누적 6개 통과. 회원가입·중복·로그인 실패·잘못된 입력·즐겨찾기 추가/삭제·다른 회원 목록 분리·다른 회원 삭제 영향 없음·로그아웃 토큰 재사용 거부·변조 토큰 거부를 검증.
- SQL로 저장된 비밀번호가 BCrypt cost 12 형식인지 검사, 위반 0건. 비밀값 로그 출력 없음.
- React production build 통과. 브라우저 상호작용 검증은 Phase 6에서 진행.

## Phase 4
- Gradle build / React production build 통과.
- MySQL API 누적 8개 테스트 통과. 3대 경로 40→26→12→조상, 깊이 3 종료, 양쪽 부모, 완전/부분 누락, 없는 말 404 검증.
- 재귀에는 최대 깊이와 경로별 방문 집합을 함께 두어 잘못된 순환 데이터에도 무한 재귀를 방지합니다.

## Phase 5
- Gradle build / React build 성공. MySQL API 누적 9개, FastAPI/모델 테스트 2개 통과.
- 회원 예측 요청, 12두 점수 범위/내림차순, 합성 실험 표시, 없는 경주 404, 독립적으로 재구성한 과거 전적 입력과 FastAPI 직접 결과 일치를 검증.
- 직접 시작한 ML 프로세스를 종료한 상태에서 Spring 예측 요청 → 503 및 한국어 일시 장애 안내 확인.
- 합성 실험: 1,920 학습 / 480 시간순 홀드아웃. Accuracy 0.875 (다수 클래스 baseline도 0.875), ROC-AUC 0.736468, Brier 0.101124. 실제 데이터나 예측 능력 검증 없음. 상세: ml/model-report.json.


## Phase 6 — 최종 통합
- scripts/build.sh 성공: JDK 21/Gradle build, JWT JUnit 4개, React TypeScript/production build, 고정 Python 의존성 설치, wheel 다운로드 및 SHA-256 생성, 모델 학습, ML 테스트 2개.
- 실제 runtime 이미지 3개 조립 성공. ML 의존성은 Dockerfile에서 --no-index --require-hashes로 설치. MySQL/ML healthy 및 Spring–DB–Nginx 프록시의 실제 말 조회 확인.
- 최종 Compose의 실제 MySQL API 테스트 9개 통과(모의 API/메모리 DB 사용 없음).
- Playwright Chromium: 공개 탐색, 가입/로그인/즐겨찾기/예측/로그아웃, 375px 모바일 7개 화면 검증. 최종 결과는 아래에 기록합니다.
- 동시 검색 50요청 모두 200: median 95.85ms, p95 163.81ms, max 182.24ms. 말 40두/경주 8개인 로컬 API 측정이며 실제 운영 50명 성능 보장은 아닙니다.
- check_restart.py가 전체 서비스를 중지한 뒤 문서의 scripts/up.sh를 실제로 재실행. 회원, 즐겨찾기, 로그아웃 토큰 철회, 샘플 40두/8경주가 유지됨을 확인. 같은 머신/동일 Docker 볼륨 검증이며 새 cloud task 복원 검증은 아닙니다.
- Compose ML 중지 → 한국어 503 → 재시작 및 준비 확인 성공. OpenAPI JSON 13개 경로 응답 확인.
- npm audit에서 high 3건 발견 → react-router-dom 7.18.4, Vite 7.3.7 적용 후 취약점 0건. npm 의존성 감사 결과이며 전체 시스템 무취약 보장이 아닙니다.
- 한 차례 장애 주입과 브라우저 예측 검사를 동시에 실행하여 예측 화면 검사가 실패. 서비스 복구 후 검사를 단독으로 재실행했습니다. 애플리케이션 성공으로 오인하지 않았습니다.

## 검증하지 않은 사항
외부 서버 배포/HTTPS/운영 데이터 복구, 실제 경마 ML 정확도, 대규모 DB 및 장기 부하, 다른 브라우저/Safari/Firefox, 원격 GitHub Actions 실행, 새 cloud task에서의 로컬 커밋 및 Docker 볼륨 복원. 초기 온보딩 당시 원격 저장소는 비어 있었으며, 후속 원격 게시·복제 결과는 아래에 기록합니다.

최종 단독 브라우저 실행: **3 passed (6.1s)**, 검색 요청부터 결과 표시까지 **167ms**. 사용자 흐름과 모바일 검증 모두 통과했습니다. 캡처는 docs/images에 보관했습니다.


## 후속 게시 및 재현성 확인 — 2026-10-22
- 실행 중인 Compose 서비스의 준비 확인 및 실제 MySQL API 테스트 9개 재실행 통과.
- 커밋 e2d3a3d의 소스만 git archive로 새 디렉터리에 추출. 기존 .env, .runtime, node_modules, build 산출물 없이 scripts/build.sh 실행 성공.
- 새 디렉터리에서 Gradle build/JWT 4개 테스트, Vite 7.3.7 production build, 고정 Python 의존성 신규 설치, 모델 학습/평가와 ML 2개 테스트 통과.
- GitHub main으로 푸시 성공. 원격 refs/heads/main의 전체 SHA가 로컬 HEAD와 일치함을 확인.
- GitHub에서 main을 새 디렉터리에 실제 clone하여 소스의 Git tree 일치 및 추적 파일 93개를 확인. .env와 .runtime은 원격 복제에 포함되지 않음.
- 위 빌드는 원격 복제와 동일한 Git tree의 소스 추출본에서 실행했으며, 원격 CI runner나 새 cloud task에서 실행한 것으로 간주하지 않습니다.
- GitHub API 요청은 Forbidden으로 거부되어 Actions 실행 결과 조회는 미검증. 저장소의 Actions 화면에서 확인할 수 있습니다.

## 한계 개선 및 추가 검증 — 2026-10-22
이 절이 최신 검증 범위입니다. 앞 절의 결과는 당시 기록으로 보존합니다.

- JUnit **10개 통과**: JWT 필수 claims/유효성, 누락·null·다른 말·범위 밖 ML 응답, 정상 응답, 실제 HTTP 응답 지연 4초에 대한 timeout, DB readiness 성공/실패.
- 실제 Spring/MySQL API **11개 통과**: 기존 인수 흐름에 검색 `%`·`_`·SQL 형태 문자열의 문자 검색, 길이/페이지 경계, 유효한 키로 서명했지만 exp/iat/jti/sub가 누락·변형된 토큰의 HTTP 401, 동시 즐겨찾기 추가 두 요청의 201/409와 한 행 유지 검사를 추가했습니다.
- ML **5개 통과**: 중복 말 ID 거부, 같은 날짜/현재 결과 유입 방지, 중복·불완전 CSV 거부, 시간순 평가 분리와 출처/SHA 기록. 실제 데이터가 아닌 생성 테스트 CSV로 평가 도구를 검사했습니다.
- Chromium **4개 통과 (14.8초)**: 기존 사용자 흐름/모바일 7개 화면에 요청 실패 시 한국어 복구 안내를 추가. 검색 결과 표시 202ms. 일부 시간에 부하 시험도 실행 중이었으며 이 환경의 관측값입니다.
- 격리 DB에 **10,040두 / 1,008경주 / 20,096출전**을 적재하고 별도 backend 컨테이너에서 **50명·30.1초** 조회. **14,017요청, 오류 0, 약 465.6req/s, p95 246.2ms, p99 341.4ms, 최대 666.3ms**. 스키마·컨테이너·권한은 검사 후 제거했고 원본 40두 DB는 유지했습니다. 원시 요약: docs/performance-2026-10-22.json. 실시간 사용자가 생각 없이 다음 조회를 보내는 closed-loop 시험이며 로그인/예측 부하나 장기 soak 시험은 아닙니다.
- `scripts/backup.py` 실행: 단일 transaction dump → 별도 스키마 복원 → 모든 테이블의 행 수/체크섬 일치 확인 → 임시 스키마 제거. 원본 회원·즐겨찾기·철회 토큰을 보존했습니다. 백업/보고서는 비공개 `.runtime/backups`에만 있습니다. 다른 서버의 재해 복구는 미검증입니다.
- 운영 Compose 해석 검사: gateway 80/443만 공개, DB/API/ML/프론트 직접 포트 없음. Caddy 2.10.2 설정 validation 통과.
- `check_tls.py`: 임시 Caddy의 로컬 CA를 명시적으로 신뢰하며 **호스트명/인증서 검증을 켠 HTTPS API 조회와 HSTS 확인**. 첫 시도는 tmpfs 인증서를 docker cp로 추출하지 못해 실패했고 docker exec로 공개 CA 파일만 읽도록 수정한 뒤 통과했습니다. 공개 인증서/도메인 배포 검증은 아닙니다.
- `check_dependencies.py`: 실제 DB를 중지했을 때 health의 한국어 503, 실제 ML을 중지했을 때 예측의 한국어 503을 확인했습니다. 각 서비스는 finally에서 재시작하고 준비 확인을 통과했습니다.
- `check_edge.py`: 프록시 로그인 제한 초과 시 한국어 JSON HTTP 429 확인. backend 직접 포트는 개발용이며 이 제한은 프록시에 적용됩니다.
- React TypeScript/production build 및 backend bootJar/runtime 이미지 조립 통과. CI에 확장 부하·백업 복원·프록시·TLS·의존 서비스 장애 검사를 추가했습니다. 원격 runner의 성공을 주장하지 않습니다.

### 해결한 코드 문제
JWT 만료 필드가 없는 서명 토큰의 허용 가능성을 차단했습니다. ML 점수 누락이 0으로 해석되거나 null 항목이 500이 되는 경로를 막았습니다. 경주 검색의 SQL wildcard 문자를 일반 부분 문자열처럼 처리합니다. 부모 정보 목록의 N+1 조회를 줄이고 예측 전적을 일괄 조회하며 원격 모델을 기다리는 동안 DB transaction을 유지하지 않습니다. API health는 DB 연결을 확인하고 브라우저 네트워크 실패는 한국어로 표시합니다.

### 남은 한계와 다음 조건
서버·도메인 및 허가된 경마 데이터가 없다는 사용자 답변에 따라 공개 배포·공개 인증서·운영 복구·실제 ML 성능 평가는 진행하지 않았습니다. 실행 절차는 docs/DEPLOYMENT.md와 docs/ML_DATA.md에 있습니다. Firefox/Safari, 장기 부하, 원격 Actions, 새 cloud task 볼륨 복원은 여전히 미검증입니다. 모든 SRS 입력/장애 조합에 대한 무결함 보장은 하지 않습니다.
