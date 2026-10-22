"""Local synthetic dataset benchmark; not a production capacity guarantee."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import perf_counter
import json
from test_catalog import request
workers=50;barrier=Barrier(workers)
def run(i):
 barrier.wait();start=perf_counter();s,d=request('/horses?q=' if i%2==0 else '/races?date=2025-01-15');elapsed=(perf_counter()-start)*1000
 assert s==200 and d['totalElements']>0
 return elapsed
with ThreadPoolExecutor(max_workers=workers) as pool: times=sorted(pool.map(run,range(workers)))
result={'concurrency':workers,'requests':len(times),'allPassed':True,'medianMs':times[len(times)//2],'p95Ms':times[int(len(times)*.95)-1],'maxMs':max(times),'scope':'local API only, 40 horses/8 races; not a production SLA'}
print(json.dumps(result,indent=2));assert max(times)<3000
open('.runtime/performance.json','w').write(json.dumps(result,indent=2)+'\n')
