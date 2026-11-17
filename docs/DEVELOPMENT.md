# 개발 환경과 검증 절차

README 재구성(2026-11-17) 때 옮긴 상세 절차입니다.

## 실행 스크립트 동작

이미 체크아웃한 클라우드 환경에서는 `/workspace/horse_racing_portal`로 이동한 뒤 `./scripts/up.sh`를 실행합니다. 이 스크립트는 기존 `.env`를 보존하며, 없으면 개발용 비밀값을 무작위로 생성합니다. `.env`는 0600 권한이고 Git에서 제외됩니다. 이미지 빌드, MySQL/Flyway 샘플 적재, 서비스 시작 및 실제 API 준비 확인까지 실행합니다. 처음 빌드는 의존성 다운로드가 필요합니다. scripts/build.sh가 백엔드 JUnit/ML 테스트와 프론트 빌드를 실행한 뒤 Docker runtime 이미지를 조립합니다.

웹 포트 5173, API 8080, ML 8000, DB 3306은 모두 호스트 loopback에만 바인딩됩니다. 이 클라우드 온보딩 UI에서는 로컬 웹 미리보기를 제공하지 않습니다. 브라우저 접근이 가능한 별도 개발 머신에서는 5173 포트로 접속하세요. 신규 회원은 회원가입 화면에서 직접 생성합니다. 기본 관리자/고정 비밀번호 계정은 없습니다.

```bash
docker compose ps
docker compose logs --tail=80 backend
docker compose stop           # 데이터 볼륨 보존
docker compose up -d          # 이미 빌드된 서비스 재시작
python3 scripts/wait-ready.py # MySQL 기반 조회·API·ML·웹 프록시 확인
```

`docker compose down -v`는 DB 데이터를 삭제하므로 사용하지 마세요. 환경의 live 프로세스는 스냅샷에 보존된다고 가정하지 않습니다. 새 task에서는 기존 체크아웃을 사용하고 `docker compose up -d` 후 준비 확인을 실행하세요. 별도 Git worktree는 필요하지 않습니다.


## 로컬 개발 서버
```bash
python3 scripts/init-env.py
python3 scripts/prepare-build.py
mkdir -p .runtime/docker
./scripts/build.sh
DOCKER_CONFIG="$PWD/.runtime/docker" docker compose up -d db ml
./scripts/gradle.sh build
python3 scripts/backend-local.py
cd frontend
npm ci --cache ../.runtime/npm
npm run dev
```
이미 전체 Compose가 실행 중이면 backend/frontend 컨테이너를 먼저 중지해 포트 충돌을 해소하세요. 로컬 백엔드는 `python3 scripts/backend-local.py stop`으로 종료합니다. Vite 프록시가 8080 API를 전달합니다. ML 모델은 컨테이너에서 학습되므로 호스트 Python 학습은 필수가 아닙니다.

```bash
# 별도로 호스트에서 ML 개발/테스트 (Python 3.12 또는 3.13 필요: 고정된 numpy 2.2.6이 3.14용 휠을 제공하지 않음)
python3.12 -m venv .runtime/ml-venv   # 없으면: curl -LsSf https://astral.sh/uv/install.sh | sh && ~/.local/bin/uv python install 3.12
.runtime/ml-venv/bin/pip install --cache-dir .runtime/pip -r ml/requirements.lock
.runtime/ml-venv/bin/python ml/train.py
.runtime/ml-venv/bin/python -m unittest discover -s ml -p 'test_*.py' -v
```

## 전체 검증
```bash
./scripts/gradle.sh build
python3 -m unittest discover -s tests -v
python3 tests/scale.py # 별도 DB에서 10,040두/50명/30초 부하
python3 scripts/backup.py # 원본을 유지하며 별도 스키마 복원 확인
python3 scripts/kra_backup.py create # DB + KRA 원본/진행 기록 통합 백업
cd frontend
npm run build
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium npm run test:e2e
```
API 테스트는 실행 중인 Spring/MySQL/FastAPI를 사용하며 테스트 회원을 생성합니다. 테스트 전용/개발 DB에서 실행하세요. Playwright는 시스템 Chromium을 사용하거나 `npx playwright install chromium` 후 실행할 수 있습니다. 전자는 클라우드 다운로드 정책 변경 없이 사용할 수 있습니다. ML 장애 검증은 `docker compose stop ml`, `python3 tests/check_outage.py`, `docker compose start ml`, 준비 확인 순서입니다.

