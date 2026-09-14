import Dexie, { type EntityTable } from 'dexie'

export type User = {id:string;nickname:string;csrf:string;guest:boolean;username:string|null;preferences:Record<string,string>}
export type Script = {id:string;title:string;subtitle:string;description:string;genre:string;difficulty:string;duration:number;cover:string;tags:string[];warnings:string[];version:number;version_id:string;character_count:number;evidence_count:number;intro?:string;characters?:Character[];custom?:boolean}
export type Character = {id:string;name:string;role:string;bio:string;color:string;trust:number;alertness:number;emotion:string;suggestions:string[];avatar?:string}
export type Evidence = {id:string;title:string;type:string;description:string;source:string;time:string;related_characters:string[];analyzed:boolean;analysis:string|null;presented_to:string[]}
export type Note = {id:string;version:number;kind:string;text:string;source_ids:string[];partner_allowed:boolean;updated_at?:string}
export type GameState = {id:string;version:number;phase:string;script:Script;config:{difficulty:string;perspective:string;partner_style:string};points:number;elapsed:number;current_scene:string;scenes:{id:string;name:string;subtitle:string;description:string;unlocked:boolean;objects:{id:string;name:string;description:string;available:boolean;searched:boolean;evidence_id?:string|null}[]}[];characters:Character[];evidence:Evidence[];analyzed:string[];combinations:{inputs:string[];output:string;label:string}[];messages:{id:string;run_id:string;actor_id:string;actor_name:string;role:string;text:string;time:string}[];statements:{id:string;text:string;actor_id:string;actor_name:string;kind:string}[];journal:{text:string;time:string}[];notes:Note[];partner_analyses:any[];hint_spent:number;active_run:string|null;questions:{id:string;label:string;options:{id:string;label:string}[]}[];result:any;updated_at:string}
export type HistoryItem = {id:string;script:Script;phase:string;evidence_count:number;score:number|null;updated_at:string;version:number}

let csrf=''
export function saveUser(user:User|null){csrf=user?.csrf||''}
export class ApiError extends Error{code:string;details:any;status:number;constructor(data:any,status:number){super(data.error?.message||'请求失败，请稍后重试。');this.code=data.error?.code||'HTTP_ERROR';this.details=data.error?.details;this.status=status}}
export async function api(path:string,options:RequestInit={}){
  const headers=new Headers(options.headers)
  headers.set('Content-Type','application/json')
  if(csrf)headers.set('X-CSRF-Token',csrf)
  const res=await fetch(path,{...options,headers,credentials:'same-origin'})
  const data=await res.json().catch(()=>({}))
  if(!res.ok)throw new ApiError(data,res.status)
  return data
}
export const idem=()=>crypto.randomUUID()
export const command=(path:string,body:unknown,key=idem())=>api(path,{method:'POST',headers:{'Idempotency-Key':key},body:JSON.stringify(body)})
export function download(name:string,data:unknown){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
export const localDB=new Dexie('casebook-local-v1') as Dexie&{
  drafts:EntityTable<{key:string;userId:string;sessionId:string;note:Note;updated:number},'key'>
  snapshots:EntityTable<{key:string;userId:string;state:GameState},'key'>
  intents:EntityTable<{key:string;userId:string;sessionId:string;body:any;expected:number;status:string},'key'>
}
localDB.version(1).stores({drafts:'key,userId,sessionId',snapshots:'key,userId',intents:'key,userId,sessionId'})
export async function clearLocal(userId:string){await Promise.all([localDB.drafts.where('userId').equals(userId).delete(),localDB.snapshots.where('userId').equals(userId).delete(),localDB.intents.where('userId').equals(userId).delete()]);for(const k of Object.keys(localStorage))if(k==='casebook_active_'+userId||k==='casebook_author_'+userId||k.startsWith('casebook_author_'+userId+':'))localStorage.removeItem(k)}
export const formatDate=(value:string)=>new Date(value).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})
