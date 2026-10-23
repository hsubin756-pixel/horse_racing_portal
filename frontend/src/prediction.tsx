import {useEffect,useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {api} from './api';
import {useAuth} from './auth';
import type {Race} from './api';
type Metrics=Record<string,number|number[]>;
type Result={modelKind:string;disclaimer:string;scores:{horseId:number;horseName:string;score:number;knownStarts:number|null}[];info:{firstDate:string|null;cutoffDate:string;trainingRaces:number|null;holdoutMetrics:Metrics|null;marketBaselineMetrics:Metrics|null}|null};
const pct=(m:Metrics|null|undefined,key:string)=>m&&typeof m[key]==='number'?(m[key] as number).toFixed(3):'—';
export function Prediction(){
 const {id}=useParams();const {user}=useAuth();
 const [race,setRace]=useState<Race|null>(null);
 const [result,setResult]=useState<Result|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{setResult(null);setError('');setRace(null);api<{race:Race}>('/races/'+id).then(d=>setRace(d.race)).catch(()=>setRace(null));},[id,user]);
 const real=!!race?.source?.startsWith('KRA_');
 return <section><Link className="breadcrumb" to={'/races/'+id}>← 경주 상세</Link>
  <div className="eyebrow">{real?'EXPERIMENTAL · KRA OPEN DATA MODEL':'EXPERIMENTAL · SYNTHETIC DATA ONLY'}</div><h1>경주 예측 실험실</h1>
  {real
   ?<div className="notice">한국마사회 공개 자료(AI학습용 경주결과)로 학습한 실험 모델입니다. 배당 등 시장 정보는 입력에 넣지 않았고, 학습 기간 이후 전적은 재학습 전까지 반영되지 않습니다. 점수는 입상 확률이 아니며 실제 결과나 수익을 보장하지 않습니다.</div>
   :<div className="notice">합성 데이터만으로 학습·평가한 실험 모델입니다. 실제 예측 능력은 검증되지 않았습니다. 점수는 입상 확률로 보장되지 않으며, 실제 결과나 수익을 보장하지 않습니다.</div>}
  <p className="sub">{real?'출주마의 보존 전적(한국마사회 마번 기준)·기수/조교사 과거 3위 이내 비율·부담중량·마체중·게이트·두수·나이·성별·거리를 입력으로 계산합니다.':'출주마의 해당 경주 이전 전적과 거리를 바탕으로 계산합니다.'}</p>
  {user?<button disabled={busy} onClick={async()=>{setBusy(true);setError('');setResult(null);try{setResult(await api<Result>('/races/'+id+'/prediction',{method:'POST'}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>{busy?'점수 계산 중…':'출주마 예측 점수 계산 ↗'}</button>:<Link className="button" to="/login">로그인하고 예측 실험하기 ↗</Link>}
  {error&&<p className="notice error" role="alert">{error}</p>}
  {user&&result&&<div className="prediction-result"><h2>예측 점수 순위</h2><p className="sub">{result.disclaimer}</p>
   {result.info&&<div className="model-info"><p className="small-note">모델: {result.modelKind} · 학습 자료 {result.info.firstDate??'?'} ~ {result.info.cutoffDate} · 경주 {result.info.trainingRaces?.toLocaleString()??'?'}개</p>
    <div className="table-wrap" role="region" aria-label="모델 홀드아웃 지표" tabIndex={0}><table><thead><tr><th scope="col">구분</th><th scope="col">ROC-AUC</th><th scope="col">AP</th><th scope="col">상위 3두 적중</th></tr></thead>
     <tbody><tr><th scope="row">이 모델(시장 정보 없음)</th><td>{pct(result.info.holdoutMetrics,'rocAuc')}</td><td>{pct(result.info.holdoutMetrics,'averagePrecision')}</td><td>{pct(result.info.holdoutMetrics,'top3Recall')}</td></tr>
     <tr><th scope="row">배당 순위만(시장 기준선)</th><td>{pct(result.info.marketBaselineMetrics,'rocAuc')}</td><td>{pct(result.info.marketBaselineMetrics,'averagePrecision')}</td><td>{pct(result.info.marketBaselineMetrics,'top3Recall')}</td></tr></tbody></table></div>
    <p className="small-note">홀드아웃은 학습 기간 마지막 20% 개최일의 결과이며 미래 성능 보장이 아닙니다. 시장 기준선은 모델 없이 단승 배당이 낮은 순으로 고른 결과입니다.</p></div>}
   {result.scores.map((s,i)=><div className="score-row" key={s.horseId}><span className="rank">{i+1}</span><Link to={'/horses/'+s.horseId}>{s.horseName} ↗</Link><meter min={0} max={1} value={s.score} aria-label={s.horseName+' 모델 점수'}/><b>{s.score.toFixed(3)}</b>{s.knownStarts!=null&&<small>{s.knownStarts===0?'보존 전적 없음':'보존 전적 '+s.knownStarts+'회'}</small>}</div>)}
  </div>}
 </section>;
}
