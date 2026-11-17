# 디렉터리
```text
backend/
  build.gradle, settings.gradle
  src/main/java/dev/keiba/
    Application                      # 진입점. 하위 패키지를 컴포넌트·엔티티·리포지토리 스캔
    common/     ApiException(+Handler), HealthController, TimeConfig
    security/   SecurityConfig, JwtFilter, JwtService
    member/     AuthController → AuthService → MemberRepository, RevokedTokenRepository
    catalog/    Horse·Race·Entry 엔티티와 리포지토리
                CatalogController → CatalogService (말·경주·전적·혈통)
                RacingInsights(구간·주행 스타일·달력·배당), PeopleController(기수·조교사)
    analytics/  AnalyticsController → AnalyticsService (조건별 성적 비교)
    favorite/   FavoriteController → FavoriteService (말 즐겨찾기)
                WatchlistController → WatchlistService (관심 경주·내 일정)
    note/       MemberTools(+Controller) (개인 메모·사이트 알림)
    prediction/ PredictController → PredictService → FastAPI, PredictionFeatures
    admin/      CatalogAdmin(+Controller) (관리자 자료 편집·감사), KraStatusController
  src/main/resources/db/migration/   # Flyway V1~V12
  src/test/java/dev/keiba/<패키지>/   # 운영 코드와 같은 패키지에 단위 테스트
                                     # catalog/CatalogFixtures: 다른 패키지 테스트용 엔티티 생성기
frontend/
  src/main.tsx                     # 라우팅/조회 화면
  src/api.ts                       # 타입/HTTP/조회 훅
  src/auth.tsx                     # 메모리 세션/가입/로그인/즐겨찾기
  src/pedigree.tsx, prediction.tsx
  src/style.css
  e2e/portal.spec.ts               # 실제 브라우저 사용자 흐름
ml/
  train.py, app.py, test_model.py
  requirements.txt, requirements.lock, model-report.json
scripts/                           # 설치/빌드/시작/준비 확인
 tests/                            # 실제 MySQL API/부하/장애 검증
```
패키지는 기능(도메인) 기준으로 나눴습니다. 패키지 의존 방향은 `member·catalog → favorite → note`, `catalog → analytics·prediction`, 모두 `common`을 사용하며 순환 의존이 없습니다. 엔티티 필드는 패키지 내부 전용이고 다른 패키지는 public getter로 읽습니다.

각 도메인의 Controller는 HTTP 전송 계층, Service는 규칙 및 트랜잭션 경계, Repository는 영속성 계층입니다. 파일별 책임과 실제 호출 흐름은 ARCHITECTURE.md 및 LEARNING.md를 참조하세요.
