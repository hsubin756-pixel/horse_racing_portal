import {useState} from 'react';
import type {Run} from './racing';
const colors=['#285d41','#ad492a','#3459a3','#834c95'];
const early=(r:Run)=>r.points.find(p=>p.distance<=Math.min(600,r.distance/2)&&p.position!=null)?.position??null;
export function SectionalComparison({runs}:{runs:Run[]}){
 const [ids,setIds]=useState<number[]>(runs.slice(0,2).map(r=>r.horseId));
 const [sort,setSort]=useState('number');
 const selected=runs.filter(r=>ids.includes(r.horseId));
 const sorted=[...selected].sort((a,b)=>sort==='last600'?(a.last600??Infinity)-(b.last600??Infinity)||a.number-b.number:a.number-b.number);
 return <section className="sectional-comparison" aria-label="출주마 구간 비교"><h3>출주마 구간 비교</h3>
  <p className="small-note">같은 경주의 말을 최대 4두 선택하세요. 기록이 없는 지점은 추정하지 않습니다. 순위 변화는 초반 통과 순위에서 결승 순위를 뺀 값으로, 양수이면 순위가 상승했습니다.</p>
  <fieldset><legend>비교할 출주마 ({ids.length}/4)</legend><div className="comparison-picks">{runs.map(r=><label key={r.horseId}><input type="checkbox" checked={ids.includes(r.horseId)} disabled={ids.length>=4&&!ids.includes(r.horseId)} onChange={()=>setIds(old=>old.includes(r.horseId)?old.filter(x=>x!==r.horseId):[...old,r.horseId])}/>{r.number}번 {r.horseName}</label>)}</div></fieldset>
  {selected.length===0?<p role="status">비교할 말을 선택하세요.</p>:<>
  <ul className="comparison-legend">{selected.map((r,i)=><li key={r.horseId} style={{color:colors[i]}}>{r.number}번 {r.horseName}</li>)}</ul>
  <svg className="position-chart" viewBox="0 0 620 230" role="img" aria-label="선택한 출주마의 통과 순위 비교 그래프">
   <text x="0" y="30">1위</text><text x="0" y="180">{runs[0].fieldSize}위</text>
   {[...new Set(selected.flatMap(r=>r.points.map(p=>p.distance)))].sort((a,b)=>a-b).map(d=><text key={d} x={45+d/runs[0].distance*520} y="220" textAnchor="middle">{d}m</text>)}
   {selected.map((r,i)=>{
    const ps=r.points.filter(p=>p.position!=null);const x=(d:number)=>45+d/r.distance*520,y=(p:number)=>25+(p-1)/Math.max(r.fieldSize-1,1)*150;
    return <g key={r.horseId}><polyline points={ps.map(p=>`${x(p.distance)},${y(p.position!)}`).join(' ')} fill="none" stroke={colors[i]} strokeWidth="2" strokeDasharray={i%2?'7 4':undefined}/>{ps.map(p=><circle key={p.distance} cx={x(p.distance)} cy={y(p.position!)} r={4+i} fill="white" stroke={colors[i]}><title>{r.number}번 · {p.distance}m · {p.position}위</title></circle>)}</g>;
   })}
  </svg>
  <label>비교 정렬 <select value={sort} onChange={e=>setSort(e.target.value)}><option value="number">마번순</option><option value="last600">마지막 600m 빠른순</option></select></label>
  <div className="table-wrap" role="region" aria-label="출주마 구간 비교 표" tabIndex={0}><table><thead><tr><th>출주마</th><th>초반 순위</th><th>착순</th><th>순위 변화</th><th>마지막 600m</th><th>해당 경주 스타일</th></tr></thead><tbody>{sorted.map(r=>{
   const start=early(r),delta=start!=null&&r.finishPosition!=null?start-r.finishPosition:null;
   return <tr key={r.horseId}><th>{r.number}번 {r.horseName}</th><td>{start??'미제공'}</td><td>{r.finishPosition??'미확정'}</td><td>{delta==null?'미제공':delta>0?'+'+delta:delta}</td><td>{r.last600==null?'미제공':r.last600.toFixed(2)+'초'}</td><td>{r.style}</td></tr>;
  })}</tbody></table></div></>}
 </section>;
}
