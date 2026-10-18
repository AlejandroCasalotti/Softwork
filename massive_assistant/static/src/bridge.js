"use strict";
async function nativeRPC(action,data={}) {
  const response=await fetch('/massive_assistant/api',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{action,data}})});
  const result=await response.json();
  if(!response.ok || result.error)throw Error(result.error?.data?.message || 'No se pudo completar la operación.');
  return result.result;
}
async function nativePoll(job, timeout=125000) {
  const deadline=Date.now()+timeout;
  while(Date.now()<deadline){await new Promise(resolve=>setTimeout(resolve,1000));const result=await nativeRPC('result',{job});if(!result.pending){if(result.error)throw Error(result.error);return result;}}
  throw Error('La consulta tardó demasiado. Revisá el estado antes de repetir.');
}
window.massiveNativeRequest=async message=>{
  try{
    const type=message.type;
    let result;
    if(type==='status'){
      result=await nativeRPC('status');document.getElementById('native-pair').hidden=true;
    }else if(type==='chat')result=await nativeRPC('chat',{messages:message.messages,conversation:message.conversation,...(message.attachments?.length?{attachments:message.attachments}:{})});
    else if(type==='media-result')result=await nativeRPC('result',{job:message.id});
    else if(['options','operation'].includes(type))result=await nativeRPC(type,{job:message.id});
    else if(['upload','preview','confirm','cancel','attachment'].includes(type)){const data={...message};delete data.type;delete data.access_id;result=await nativeRPC(type,data);}
    else throw Error('Acción no habilitada.');
    if(result.job)result=await nativePoll(result.job,type==='preview'?1200000:125000);
    return {ok:true,data:result};
  }catch(error){return {ok:false,error:error.message};}
};
const nativeMessage=document.getElementById('native-message');
document.getElementById('native-connect').onclick=async()=>{
  const input=document.getElementById('native-key'),button=document.getElementById('native-connect');button.disabled=true;
  try{const result=await nativeRPC('pair',{api_key:input.value});input.value='';const link=document.getElementById('native-authorize');link.href=result.url;link.hidden=false;link.textContent='Abrir autorización en Massive Connector';nativeMessage.textContent='Abrí el enlace, autorizá y luego presioná Completar vinculación.';}
  catch(error){nativeMessage.textContent=error.message;}finally{button.disabled=false;}
};
document.getElementById('native-finish').onclick=async()=>{
  const button=document.getElementById('native-finish');button.disabled=true;
  try{await nativeRPC('finish');location.reload();}catch(error){nativeMessage.textContent=error.message;}finally{button.disabled=false;}
};
document.getElementById('native-disconnect').onclick=async()=>{try{await nativeRPC('disconnect');location.reload();}catch(error){nativeMessage.textContent=error.message;document.getElementById('native-pair').hidden=false;}};
