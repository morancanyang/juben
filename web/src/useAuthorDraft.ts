import { useEffect, useRef, useState } from 'react'
import { api } from './api'

type Draft = {format:2;content:any;raw:string;selected:string;draftStatus:string;dirty:boolean}
const key=(uid:string,id='')=>'casebook_author_'+uid+(id?':'+id:'')
const unpack=(text:string):Draft=>{
  const value=JSON.parse(text)
  const draft=value.format===2?value:{format:2,content:value,raw:JSON.stringify(value,null,2),selected:'',draftStatus:'draft',dirty:false}
  if(!draft.content || typeof draft.content!=='object' || Array.isArray(draft.content) || typeof draft.raw!=='string')throw new Error('无效草稿')
  return draft
}

export function useAuthorDraft(uid:string|undefined,notice:(message:string)=>void){
  const [draft,setDraft]=useState<Draft|null>(null)
  const [drafts,setDrafts]=useState<any[]>([])
  const [saveStatus,setSaveStatus]=useState('正在载入…')
  const current=useRef<Draft|null>(null)
  const live=useRef(false)
  const queue=useRef<Promise<any>>(Promise.resolve())
  const serialize=<T,>(operation:()=>Promise<T>):Promise<T>=>{
    const task=queue.current.catch(()=>{}).then(operation)
    queue.current=task
    return task
  }
  const remember=(next:Draft)=>{
    current.current=next
    setDraft(next)
    if(uid)try{
      const text=JSON.stringify(next)
      // Write on edit, before navigation or logout can unmount the workbench.
      localStorage.setItem(key(uid),text)
      if(next.selected)localStorage.setItem(key(uid,next.selected),text)
    }catch{setSaveStatus('本机保存失败，请立即导出备份');notice('本机存储不可用或空间不足，请导出内容备份。')}
  }
  const loadList=async()=>{
    const items=(await api('/api/v1/author/drafts')).items
    if(live.current)setDrafts(items)
    return items
  }
  const describe=(d:Draft)=>d.raw!==JSON.stringify(d.content,null,2)?'JSON 修改已存本机，尚未应用':d.draftStatus==='frozen'?'冻结版本 · 修改保存在本机，请另存新版本':d.dirty&&d.selected?'本机已保存，等待同步':d.selected?'私人草稿已保存':'本机已保存 · 点击保存新版本同步到账号'
  useEffect(()=>{
    live.current=true
    let cancelled=false
    if(uid)(async()=>{
      let cached:Draft|null=null
      try{const text=localStorage.getItem(key(uid));if(text)cached=unpack(text)}catch{}
      if(cached){remember(cached);setSaveStatus(describe(cached))}
      try{
        const items=await loadList()
        if(cancelled)return
        if(cached){
          const row=items.find((d:any)=>d.id===cached!.selected)
          if(current.current===cached && row && row.status!==cached.draftStatus){const next={...cached,draftStatus:row.status};remember(next);setSaveStatus(describe(next))}
        }else if(items.length){
          const saved=await api(`/api/v1/author/drafts/${items[0].id}`)
          if(cancelled)return
          const next:Draft={format:2,content:saved.content,raw:JSON.stringify(saved.content,null,2),selected:saved.id,draftStatus:saved.status,dirty:false}
          remember(next);setSaveStatus(describe(next))
        }else{
          const content=await api('/api/v1/author/template')
          if(!cancelled){const next:Draft={format:2,content,raw:JSON.stringify(content,null,2),selected:'',draftStatus:'draft',dirty:false};remember(next);setSaveStatus(describe(next))}
        }
      }catch(e:any){if(!cancelled){setSaveStatus(cached?'本机草稿已恢复，服务器暂不可用':'载入失败，请刷新重试');notice(e.message)}}
    })()
    return()=>{cancelled=true;live.current=false}
  },[uid])
  useEffect(()=>{
    if(!draft?.selected || !draft.dirty || draft.draftStatus==='frozen' || draft.raw!==JSON.stringify(draft.content,null,2))return
    const timer=setTimeout(()=>{
      void serialize(async()=>{
        if(!live.current || current.current!==draft)return
        setSaveStatus('本机已保存，正在同步…')
        try{
          const saved=await api(`/api/v1/author/drafts/${draft.selected}`,{method:'PUT',body:JSON.stringify({content:draft.content})})
          if(live.current && current.current===draft){const next={...draft,content:saved.content,raw:JSON.stringify(saved.content,null,2),dirty:false};remember(next);setSaveStatus('私人草稿已保存')}
          if(live.current)setDrafts(rows=>rows.map(row=>row.id===draft.selected?{...row,title:saved.content.title}:row))
        }catch{if(live.current && current.current===draft)setSaveStatus('本机已保存，服务器同步失败；修改或保存新版本可重试')}
      })
    },1200)
    return()=>clearTimeout(timer)
  },[draft])
  useEffect(()=>{
    const retry=()=>{
      const d=current.current
      if(d?.dirty && d.selected && d.draftStatus!=='frozen')remember({...d})
    }
    window.addEventListener('online',retry)
    return()=>window.removeEventListener('online',retry)
  },[uid])
  const setPackage=(content:any)=>{
    const next:Draft={format:2,content,raw:JSON.stringify(content,null,2),selected:'',draftStatus:'draft',dirty:true}
    setSaveStatus(describe(next));remember(next)
  }
  const applyContent=(content:any)=>{
    if(!current.current)return
    const next={...current.current,content,raw:JSON.stringify(content,null,2),dirty:true}
    setSaveStatus(describe(next));remember(next)
  }
  const setRaw=(raw:string)=>{
    if(!current.current)return
    const next={...current.current,raw,dirty:true}
    setSaveStatus(describe(next));remember(next)
  }
  const applied=()=>{
    const d=current.current!
    if(d.raw===JSON.stringify(d.content,null,2))return d.content
    let content:any
    try{content=JSON.parse(d.raw);if(!content||typeof content!=='object'||Array.isArray(content))throw new Error()}catch{throw new Error('JSON 格式无效，修改已保存在本机；请修正后再质检或保存。')}
    applyContent(content)
    return content
  }
  const save=()=>serialize(async()=>{
    const content=applied(),snapshot=current.current!
    const saved=await api('/api/v1/author/drafts',{method:'POST',body:JSON.stringify({content})})
    if(live.current && current.current===snapshot){remember({...snapshot,content:saved.content,raw:JSON.stringify(saved.content,null,2),selected:saved.id,draftStatus:'draft',dirty:false});setSaveStatus('私人草稿已保存')}
    await loadList()
    return saved.id as string
  })
  const loadDraft=async(id:string)=>{
    if(!id)return
    // Preserve each draft's unfinished local text when switching versions.
    await serialize(async()=>{
      const saved=await api(`/api/v1/author/drafts/${id}`)
      let local:Draft|null=null
      try{const text=localStorage.getItem(key(uid!,id));if(text)local=unpack(text)}catch{}
      const next:Draft=local?.dirty?{...local,draftStatus:saved.status}:{format:2,content:saved.content,raw:JSON.stringify(saved.content,null,2),selected:id,draftStatus:saved.status,dirty:false}
      remember(next);setSaveStatus(describe(next))
    })
  }
  return {content:draft?.content,raw:draft?.raw||'',selected:draft?.selected||'',drafts,saveStatus,loadList,setPackage,applyContent,setRaw,applied,save,loadDraft}
}
