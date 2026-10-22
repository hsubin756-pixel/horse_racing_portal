import uuid
from test_catalog import request
b={'email':uuid.uuid4().hex+'@example.test','password':'Outage-test-password','nickname':'장애 확인'}
assert request('/auth/register','POST',b)[0]==201
_,auth=request('/auth/login','POST',b)
s,d=request('/races/8/prediction','POST',token=auth['token'])
assert s==503,(s,d)
assert '일시적으로 이용할 수 없습니다' in d['message']
print('ML unavailable → localized 503 verified')
