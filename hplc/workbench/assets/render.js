import {S,$,selected} from './store.js';
import {draw} from './chart.js';
const fmt=v=>v===null?'unavailable':typeof v==='number'?v.toLocaleString(undefined,{maximumFractionDigits:4}):String(v);
function table(target,headers,rows,manual=false){
 const table=document.createElement('table'),head=table.createTHead().insertRow();
 for(const text of headers){const th=document.createElement('th');th.textContent=text;head.append(th);}
 const body=table.createTBody();
 for(const row of rows){const tr=body.insertRow();if(manual&&row[0]===S.selected)tr.className='selected';
  if(manual){const td=tr.insertCell(),box=document.createElement('input');box.type='checkbox';box.dataset.peak=row[0];box.setAttribute('aria-label',`Select ${row[0]} for merge or separation`);td.append(box);tr.addEventListener('click',event=>{if(event.target===box)return;S.selected=row[0];render();});}
  for(const value of row){tr.insertCell().textContent=fmt(value);}
 }
 $(target).replaceChildren(table);
}
export function fields(){
 try{const p=selected();$('start').value=p.start_min;$('end').value=p.end_min;$('left').value=p.endpoints_mv[0];$('right').value=p.endpoints_mv[1];$('cut').value=(p.start_min+p.end_min)/2;}catch{}
}
export function render(){
 const s=S.state;if(!s)return;
 $('label').textContent=s.label;
 $('file').replaceChildren(...s.files.map((name,index)=>new Option(name,String(index))));$('file').value=String(s.source_index);
 $('channel').value=s.channel;
 if(!s.peaks.some(p=>p.peak_id===S.selected))S.selected=s.peaks.find(p=>p.enabled)?.peak_id||s.peaks[0]?.peak_id||'';
 $('peak').replaceChildren(...s.peaks.map(p=>new Option(p.peak_id+(p.enabled?'':' (rejected)'),p.peak_id)));$('peak').value=S.selected;fields();
 table('manualTable',['Select','Peak','Status','Start (min)','End (min)','Apex (min)','Area (µV·s)','Flags'],s.rows.map(r=>[r.peak_id,r.status,r.start_min,r.end_min,r.retention_time_min,r.area_uV_s,r.flags]),true);
 if(s.fit){const f=s.fit,d=f.diagnostics;table('fitTable',['Component','Location (min)','Apex (min)','σ (min)','τ (min)','Window area','Full model area','Full area SE'],f.components.map(r=>[r.component_id,r.location_min,r.apex_min,r.sigma_min,r.tau_min,r.area_window_uV_s,r.area_full_model_uV_s,r.area_full_model_se_uV_s]));
 $('diagnostics').textContent=`RMSE: ${fmt(d.rmse_mv)} mV · ${d.sample_count} original samples · ${d.converged_starts} converged starts\nFlags: ${d.flags.join(', ')||'none'}\nWindow areas integrate the model inside the reviewed envelope. Full areas extrapolate tails. SE is conditional on the selected model and baseline.`;
 }else{$('fitTable').textContent='No current fit. Edits clear previous fits.';$('diagnostics').textContent='No current fit. Select an envelope and review its baseline before fitting.';}
 draw();
}
