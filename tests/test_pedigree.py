import unittest
from test_catalog import request
class PedigreeTests(unittest.TestCase):
 def test_three_generations(self):
  s,n=request('/horses/40/pedigree');self.assertEqual(s,200);self.assertEqual(n['id'],40)
  self.assertEqual(n['sire']['id'],26);self.assertEqual(n['sire']['sire']['id'],12)
  self.assertIsNotNone(n['sire']['sire']['sire']['id'])
  self.assertIsNone(n['sire']['sire']['sire']['sire'])
  self.assertTrue(n['dam']['name'])
 def test_missing_and_not_found(self):
  _,n=request('/horses/1/pedigree');self.assertIsNone(n['sire']);self.assertIsNone(n['dam'])
  _,n=request('/horses/11/pedigree');self.assertIsNotNone(n['sire']);self.assertIsNone(n['dam'])
  self.assertEqual(request('/horses/9999/pedigree')[0],404)
