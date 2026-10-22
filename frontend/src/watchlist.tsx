import {useState} from 'react';
import {Link,Navigate} from 'react-router-dom';
import {api,useLoad,type Race,type Ref} from './api';
import {useAuth} from './auth';
type Schedule={asOfDate:string;through:string;races:{race:Race;savedRace:boolean;favoriteHorses:Ref[]}[]};
export function RaceWatchButton({id}:{id:number}){
 const {user}=useAuth();const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
 return <div className="favorite-action">{user?<button disabled={busy} onClick={async()=>{setBusy(true);try{await api('/race-favorites/'+id,{method:'POST'});setMessage('관심 경주에 저장했습니다.');}catch(error){setMessage((error as Error).message);}finally{setBusy(false);}}}>☆ 관심 경주 저장</button>:<Link className="button secondary" to="/login">로그인하고 관심 경주 저장</Link>}{message&&<span role="status">{message}</span>}</div>;
}
export function Watchlist(){const {user}=useAuth();return user?<WatchlistContent key={user.token}/>:<Navigate to="/login" replace/>;}
function WatchlistContent(){
 const [version,setVersion]=useState(0),[error,setError]=useState(''),[busy,setBusy]=useState<number|null>(null);
 const favorites=useLoad<Race[]>('/race-favorites?v='+version),schedule=useLoad<Schedule>('/my-schedule?v='+version);
 const remove=async(id:number)=>{setBusy(id);setError('');try{await api('/race-favorites/'+id,{method:'DELETE'});setVersion(v=>v+1);}catch(error){setError((error as Error).message);}finally{setBusy(null);}};
 return <section><div className="eyebrow">MY RACE CALENDAR</div><h1>관심 경주와 출전 일정</h1><p className="sub">저장한 경주와 즐겨찾기 말의 예정 출전을 한곳에서 확인하세요.</p>
  <Link className="textlink" to="/favorites">즐겨찾기 경주마 관리 ↗</Link>
  {(error||favorites.error||schedule.error)&&<p role="alert" className="notice error">{error||favorites.error||schedule.error}</p>}
  {(!favorites.data&&!favorites.error||!schedule.data&&!schedule.error)&&<p role="status">일정을 불러오는 중…</p>}
  <h2 className="watch-heading">다가오는 90일 일정</h2>
  {schedule.data&&<><p className="small-note">{schedule.data.asOfDate} ~ {schedule.data.through} · 한국·일본 날짜 기준 · 발주 시각은 미제공</p>
   {schedule.data.races.length===0?<p className="notice">앞으로 90일 동안 관심 대상의 예정 경주가 없습니다.</p>:<>
    <p className="notice" role="status">관심 대상의 예정 경주가 {schedule.data.races.length}개 있습니다.</p>
    <ol className="schedule-list">{schedule.data.races.map(({race,savedRace,favoriteHorses})=><li key={race.id}>
     <time dateTime={race.raceDate}>{race.raceDate}</time><div><h3><Link to={'/races/'+race.id}>{race.name} ↗</Link></h3><p>{race.venue} · {race.surface} {race.distance}m {savedRace&&<span className="pill">저장한 경주</span>}</p>
      {favoriteHorses.length>0&&<div className="scheduled-horses">관심 말 출전: {favoriteHorses.map(h=><Link key={h.id} to={'/horses/'+h.id}>{h.name} ↗</Link>)}</div>}
     </div></li>)}</ol>
   </>}
  </>}
  <h2 className="watch-heading">저장한 경주</h2>
  {favorites.data?.length===0&&<p className="notice">저장한 경주가 없습니다. <Link to="/races">경주 찾아보기 →</Link></p>}
  <div className="saved-races">{favorites.data?.map(race=><article className="saved-race" key={race.id}><div><h3><Link to={'/races/'+race.id}>{race.name} ↗</Link></h3><p>{race.raceDate} · {race.venue}</p></div><button className="remove" disabled={busy!==null} aria-label={race.name+' 관심 경주 삭제'} onClick={()=>remove(race.id)}>삭제</button></article>)}</div>
 </section>;
}
