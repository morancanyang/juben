import { useEffect, useRef, useState } from 'react'
import { NotebookPen, Plus, Trash2 } from 'lucide-react'
import { ApiError, api, localDB, type GameState, type Note, type User } from './api'

const kinds:Record<string,string>={fact:'事实',statement:'角色陈述',inference:'玩家推断',hypothesis:'未验证假设'}
const fresh=():Note=>({id:crypto.randomUUID(),version:0,kind:'hypothesis',text:'',source_ids:[],partner_allowed:true})
export default function NotesPanel({state,user,refresh,notice,incoming}:{state:GameState;user:User;refresh:()=>Promise<void>;notice:(x:string)=>void;incoming:Note|null}){
 const [draft,setDraft]=useState<Note>(fresh)
 const [status,setStatus]=useState('尚未编辑')
 const [tab,setTab]=useState('notes')
 const [dirty,setDirty]=useState(false)
 const [conflict,setConflict]=useState<Note|null>(null)
 const saving=useRef(false),latest=useRef(draft),hydrated=useRef(false)
 latest.current=draft
 const key=user.id+':'+state.id
 useEffect(()=>{let live=true;localDB.drafts.get(key).then(saved=>{if(live&&saved){setDraft(saved.note);setDirty(true);setStatus('本地草稿已恢复')}hydrated.current=true});return()=>{live=false}},[key])
 useEffect(()=>{if(incoming){setDraft(incoming);setDirty(true);setTab('notes')}},[incoming])
 const edit=(patch:Partial<Note>)=>{setDraft(d=>({...d,...patch}));setDirty(true);setConflict(null)}
 useEffect(()=>{if(hydrated.current&&dirty){localDB.drafts.put({key,userId:user.id,sessionId:state.id,note:draft,updated:Date.now()}).then(()=>setStatus(navigator.onLine?'本地已保存，等待同步':'离线 · 草稿已存本机')).catch(()=>setStatus('本地存储不可用，请及时复制笔记'))}},[draft,dirty,key,state.id,user.id])
 const save=async(force=false)=>{
  if(saving.current||!latest.current.text.trim()||!navigator.onLine||(!dirty&&!force)||conflict)return
  saving.current=true;const original=latest.current;setStatus('同步中…')
  try{const result:Note=await api(`/api/v1/sessions/${state.id}/notes/${original.id}`,{method:'PUT',body:JSON.stringify({version:original.version,kind:original.kind,text:original.text,source_ids:original.source_ids,partner_allowed:original.partner_allowed})});
   setDraft(current=>current.id===result.id?{...current,version:result.version}:current)
   if(latest.current.text===original.text&&latest.current.kind===original.kind&&latest.current.partner_allowed===original.partner_allowed&&JSON.stringify(latest.current.source_ids)===JSON.stringify(original.source_ids)){setDirty(false);setStatus('已同步到存档');await localDB.drafts.delete(key)}
   await refresh()
  }catch(e:any){if(e instanceof ApiError&&e.code==='NOTE_CONFLICT'){setConflict(e.details?.server||original);setStatus('有版本冲突，当前文字仍保存在本机')}else setStatus(e instanceof ApiError?e.message:'网络不可用 · 本地草稿已保留')}
  finally{saving.current=false}
 }
 useEffect(()=>{if(!dirty)return;const t=setTimeout(()=>save(),1000);return()=>clearTimeout(t)},[draft,dirty,conflict])
 useEffect(()=>{const online=()=>{setDirty(true)};window.addEventListener('online',online);return()=>window.removeEventListener('online',online)},[])
 const choose=async(note:Note)=>{if(dirty&&draft.text.trim()&&!confirm('当前草稿尚未同步。是否切换？取消可继续编辑。'))return;setDraft(note);setDirty(false);setConflict(null);setStatus('已载入笔记')}
 const remove=async(n:Note)=>{if(!confirm('删除这条笔记？'))return;try{await api(`/api/v1/sessions/${state.id}/notes/${n.id}?version=${n.version}`,{method:'DELETE'});if(draft.id===n.id){setDraft(fresh());setDirty(false)}await refresh();notice('笔记已删除')}catch(e:any){notice(e.message)}}
 return <div className="side-panel notes-panel"><div className="compact-actions">{[['notes','笔记'],['timeline','时间线'],['relations','关系线索']].map(([id,label])=><button key={id} className={id===tab?'active':''} onClick={()=>setTab(id)}>{label}</button>)}</div>
 {tab==='notes'&&<><div className="panel-head"><span>推理笔记</span><button className="text-button" onClick={()=>choose(fresh())}><Plus size={14}/>新建</button></div><select aria-label="笔记类型" value={draft.kind} onChange={e=>edit({kind:e.target.value})}>{Object.entries(kinds).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select><textarea aria-label="笔记内容" value={draft.text} onChange={e=>edit({text:e.target.value})} placeholder="记录矛盾、时间点或动机。输入后自动保存。"/><div className="source-checkboxes">{state.evidence.map(e=><label key={e.id}><input type="checkbox" checked={draft.source_ids.includes(e.id)} onChange={()=>edit({source_ids:draft.source_ids.includes(e.id)?draft.source_ids.filter(x=>x!==e.id):[...draft.source_ids,e.id]})}/>{e.title}</label>)}</div><label className="note-consent"><input type="checkbox" checked={draft.partner_allowed} onChange={e=>edit({partner_allowed:e.target.checked})}/>允许搭档读取此笔记</label><div className="autosave-status" role="status">{status}</div><button className="small-action" onClick={()=>save(true)} disabled={!draft.text.trim()||!!conflict}><NotebookPen size={14}/>保存笔记</button>
 {conflict&&<div className="note-conflict"><p>服务器已保存另一个版本。你的文字没有被覆盖。</p><blockquote>{conflict.text}</blockquote><button className="small-action" onClick={()=>{setDraft(d=>({...d,id:crypto.randomUUID(),version:0}));setConflict(null);setDirty(true)}}>将我的文字另存为副本</button><button className="text-button" onClick={()=>{setDraft(conflict);setConflict(null);setDirty(false)}}>使用服务器版本</button></div>}
 <div className="saved-notes">{state.notes.map(n=><div className="saved-note" key={n.id}><span>{kinds[n.kind]} · V{n.version}</span><p>{n.text}</p><small>{n.partner_allowed?'已授权搭档':'仅自己可见'}</small><div className="compact-actions"><button onClick={()=>choose(n)}>编辑</button><button aria-label={'删除笔记 '+n.text.slice(0,10)} onClick={()=>remove(n)}><Trash2 size={12}/></button></div></div>)}</div></>}
 {tab==='timeline'&&<><div className="panel-head">已知证物时间线</div>{state.evidence.slice().sort((a,b)=>a.time.localeCompare(b.time)).map(e=><div className="timeline-item" key={e.id}><small>{e.time} · {e.source}</small><b>{e.title}</b><p>{e.analyzed?e.analysis:e.description}</p></div>)}{!state.evidence.length&&<p className="empty-small">发现证物后，这里会显示其时间信息。</p>}</>}
 {tab==='relations'&&<><div className="panel-head">角色与证据联系</div><p className="empty-small">关联表示与线索有关，不等于有罪。</p>{state.characters.map(c=><div className="relation-node" key={c.id}><span style={{borderColor:c.color}}>{c.name}</span><div>{state.evidence.filter(e=>e.related_characters.includes(c.id)).map(e=><p key={e.id}>↳ {e.title} <small>{e.analyzed?'已分析':'待验证'}</small></p>)}</div></div>)}{state.statements.map(s=><div className="timeline-item" key={s.id}><small>角色陈述 · {s.actor_name}</small><p>{s.text}</p></div>)}</>}
 </div>
}
