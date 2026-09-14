import { useState } from 'react'
import { ChevronRight, FlaskConical, Link2, NotebookPen, ShieldCheck, X } from 'lucide-react'
import type { Evidence, GameState } from './api'
import { evidenceImage } from './media/evidence'

export default function EvidencePanel({state,action,addNote,busy,onView}:{state:GameState;action:(body:any)=>Promise<void>;addNote:(e:Evidence)=>void;busy:boolean;onView:(evidence:Evidence)=>void}){
 const [selectedId,setSelectedId]=useState<string|null>(null)
 const [recipient,setRecipient]=useState(state.characters[0]?.id||''),[pair,setPair]=useState<string[]>([])
 const selected=state.evidence.find(e=>e.id===selectedId)
 return <div className="side-panel evidence-panel">
  <div className="panel-head"><span>{state.evidence.length} 件已发现</span><small>选中证物可分析、查看或出示</small></div>
  {!state.evidence.length&&<div className="empty-small">调查场景中的对象，第一件证物就在那里。</div>}
  <div className="evidence-list">{state.evidence.map(e=><button className={`evidence-item ${selectedId===e.id?'selected':''}`} key={e.id} onClick={()=>{setSelectedId(e.id);onView(e)}}><span className="evidence-type">{e.type==='document'?'文':e.type==='trace'?'痕':e.type==='deduction'?'链':'物'}</span><span><b>{e.title}</b><small>{e.source} · {e.time}</small></span>{e.analyzed&&<ShieldCheck size={14} aria-label="已分析"/>}</button>)}</div>
  {selected&&<div className="evidence-detail"><button aria-label="关闭证物详情" onClick={()=>setSelectedId(null)}><X size={14}/></button><span className="section-kicker">EVIDENCE / {selected.id.toUpperCase()}</span><h3>{selected.title}</h3><p>{selected.description}</p>
   <button className="evidence-view-button" onClick={()=>onView(selected)}><span className="evidence-thumb">{evidenceImage(state.script.id,selected)&&<img src={evidenceImage(state.script.id,selected)} alt="" />}</span><span><b>查看证据影像</b><small>电影化现场记录 · 点击放大</small></span><ChevronRight size={15}/></button>
   {selected.analyzed?<div className="analysis"><span>分析结论 · 已验证事实</span><p>{selected.analysis}</p></div>:<button className="small-action" disabled={busy} onClick={()=>action({type:'analyze',evidence_id:selected.id})}>分析证物 · 1 点 <FlaskConical size={14}/></button>}
   <div className="present-form"><label htmlFor="evidence-recipient">向角色出示</label><select id="evidence-recipient" value={recipient} onChange={e=>setRecipient(e.target.value)}>{state.characters.map(c=><option key={c.id} value={c.id}>{c.name} · {c.role}</option>)}</select><button className="small-action" disabled={busy||selected.presented_to.includes(recipient)} onClick={()=>action({type:'present',evidence_id:selected.id,actor_id:recipient})}>{selected.presented_to.includes(recipient)?'已向该角色出示':'出示证物 · 1 点'}<ChevronRight size={14}/></button></div>
   <button className="text-button" onClick={()=>addNote(selected)}><NotebookPen size={14}/>加入推理笔记</button>
  </div>}
  {state.evidence.length>=2&&<div className="combine-panel"><h4><Link2 size={15}/>证物组合</h4><p>选择两件物证，比对它们的联系。</p><div className="source-checkboxes">{state.evidence.filter(e=>e.type!=='deduction').map(e=><label key={e.id}><input type="checkbox" checked={pair.includes(e.id)} onChange={()=>setPair(p=>p.includes(e.id)?p.filter(x=>x!==e.id):[...p.slice(-1),e.id])}/>{e.title}</label>)}</div><button className="small-action" disabled={pair.length!==2||busy} onClick={()=>action({type:'combine',evidence_ids:pair})}>组合分析 · 1 点</button>{state.combinations.map(c=><button key={c.output} className="combination-hint" disabled={busy||state.evidence.some(e=>e.id===c.output)} onClick={()=>action({type:'combine',evidence_ids:c.inputs})}><Link2 size={13}/>{c.label}{state.evidence.some(e=>e.id===c.output)?' · 已建立':''}</button>)}</div>}
 </div>
}
