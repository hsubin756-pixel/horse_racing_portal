import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter, Routes, Route, Link, NavLink, useParams, useSearchParams} from 'react-router-dom';
import {useLoad, type Horse, type Race, type Entry, type Page, type RaceDetail} from './api';
import './style.css';
import {Calendar,HorseRunningStyle,RaceSectionals,RaceFacts,Payouts,raceStatus,entryStatus,sourceLabel} from './racing';
import {Notes,Notifications,People,PersonProfile,NoteLink} from './member-tools';
import {Admin} from './admin';
import {HorseComparison,StatisticsPage} from './analytics';
import {Watchlist,RaceWatchButton} from './watchlist';
import {Prediction} from './prediction';
import {Pedigree} from './pedigree';
import {AuthProvider,Account,AuthPage,Favorites,FavoriteButton} from './auth';
function Status({error,loading}:{error:string;loading:boolean}) { return error ? <p className="notice error" role="alert">{error}</p> : loading ? <p className="notice" role="status">데이터를 불러오는 중입니다…</p> : null; }
function Layout(){return <><div className="topline">출처와 함께 살펴보는 경마 기록 <span>RACING DATA ARCHIVE</span></div><header><Link to="/" className="brand"><b>♞</b><span>KEIBA<em>FIELD</em><small>경마 데이터 아카이브</small></span></Link><nav><NavLink to="/horses">경주마</NavLink><NavLink to="/races">경주·결과</NavLink><NavLink to="/compare">경주마 비교</NavLink><NavLink to="/statistics">조건별 성적</NavLink><NavLink to="/favorites">즐겨찾기</NavLink><NavLink to="/watchlist">관심 일정</NavLink></nav><Account/></header><div className="utility-nav"><Link to="/calendar">개최 캘린더</Link><Link to="/people">기수·조교사</Link><Link to="/notes">개인 메모</Link><Link to="/notifications">알림함</Link><Link to="/admin">자료 관리</Link></div><main><Routes><Route path="/" element={<Home/>}/><Route path="/horses" element={<HorseList/>}/><Route path="/horses/:id/pedigree" element={<Pedigree/>}/><Route path="/horses/:id" element={<HorseDetail/>}/><Route path="/races" element={<RaceList/>}/><Route path="/races/:id/prediction" element={<Prediction/>}/><Route path="/races/:id" element={<RacePage/>}/><Route path="/login" element={<AuthPage key="login"/>}/><Route path="/register" element={<AuthPage key="register" register/>}/><Route path="/favorites" element={<Favorites/>}/><Route path="/compare" element={<HorseComparison/>}/><Route path="/statistics" element={<StatisticsPage/>}/><Route path="/watchlist" element={<Watchlist/>}/><Route path="/calendar" element={<Calendar/>}/><Route path="/notes" element={<Notes/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="/people" element={<People/>}/><Route path="/people/:id" element={<PersonProfile/>}/><Route path="/admin" element={<Admin/>}/><Route path="*" element={<section><h1>페이지를 준비하고 있습니다</h1><Link to="/">홈으로</Link></section>}/></Routes></main><footer><strong>KEIBA FIELD</strong><p>기본 자료는 가상 샘플입니다. 한국마사회에서 가져온 기록은 출처를 별도로 표시하며 실시간 정보가 아닙니다. 베팅 기능은 없습니다.</p><span>2026 · Racing stories, connected.</span></footer></>}
function Home(){const horses=useLoad<Page<Horse>>('/horses'); const races=useLoad<Page<Race>>('/races');return <><section className="hero"><div><div className="eyebrow">THE RACING DATA PORTAL</div><h1>한 마리의 기록에서,<br/><i>경마의 세계로.</i></h1><p>경주마의 발자취, 경주의 순간, 세대를 잇는 혈통.<br/>흩어진 기록을 하나의 이야기로 만나보세요.</p><div className="actions"><Link className="button" to="/horses">경주마 찾아보기 <span>↗</span></Link><Link className="textlink" to="/races">경주 결과 탐색 →</Link></div></div><div className="hero-art" aria-hidden="true"><div className="orbit o1"/><div className="orbit o2"/><div className="horse-symbol">♞</div><span className="art-label">EVERY HORSE HAS A STORY</span><span className="track-number">01 — FIELD NOTES</span></div></section><div className="metrics"><div><span>DATABASE</span><strong>{horses.data?.totalElements ?? '—'} <small>경주마</small></strong></div><div><span>RACE ARCHIVE</span><strong>{races.data?.totalElements ?? '—'} <small>경주</small></strong></div><div><span>CONNECTED GENERATIONS</span><strong>3 <small>대 혈통 탐색</small></strong></div><div className="data-note">작은 데이터, 연결된 이야기.<br/><b>기본 자료: 합성 샘플 데이터</b></div></div><section><div className="section-title"><div><div className="eyebrow">RACE CALENDAR</div><h2>경주 아카이브</h2></div><Link to="/races">전체 경주 보기 ↗</Link></div><Status error={races.error} loading={!races.data}/><div className="race-grid">{races.data?.content.slice(0,3).map(r=><Link className="race-card" to={'/races/'+r.id} key={r.id}><div className="card-top"><span>{r.raceDate}</span><span className="pill">{raceStatus[r.status]}</span></div><h3>{r.name}</h3><p>{r.venue} · {sourceLabel(r.source)}</p><div className="card-bottom"><span>{r.surface} · {r.distance.toLocaleString()}m</span><b>↗</b></div></Link>)}</div></section><section className="explore"><div><div className="eyebrow">BLOODLINE EXPLORER</div><h2>기록 너머의 연결,<br/>혈통을 읽다.</h2><p>부마와 모마에서 시작해 3대의 계보를 탐색하세요.<br/>경주마 상세 페이지에서 혈통도를 만날 수 있습니다.</p><Link className="textlink" to="/horses">경주마 아카이브로 →</Link></div><div className="tree-art" aria-hidden="true"><span>한 마리의 이야기</span><div><span>父 부마</span><span>母 모마</span></div><div><span>조부</span><span>조모</span><span>외조부</span><span>외조모</span></div></div></section></>}
function Pager({page,total,onChange}:{page:number;total:number;onChange:(n:number)=>void}){return <div className="pager"><button disabled={page===0} onClick={()=>onChange(page-1)}>← 이전</button><span>{page+1} / {Math.max(total,1)}</span><button disabled={page+1>=total} onClick={()=>onChange(page+1)}>다음 →</button></div>}
function HorseList(){const [params,setParams]=useSearchParams();const q=params.get('q')||'',page=Number(params.get('page')||0);const [input,setInput]=useState(q);const sort=params.get('sort')||'name';const direction=params.get('direction')||'asc';const {data,error}=useLoad<Page<Horse>>('/horses?'+new URLSearchParams({q,page:String(page),sort,direction}));return <section><div className="eyebrow">HORSE DATABASE</div><h1>경주마 아카이브</h1><p className="sub">이름으로 찾고, 기록으로 알아보세요.</p><form className="searchbar" onSubmit={e=>{e.preventDefault();setParams({q:input,sort,direction});}}><label className="sr" htmlFor="horse-search">경주마 이름</label><input id="horse-search" placeholder="경주마 이름 전체 또는 일부 입력" value={input} onChange={e=>setInput(e.target.value)} maxLength={100}/><button>검색 ↗</button></form><div className="list-top"><span>총 <b>{data?.totalElements??'—'}</b>두 · 페이지당 20건</span><div><label className="sr" htmlFor="sort">정렬 기준</label><select id="sort" value={sort} onChange={e=>setParams({q,sort:e.target.value,direction})}><option value="name">이름순</option><option value="sex">성별순</option><option value="birthDate">생년순</option></select><label className="sr" htmlFor="direction">정렬 방향</label><select id="direction" value={direction} onChange={e=>setParams({q,sort,direction:e.target.value})}><option value="asc">오름차순</option><option value="desc">내림차순</option></select></div></div><Status error={error} loading={!data}/>{data?.content.length===0&&<p className="notice">검색 결과가 없습니다</p>}<div className="horse-grid">{data?.content.map(h=><Link key={h.id} to={'/horses/'+h.id} className="horse-card"><div className="horse-avatar">♞<span>{h.sex}</span></div><div><span className="eyebrow">HORSE NO. {String(h.id).padStart(3,'0')}</span><h3>{h.name}</h3>{h.kraId&&<small>한국마사회 · {h.kraId}</small>}<p>{h.birthDate?h.birthDate.slice(0,4)+'년생':'생년 미제공'} · {h.color}</p><small>{h.trainer}</small></div><span className="arrow">↗</span></Link>)}</div>{data&&<Pager page={page} total={data.totalPages} onChange={n=>setParams({q,sort,direction,page:String(n)})}/>}</section>}
function KraHorseProfile({horse}:{horse:Horse}){
 const p=horse.profile;if(!p||!horse.profileAsOf)return null;
 const asOf=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(horse.profileAsOf));
 const row=(label:string,starts?:string,w1?:string,w2?:string,w3?:string)=>starts==null?null:<tr key={label}><th scope="row">{label}</th><td>{starts}</td><td>{w1??'—'}</td><td>{w2??'—'}</td><td>{w3??'—'}</td></tr>;
 return <section className="kra-profile"><div className="section-title"><h2>한국마사회 집계 전적</h2><span>{asOf} 수집 · 사이트 전적과 별도</span></div>
  <div className="table-wrap" role="region" aria-label="한국마사회 집계 전적" tabIndex={0}><table><thead><tr><th scope="col">구분</th><th scope="col">출주</th><th scope="col">1착</th><th scope="col">2착</th><th scope="col">3착</th></tr></thead>
  <tbody>{row('통산',p.rcCntT,p.ord1CntT,p.ord2CntT,p.ord3CntT)}{row('최근 1년',p.rcCntY,p.ord1CntY,p.ord2CntY,p.ord3CntY)}</tbody></table></div>
  <p className="small-note">{p.winRate&&'승률 '+p.winRate+'% · '}{p.quinRate&&'복승률 '+p.quinRate+'% · '}{p.chaksunT&&'통산 상금 '+Number(p.chaksunT).toLocaleString()+'원 · '}{p.rating&&p.rating!=='0'&&'레이팅 '+p.rating+' · '}{p.lchulDt&&'최근 출전 '+p.lchulDt.replace(/(\d{4})(\d{2})(\d{2})/,'$1-$2-$3')}</p></section>;
}
function HorseDetail(){const {id}=useParams();const {data:h,error}=useLoad<Horse>('/horses/'+id);const history=useLoad<Entry[]>('/horses/'+id+'/history');return <section><Link className="breadcrumb" to="/horses">← 경주마 아카이브</Link><Status error={error} loading={!h}/>{h&&<><div className="detail-head"><div className="detail-icon">♞</div><div><div className="eyebrow">HORSE PROFILE · {h.id}</div><h1>{h.name}</h1>{h.kraId&&<p>한국마사회 자료 · 마번 {h.kraId}{h.nameEn&&' · '+h.nameEn}</p>}{h.ancestorOnly&&<p>혈통 참조용 자료 · 한국마사회 선대마정보의 이름만 제공되어 상세 정보가 없습니다</p>}<p>{h.sex} · {h.birthDate?h.birthDate+' 출생':'생년월일 미제공'} · {h.color}</p></div></div><div className="profile-actions"><FavoriteButton id={h.id}/><NoteLink horse={h.id}/><Link className="button secondary" to={"/horses/"+h.id+"/pedigree"}>3대 혈통 탐색 ↗</Link><Link className="button secondary" to={"/compare?ids="+h.id}>다른 말과 비교 ↗</Link><Link className="button secondary" to={"/statistics?horse="+h.id}>조건별 성적 ↗</Link></div><div className="facts"><div><span>조교사</span>{h.trainerId?<Link to={"/people/"+h.trainerId}>{h.trainer} ↗</Link>:<b>{h.trainer}</b>}</div><div><span>부마</span>{h.sire?<Link to={'/horses/'+h.sire.id}>{h.sire.name} ↗</Link>:<b>정보 없음</b>}</div><div><span>모마</span>{h.dam?<Link to={'/horses/'+h.dam.id}>{h.dam.name} ↗</Link>:<b>정보 없음</b>}</div>{h.origin&&<div><span>산지</span><b>{h.origin}</b></div>}{h.breed&&<div><span>품종</span><b>{h.breed}</b></div>}{h.kraRank&&<div><span>등급</span><b>{h.kraRank}</b></div>}{h.ownerName&&<div><span>마주</span><b>{h.ownerName}</b></div>}</div><KraHorseProfile horse={h}/><HorseRunningStyle key={h.id} id={h.id}/><div className="section-title"><h2>출전 전적</h2><span>최신 경주부터 표시</span></div><Status error={history.error} loading={!history.data}/>{history.data&&<EntryTable entries={history.data} mode="horse"/>}</>}</section>}
function EntryTable({entries,mode}:{entries:Entry[];mode:'horse'|'race'}) {
 const hasTrainer=entries.some(e=>e.trainerName);
 const oddsEntries=entries.filter(e=>e.winOdds!=null);
 const commonOdds=mode==='race'&&oddsEntries.length>0&&oddsEntries.every(e=>e.oddsSource===oddsEntries[0].oddsSource&&e.oddsAsOf===oddsEntries[0].oddsAsOf)?oddsEntries[0]:null;
 if(entries.length===0)return <p className="notice">출전 기록이 없습니다.</p>;
 const asOf=(value:string)=>new Intl.DateTimeFormat('ko-KR',{
  timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false
 }).format(new Date(value));
 return <>
  <p className="odds-note">단승 배당은 1위 적중 시 원금을 포함한 배수입니다. 가상 샘플과 한국마사회 자료의 출처를 구분해 표시합니다. 실시간 배당이 아닙니다. 제공되지 않은 공식 인기 순위는 추정하지 않습니다. <b>배당 기준 인기</b>는 저장된 단승 배당이 낮은 순서로 조회 시 계산한 순위이며 공식 인기 순위가 아닙니다. 같은 배당은 공동 순위로, 배당이 없는 말은 순위를 비워 둡니다. 인기 순위는 착순·모델 예측 순위와 다릅니다.</p>
  {commonOdds&&<p className="odds-provenance">배당 출처: {sourceLabel(commonOdds.oddsSource||'제공 자료')}{commonOdds.oddsAsOf&&<> · {asOf(commonOdds.oddsAsOf)} KST {commonOdds.oddsSource==='KRA_API214_1'?'수집':'기준'}</>}</p>}
  <div className="table-wrap" role="region" aria-label={mode==='horse'?'출전 전적 표':'출주마 및 배당 표'} tabIndex={0}>
   <table className="entry-table">
    <thead><tr>
     <th scope="col">{mode==='horse'?'경주일':'마번'}</th>
     <th scope="col">{mode==='horse'?'경주명':'경주마'}</th>
     <th scope="col">기수</th>{hasTrainer&&<th scope="col">경주 당시 조교사</th>}<th scope="col">인기</th><th scope="col">배당 기준 인기</th><th scope="col">단승 배당</th>
     <th scope="col">출전 상태</th><th scope="col">게이트</th><th scope="col">부담중량</th><th scope="col">마체중(증감)</th><th scope="col">주파기록(초)</th><th scope="col">착순</th>
    </tr></thead>
    <tbody>{entries.map(e=><tr key={e.raceId+'-'+e.horseId}>
     <td>{mode==='horse'?e.raceDate:String(e.number).padStart(2,'0')}</td>
     <td><Link to={mode==='horse'?'/races/'+e.raceId:'/horses/'+e.horseId}>{mode==='horse'?e.raceName:e.horseName} ↗</Link></td>
     <td><Link to={e.jockeyId?"/people/"+e.jockeyId:"/statistics?jockey="+encodeURIComponent(e.jockey)}>{e.jockey} ↗</Link></td>
     {hasTrainer&&<td>{e.trainerId?<Link to={'/people/'+e.trainerId}>{e.trainerName} ↗</Link>:(e.trainerName||'미제공')}</td>}
     <td className="popularity-value">{e.popularityRank==null?'미제공':e.popularityRank+'위'}</td>
     <td className="odds-rank-value">{e.oddsRank==null?'—':<>{e.oddsRankShared?'공동 ':''}{e.oddsRank}위{e.oddsRankField!=null&&e.oddsRankTotal!=null&&e.oddsRankField<e.oddsRankTotal&&<small>{e.oddsRankField}두 기준 (전체 {e.oddsRankTotal}두)</small>}</>}</td>
     <td className="odds-value">{e.winOdds==null?'미제공':<>
      <strong>{e.winOdds.toFixed(1)}배</strong>
      {!commonOdds&&<small>{sourceLabel(e.oddsSource||'제공 자료')}</small>}
      {!commonOdds&&e.oddsAsOf&&<time dateTime={e.oddsAsOf}>{asOf(e.oddsAsOf)} KST {e.oddsSource==='KRA_API214_1'?'수집':'기준'}</time>}
     </>}</td>
     <td>{e.statusNote||entryStatus[e.status]}</td><td>{e.gate??'미제공'}</td><td>{e.carriedWeight==null?'미제공':e.carriedWeight+'kg'}</td><td>{e.bodyWeight==null?'미제공':e.bodyWeight+'kg'} ({e.weightChange==null?'미제공':(e.weightChange>0?'+':'')+e.weightChange+'kg'})</td><td>{e.timeSeconds??(['SCRATCHED','DNF','DISQUALIFIED','VOID'].includes(e.status)?'기록 없음':'미확정')}</td>
     <td><span className={e.finishPosition===1?'rank winner':'rank'}>{e.finishPosition??'—'}</span></td>
    </tr>)}</tbody>
   </table>
  </div>
 </>;
}
function RaceList(){const [params,setParams]=useSearchParams();const q=params.get('q')||'',date=params.get('date')||'',page=Number(params.get('page')||0);const [input,setInput]=useState(q);const [day,setDay]=useState(date);const {data,error}=useLoad<Page<Race>>('/races?'+new URLSearchParams({...date?{date}:{},q,page:String(page)}));return <section><div className="eyebrow">RACES & RESULTS</div><h1>경주와 그 순간의 기록</h1><p className="sub">개최일과 경주명으로 아카이브를 탐색하세요.</p><form className="searchbar" onSubmit={e=>{e.preventDefault();setParams({...day?{date:day}:{},q:input});}}><label className="sr" htmlFor="race-search">경주명</label><input id="race-search" value={input} placeholder="경주명 입력" maxLength={150} onChange={e=>setInput(e.target.value)}/><label className="sr" htmlFor="race-date">개최일</label><input id="race-date" type="date" value={day} onChange={e=>setDay(e.target.value)}/><button>검색 ↗</button></form><Status error={error} loading={!data}/>{data?.content.length===0&&<p className="notice">검색 결과가 없습니다</p>}<div className="race-grid">{data?.content.map(r=><Link key={r.id} to={'/races/'+r.id} className="race-card"><div className="card-top"><span>{r.raceDate}</span><span className="pill">{r.surface}</span></div><h3>{r.name}</h3><p>{r.venue} · {sourceLabel(r.source)}</p><div className="card-bottom"><span>{r.distance.toLocaleString()}m</span><b>↗</b></div></Link>)}</div>{data&&<Pager page={page} total={data.totalPages} onChange={n=>setParams({...date?{date}:{},q,page:String(n)})}/>}</section>}
function RacePage() {
 const {id}=useParams();
 const {data,error}=useLoad<RaceDetail>('/races/'+id);
 const [sort,setSort]=useState<'finishPosition'|'number'|'popularityRank'|'oddsRank'|'winOdds'>('finishPosition');
 const entries=[...(data?.entries??[])].sort((a,b)=>
  ((a[sort]??Infinity)-(b[sort]??Infinity)) || a.number-b.number);
 return <section>
  <Link className="breadcrumb" to="/races">← 경주 아카이브</Link>
  <Status error={error} loading={!data}/>
  {data&&<>
   <div className="eyebrow">RACE DETAIL · {data.race.raceDate}</div>
   <h1>{data.race.name}</h1>
   <p className="sub">{data.race.venue} · {data.race.surface==='미제공'?'주로 정보 미제공 ·':data.race.surface} {data.race.distance}m</p>
   <RaceFacts race={data.race}/>{data.race.status==='VOID'&&<p className="notice">경주불성립으로 확정된 경주입니다. 착순·성적 통계·예측 대상에서 제외됩니다.</p>}<NoteLink race={data.race.id}/><div className="section-title"><h2>출주마 및 착순 결과</h2>
    {!['VOID','CANCELLED'].includes(data.race.status)&&<Link className="button secondary" to={"/races/"+id+"/prediction"}>실험 모델 예측 ↗</Link>}
   </div>
   <RaceWatchButton key={id} id={Number(id)}/><div className="entry-controls"><label htmlFor="entry-sort">출주마 정렬</label>
    <select id="entry-sort" value={sort} onChange={e=>setSort(e.target.value as typeof sort)}>
     <option value="finishPosition">착순순</option><option value="number">마번순</option>
     <option value="popularityRank">인기순</option><option value="oddsRank">배당 기준 인기순</option><option value="winOdds">단승 배당 낮은순</option>
    </select>
   </div>
   <EntryTable entries={entries} mode="race"/><RaceSectionals key={id} id={Number(id)}/><Payouts id={Number(id)} source={data.race.source}/>
  </>}
 </section>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><AuthProvider><Layout/></AuthProvider></BrowserRouter></React.StrictMode>);
