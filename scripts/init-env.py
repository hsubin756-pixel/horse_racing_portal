from pathlib import Path
import secrets, os
p=Path(__file__).resolve().parents[1]/'.env'
if not p.exists():
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:
  for k in ['DB_PASSWORD','MYSQL_ROOT_PASSWORD','JWT_SECRET']:
   f.write(k+'='+secrets.token_urlsafe(48)+'\n')
 print('로컬 .env 생성 완료 (값은 표시하지 않습니다)')
else: print('기존 .env 보존')
