#!/usr/bin/env python3
"""Run the API integration tests against a throwaway schema and backend container.

The development database may hold real KRA data, while the tests expect the
fresh synthetic sample (40 horses, races 1..8). This runner never touches the
`keiba` schema:

1. creates a random schema `it_<hex>` and lets Flyway migrate it (V1..latest,
   including the synthetic sample),
2. starts a temporary backend container from the already built `keiba-backend`
   image on the Compose network (shared stateless ML service),
3. runs the tests with TEST_BASE_URL / KEIBA_DB pointing at that backend/schema,
4. removes the container and drops the schema, even on failure or Ctrl+C.

Usage (WSL, repository root, Compose stack running):
  python3 tests/run_isolated.py                 # all tests (unittest discover)
  python3 tests/run_isolated.py test_ml test_auth   # selected modules
"""
import json, os, subprocess, sys, time, uuid
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from backup import mysql

os.chdir(ROOT)
os.environ.setdefault('DOCKER_CONFIG', str(ROOT / '.runtime/docker'))
os.environ.pop('KEIBA_DB', None)  # the runner itself must address the real server, not a stale override


def wait_ready(base, container):
    for _ in range(150):
        try:
            with urlopen(base + '/horses', timeout=2) as response:
                if json.load(response)['totalElements'] == 40:
                    return
        except Exception:
            pass
        state = subprocess.run(['docker', 'inspect', '-f', '{{.State.Running}}', container], capture_output=True, text=True)
        if state.stdout.strip() != 'true':
            break
        time.sleep(1)
    subprocess.run(['docker', 'logs', '--tail', '80', container])
    raise SystemExit('격리 백엔드가 준비되지 않았습니다(위 로그 확인). 먼저 ./scripts/up.sh로 이미지를 빌드했는지 확인하세요.')


def main(selected):
    schema = 'it_' + uuid.uuid4().hex[:16]
    container = 'keiba-it-' + uuid.uuid4().hex[:12]
    dashboard = ROOT / '.runtime/kra/sync/dashboard'
    dashboard.mkdir(parents=True, exist_ok=True)
    try:
        mysql(f"CREATE DATABASE {schema} CHARACTER SET utf8mb4; GRANT ALL ON {schema}.* TO 'keiba'@'%';")
        networks = json.loads(subprocess.check_output(['docker', 'inspect', 'keiba-db-1']))[0]['NetworkSettings']['Networks']
        subprocess.run(['docker', 'run', '-d', '--name', container, '--network', next(iter(networks)), '--env-file', '.env',
                        '-e', f'DB_URL=jdbc:mysql://db:3306/{schema}?connectionTimeZone=UTC', '-e', 'DB_USER=keiba',
                        '-e', 'ML_URL=http://ml:8000', '-e', 'KRA_SYNC_DIR=/data/kra-sync',
                        '-v', f'{dashboard}:/data/kra-sync:ro', '-p', '127.0.0.1::8080', 'keiba-backend'],
                       check=True, stdout=subprocess.DEVNULL)
        port = json.loads(subprocess.check_output(['docker', 'inspect', container]))[0]['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
        base = f'http://127.0.0.1:{port}/api'
        wait_ready(base, container)
        print(f'격리 환경 준비: 스키마 {schema}, API {base}', flush=True)
        env = {**os.environ, 'TEST_BASE_URL': base, 'KEIBA_DB': schema}
        if selected:
            command = [sys.executable, '-m', 'unittest', '-v', *selected]
            return subprocess.run(command, cwd=ROOT / 'tests', env=env).returncode
        return subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], env=env).returncode
    finally:
        subprocess.run(['docker', 'rm', '-f', container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for sql in (f'DROP DATABASE IF EXISTS {schema};', f"REVOKE ALL PRIVILEGES ON {schema}.* FROM 'keiba'@'%';"):
            try:
                mysql(sql)
            except subprocess.CalledProcessError:
                pass  # e.g. CREATE/GRANT never ran; nothing to revoke
        print(f'격리 환경 정리 완료: 컨테이너·스키마 {schema} 삭제', flush=True)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
