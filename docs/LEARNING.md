# 코드를 다시 구현할 때
1. migration의 FK/UNIQUE와 ERD를 먼저 읽습니다.
2. Horse와 Race는 Entry를 통해 다대다 관계를 맺습니다. 관계에 속한 기수/착순은 Entry 필드입니다.
3. CatalogController → CatalogService → Repository → MySQL 순서로 검색을 따라갑니다. Service의 readOnly 트랜잭션 안에서 lazy 연관을 DTO로 변환합니다.
4. AuthService는 회원 중복을 검사한 뒤 BCrypt 해시만 저장합니다. JWT 서명 키는 설정에서 주입되고 서버 시작 전에 검사합니다.
5. JwtFilter가 서명/만료/철회와 회원 존재를 확인하고 principal에 Long 회원 ID를 넣습니다. FavoriteService는 이 ID만 사용하므로 다른 회원 데이터를 지정하는 경로가 없습니다.
6. PredictService는 경주일 이전의 Entry만 조회하여 모델에 전달합니다. 미래 결과 누출을 막는 조건을 확인하세요.
7. React api 함수가 Bearer를 전달하고 HTTP 오류를 사용자에게 표시합니다. 공개 상세와 회원 전용 화면의 차이를 SecurityConfig와 비교하세요.
