"""Hash trusted pip downloads for verification during offline Docker assembly."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]
lines=[]
for wheel in sorted((root/'ml/.wheels').glob('*.whl')):
 name,version,*_=wheel.name.split('-')
 lines.append(f'{name}=={version} --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}')
assert lines,'No wheels downloaded'
(root/'ml/.wheels/requirements.hashed.txt').write_text('\n'.join(lines)+'\n')
