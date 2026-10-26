#!/usr/bin/env python3
"""Create a private logical backup and verify it in a disposable schema.
Never replaces keiba or stops services. Keep the database quiet for the checksum comparison.
"""
import argparse, gzip, json, os, subprocess, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('DOCKER_CONFIG',str(ROOT/'.runtime/docker'))
PREFIX=['docker','compose','exec','-T','db','sh','-c']
def mysql(sql, database=None):
 command='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names'
 if database: command+=' '+database
 return subprocess.run(PREFIX+[command],input=sql.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode()
def inventory(database):
 tables=mysql('SHOW TABLES;',database).splitlines()
 return {table:{'rows':int(mysql('SELECT COUNT(*) FROM `'+table+'`;',database)),
                'checksum':mysql('CHECKSUM TABLE `'+table+'` EXTENDED;',database).strip().split('\t')[-1]}
         for table in tables}
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--directory',default='.runtime/backups')
 args=parser.parse_args()
 directory=Path(args.directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
 name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
 backup=directory/(name+'.sql.gz')
 before=inventory('keiba')
 fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as raw, gzip.GzipFile(fileobj=raw,mode='wb') as output:
  command='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --default-character-set=utf8mb4 --single-transaction --quick --no-tablespaces --set-gtid-purged=OFF --skip-comments keiba'
  process=subprocess.Popen(PREFIX+[command],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  while chunk:=process.stdout.read(1024*1024): output.write(chunk)
  _,error=process.communicate()
  if process.returncode: raise RuntimeError('mysqldump failed; backup must not be used')
 schema='restore_check_'+uuid.uuid4().hex
 try:
  mysql('CREATE DATABASE '+schema+' CHARACTER SET utf8mb4;')
  with gzip.open(backup,'rb') as source:
   process=subprocess.Popen(PREFIX+['MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 '+schema],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   while chunk:=source.read(1024*1024): process.stdin.write(chunk)
   process.stdin.close();process.stdin=None
   _,error=process.communicate()
   if process.returncode: raise RuntimeError('Isolated restore failed')
  restored=inventory(schema)
  after=inventory('keiba')
  if before!=after or before!=restored: raise RuntimeError('Checksum mismatch or live database changed during verification; retry when quiet')
  report={'verifiedAt':datetime.now(timezone.utc).isoformat(),'backup':str(backup),'isolatedRestorePassed':True,'tables':restored,
          'scope':'Same MySQL server, separate disposable schema. Off-host disaster recovery is not verified.'}
  report_path=directory/(name+'.json')
  with os.fdopen(os.open(report_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as output: json.dump(report,output,indent=2)
  print(json.dumps({'backup':str(backup),'report':str(report_path),'isolatedRestorePassed':True},indent=2))
 finally:
  mysql('DROP DATABASE IF EXISTS '+schema+';')
if __name__=='__main__':main()
