"""Start/stop only this project's local backend; do not print configuration values."""
from pathlib import Path
import os,signal,subprocess,sys,time,urllib.request
root=Path(__file__).resolve().parents[1]; runtime=root/'.runtime'; runtime.mkdir(exist_ok=True)
pidfile=runtime/'backend.pid'
if pidfile.exists():
 pid=int(pidfile.read_text())
 try:
  cmd=Path(f'/proc/{pid}/cmdline').read_bytes()
  if b'keiba-portal-0.1.0.jar' in cmd:
   os.kill(pid,signal.SIGTERM)
   for _ in range(60):
    if not Path(f'/proc/{pid}').exists(): break
    time.sleep(.1)
 except FileNotFoundError: pass
 pidfile.unlink()
if 'stop' in sys.argv: sys.exit(0)
env=os.environ.copy()
for line in (root/'.env').read_text().splitlines():
 if line and not line.startswith('#'):
  k,v=line.split('=',1);env[k]=v
with (runtime/'backend.log').open('w') as log:
 p=subprocess.Popen(['java','-jar',str(root/'backend/build/libs/keiba-portal-0.1.0.jar')],env=env,stdout=log,stderr=log,start_new_session=True)
pidfile.write_text(str(p.pid))
for _ in range(100):
 if p.poll() is not None: raise SystemExit('Backend failed; inspect .runtime/backend.log')
 try:
  with urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=1) as r:
   if r.status==200: print('Backend ready');sys.exit(0)
 except Exception: time.sleep(.3)
raise SystemExit('Backend readiness timeout; inspect .runtime/backend.log')
