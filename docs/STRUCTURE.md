# 디렉터리
```text
backend/
  build.gradle, settings.gradle
  src/main/java/dev/keiba/
    Application, HealthController
    CatalogController → CatalogService → Horse/Race/EntryRepository
    AuthController → AuthService → MemberRepository
    SecurityConfig, JwtFilter, JwtService, RevokedTokenRepository
    FavoriteController → FavoriteService → FavoriteRepository
    PredictController → PredictService → FastAPI
    ApiExceptionHandler
  src/main/resources/db/migration/  # V1 スキーマ, V2 가상 기록, V3 회원
  src/test/java/dev/keiba/          # JWT 단위 테스트
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
각 도메인의 Controller는 HTTP 전송 계층, Service는 규칙 및 트랜잭션 경계, Repository는 영속성 계층입니다. 파일별 책임과 실제 호출 흐름은 ARCHITECTURE.md 및 LEARNING.md를 참조하세요.
