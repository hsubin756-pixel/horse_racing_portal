"""Closed-loop sustained local benchmark; no production capacity claim."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import perf_counter
import argparse,json,math
from pathlib import Path
from test_catalog import request
parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=float,default=30)
parser.add_argument('--workers',type=int,default=50)
parser.add_argument('--output',default='.runtime/performance.json')
args=parser.parse_args()
if args.seconds<=0 or not 1<=args.workers<=100: parser.error('seconds > 0 and workers 1..100 required')
barrier=Barrier(args.workers)
paths=['/horses?q=','/horses?page=1','/horses/40','/horses/40/pedigree','/races','/races/1']
def run(worker):
 barrier.wait();deadline=perf_counter()+args.seconds;timings=[];errors=0;index=worker
 while perf_counter()<deadline:
  start=perf_counter()
  try:
   status,data=request(paths[index%len(paths)])
   if status!=200: errors+=1
  except Exception: errors+=1
  timings.append((perf_counter()-start)*1000);index+=1
 return timings,errors
start=perf_counter()
with ThreadPoolExecutor(max_workers=args.workers) as pool: results=list(pool.map(run,range(args.workers)))
elapsed=perf_counter()-start
times=sorted(t for values,_ in results for t in values);errors=sum(e for _,e in results)
result={'concurrency':args.workers,'durationSeconds':elapsed,'requests':len(times),'errors':errors,
 'requestsPerSecond':len(times)/elapsed,'medianMs':times[len(times)//2],
 'p95Ms':times[math.ceil(len(times)*.95)-1],'p99Ms':times[math.ceil(len(times)*.99)-1],'maxMs':max(times),
 'scope':'Closed-loop API reads, no think time. Fixture scale is reported separately; no public-network or browser SLA.'}
print(json.dumps(result,indent=2));Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
assert errors==0 and result['p95Ms']<3000,result
