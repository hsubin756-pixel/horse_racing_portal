import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import {Link,Navigate,useNavigate} from 'react-router-dom';
import {api,setToken,useLoad,type Horse} from './api';
type Session={nickname:string;expiresIn:number;token:string};
const Context=createContext<{user:Session|null;login:(s:Session)=>void;logout:()=>Promise<void>}>({user:null,login:()=>{},logout:async()=>{}});
export function AuthProvider({children}:{children:ReactNode}) {
 const [user,setUser]=useState<Session|null>(null);
 const clear=()=>{setToken(null);setUser(null);};
 useEffect(()=>{if(!user)return;const timer=setTimeout(clear,user.expiresIn*1000);return ()=>clearTimeout(timer);},[user]);
 useEffect(()=>{window.addEventListener('auth-expired',clear);return ()=>window.removeEventListener('auth-expired',clear);},[]);
 return <Context.Provider value={{user,login:s=>{setToken(s.token);setUser(s);},logout:async()=>{await api('/auth/logout',{method:'POST'});clear();}}}>{children}</Context.Provider>;
}
export const useAuth=()=>useContext(Context);
export function Account(){const {user,logout}=useAuth();const [error,setError]=useState('');return <div className="account-area">{user?<><span>{user.nickname}님</span><button className="account" onClick={()=>logout().catch(e=>setError(e.message))}>로그아웃</button></>:<Link className="account" to="/login">로그인 ↗</Link>}{error&&<small role="alert">{error}</small>}</div>}
export function AuthPage({register=false}:{register?:boolean}) {
 const {login,user}=useAuth();const navigate=useNavigate();const [error,setError]=useState(''),[busy,setBusy]=useState(false),[done,setDone]=useState(false);
 if(user)return <Navigate to="/favorites" replace/>;
 return <section className="auth-section"><div className="eyebrow">YOUR RACING NOTEBOOK</div><h1>{register?'새로운 이야기를 시작하세요':'다시 만나 반갑습니다'}</h1><p className="sub">{register?'나만의 경주마 컬렉션을 만들어 보세요.':'로그인하고 관심 있는 경주마를 기록하세요.'}</p>{done?<div className="notice" role="status">회원가입이 완료되었습니다. <Link to="/login">로그인하기 →</Link></div>:<form className="auth-form" onSubmit={async e=>{e.preventDefault();setError('');setBusy(true);const f=new FormData(e.currentTarget);try{const email=String(f.get('email')),password=String(f.get('password'));if(register){await api('/auth/register',{method:'POST',body:JSON.stringify({email,password,nickname:f.get('nickname')})});setDone(true);}else{const s=await api<Session>('/auth/login',{method:'POST',body:JSON.stringify({email,password})});login(s);navigate('/favorites');}}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>
 <label>이메일<input name="email" type="email" autoComplete="email" required maxLength={254} placeholder="you@example.com"/></label>
 <label>비밀번호<input name="password" type="password" autoComplete={register?'new-password':'current-password'} required minLength={register?10:1} maxLength={72} placeholder={register?'10자 이상 · UTF-8 72바이트 이하':'비밀번호 입력'}/></label>
 {register&&<label>닉네임<input name="nickname" required maxLength={40} autoComplete="nickname" placeholder="사용할 닉네임"/></label>}
 {error&&<p className="notice error" role="alert">{error}</p>}<button disabled={busy}>{busy?'처리 중…':register?'회원가입':'로그인'} ↗</button>
 <p>{register?'이미 계정이 있으신가요?':'처음 방문하셨나요?'} <Link to={register?'/login':'/register'}>{register?'로그인':'회원가입'}</Link></p></form>}<small>토큰은 브라우저 메모리에만 보관됩니다. 새로고침하면 다시 로그인해 주세요.</small></section>
}
export function FavoriteButton({id}:{id:number}){const {user}=useAuth();const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);return <div className="favorite-action">{user?<button disabled={busy} onClick={async()=>{setBusy(true);try{await api('/favorites/'+id,{method:'POST'});setMessage('즐겨찾기에 추가했습니다.');}catch(e){setMessage((e as Error).message);}finally{setBusy(false);}}}>☆ 즐겨찾기 추가</button>:<Link className="button" to="/login">☆ 로그인하고 즐겨찾기</Link>}{message&&<span role="status">{message}</span>}</div>}
export function Favorites(){const {user}=useAuth();return user?<FavoriteList/>:<Navigate to="/login" replace/>;}
function FavoriteList(){const [version,setVersion]=useState(0),[error,setError]=useState('');const {data,error:loadError}=useLoad<Horse[]>('/favorites?v='+version);return <section><div className="eyebrow">MY COLLECTION</div><h1>나의 즐겨찾기</h1><p className="sub">관심 있는 경주마의 이야기를 이어가세요.</p>{(error||loadError)&&<p className="notice error" role="alert">{error||loadError}</p>}{!data&&!loadError&&<p role="status">불러오는 중…</p>}{data?.length===0&&<p className="notice">등록된 즐겨찾기가 없습니다. <Link to="/horses">경주마 찾아보기 →</Link></p>}<div className="horse-grid">{data?.map(h=><div className="horse-card" key={h.id}><div className="horse-avatar">♞</div><Link to={'/horses/'+h.id}><h3>{h.name}</h3><p>{h.sex} · {h.birthDate}</p></Link><button className="remove" aria-label={h.name+' 즐겨찾기 삭제'} onClick={async()=>{try{await api('/favorites/'+h.id,{method:'DELETE'});setVersion(v=>v+1);}catch(e){setError((e as Error).message);}}}>삭제</button></div>)}</div></section>}
