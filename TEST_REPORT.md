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
