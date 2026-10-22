"""Run sustained reads on an isolated 10k-horse / 1k-race / 20k-entry copy.
Creates only a random schema and temporary backend container; never alters live fixtures.
"""
import json,os,subprocess,sys,time,uuid
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from backup import mysql
os.chdir(ROOT);os.environ.setdefault('DOCKER_CONFIG',str(ROOT/'.runtime/docker'))
schema='scale_check_'+uuid.uuid4().hex
container='keiba-scale-'+uuid.uuid4().hex[:12]
def command(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
try:
 mysql('CREATE DATABASE '+schema+' CHARACTER SET utf8mb4; GRANT ALL ON '+schema+".* TO 'keiba'@'%';")
 # Fresh migration/fixtures only: no user records copied into the scale environment.
 for path in sorted((ROOT/'backend/src/main/resources/db/migration').glob('V*.sql')):
  mysql(path.read_text(),schema)
 for start in range(1000,11000,500):
  values=[f"({i},'Scale horse {i}','M','2020-01-01','bay','Synthetic trainer',1,2)" for i in range(start,start+500)]
  mysql('INSERT INTO horse(id,name,sex,birth_date,color,trainer,sire_id,dam_id) VALUES '+','.join(values)+';',schema)
 for start in range(1000,2000,100):
  mysql("INSERT INTO race(id,name,race_date,venue,distance,surface) VALUES "+','.join(f"({i},'Scale race {i}','2024-01-01','Synthetic venue',1600,'TURF')" for i in range(start,start+100))+';',schema)
  values=[f"({r},{1000+((r-1000)*20+h)%10000},{h+1},'Synthetic jockey',{h+1},100.0)" for r in range(start,start+100) for h in range(20)]
  mysql('INSERT INTO entry(race_id,horse_id,number,jockey,finish_position,time_seconds) VALUES '+','.join(values)+';',schema)
 network=json.loads(subprocess.check_output(['docker','inspect','keiba-db-1']))[0]['NetworkSettings']['Networks']
 network=next(iter(network))
 command(['docker','run','-d','--name',container,'--network',network,'--env-file','.env',
  '-e','DB_URL=jdbc:mysql://db:3306/'+schema+'?connectionTimeZone=UTC','-e','DB_USER=keiba',
  '-e','ML_URL=http://ml:8000','-e','SPRING_FLYWAY_ENABLED=false',
  '-p','127.0.0.1::8080','keiba-backend'],stdout=subprocess.DEVNULL)
 info=json.loads(subprocess.check_output(['docker','inspect',container]))[0]
 port=info['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
 base='http://127.0.0.1:'+port+'/api'
 for attempt in range(90):
  try:
   with urlopen(base+'/horses',timeout=2) as response: data=json.load(response)
   if data['totalElements']==10040:break
  except Exception:pass
  time.sleep(1)
 else:raise RuntimeError('Scale backend did not become ready')
 counts={table:int(mysql('SELECT COUNT(*) FROM '+table+';',schema)) for table in ('horse','race','entry')}
 output=ROOT/'.runtime/performance-scale.json'
 command([sys.executable,'tests/performance.py','--seconds','30','--workers','50','--output',str(output)],env={**os.environ,'TEST_BASE_URL':base})
 report=json.loads(output.read_text());report['fixtureCounts']=counts
 output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(counts))
finally:
 subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 mysql('DROP DATABASE IF EXISTS '+schema+';')
 mysql("REVOKE ALL PRIVILEGES ON "+schema+".* FROM 'keiba'@'%';")
