# 단계별 결과

| Phase | 실제 결과 | 검증 | 주요 파일 |
|---|---|---|---|
| 1 설계/환경 | SRS 전체 분석, 아키텍처/ERD/API/추적표, React–Spring–MySQL 초기 실행 | 초기 두 빌드 및 Vite 프록시 health 성공 | 루트 문서, build.gradle, compose.yaml |
| 2 조회 | 40두/8경주/96출전, 부분 검색/페이지/정렬/상세/완료 전적/착순, UI 이동 | API 3개 + 빌드 | Catalog*, 엔티티/Repository, V1~V2, main.tsx |
| 3 인증/즐겨찾기 | BCrypt/JWT/만료/로그아웃 철회/본인 목록과 추가·삭제 | API 누적 6개 + JWT 4개 | Auth*, Jwt*, Favorite*, V3, auth.tsx |
| 4 혈통 | 양쪽 3대, 누락 처리, 순환/깊이 제한, 트리 | API 누적 8개 + 빌드 | CatalogService.ancestors, pedigree.tsx |
| 5 ML | 합성 실험 학습/평가, 회원 Spring→FastAPI, 점수 정렬, 면책/503 | API 누적 9개, 모델 2개, 장애 검사 | ml/, Predict*, prediction.tsx |
| 6 통합 | Docker Compose 전체 실행, 문서의 재설치/재시작, 브라우저/모바일/부하, 의존성 보안 수정 | 세부 TEST_REPORT.md | scripts/, tests/, e2e/, README, CI |

## 해결한 오류
- 쓰기 불가능한 npm/Docker CLI 캐시 → 프로젝트 .runtime 사용.
- Gradle 프록시 CA/네트워크 → 신뢰 저장소 + 기존 프록시 속성, TLS 검증 유지.
- MySQL auto_increment PK를 참조하는 CHECK 불가 → 해당 CHECK 제거, 부모 FK 유지.
- JPA lazy proxy 직접 필드 읽기로 null 응답 → DTO 변환에서 명시적 unproxy.
- Docker BuildKit 네트워크 차이 → 검증된 실행 환경에서 빌드한 산출물과 checksum 검증 wheel을 runtime 이미지로 조립.
- 비 root ML/Nginx 파일 권한 → 이미지의 공개 앱 산출물 읽기 권한 설정.
- React Router/Vite 감사 결과 → 패치 버전 적용, npm audit 0건.
- 예정 경주가 과거 전적에 섞임 → 완료 착순과 오늘 이전 경주만 표시.

## 후속 개선 — 2026-10-22
- JWT 필수 claims·서명된 만료 토큰 HTTP 검증과 동시 즐겨찾기 중복 검사를 추가했습니다.
- 검색 wildcard 처리, 부모 조회 N+1, 예측 과거 기록 일괄 조회와 트랜잭션 범위를 개선했습니다.
- ML 응답의 누락/null/잘못된 점수와 시간초과를 한국어 503으로 처리하고 DB health가 실제 연결을 확인하도록 했습니다.
- 10,040두/1,008경주/20,096건의 격리 DB에서 50명·30초 조회: 14,017건, 오류 0, p95 246ms.
- DB 백업/별도 스키마 복원·체크섬 검사를 실행했습니다. HTTPS 운영 Compose, 프록시 로그인 제한, 실제 데이터 오프라인 평가 경로를 추가했습니다.
- 현재 검증: JUnit 10개, 실제 API 11개, ML 5개, Chromium 4개. 추가 운영 검증은 TEST_REPORT.md 참조.

## 남은 범위와 해결 조건
사용자가 서버·도메인·사용 허가된 데이터가 없음을 확인했습니다. 서버·도메인을 확보하면 docs/DEPLOYMENT.md의 운영 override로 배포하고 공개 인증서·외부 사용자 흐름·별도 서버 복구를 검증합니다. 허가된 데이터가 준비되면 docs/ML_DATA.md의 CSV 계약과 시간순 평가를 사용하며 결과를 확인한 뒤 서비스 반영을 결정합니다.

현재 로컬 부하 검사는 30초이므로 장기 부하·운영 성능을 보장하지 않습니다. Safari/Firefox, 원격 GitHub Actions 실행, 새 cloud task에서의 볼륨 복원은 미검증입니다. 전체 기능이 완벽하다고 표현하지 않으며 확인한 범위와 외부 조건을 구분합니다.
