import {S,$,number,selected,checked,newId,status} from './store.js';
import {edit,request} from './api.js';
import {render} from './render.js';
function bind(id,fn){$(id).addEventListener('click',async()=>{if(S.busy)return;try{await fn();}catch(error){status(error.message,true);}});}
export function wireActions(){
 function panel(fit){$('manualControls').hidden=fit;$('fitControls').hidden=!fit;for(const [id,active] of [['manualTab',!fit],['fitTab',fit]]){$(id).classList.toggle('primary',active);$(id).setAttribute('aria-pressed',String(active));}}
 bind('manualTab',()=>panel(false));bind('fitTab',()=>panel(true));
 $('peak').addEventListener('change',()=>{S.selected=$('peak').value;render();});
 bind('undo',()=>edit('undo'));bind('redo',()=>edit('redo'));
 bind('export',()=>request({action:'export'}));
 bind('load',()=>{if(S.dirty&&!confirm('Changing files discards unsaved edits. Export first if needed. Continue?'))return;return request({action:'load',index:Number($('file').value),channel:$('channel').value});});
 bind('move',()=>edit('move_baseline',{peak_id:selected().peak_id,start_min:number('start'),end_min:number('end'),start_mv:number('left'),end_mv:number('right')}));
 bind('setbase',()=>{const mode=$('baseline').value,p={peak_id:selected().peak_id,mode};if(mode==='custom'){p.knots=$('knots').value.split(';').map(pair=>pair.split(',').map(Number));if(p.knots.some(pair=>pair.length!==2||pair.some(v=>!Number.isFinite(v))))throw Error('Use time,mV; time,mV for custom knots.');}else if(mode!=='zero'){p.start_mv=number('left');p.end_mv=mode==='horizontal'?p.start_mv:number('right');}return edit('set_baseline',p);});
 bind('insert',()=>{const id=newId();return edit('insert_peak',{peak_id:id,start_min:number('start'),end_min:number('end'),start_mv:number('left'),end_mv:number('right')});});
 bind('skim',()=>{const parent=selected().peak_id,id=newId();return edit('skim_peak',{parent_id:parent,peak_id:id,start_min:number('start'),end_min:number('end'),start_mv:number('left'),end_mv:number('right')});});
 bind('reject',()=>{const p=selected();return edit(p.enabled?'reject_peak':'restore_peak',{peak_id:p.peak_id});});
 bind('unskim',()=>edit('remove_skim',{peak_id:selected().peak_id}));
 bind('split',()=>edit('split_peak',{peak_id:selected().peak_id,at_min:number('cut'),separation:$('separation').value}));
 bind('valley',()=>edit('split_at_valley',{peak_id:selected().peak_id,between_min:[number('valleyStart'),number('valleyEnd')],separation:$('separation').value}));
 bind('merge',()=>edit('unify_peaks',{peak_ids:checked(),new_id:newId()}));
 bind('separate',()=>{const ids=checked().sort((a,b)=>S.state.peaks.find(p=>p.peak_id===a).start_min-S.state.peaks.find(p=>p.peak_id===b).start_min);if(ids.length!==2)throw Error('Check exactly two adjacent peaks.');return edit('set_separation',{left_id:ids[0],right_id:ids[1],mode:$('separation').value,at_min:number('cut')});});
 bind('fit',()=>{const text=$('centers').value.trim();if(!text||text.split(',').some(s=>!s.trim()))throw Error('Supply comma-separated center estimates.');return request({action:'fit',parameters:{peak_id:selected().peak_id,centers_min:text.split(',').map(Number),model:$('model').value,center_tolerance_min:$('tolerance').value?number('tolerance'):null}});});
 bind('reset',()=>{S.view=null;render();});
 $('audit').addEventListener('change',async event=>{try{const file=event.target.files[0];if(file)await request({action:'restore',audit:JSON.parse(await file.text())});}catch(error){status(error.message,true);}event.target.value='';});
 window.addEventListener('beforeunload',event=>{if(S.dirty){event.preventDefault();event.returnValue='';}});
}
