import json,time,urllib.request
for port,path in [(8080,'/api/health'),(8000,'/health'),(5173,'/api/horses')]:
 for attempt in range(120):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=2) as r:
    result=json.load(r)
    if (result.get('status')=='ok' if 'health' in path else result.get('totalElements',0)>=40):break
  except Exception:pass
  time.sleep(.5)
 else:raise SystemExit(f'Readiness failed on port {port}; inspect docker compose logs')
print('MySQL-backed catalog, backend, ML, and frontend proxy ready')
