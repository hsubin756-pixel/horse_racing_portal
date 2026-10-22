"""Exercise malformed/expired *signed* tokens through the real security filter.
Uses the local ignored development key without printing it. Do not run on production.
"""
import base64,hashlib,hmac,json,unittest,uuid,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from test_catalog import request
class TokenClaimsTests(unittest.TestCase):
 def test_signed_invalid_claims_and_concurrent_favorite(self):
  body={'email':'claims-'+uuid.uuid4().hex+'@example.test','password':'test-pass-long-123','nickname':'인증 테스트'}
  self.assertEqual(request('/auth/register','POST',body)[0],201)
  status,response=request('/auth/login','POST',body);self.assertEqual(status,200)
  token=response['token'];header,payload,_=token.split('.')
  claims=json.loads(base64.urlsafe_b64decode(payload+'=='))
  algorithm=json.loads(base64.urlsafe_b64decode(header+'=='))['alg']
  secret=next(line.split('=',1)[1].strip() for line in Path('.env').read_text().splitlines() if line.startswith('JWT_SECRET='))
  def signed(data):
   encoded=base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')
   content=header+'.'+encoded
   signature=hmac.new(secret.encode(),content.encode(),{'HS256':hashlib.sha256,'HS384':hashlib.sha384,'HS512':hashlib.sha512}[algorithm]).digest()
   return content+'.'+base64.urlsafe_b64encode(signature).decode().rstrip('=')
  variants=[{k:v for k,v in claims.items() if k!=missing} for missing in ('exp','iat','jti','sub')]
  variants += [dict(claims,exp=int(time.time())-1),dict(claims,iat=int(time.time())+600),dict(claims,sub='-1'),dict(claims,jti='invalid')]
  for variant in variants:
   status,data=request('/favorites',token=signed(variant))
   self.assertEqual(status,401);self.assertIn('다시 로그인',data['message'])
  with ThreadPoolExecutor(max_workers=2) as pool:
   statuses=list(pool.map(lambda _:request('/favorites/40','POST',token=token)[0],range(2)))
  self.assertEqual(sorted(statuses),[201,409])
  self.assertEqual(len(request('/favorites',token=token)[1]),1)
