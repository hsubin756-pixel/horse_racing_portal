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
실서비스 배포, HTTPS/운영 DB 백업 및 복구, 실제 데이터 기반 ML 평가는 수행하지 않았습니다. GitHub Actions 구성은 저장했으나 원격 runner 실행은 확인하지 않았습니다. GitHub main 게시 후 원격 복제를 통해 동일한 Git 트리와 추적 파일 93개를 확인했습니다. 비밀값과 런타임 캐시는 게시에서 제외했습니다. 같은 Git 트리의 소스를 기존 설치/캐시 없이 별도 디렉터리에 추출해 전체 빌드를 검증했습니다. 새 cloud task의 프로세스/DB 볼륨 복원은 별도 검증이 필요합니다.

GitHub 반영과 소스 재현성 검증을 마쳤습니다. 다음 단계는 배포 대상 서버·도메인이 정해진 뒤 외부 배포, HTTPS, 백업·복구를 검증하는 것입니다. Must 구현은 남아 있지 않습니다.
