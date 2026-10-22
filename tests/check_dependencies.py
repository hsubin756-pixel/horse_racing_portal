"""Sequential development outage drill. Restores each service in finally.
Run without concurrent API/browser/backup/load tests.
"""
import os,subprocess
from pathlib import Path
from test_catalog import request
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);os.environ.setdefault('DOCKER_CONFIG',str(ROOT/'.runtime/docker'))
def run(*args):subprocess.run(args,check=True)
run('python3','scripts/wait-ready.py')
for service in ('db','ml'):
 try:
  run('docker','compose','stop',service)
  if service=='db':
   status,data=request('/health');assert status==503 and '데이터베이스' in data['message'],(status,data)
   print('Real database outage: readiness returns Korean 503',flush=True)
  else:run('python3','tests/check_outage.py')
 finally:
  run('docker','compose','start',service)
  run('python3','scripts/wait-ready.py')
