const historySamples=[];
let historyMinutes=15;
const chartSensors=[['Soil moisture','%','#2398df'],['Soil temperature','°C','#bc8423'],['Air temperature','°C','#df7655'],['Humidity','%','#7771d7']];
const chartGrid=document.getElementById('chartGrid');
chartGrid.innerHTML=chartSensors.map(([name,unit,color],i)=>`<article class="chart-card"><div class="chart-heading"><h3><span class="legend-dot" style="background:${color}"></span>${name}</h3><span>${unit}</span></div><div class="plot" id="plot${i}"><div class="chart-empty">Your first readings will appear here.<br><small>Connect your ESP32 to load telemetry.</small></div></div><div class="chart-stats" id="stats${i}"><span>MIN <b>—</b></span><span>AVG <b>—</b></span><span>MAX <b>—</b></span></div></article>`).join('');
function recordTelemetry(values,pump){TelemetryHistory.append(historySamples,{time:Date.now(),values:values.slice(0,4),pump});renderHistory();}
function resetHistory(){historySamples.length=0;renderHistory();}
function renderHistory(){
 const now=Date.now(),samples=TelemetryHistory.windowed(historySamples,historyMinutes,now);
 document.getElementById('sampleCount').textContent=historySamples.length+' samples loaded';
 document.getElementById('exportCsv').disabled=historySamples.length===0;
 chartSensors.forEach(([name,unit,color],i)=>{
  const stat=TelemetryHistory.summarize(samples,i);
  if(!stat){document.getElementById('plot'+i).innerHTML='<div class="chart-empty">No readings in this time range.<br><small>Connect your ESP32 to collect telemetry.</small></div>';document.getElementById('stats'+i).innerHTML='<span>MIN <b>—</b></span><span>AVG <b>—</b></span><span>MAX <b>—</b></span>';return;}
  const pad=Math.max((stat.max-stat.min)*.15,unit==='%'?2:1),low=stat.min-pad,high=stat.max+pad;
  const end=now,start=historyMinutes?now-historyMinutes*60000:Math.min(samples[0].time,now-60000);
  const segments=TelemetryHistory.segments(samples,i,start,end,low,high);
  const tick=t=>new Date(t).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
  let svg=`<svg viewBox="0 0 700 228" role="img" aria-label="${name} history: ${samples.length} samples, minimum ${stat.min.toFixed(1)}, maximum ${stat.max.toFixed(1)} ${unit}">`;
  for(let n=0;n<4;n++){const y=28+n*152/3;svg+=`<line x1="54" x2="674" y1="${y}" y2="${y}" stroke="#edf0f3"/><text x="44" y="${y+4}" text-anchor="end" fill="#88949b" font-size="12">${(high-n*(high-low)/3).toFixed(1)}</text>`;}
  segments.forEach(points=>{const coords=points.map(p=>p.join(',')).join(' ');svg+=`<polygon points="${points[0][0]},180 ${coords} ${points.at(-1)[0]},180" fill="${color}" opacity=".07"/><polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>`;});
  const point=segments.at(-1).at(-1);svg+=`<circle cx="${point[0]}" cy="${point[1]}" r="3.5" fill="${color}"/><text x="54" y="213" fill="#88949b" font-size="12">${tick(start)}</text><text x="364" y="213" text-anchor="middle" fill="#88949b" font-size="12">${tick((start+end)/2)}</text><text x="674" y="213" text-anchor="end" fill="#88949b" font-size="12">${tick(end)}</text></svg>`;
  document.getElementById('plot'+i).innerHTML=svg;
  document.getElementById('stats'+i).innerHTML=['min','avg','max'].map(k=>`<span>${k.toUpperCase()} <b>${stat[k].toFixed(1)} ${unit}</b></span>`).join('');
 });
}
document.getElementById('historyRange').onchange=e=>{historyMinutes=Number(e.target.value);renderHistory()};
document.getElementById('exportCsv').onclick=()=>{const url=URL.createObjectURL(new Blob([TelemetryHistory.csv(historySamples)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='smart-agric-'+new Date().toISOString().slice(0,10)+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
setInterval(renderHistory,5000);
