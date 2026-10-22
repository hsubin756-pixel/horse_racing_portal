"""Run after browser tests: consumes the local proxy's authentication rate budget."""
import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError
statuses=[]
for _ in range(15):
 request=Request('http://127.0.0.1:5173/api/auth/login',data=b'{}',headers={'Content-Type':'application/json'})
 try:
  with urlopen(request,timeout=5) as response:statuses.append(response.status)
 except HTTPError as error:
  statuses.append(error.code)
  if error.code==429: assert '잠시 후' in json.load(error)['message']
assert 429 in statuses and set(statuses)<={400,429},statuses
print('Proxy authentication rate limit: Korean 429 verified')
