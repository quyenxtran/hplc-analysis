import {S,$,selected,status} from './store.js';
import {coords,draw,interpolate} from './chart.js';
import {edit} from './api.js';
import {render} from './render.js';
export function wirePointer(){
 const canvas=$('graph');let drag=null;
 function point(event){const rect=canvas.getBoundingClientRect();return {x:event.clientX-rect.left,y:event.clientY-rect.top};}
 canvas.addEventListener('pointerdown',event=>{
  if(S.busy||event.button!==0||!S.state)return;
  const g=coords(),p=point(event);if(p.x<g.box.l||p.x>g.box.r||p.y<g.box.t||p.y>g.box.b)return;
  const x=g.dx(p.x),mode=$('tool').value;
  try{
   if(mode==='seed'){const values=$('centers').value.split(',').filter(v=>v.trim()).map(Number);values.push(Number(x.toFixed(5)));values.sort((a,b)=>a-b);$('centers').value=values.join(', ');return;}
   if(mode==='split'){const peak=selected();edit('split_peak',{peak_id:peak.peak_id,at_min:x,separation:$('separation').value});return;}
   if(mode==='select'){
    let peak=S.state.peaks.find(item=>item.peak_id===S.selected);
    if(peak?.enabled){const ends=[peak.start_min,peak.end_min];const handle=ends.findIndex((t,i)=>Math.hypot(g.px(t)-p.x,g.py(peak.endpoints_mv[i])-p.y)<13);if(handle>=0){drag={mode:'handle',handle,peak,x,p,g};canvas.setPointerCapture(event.pointerId);return;}}
    peak=S.state.peaks.find(item=>item.enabled&&item.start_min<=x&&item.end_min>=x);if(peak){S.selected=peak.peak_id;render();}return;
   }
   drag={mode,x,p,g};canvas.setPointerCapture(event.pointerId);
  }catch(error){status(error.message,true);}
 });
 canvas.addEventListener('pointermove',event=>{
  if(!drag)return;draw();const p=point(event),g=drag.g,c=coords().c;c.strokeStyle='#146a61';c.setLineDash([4,3]);c.beginPath();c.moveTo(drag.p.x,drag.mode==='handle'?drag.p.y:g.box.t);c.lineTo(p.x,drag.mode==='handle'?p.y:g.box.t);c.stroke();if(drag.mode!=='handle'){c.fillStyle='#146a6122';c.fillRect(Math.min(p.x,drag.p.x),g.box.t,Math.abs(p.x-drag.p.x),g.box.b-g.box.t);}
 });
 canvas.addEventListener('pointerup',async event=>{
  if(!drag)return;const d=drag;drag=null;
  const p=point(event),g=d.g,x=Math.max(S.state.time[0],Math.min(S.state.time.at(-1),g.dx(p.x)));
  try{
   if(d.mode==='handle'){const params={peak_id:d.peak.peak_id};params[d.handle?'end_min':'start_min']=x;params[d.handle?'end_mv':'start_mv']=g.dy(p.y);await edit('move_baseline',params);}
   else if(Math.abs(p.x-d.p.x)>5){const bounds=[d.x,x].sort((a,b)=>a-b);if(d.mode==='zoom'){S.view=bounds;draw();}else{[ $('start').value,$('end').value]=bounds;const ys=bounds.map(t=>interpolate(t,S.state.time,S.state.signal));[$('left').value,$('right').value]=ys;status('Window selected. Click Insert window, or Skim inside selected.');}}
  }catch(error){status(error.message,true);}draw();
 });
 canvas.addEventListener('pointercancel',()=>{drag=null;draw();});
 new ResizeObserver(draw).observe(canvas);
}
