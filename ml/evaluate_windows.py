"""Expanding-history, disjoint temporal validation windows. No training download/model promotion."""
import argparse
import hashlib
from datetime import date,timedelta
import json
from pathlib import Path
from evaluate_tracks import merge,compare


def evaluate(paths,windows=3,test_days=30):
    if not 2<=windows<=12 or not 7<=test_days<=180:raise ValueError('windows 2..12; test-days 7..180')
    hashes={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    races=merge(paths)
    if not races:raise ValueError('No races')
    last=max(r[0]['race_date'] for r in races.values())+timedelta(days=1)
    reports=[]
    for index in range(windows):
        start=last-timedelta(days=(windows-index)*test_days);end=start+timedelta(days=test_days)
        reports.append(compare(paths,start.isoformat(),end.isoformat()))
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=hashes[str(p)] for p in paths):
        raise ValueError('Input CSV changed during evaluation; retry after collection finishes')
    return {'method':'Expanding training history; non-overlapping calendar test windows', 'dataHashes':hashes,
            'windows':reports,'promoted':False,
            'limitations':['Historical features update only from earlier dates, including earlier test dates.',
              'Market comparison must use modelOnMarketSubset and market on the same races.',
              'Insufficient dates/tracks are reported, never filled with fabricated scores.',
              'No automatic model selection, promotion, calibrated win probabilities or profit claim.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv',nargs='+',type=Path)
    p.add_argument('--windows',type=int,default=3);p.add_argument('--test-days',type=int,default=30)
    p.add_argument('--output',type=Path,default=Path('.runtime/kra/windows-evaluation.json'));a=p.parse_args()
    try:report=evaluate(a.csv,a.windows,a.test_days)
    except (ValueError,OSError) as exc:p.error(str(exc))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    for window in report['windows']:
        print(window['cutoff'],'~',window['testEndExclusive'],'(끝 날짜 제외)')
        for name,cohort in window['cohorts'].items():
            print(' ',name,cohort['status'])
            for track,result in cohort.get('byTrack',{}).items():
                model=result['modelOnMarketSubset'];market=result['market']
                print('  경마장',track,'/ 시장 비교',result['marketRaces'],'경주',
                      '/ AUC 모델/시장',f"{model['rocAuc']:.3f}/{market['rocAuc']:.3f}" if market else '미제공')
    print('보고서:',a.output,'/ 서비스 모델 교체 없음')


if __name__=='__main__':main()
