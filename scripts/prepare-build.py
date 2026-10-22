"""Use trusted machine CA roots for builds, preserving TLS verification."""
from pathlib import Path
import os,shutil,subprocess,urllib.parse
root=Path(__file__).resolve().parents[1];runtime=root/'.runtime';runtime.mkdir(exist_ok=True);(runtime/'gradle').mkdir(exist_ok=True)
java_ca=Path('/etc/ssl/certs/java/cacerts')
if java_ca.exists(): shutil.copyfile(java_ca,runtime/'cacerts')
else:
 c=subprocess.check_output(['docker','create','gradle:8.14.3-jdk21'],text=True).strip()
 try: subprocess.run(['docker','cp',c+':/opt/java/openjdk/lib/security/cacerts',str(runtime/'cacerts')],check=True)
 finally: subprocess.run(['docker','rm',c],check=True,stdout=subprocess.DEVNULL)
# Import host-installed organization/proxy roots; never download or invent a trust root.
keytool=shutil.which('keytool')
for cert in Path('/usr/local/share/ca-certificates').glob('*.crt'):
 args=['-importcert','-noprompt','-alias','host-'+cert.stem,'-file',str(cert),'-keystore',str(runtime/'cacerts'),'-storepass','changeit']
 if keytool: subprocess.run([keytool]+args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 else:
  subprocess.run(['docker','run','--rm','-v',str(runtime)+':/trust','-v',str(cert)+':/cert.crt:ro','gradle:8.14.3-jdk21','keytool','-importcert','-noprompt','-alias','host-'+cert.stem,'-file','/cert.crt','-keystore','/trust/cacerts','-storepass','changeit'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
shutil.copyfile('/etc/ssl/certs/ca-certificates.crt',runtime/'ca-bundle.crt')
u=urllib.parse.urlsplit(os.environ.get('HTTPS_PROXY',os.environ.get('https_proxy','')))
props=''
if u.hostname:
 for protocol in ['http','https']: props+=f'systemProp.{protocol}.proxyHost={u.hostname}\nsystemProp.{protocol}.proxyPort={u.port or 80}\n'
(runtime/'gradle/gradle.properties').write_text(props)
print('Trusted CA build configuration prepared; TLS verification remains enabled')
