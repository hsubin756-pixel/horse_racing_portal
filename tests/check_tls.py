"""Verify the deployment proxy over TLS using a disposable local CA.
Does not contact ACME or claim publicly trusted HTTPS deployment.
"""
import json,os,ssl,subprocess,tempfile,time,uuid
from pathlib import Path
from urllib.request import build_opener,HTTPSHandler,ProxyHandler
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);os.environ.setdefault('DOCKER_CONFIG',str(ROOT/'.runtime/docker'))
name='keiba-tls-check-'+uuid.uuid4().hex[:12]
network=next(iter(json.loads(subprocess.check_output(['docker','inspect','keiba-frontend-1']))[0]['NetworkSettings']['Networks']))
with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as directory:
 directory=Path(directory);config=directory/'Caddyfile'
 config.write_text((ROOT/'deploy/Caddyfile').read_text().replace('{$DOMAIN} {','{$DOMAIN} {\n tls internal'))
 try:
  subprocess.run(['docker','run','-d','--name',name,'--network',network,'--tmpfs','/data','--tmpfs','/config',
   '-p','127.0.0.1::443','-e','DOMAIN=localhost','-e','ACME_EMAIL=admin@example.invalid',
   '-v',str(config)+':/etc/caddy/Caddyfile:ro','caddy:2.10.2-alpine'],check=True,stdout=subprocess.DEVNULL)
  info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
  port=info['NetworkSettings']['Ports']['443/tcp'][0]['HostPort']
  ca=directory/'root.crt'
  for attempt in range(30):
   result=subprocess.run(['docker','exec',name,'cat','/data/caddy/pki/authorities/local/root.crt'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
   if result.returncode==0:
    ca.write_bytes(result.stdout)
    break
   time.sleep(1)
  else:
   subprocess.run(['docker','logs','--tail','30',name],check=False)
   raise RuntimeError('Test CA not ready')
  # Trust only the generated CA and keep hostname verification enabled.
  context=ssl.create_default_context(cafile=str(ca))
  opener=build_opener(ProxyHandler({}),HTTPSHandler(context=context))
  for attempt in range(20):
   try:
    with opener.open('https://localhost:'+port+'/api/horses',timeout=5) as response:
     assert response.status==200 and json.load(response)['totalElements']==40
     assert 'max-age=31536000' in response.headers['Strict-Transport-Security']
    break
   except OSError:
    if attempt==19:raise
    time.sleep(1)
  print('Local TLS gateway: CA and hostname verified; HTTPS API and HSTS passed. Public ACME remains untested.')
 finally:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
