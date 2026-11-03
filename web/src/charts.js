export const escapeHTML = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
import { finiteValue } from './study-data.js';
export function number(n, digits = 2) { const value = finiteValue(n); return value === null ? '—' : value.toLocaleString('en-GB', {maximumFractionDigits: digits, minimumFractionDigits: digits}); }
export function compact(n) { const value = finiteValue(n); return value === null ? '—' : value.toPrecision(3); }

// SVG keeps scientific curves sharp, locally rendered, and readable to assistive tools.
export function lineChart({x, series, xLabel, yLabel, title, height = 190}) {
  if (!x?.length || !series?.some(s => s.values?.length)) return `<div class="chart-empty">Your study will reveal the response.</div>`;
  const w=640, h=height, pad={l:53,r:18,t:15,b:35};
  const clean=series.filter(s=>s.values?.some((value,index)=>Number.isFinite(value)&&Number.isFinite(x[index])));
  const points=clean.flatMap(s=>s.values.map((y,index)=>({x:x[index],y})).filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));
  if(!points.length)return '<div class="chart-empty">No finite measurements are available.</div>';
  const finite=points.map(p=>p.y);
  let ymin=Math.min(0,...finite), ymax=Math.max(...finite), xmin=Math.min(...points.map(p=>p.x)), xmax=Math.max(...points.map(p=>p.x));
  if(ymax===ymin) ymax=ymin+1;
  const ymargin=(ymax-ymin)*.09; ymax+=ymargin; if(ymin<0)ymin-=ymargin;
  const px=v=>pad.l+(v-xmin)/(xmax-xmin||1)*(w-pad.l-pad.r);
  const py=v=>h-pad.b-(v-ymin)/(ymax-ymin)*(h-pad.b-pad.t);
  let grid='';
  for(let i=0;i<4;i++){const v=ymin+(ymax-ymin)*i/3;const yp=py(v);grid+=`<line x1="${pad.l}" y1="${yp}" x2="${w-pad.r}" y2="${yp}" class="gridline"/><text x="${pad.l-10}" y="${yp+3}" text-anchor="end">${escapeHTML(Math.abs(v)<.1&&v!==0?v.toExponential(0):Number(v.toPrecision(3)))}</text>`;}
  for(let i=0;i<5;i++){const v=xmin+(xmax-xmin)*i/4;grid+=`<text x="${px(v)}" y="${h-12}" text-anchor="middle">${Number(v.toPrecision(3))}</text>`;}
  const lines=clean.map(s=>{let connected=false;const path=s.values.map((value,index)=>{if(!Number.isFinite(value)||!Number.isFinite(x[index])){connected=false;return '';}const command=connected?'L':'M';connected=true;return `${command}${px(x[index]).toFixed(2)},${py(value).toFixed(2)}`;}).filter(Boolean).join(' ');return `<path d="${path}" fill="none" stroke="${escapeHTML(s.color||'#e6b66a')}" stroke-width="2" ${s.dash?'stroke-dasharray="5 5"':''}/>`;}).join('');
  return `<div class="chart-units"><span>${escapeHTML(yLabel)}</span><span>${escapeHTML(xLabel)}</span></div><svg class="line-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${escapeHTML(title)}"><title>${escapeHTML(title)}</title>${grid}${lines}</svg><div class="chart-legend">${clean.map(s=>`<span><i style="--series:${s.color}"></i>${escapeHTML(s.name)}</span>`).join('')}</div>`;
}

export function challengeBars(challenges) {
  if(!challenges?.length)return '';
  const extent=Math.max(20,...challenges.map(c=>Math.abs(c.reduction_pct)));
  return `<div class="challenge-bars">${challenges.map(c=>`<div class="challenge-row"><span title="${escapeHTML(c.name)}">${escapeHTML(c.name.replaceAll('_',' '))}${c.constraint_violation?'<b class="violation">constraint violation</b>':''}</span><div class="bar-track"><i class="bar-zero"></i><i class="bar-value ${c.reduction_pct<0?'negative':''}" style="left:${c.reduction_pct<0?50-Math.abs(c.reduction_pct)/extent*50:50}%;width:${Math.abs(c.reduction_pct)/extent*50}%"></i></div><strong class="${c.reduction_pct<0?'negative-text':''}">${c.reduction_pct>0?'+':''}${number(c.reduction_pct,1)}%</strong></div>`).join('')}<div class="bar-axis"><span>Higher vibration</span><span>Lower vibration →</span></div></div>`;
}
