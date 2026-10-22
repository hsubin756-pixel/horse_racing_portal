"""Repeat the documented full startup and check persistent members, favorites and revocation."""
from pathlib import Path
import subprocess,uuid
from test_catalog import request
body={'email':'restart-'+uuid.uuid4().hex+'@example.test','password':'Restart-test-password-123','nickname':'재시작 검증'}
assert request('/auth/register','POST',body)[0]==201
_,a=request('/auth/login','POST',body)
assert request('/favorites/40','POST',token=a['token'])[0]==201
assert request('/auth/logout','POST',token=a['token'])[0]==204
_,b=request('/auth/login','POST',body)
with Path('.runtime/restart.log').open('w') as log:
 subprocess.run(['docker','compose','stop'],check=True,stdout=log,stderr=log)
 subprocess.run(['./scripts/up.sh'],check=True,stdout=log,stderr=log)
assert request('/favorites',token=a['token'])[0]==401
s,f=request('/favorites',token=b['token']);assert s==200 and [x['id'] for x in f]==[40]
assert request('/horses')[1]['totalElements']==40
assert request('/races')[1]['totalElements']==8
print('Full documented startup repeated: data, favorites, revocation and fixture counts preserved')
