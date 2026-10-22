import unittest,uuid,json,subprocess,base64
from test_catalog import request
class AuthTests(unittest.TestCase):
 def register(self,label):
  self.password='Safe-test-'+uuid.uuid4().hex
  self.email=label+uuid.uuid4().hex+'@example.test'
  body={'email':self.email,'password':self.password,'nickname':'테스트 회원'}
  self.assertEqual(request('/auth/register','POST',body)[0],201)
  s,d=request('/auth/login','POST',body);self.assertEqual(s,200)
  return body,d['token']
 def test_registration_login_and_validation(self):
  b,t=self.register('a');self.assertEqual(request('/auth/register','POST',b)[0],409)
  self.assertEqual(request('/auth/login','POST',dict(b,password='wrong'))[0],401)
  self.assertEqual(request('/auth/register','POST',dict(b,email='invalid'))[0],400)
  self.assertEqual(request('/auth/register','POST',dict(b,email='new@example.test',password='가'*30))[0],400)
  self.assertEqual(request('/auth/register','POST',dict(b,email='new@example.test',nickname='   '))[0],400)
  claim=json.loads(base64.urlsafe_b64decode(t.split('.')[1]+'=='));self.assertEqual(claim['exp']-claim['iat'],1800)
  self.assertNotIn('password',claim);self.assertNotIn('email',claim)
 def test_favorites_isolation_duplicate_and_logout(self):
  _,a=self.register('a');_,b=self.register('b')
  self.assertEqual(request('/favorites')[0],401)
  self.assertEqual(request('/favorites/22','POST',token=a)[0],201)
  self.assertEqual(request('/favorites/22','POST',token=a)[0],409)
  self.assertEqual(request('/favorites/99999','POST',token=a)[0],404)
  self.assertEqual(request('/favorites',token=b)[1],[])
  self.assertEqual(request('/favorites/22','DELETE',token=b)[0],204)
  self.assertEqual([x['id'] for x in request('/favorites',token=a)[1]],[22])
  self.assertEqual(request('/favorites/22','DELETE',token=a)[0],204)
  self.assertEqual(request('/favorites',token=a)[1],[])
  self.assertEqual(request('/auth/logout','POST',token=a)[0],204)
  self.assertEqual(request('/favorites',token=a)[0],401)
  self.assertEqual(request('/favorites',token=b)[0],200)
  self.assertEqual(request('/favorites',token=b[:-4]+'xxxx')[0],401)
  self.assertEqual(request('/races/1/prediction','POST')[0],401)
 def test_hashes_at_rest(self):
  self.register('hash')
  # Count violations without printing hashes, passwords, or environment values.
  r=subprocess.run(['docker','compose','exec','-T','db','sh','-c',
   '''MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N keiba -e "SELECT COUNT(*) FROM member WHERE password_hash NOT LIKE '\\$2a\\$12\\$%';"'''],capture_output=True,text=True,check=True)
  self.assertEqual(r.stdout.strip(),'0')
