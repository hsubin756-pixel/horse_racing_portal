#!/usr/bin/env python3
"""관리자 화면용 집계 스냅샷 발행. 원본·절대 경로·인증키는 포함하지 않습니다."""
import json
import os
from pathlib import Path
import re
import tempfile
import kra


def reason(value):
    value=str(value)
    if len(value)>300 or '/' in value or '\\' in value:return '상세 사유는 로컬 상태 조회에서 확인하세요.'
    return ''.join(c if ord(c)>=32 else ' ' for c in value)


def publish(path,state):
    if not re.fullmatch(r'[0-9]{8}-[0-9]{8}-[123]{1,3}\.json',path.name):return
    snapshot={'updatedAt':str(state.get('updatedAt','')),'calls':max(0,int(state.get('calls',0))),'tasks':{}}
    for key,task in state.get('tasks',{}).items():
        if not re.fullmatch(r'[123]:[0-9]{8}',key):continue
        out={name:task[name] for name in ('site','training') if name in task}
        for stage in ('site','training'):
            if task.get(stage+'_error'):out[stage+'_error']=reason(task[stage+'_error'])
        out['races']={}
        for number,result in task.get('races',{}).items():
            if not re.fullmatch(r'[0-9]{1,2}',number):continue
            out['races'][number]={name:reason(result[name]) for name in ('status','error') if name in result}
        snapshot['tasks'][key]=out
    directory=path.parent/'dashboard';directory.mkdir(exist_ok=True,mode=0o755);directory.chmod(0o755)
    fd,temp=tempfile.mkstemp(prefix='.status-',dir=directory)
    try:
        with os.fdopen(fd,'w') as output:
            os.fchmod(output.fileno(),0o644);json.dump(snapshot,output,ensure_ascii=False)
        os.replace(temp,directory/path.name)
    finally:
        Path(temp).unlink(missing_ok=True)


if __name__=='__main__':
    folder=kra.STATE/'sync';folder.mkdir(parents=True,exist_ok=True)
    (folder/'dashboard').mkdir(exist_ok=True,mode=0o755)
    count=0
    for path in folder.glob('*.json'):
        if re.fullmatch(r'[0-9]{8}-[0-9]{8}-[123]{1,3}\.json',path.name):
            publish(path,json.loads(path.read_text()));count+=1
    print('관리자 화면용 진행 기록 갱신:',count,'개 / API 호출 없음')
