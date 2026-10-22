import {useState,type FormEvent} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {useLoad,type Horse,type Page} from './api';

type Totals={starts:number;wins:number;top3:number;winRate:number|null;top3Rate:number|null;averageFinish:number|null;bestFinish:number|null};
type Breakdown={condition:string;totals:Totals};
type Recent={raceId:number;raceName:string;raceDate:string;horseId:number;horseName:string;jockey:string;distance:number;surface:string;finishPosition:number};
type Statistics={totals:Totals;byDistance:Breakdown[];bySurface:Breakdown[];recent:Recent[]};
type Comparison={asOfDate:string;horses:{horse:Horse;statistics:Statistics}[]};
type JockeyStats={asOfDate:string;jockey:string;statistics:Statistics};
const filterKeys=['distance','surface','from','to'] as const;
const percent=(value:number|null)=>value==null?'—':value.toFixed(1)+'%';
function queryFilters(params:URLSearchParams){const result=new URLSearchParams();for(const key of filterKeys){const value=params.get(key);if(value)result.set(key,value);}return result;}
function applyFilters(params:URLSearchParams,form:HTMLFormElement){
 const next=new URLSearchParams(params),data=new FormData(form);
 for(const key of filterKeys){const value=String(data.get(key)||'');if(value)next.set(key,value);else next.delete(key);}
 return next;
}
function Filters({params,onChange}:{params:URLSearchParams;onChange:(next:URLSearchParams)=>void}) {
 return <form className="stats-filters" key={queryFilters(params).toString()} onSubmit={e=>{e.preventDefault();onChange(applyFilters(params,e.currentTarget));}}>
  <label>거리(m)<input name="distance" type="number" min="400" max="10000" placeholder="전체" defaultValue={params.get('distance')||''}/></label>
  <label>주로<select name="surface" defaultValue={params.get('surface')||''}><option value="">전체</option><option>잔디</option><option>더트</option><option>장애</option></select></label>
  <label>조회 시작일<input name="from" type="date" defaultValue={params.get('from')||''}/></label>
  <label>조회 종료일<input name="to" type="date" defaultValue={params.get('to')||''}/></label>
  <button>조건 적용</button><button type="button" className="secondary" onClick={()=>{const next=new URLSearchParams(params);filterKeys.forEach(key=>next.delete(key));onChange(next);}}>조건 초기화</button>
 </form>;
}
function Loading({error,loading}:{error:string;loading:boolean}){return error?<p className="notice error" role="alert">{error}</p>:loading?<p role="status">성적을 불러오는 중…</p>:null;}
function BreakdownTable({title,rows,unit=''}:{title:string;rows:Breakdown[];unit?:string}){
 return <div className="breakdown"><h3>{title}</h3><div className="table-wrap" tabIndex={0} role="region" aria-label={title}>
  <table><thead><tr><th scope="col">조건</th><th scope="col">출전</th><th scope="col">승률</th><th scope="col">3위 이내</th></tr></thead>
   <tbody>{rows.map(row=><tr key={row.condition}><th scope="row">{row.condition}{unit}</th><td>{row.totals.starts}</td><td>{percent(row.totals.winRate)}</td><td>{percent(row.totals.top3Rate)}</td></tr>)}</tbody>
  </table>
 </div></div>;
}
function StatisticsView({statistics}:{statistics:Statistics}){
 const t=statistics.totals;
 return <>
  <dl className="stat-metrics"><div><dt>출전</dt><dd>{t.starts}회</dd></div><div><dt>우승</dt><dd>{t.wins}회</dd></div><div><dt>승률</dt><dd>{percent(t.winRate)}</dd></div><div><dt>3위 이내 비율</dt><dd>{percent(t.top3Rate)}</dd></div><div><dt>평균 착순</dt><dd>{t.averageFinish==null?'—':t.averageFinish.toFixed(1)+'위'}</dd></div><div><dt>최고 착순</dt><dd>{t.bestFinish==null?'—':t.bestFinish+'위'}</dd></div></dl>
  {t.starts===0?<p className="notice">조건에 맞는 완료 전적이 없습니다.</p>:<>
   <h3>최근 5경주</h3><p className="small-note">선택한 조건 내 최신 경주부터 표시합니다.</p>
   <ol className="recent-starts">{statistics.recent.map(e=><li key={e.raceId+'-'+e.horseId}>
    <Link to={'/races/'+e.raceId}><span className={e.finishPosition===1?'rank winner':'rank'}>{e.finishPosition}</span><span>{e.raceName}<small>{e.raceDate} · {e.surface} {e.distance}m · {e.horseName}</small></span></Link>
   </li>)}</ol>
   <BreakdownTable title="거리별 성적" rows={statistics.byDistance} unit="m"/>
   <BreakdownTable title="주로별 성적" rows={statistics.bySurface}/>
  </>}
 </>;
}
export function HorseComparison(){
 const [params,setParams]=useSearchParams(),[input,setInput]=useState(''),[q,setQ]=useState('');
 const ids=(params.get('ids')||'').split(',').filter(Boolean);
 const choices=useLoad<Page<Horse>>('/horses?q='+encodeURIComponent(q));
 const query=queryFilters(params);query.set('ids',ids.join(','));
 const result=useLoad<Comparison>(ids.length?'/horses/compare?'+query:null);
 const select=(id:string)=>{if(!id||ids.includes(id)||ids.length>=4)return;const next=new URLSearchParams(params);next.set('ids',[...ids,id].join(','));setParams(next);};
 const remove=(id:string)=>{const next=new URLSearchParams(params),remaining=ids.filter(value=>value!==id);if(remaining.length)next.set('ids',remaining.join(','));else next.delete('ids');setParams(next);};
 return <section><div className="eyebrow">SIDE BY SIDE</div><h1>경주마 비교</h1><p className="sub">최대 4두의 최근 성적과 거리·주로별 기록을 나란히 비교하세요.</p>
  <form className="searchbar" onSubmit={e=>{e.preventDefault();setQ(input);}}><label className="sr" htmlFor="compare-search">비교할 말 이름 검색</label><input id="compare-search" value={input} onChange={e=>setInput(e.target.value)} maxLength={100} placeholder="이름 전체 또는 일부"/><button>말 검색</button></form>
  {choices.error&&<p role="alert" className="notice error">{choices.error}</p>}
  <label className="entity-picker">비교할 경주마<select value="" disabled={ids.length>=4} onChange={e=>select(e.target.value)}><option value="">검색 결과에서 선택하세요</option>{choices.data?.content.map(h=><option key={h.id} value={h.id} disabled={ids.includes(String(h.id))}>{h.name}</option>)}</select></label>
  {choices.data?.content.length===0&&<p className="notice">검색 결과가 없습니다.</p>}
  <p className="small-note">검색 결과는 최대 20두입니다. 이름으로 범위를 좁혀주세요. 선택 {ids.length}/4두</p>
  <div className="selected-horses">{ids.map(id=>{const name=result.data?.horses.find(h=>String(h.horse.id)===id)?.horse.name||'경주마 #'+id;return <button key={id} className="secondary" onClick={()=>remove(id)} aria-label={name+' 비교에서 제외'}>{name} ×</button>;})}</div>
  <Filters params={params} onChange={setParams}/>
  <p className="small-note">가상 데이터의 완료 착순만 집계합니다. 승률은 우승/출전, 3위 이내 비율은 1~3위/출전입니다.</p>
  <Loading error={result.error} loading={ids.length>0&&!result.data}/>
  {!ids.length&&<p className="notice">비교할 경주마를 선택하세요.</p>}
  {ids.length>0&&result.data&&<><p className="small-note">집계 기준일: {result.data.asOfDate} (한국·일본 시간)</p><div className="comparison-grid">{result.data.horses.map(({horse,statistics})=><article className="comparison-card" key={horse.id}>
   <h2><Link to={'/horses/'+horse.id}>{horse.name} ↗</Link></h2><p className="small-note">{horse.sex} · {horse.birthDate} 출생 · {horse.trainer}</p><StatisticsView statistics={statistics}/>
  </article>)}</div></>}
 </section>;
}
function HorseStatistics({path}:{path:string}){
 const {data,error}=useLoad<Comparison>(path);
 return <><Loading error={error} loading={!data}/>{data?.horses.map(({horse,statistics})=><article className="stats-result" key={horse.id}><h2>{horse.name}의 성적</h2><p className="small-note">집계 기준일: {data.asOfDate}</p><Link className="textlink" to={'/compare?ids='+horse.id}>다른 말과 비교하기 ↗</Link><StatisticsView statistics={statistics}/></article>)}</>;
}
function JockeyStatistics({path}:{path:string}){
 const {data,error}=useLoad<JockeyStats>(path);
 return <><Loading error={error} loading={!data}/>{data&&<article className="stats-result"><h2>{data.jockey}의 성적</h2><p className="small-note">집계 기준일: {data.asOfDate}</p><StatisticsView statistics={data.statistics}/></article>}</>;
}
export function StatisticsPage(){
 const [params,setParams]=useSearchParams(),[input,setInput]=useState(''),[q,setQ]=useState('');
 const horses=useLoad<Page<Horse>>('/horses?q='+encodeURIComponent(q));
 const jockeys=useLoad<string[]>('/jockeys?q='+encodeURIComponent(q));
 const choose=(kind:'horse'|'jockey',value:string)=>{if(!value)return;const next=queryFilters(params);next.set(kind,value);setParams(next);};
 const horse=params.get('horse'),jockey=params.get('jockey'),query=queryFilters(params);
 if(jockey)query.set('name',jockey);
 return <section><div className="eyebrow">FORM & CONDITIONS</div><h1>조건별 성적</h1><p className="sub">경주마 또는 기수를 선택하고 거리·주로·기간별 성적을 확인하세요.</p>
  <form className="searchbar" onSubmit={(e:FormEvent<HTMLFormElement>)=>{e.preventDefault();setQ(input);}}><label className="sr" htmlFor="stats-search">말 또는 기수 이름 검색</label><input id="stats-search" value={input} maxLength={100} onChange={e=>setInput(e.target.value)} placeholder="말 또는 기수 이름"/><button>대상 검색</button></form>
  {(horses.error||jockeys.error)&&<p className="notice error" role="alert">{horses.error||jockeys.error}</p>}
  <div className="entity-pickers"><label className="entity-picker">성적을 볼 경주마<select value="" onChange={e=>choose('horse',e.target.value)}><option value="">경주마 선택</option>{horses.data?.content.map(h=><option key={h.id} value={h.id}>{h.name}</option>)}</select></label>
   <label className="entity-picker">성적을 볼 기수<select value="" onChange={e=>choose('jockey',e.target.value)}><option value="">기수 선택</option>{jockeys.data?.map(name=><option key={name}>{name}</option>)}</select></label></div>
  {horses.data?.content.length===0&&jockeys.data?.length===0&&<p className="notice">검색 결과가 없습니다.</p>}
  <Filters params={params} onChange={setParams}/><p className="small-note">가상 데이터의 완료 착순만 집계합니다. 예정 경주는 제외하며, 완료 전적이 없으면 비율을 ‘—’로 표시합니다.</p>
  {horse?<HorseStatistics path={'/horses/'+encodeURIComponent(horse)+'/stats?'+query}/>:jockey?<JockeyStatistics path={'/jockeys/stats?'+query}/>:<p className="notice">성적을 볼 경주마 또는 기수를 선택하세요.</p>}
 </section>;
}
