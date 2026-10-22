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
