import {useState} from 'react';
import {useLoad} from './api';
type Job={id:string;updatedAt:string;tasks:number;siteCompleted:number;trainingCompleted:number;importedRaces:number;heldRaces:number;calls:number;issues:{task:string;race:string;reason:string}[]};
type Data={jobs:Job[];database:{races:number;voidRaces:number;firstDate:string|null;lastDate:string|null;lastImportedAt:string|null};unreadableFiles:number;limited:boolean;note:string};
const meets:Record<string,string>={'1':'서울','2':'제주','3':'부산경남'};
export function KraStatus(){
 const [version,setVersion]=useState(0);const {data,error}=useLoad<Data>('/admin/kra-status?v='+version);
 return <details className="kra-status" open><summary>한국마사회 데이터 상태</summary>
  <button className="secondary" onClick={()=>setVersion(x=>x+1)}>수집 상태 새로고침</button>
  {error&&<p role="alert">{error}</p>}{!data&&!error&&<p role="status">상태 확인 중…</p>}
  {data&&<><p>{data.note}</p><div className="facts">
   <div><span>DB 반영 경주</span><b>{data.database.races}개</b></div><div><span>경주불성립</span><b>{data.database.voidRaces}개</b></div>
   <div><span>DB 자료 기간</span><b>{data.database.firstDate||'미제공'} ~ {data.database.lastDate||'미제공'}</b></div>
   <div><span>마지막 DB 반영</span><b>{data.database.lastImportedAt||'기록 없음'}</b></div></div>
   {data.jobs.length===0&&<p className="notice">수집 진행 기록이 없습니다. 자료 수집 후 다시 확인하세요.</p>}
   {(data.unreadableFiles>0||data.limited)&&<p className="notice">일부 진행 기록을 표시하지 못했습니다. 로컬 상태 파일을 확인하세요.</p>}
   {data.jobs.map(job=><article key={job.id}><h3>{job.id}</h3><p>마지막 작업: {job.updatedAt||'기록 없음'} · 누적 호출 {job.calls}회</p>
    <p>날짜×경마장 {job.tasks}개 중 사이트 완료 {job.siteCompleted}개 · 학습 수집 완료 {job.trainingCompleted}개</p>
    <p>반영 경주 {job.importedRaces}개 · 보류 경주 {job.heldRaces}개</p>
    <details><summary>보류·실패 사유 {job.issues.length}건</summary><ul>{job.issues.map((issue,i)=>{const [meet,day]=issue.task.split(':');return <li key={i}>{day} {meets[meet]} {issue.race&&issue.race+'R'} — {issue.reason}</li>;})}</ul></details>
   </article>)}</>}
 </details>;
}
