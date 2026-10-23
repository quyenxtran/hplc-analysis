export const S={state:null,selected:"",view:null,busy:false,dirty:false};
export const $=id=>document.getElementById(id);
export function number(id){const value=$(id).value.trim();if(!value||!Number.isFinite(Number(value)))throw Error(`Enter a finite value for ${id}.`);return Number(value);}
export function selected(){const peak=S.state?.peaks.find(p=>p.peak_id===S.selected);if(!peak)throw Error("Select a peak first.");return peak;}
export function status(message,error=false){$("status").textContent=message;$("status").classList.toggle("error",error);}
export function checked(){return [...document.querySelectorAll("[data-peak]:checked")].map(el=>el.dataset.peak);}
export const newId=()=>`peak_${Date.now()}`;
