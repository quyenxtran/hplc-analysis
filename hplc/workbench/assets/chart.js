import {S,$} from './store.js';
export const colors=['#146a61','#9b4800','#4d60ae','#a43872','#55751e','#126a92'];
let geometry=null;
export const coords=()=>geometry;
export function interpolate(x,xs,ys){let lo=0,hi=xs.length-1;while(lo+1<hi){const mid=(lo+hi)>>1;if(xs[mid]>x)hi=mid;else lo=mid;}const ratio=Math.max(0,Math.min(1,(x-xs[lo])/(xs[hi]-xs[lo])));return ys[lo]+ratio*(ys[hi]-ys[lo]);}
function setup(canvas,xRange,yRange,yLabel){
 const ratio=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*ratio;canvas.height=h*ratio;
 const c=canvas.getContext('2d');c.scale(ratio,ratio);c.clearRect(0,0,w,h);c.font='12px system-ui';
 const box={l:62,r:w-18,t:22,b:h-34};
 const px=x=>box.l+(x-xRange[0])/(xRange[1]-xRange[0])*(box.r-box.l),py=y=>box.b-(y-yRange[0])/(yRange[1]-yRange[0])*(box.b-box.t);
 c.strokeStyle='#dce4e8';c.fillStyle='#526675';
 for(let i=0;i<=5;i++){const tx=xRange[0]+i*(xRange[1]-xRange[0])/5,ty=yRange[0]+i*(yRange[1]-yRange[0])/5;c.beginPath();c.moveTo(px(tx),box.t);c.lineTo(px(tx),box.b);c.moveTo(box.l,py(ty));c.lineTo(box.r,py(ty));c.stroke();c.fillText(tx.toFixed(2),px(tx)-12,h-12);c.fillText(ty.toPrecision(3),2,py(ty)+4);}
 c.fillText(yLabel,4,12);c.fillText('min',w-25,h-2);
 function line(xs,ys,color,dashed=false){c.save();c.beginPath();c.rect(box.l,box.t,box.r-box.l,box.b-box.t);c.clip();c.strokeStyle=color;c.lineWidth=1.4;c.setLineDash(dashed?[5,4]:[]);c.beginPath();xs.forEach((x,i)=>i?c.lineTo(px(x),py(ys[i])):c.moveTo(px(x),py(ys[i])));c.stroke();c.restore();}
 return {c,box,px,py,line,dx:p=>xRange[0]+(p-box.l)/(box.r-box.l)*(xRange[1]-xRange[0]),dy:p=>yRange[0]+(box.b-p)/(box.b-box.t)*(yRange[1]-yRange[0])};
}
export function draw(){
 const s=S.state;if(!s)return;const xr=S.view||[s.time[0],s.time.at(-1)];
 let low=Infinity,high=-Infinity;s.time.forEach((t,i)=>{if(t>=xr[0]&&t<=xr[1]){low=Math.min(low,s.signal[i]);high=Math.max(high,s.signal[i]);}});
 if(!Number.isFinite(low)){low=0;high=1;}
 const chosen=s.peaks.find(p=>p.peak_id===S.selected);if(chosen){low=Math.min(low,...chosen.endpoints_mv);high=Math.max(high,...chosen.endpoints_mv);}
 const pad=Math.max((high-low)*.12,.01),g=setup($('graph'),xr,[low-pad,high+pad],'mV');geometry=g;
 s.peaks.forEach((p,i)=>{if(!p.enabled)return;const left=Math.max(p.start_min,xr[0]),right=Math.min(p.end_min,xr[1]);if(left>=right)return;g.c.fillStyle=p.peak_id===S.selected?'#146a611c':'#172b3a08';g.c.fillRect(g.px(left),g.box.t,g.px(right)-g.px(left),g.box.b-g.box.t);g.line(p.baseline_times,p.baseline_values_mv,colors[i%colors.length],true);g.c.fillStyle=colors[i%colors.length];g.c.fillText(p.peak_id,g.px(left)+4,g.box.t+14+(i%3)*14);});
 g.line(s.time,s.signal,'#172b3a');
 if(s.fit){const f=s.fit.curves;g.line(f.time_min,f.fitted_net_mV.map((v,i)=>v+f.baseline_mV[i]),'#b64524');Object.keys(f).filter(k=>k.startsWith('component_')).forEach((key,i)=>g.line(f.time_min,f[key].map((v,j)=>v+f.baseline_mV[j]),colors[i%colors.length]));}
 if(chosen&&chosen.enabled){[chosen.start_min,chosen.end_min].forEach((x,i)=>{g.c.beginPath();g.c.arc(g.px(x),g.py(chosen.endpoints_mv[i]),6,0,Math.PI*2);g.c.fillStyle='#146a61';g.c.fill();});}
 const f=s.fit?.curves,amplitude=f?f.residual_mV.reduce((m,v)=>Math.max(m,Math.abs(v)),.001):.1;
 const r=setup($('residual'),xr,[-amplitude*1.2,amplitude*1.2],'Residual mV');r.line(xr,[0,0],'#526675',true);if(f)r.line(f.time_min,f.residual_mV,'#172b3a');
}
