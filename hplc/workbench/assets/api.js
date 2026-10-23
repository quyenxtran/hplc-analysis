import {S,$,status} from './store.js';
import {render} from './render.js';
const token=location.hash.slice(1);
export async function request(body){
 if(S.busy)return;
 if(body?.action==='fit'&&S.state){S.state.fit=null;render();}
 S.busy=true;document.querySelectorAll('button,input,select').forEach(el=>el.disabled=true);
 status(body?.action==='fit'?'Fitting components… please wait.':'Updating local session…');
 try{
  const response=await fetch(body?'/api/action':'/api/state',{method:body?'POST':'GET',headers:{'X-Session':token,'Content-Type':'application/json'},body:body?JSON.stringify({...body,revision:S.state.revision}):undefined});
  const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed.');
  S.state=body?result.state:result;
  if(body?.action==='edit'||body?.action==='restore')S.dirty=true;
  if(body?.action==='export'||body?.action==='load')S.dirty=false;
  if(body?.action==='load')S.view=null;
  render();status(result.message||'Ready. Review a window and baseline, then edit or fit.');
 }catch(error){status(error.message,true);}
 finally{S.busy=false;document.querySelectorAll('button,input,select').forEach(el=>el.disabled=false);if(S.state){$('undo').disabled=!S.state.undo;$('redo').disabled=!S.state.redo;$('load').disabled=!S.state.files.length;}}
}
export function edit(op,parameters={}){return request({action:'edit',op,parameters});}
