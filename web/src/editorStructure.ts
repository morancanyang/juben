// Keep the count controls within the same contract as author/validate.
type Package = Record<string, any>
const uniqueId = (prefix:string, ids:string[]) => {
  let n=1
  while(ids.includes(`${prefix}_${n}`))n++
  return `${prefix}_${n}`
}
function conditionUses(node:any, key:string, id:string):boolean {
  if(!node || typeof node!=='object')return false
  if(node.condition && conditionUses(node.condition,key,id))return true
  if(node.op && node[key]===id)return true
  return Object.values(node).some(value=>typeof value==='object' && conditionUses(value,key,id))
}
export function resizeCharacters(content:Package, delta:number):Package {
  const list=[...content.characters]
  if(delta>0){
    if(list.length>=8)throw new Error('每个剧本最多设置 8 位角色。')
    const id=uniqueId('actor',list.map(c=>c.id))
    const statementId=uniqueId(id,list.flatMap(c=>c.statements.map((s:any)=>s.id)))
    list.push({id,name:`角色${list.length+1}`,role:'待设定职位',bio:'请补充角色背景。',personality:'请补充说话方式与秘密。',color:'#9aa891',statements:[{id:statementId,text:'请补充该角色掌握的第一条证词。',keywords:['时间']}]})
  }else{
    if(list.length<=2)throw new Error('剧本至少需要 2 位角色。')
    const last=list[list.length-1]
    if(Object.values(content.answer||{}).includes(last.id) || content.evidence.some((e:any)=>e.related_characters?.includes(last.id)) || conditionUses(content,'actor',last.id) || content.questions.some((q:any)=>q.id!=='culprit'&&q.options.some((o:any)=>o.id===last.id)))throw new Error(`「${last.name}」仍被答案、证物或条件引用，请在完整结构中调整引用后再减少。`)
    list.pop()
  }
  return {...content,characters:list,questions:content.questions.map((q:any)=>q.id==='culprit'?{...q,options:list.map(c=>({id:c.id,label:c.name}))}:q)}
}
export function resizeEvidence(content:Package, delta:number):Package {
  const list=[...content.evidence]
  let scenes=content.scenes.map((s:any)=>({...s,objects:[...s.objects]}))
  if(delta>0){
    if(list.length>=60)throw new Error('每个剧本最多设置 60 件证物。')
    const id=uniqueId('evidence',list.map(e=>e.id))
    const scene=scenes.find((s:any)=>s.objects.length<20)
    if(!scene)throw new Error('现有房间已满，请在完整结构中增加房间后再添加证物。')
    const title=`新证物${list.length+1}`
    list.push({id,title,type:'trace',description:'请补充证物描述。',analysis:'请补充检验结论。',source:scene.name,time:'待补充',related_characters:[]})
    scene.objects.push({id:uniqueId('object',scene.objects.map((o:any)=>o.id)),name:title,description:'请补充调查对象描述。',evidence_id:id})
  }else{
    if(list.length<=3)throw new Error('剧本至少需要 3 件证物。')
    const last=list[list.length-1]
    if(content.key_evidence?.includes(last.id) || conditionUses(content,'ref',last.id) || content.triggers?.some((t:any)=>t.evidence_id===last.id) || content.combinations?.some((c:any)=>c.output===last.id||c.inputs.includes(last.id)) || scenes.some((s:any)=>s.objects.every((o:any)=>o.evidence_id===last.id)))throw new Error(`「${last.title}」仍被关键线索、条件、组合或房间引用，请在完整结构中调整后再减少。`)
    list.pop()
    scenes=scenes.map((s:any)=>({...s,objects:s.objects.filter((o:any)=>o.evidence_id!==last.id)}))
  }
  return {...content,evidence:list,scenes}
}
