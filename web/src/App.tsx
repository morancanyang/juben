import { useCallback, useEffect, useRef, useState } from 'react'
import { BookOpen, ChevronRight, RefreshCcw, ShieldCheck, X } from 'lucide-react'
import { api, clearLocal, command, formatDate, localDB, saveUser, type GameState, type HistoryItem, type Script, type User } from './api'
import { Home, Sidebar, Topbar } from './Layout'
import Library from './Library'
import PlayScript from './PlayScript'
import { Docs } from './Reveal'
import Editor from './ScriptEditor'
import SettingsPage from './SettingsPage'

export default function App(){
 const [user,setUser]=useState<User|null>(null)
 const [page,setPageState]=useState(location.hash.slice(1)||'home')
 const [scripts,setScripts]=useState<Script[]>([])
 const [selected,setSelected]=useState<Script|null>(null)
 const [session,setSession]=useState<GameState|null>(null)
 const [history,setHistory]=useState<HistoryItem[]>([])
 const [notice,setNotice]=useState('')
 const [loading,setLoading]=useState(true)
 const [bootError,setBootError]=useState('')
 const [startBusy,setStartBusy]=useState(false)
 const guestRequest=useRef<Promise<User>|null>(null)
 const userRef=useRef<User|null>(null)
 const notify=useCallback((x:string)=>setNotice(x),[])
 const setPage=useCallback((p:string)=>{location.hash=p;setPageState(p);window.scrollTo(0,0)},[])
 const updateUser=useCallback((u:User|null)=>{saveUser(u);userRef.current=u;setUser(u)},[])
 const refreshHistory=useCallback(async()=>{if(userRef.current){const d=await api('/api/v1/sessions');setHistory(d.items)}},[])
 useEffect(()=>{const fn=()=>setPageState(location.hash.slice(1)||'home');window.addEventListener('hashchange',fn);return()=>window.removeEventListener('hashchange',fn)},[])
 useEffect(()=>{let live=true;(async()=>{try{const [me,lib]=await Promise.all([api('/api/v1/me'),api('/api/v1/scripts')]);if(!live)return;setScripts(lib.items);if(me.user){updateUser(me.user);const list=await api('/api/v1/sessions');if(!live)return;setHistory(list.items);const last=localStorage.getItem('casebook_active_'+me.user.id)||list.items[0]?.id;if(last){try{const state=await api(`/api/v1/sessions/${last}/state`);if(live)setSession(state)}catch{}}}}catch(e:any){if(live)setBootError('无法连接游戏服务。请运行项目中的启动脚本，再点击重试。')}finally{if(live)setLoading(false)}})();return()=>{live=false}},[updateUser])
 useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(''),7000);return()=>clearTimeout(t)},[notice])
 useEffect(()=>{if(user){document.body.classList.toggle('large',user.preferences.font_size==='large');document.body.classList.toggle('light',user.preferences.theme==='light')}else{document.body.classList.remove('large','light')}},[user])
 const ensureUser=useCallback(async()=>{if(userRef.current)return userRef.current;if(!guestRequest.current){guestRequest.current=api('/api/v1/auth/guest',{method:'POST',body:'{}'}).then(d=>{updateUser(d.user);return d.user}).finally(()=>{guestRequest.current=null})}return guestRequest.current},[updateUser])
 const enter=async()=>{try{await ensureUser();notify('游客档案已建立，可随时注册账号保存跨设备进度。')}catch(e:any){notify(e.message)}}
 const openScript=async(s:Script)=>{try{const detail=await api(`/api/v1/scripts/${s.id}`);setSelected(detail);setPage('library')}catch(e:any){notify(e.message)}}
 const setGame=useCallback((state:GameState)=>{setSession(state);const u=userRef.current;if(u){localStorage.setItem('casebook_active_'+u.id,state.id);if(state.phase==='investigation')localDB.snapshots.put({key:u.id+':'+state.id,userId:u.id,state}).catch(()=>{})}},[])
 const startGame=async(config:{difficulty:string;perspective:string;partner_style:string},scriptId?:string)=>{if(startBusy)return;const id=scriptId||selected?.id;if(!id)return;setStartBusy(true);try{await ensureUser();const d=await command('/api/v1/sessions',{script_id:id,...config});setGame(d.state);await refreshHistory();setPage('play');notify('案件已开封。搜索现场、分析证物，再向角色追问。')}catch(e:any){notify(e.message)}finally{setStartBusy(false)}}
 const resume=async(id?:string)=>{const sid=id||session?.id;if(!sid)return;try{await ensureUser();setGame(await api(`/api/v1/sessions/${sid}/state`));setPage('play')}catch(e:any){const cached=userRef.current?await localDB.snapshots.get(userRef.current.id+':'+sid):null;if(cached){setGame(cached.state);setPage('play');notify('正在查看上次保存的已知内容。离线行动会排队等待核验。')}else notify(e.message)}}
 const logout=async()=>{try{await api('/api/v1/auth/logout',{method:'POST'});await clearLocal();updateUser(null);setSession(null);setHistory([]);setPage('home')}catch(e:any){notify(e.message)}}
 const onAuthenticated=async(u:User)=>{await clearLocal();updateUser(u);setSession(null);await refreshHistory();notify('已登录，可从调查记录恢复游戏。')}
 return <div className="app-shell"><div className="grain"/><Sidebar page={page} setPage={setPage} user={user} onLogout={logout}/><main className="main-content"><Topbar page={page} setPage={setPage} user={user} onEnter={enter}/>
 {bootError?<div className="empty-state"><h2>调查桌尚未就绪</h2><p>{bootError}</p><button className="primary-button" onClick={()=>location.reload()}>重试连接</button></div>:loading?<div className="empty-state" role="status"><span className="spinner"/> 正在整理卷宗…</div>:<>
 {page==='home'&&<><Home scripts={scripts} selected={selected} session={session} onOpen={openScript} onStart={()=>startGame({difficulty:'standard',perspective:'侦探',partner_style:'逻辑'})} onResume={()=>resume()} onLibrary={()=>setPage('library')}/>{history.length>0&&<History items={history} resume={resume}/>}</>}
 {page==='library'&&<Library scripts={scripts} selected={selected} onOpen={openScript} onClose={()=>setSelected(null)} start={startGame} busy={startBusy}/>}
 {['play','history'].includes(page)&&(session&&user?<PlayScript key={session.id} state={session} setState={setGame} user={user} notice={notify} setPage={setPage} refreshHistory={refreshHistory} showHistory={page==='history'}/>:<div className="empty-state"><BookOpen size={30}/><h2>还没有打开的卷宗</h2><p>选择一桩案件，即可开始调查。</p><button className="primary-button" onClick={()=>setPage('library')}>选择剧本</button>{history.length>0&&<History items={history} resume={resume}/>}</div>)}
 {page==='editor'&&<Editor user={user} ensureUser={ensureUser} notice={notify} start={id=>startGame({difficulty:'story',perspective:'侦探',partner_style:'逻辑'},id)}/>}
 {page==='docs'&&<Docs/>}
 {page==='settings'&&<SettingsPage user={user} updateUser={updateUser} ensureUser={ensureUser} onAuthenticated={onAuthenticated} onDeleted={async()=>{await clearLocal();updateUser(null);setSession(null);setHistory([]);setPage('home')}} notice={notify}/>}
 {!['home','library','play','history','editor','docs','settings'].includes(page)&&<div className="empty-state"><h2>页面不存在</h2><button className="primary-button" onClick={()=>setPage('home')}>回到调查总览</button></div>}
 </>}
 </main>{notice&&<div className="toast" role="status"><ShieldCheck size={17}/><span>{notice}</span><button aria-label="关闭通知" onClick={()=>setNotice('')}><X size={15}/></button></div>}</div>
}
function History({items,resume}:{items:HistoryItem[];resume:(id:string)=>void}){return <section className="page history-section"><div className="section-heading"><div><span className="section-kicker">MY CASES / 个人存档</span><h2>调查记录</h2></div></div><div className="history-grid">{items.slice(0,9).map(x=><button className="history-card" key={x.id} onClick={()=>resume(x.id)}><span className="section-kicker">{x.phase==='finished'?'已结案 · '+x.score+' 分':'调查进行中'}</span><h3>{x.script.title}</h3><p>{x.evidence_count} 件证物 · {formatDate(x.updated_at)}</p><span className="text-button">{x.phase==='finished'?'查看复盘':'继续调查'}<ChevronRight size={14}/></span></button>)}</div></section>}
