import unittest
from fastapi.testclient import TestClient
from app import app
from train import dataset
class ModelTests(unittest.TestCase):
 def test_dataset_temporal_features(self):
  x,y,r=dataset();self.assertEqual(x.shape,(2400,3));self.assertTrue((x[:24,1]==0).all());self.assertTrue((x[24:48,1]==1).all());self.assertEqual(y[:24].sum(),3);self.assertEqual(int((r<80).sum()),1920)
 def test_schema_and_scores(self):
  with TestClient(app) as c:
   self.assertEqual(c.get('/health').json()['modelKind'],'synthetic_experiment')
   self.assertEqual(c.post('/predict',json={'horses':[]}).status_code,422)
   self.assertEqual(c.post('/predict',json={'horses':[{'horseId':1,'priorMeanFinish':0,'starts':-1,'distance':2}]}).status_code,422)
   duplicate={'horseId':1,'priorMeanFinish':5,'starts':7,'distance':1600}
   self.assertEqual(c.post('/predict',json={'horses':[duplicate,duplicate]}).status_code,422)
   d=c.post('/predict',json={'horses':[{'horseId':1,'priorMeanFinish':5,'starts':7,'distance':1600}]}).json();self.assertTrue(0<=d['scores'][0]['score']<=1)
if __name__=='__main__':unittest.main(verbosity=2)
