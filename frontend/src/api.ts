import {useEffect, useState} from 'react';
let token: string | null = null;
export function setToken(value: string | null) { token=value; }
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
 let response: Response;
 try { response = await fetch('/api'+path, {...options, signal: options.signal ?? AbortSignal.timeout(10000), headers: {'Content-Type':'application/json', ...(token ? {Authorization: 'Bearer '+token}: {}), ...options.headers}}); }
 catch { throw new Error('서버에 연결할 수 없습니다. 네트워크 상태를 확인하고 다시 시도하세요.'); }
 if(response.status===401 && token) { window.dispatchEvent(new Event('auth-expired')); }
 if (!response.ok) { const error = await response.json().catch(()=>({message:'서버 연결을 확인하세요.'})); throw new Error(error.message || '요청을 처리할 수 없습니다.'); }
 const text=await response.text(); return text ? JSON.parse(text) as T : undefined as T;
}
export function useLoad<T>(path: string | null) {
 const [data,setData]=useState<T|null>(null), [error,setError]=useState('');
 useEffect(()=>{ let active=true; setData(null); setError(''); if(path===null)return; api<T>(path).then(d=>{if(active)setData(d);}).catch(e=>{if(active)setError(e.message);}); return ()=>{active=false;};},[path]);
 return {data,error};
}
export type HorseProfile=Record<string,string>;
export type Horse={id:number;name:string;sex:string;birthDate:string|null;color:string;trainer:string;sire:Ref|null;dam:Ref|null;trainerId:number|null;kraId:string|null;source:string;nameEn:string|null;origin:string|null;breed:string|null;kraRank:string|null;ownerName:string|null;ancestorOnly:boolean;profile:HorseProfile|null;profileAsOf:string|null};
export type Ref={id:number;name:string};
export type Race={id:number;name:string;raceDate:string;venue:string;distance:number;surface:string;startTime:string|null;raceClass:string|null;weather:string|null;going:string|null;status:string;source:string};
export type Entry={horseId:number;horseName:string;raceId:number;raceName:string;raceDate:string;number:number;jockey:string;finishPosition:number|null;timeSeconds:number|null;popularityRank:number|null;winOdds:number|null;oddsSource:string|null;oddsAsOf:string|null;gate:number|null;carriedWeight:number|null;bodyWeight:number|null;weightChange:number|null;status:string;jockeyId:number|null;trainerId:number|null;trainerName:string|null;oddsRank:number|null;oddsRankShared:boolean|null;oddsRankField:number|null;oddsRankTotal:number|null};
export type Page<T>={content:T[];page:number;totalPages:number;totalElements:number};
export type RaceDetail={race:Race;entries:Entry[]};
