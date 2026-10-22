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

## 남은 범위
실서비스 배포, HTTPS/운영 DB 백업 및 복구, 실제 데이터 기반 ML 평가는 수행하지 않았습니다. GitHub Actions 구성은 저장했으나 원격 runner 실행은 확인하지 않았습니다. 원격 저장소에는 아직 커밋이 없고 개발 결과는 로컬 기능별 커밋입니다. 새 cloud task 복원/원격 재현은 별도 검증이 필요합니다. 원격 푸시 없이 저장소를 초기화하거나 기존 로컬 커밋을 버리지 않습니다.

다음 단계는 포트폴리오 검토 후 GitHub 반영과 실제 배포 환경 검증이며, Must 구현은 남아 있지 않습니다.
