'use strict';
const $ = id => document.getElementById(id);
const COLORS = ['#c5ed90', '#81cbd4'];
let data, selected, filter = 'all', playing = !matchMedia('(prefers-reduced-motion: reduce)').matches;
let progress = 0, speed = 1, view3d = true, lastFrame = 0, projectedStops = [], polling = false, busyPreview = false;
let manual = null, history = [], liveHistory = [], jobStarted = 0;
const canvas = $('map'), ctx = canvas.getContext('2d'), chart = $('energy'), cc = chart.getContext('2d');
const fmt = (n, digits = 2) => Number(n).toFixed(digits);
const pct = n => `${fmt(n * 100, 1)}%`;
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || `Request failed (${response.status})`);
  return result;
}
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; }
async function load() {
  data = await api('/api/data');
  $('benchmark').innerHTML = `${fmt(data.optimum)} <small>km</small>`;
  $('qubits').innerHTML = `${data.quantum.num_qubits} <small>qubits · QAOA</small>`;
  $('source').textContent = data.source === 'session' ? 'THIS SESSION' : 'RECORDED RESULTS';
  $('count').textContent = `${data.candidates.length} results`;
  const quantum = data.candidates.filter(c => c.family === 'quantum');
  const best = quantum.reduce((a,b) => !a || b.prob_optimum > a.prob_optimum ? b : a, null);
  select(best || data.candidates[0]);
}
function select(candidate) {
  selected = candidate;
  manual = null;
  $('edit').checked = false;
  $('customer-editor').hidden = true;
  history = candidate.energy_history || [];
  if (!polling) { $('chart-mode').textContent = 'RECORDED'; $('chart-mode').classList.remove('live-dot'); }
  $('map-note').textContent = 'SELECT A SOLVER TO EXPLORE ITS ROUTES';
  progress = 0;
  renderSelection(); renderCandidates(); drawChart();
}
function renderCandidates() {
  const rows = data.candidates.map((c,i) => ({...c,index:i})).filter(c => filter === 'all' || c.family === filter);
  rows.sort((a,b) => a.true_route_length - b.true_route_length || a.index - b.index);
  $('candidates').innerHTML = rows.map(c => `<button class="candidate ${selected === data.candidates[c.index] && !manual ? 'selected' : ''}" data-index="${c.index}" aria-pressed="${selected === data.candidates[c.index] && !manual}"><span class="candidate-head"><span class="candidate-name"><span class="${c.family}-mark">${c.family === 'quantum' ? '✳' : '◇'}</span> ${escapeHTML(c.label)}</span><span class="candidate-km">${fmt(c.true_route_length)} <small>km</small></span></span><span class="candidate-foot"><span>${c.gap < .001 ? 'MATCHES EXACT ROUTE LENGTH' : '+' + fmt(c.gap,1) + '% ROUTE GAP'}</span><span>${c.family === 'quantum' ? pct(c.prob_optimum) + ' P(opt)' : fmt(c.runtime_s * 1000,1) + ' ms'}</span></span></button>`).join('');
  $('candidates').querySelectorAll('button').forEach(b => b.onclick = () => select(data.candidates[Number(b.dataset.index)]));
}
function current() { return manual || selected; }
function renderSelection() {
  const c = current();
  $('selection-title').textContent = c.label;
  $('distance').textContent = `${fmt(c.true_route_length)} km`;
  const gap = 100 * (c.true_route_length / data.optimum - 1);
  $('gap').textContent = c.feasible ? `${fmt(Math.max(0,gap))}%` : 'Infeasible';
  $('objective').textContent = fmt(c.model_objective);
  $('feasibility').textContent = c.feasible ? 'CAPACITY FEASIBLE' : 'OVER CAPACITY';
  $('feasibility').classList.toggle('bad', !c.feasible);
  $('insight').textContent = manual ? 'Your split uses exact shortest tours within each van. It is a manual exploration, not a QAOA result.' : c.family === 'quantum' ? `P(feasible): ${pct(c.prob_feasible)} · P(model optimum): ${pct(c.prob_optimum)} · Runtime: ${fmt(c.runtime_s,2)} s. Route shown is the run’s highest-probability feasible state.` : 'Classical benchmark. Each van follows its exact shortest tour for this customer assignment.';
  $('vans').innerHTML = ['A','B'].map((van,i) => `<article class="van-card"><div class="van-top"><i class="dot ${i ? 'b':'a'}"></i><strong>Van ${van}</strong><span class="${c.loads[i] > data.instance.capacity ? 'bad':''}">${c.loads[i]} / ${data.instance.capacity} units</span></div><div class="van-route">D ${c.routes[van].map(n => '→ ' + n).join(' ')} → D</div><div class="load-bar"><i style="width:${Math.min(100,c.loads[i] / data.instance.capacity * 100)}%;background:${c.loads[i] > data.instance.capacity ? '#f1aa8d':COLORS[i]}"></i></div></article>`).join('');
  $('customer-buttons').innerHTML = c.assignment.map((v,i) => `<button data-stop="${i}" style="color:${COLORS[v]}">Stop ${i+1} · ${v ? 'B':'A'} <small>(${data.instance.demands[i]})</small></button>`).join('');
  $('customer-buttons').querySelectorAll('button').forEach(b => b.onclick = () => switchStop(Number(b.dataset.stop)));
}
async function switchStop(index) {
  if (!$('edit').checked || busyPreview) return;
  const assignment = [...current().assignment]; assignment[index] = 1 - assignment[index];
  busyPreview = true;
  try { manual = await api('/api/preview', {assignment}); renderSelection(); renderCandidates(); progress = 0; }
  catch (e) { toast(e.message); }
  finally { busyPreview = false; }
}

// Local, dependency-free orthographic renderer. Vans are shaded 3D box meshes.
function sizeCanvas(element) {
  const rect = element.getBoundingClientRect(), ratio = Math.min(devicePixelRatio || 1, 2);
  if (element.width !== Math.round(rect.width * ratio) || element.height !== Math.round(rect.height * ratio)) {
    element.width = Math.round(rect.width * ratio); element.height = Math.round(rect.height * ratio);
  }
  return {w:rect.width,h:rect.height,ratio};
}
let W = 0, H = 0, S = 1;
function project(x,y,z=0) {
  return [W*.5 + (x + (view3d ? y*.2 : 0))*S, H*.53 + ((view3d ? -.64 : -.85)*(y-1) + (view3d ? .09*x : 0) - z)*S];
}
function line(points,color,width=1,dash=[]) {
  if (!points.length) return;
  ctx.beginPath(); points.forEach((p,i) => i ? ctx.lineTo(...p) : ctx.moveTo(...p));
  ctx.strokeStyle=color; ctx.lineWidth=width; ctx.setLineDash(dash); ctx.stroke(); ctx.setLineDash([]);
}
function polygon(points,fill,stroke) {
  ctx.beginPath(); points.forEach((p,i) => i ? ctx.lineTo(...p) : ctx.moveTo(...p)); ctx.closePath();
  ctx.fillStyle=fill; ctx.fill(); if (stroke) {ctx.strokeStyle=stroke;ctx.lineWidth=.6;ctx.stroke();}
}
function shade(hex,amount) {
  return '#' + [1,3,5].map(i => Math.max(0,Math.min(255,parseInt(hex.slice(i,i+2),16)*amount)).toFixed(0)).map(x=>Number(x).toString(16).padStart(2,'0')).join('');
}
function box(x,y,z,length,width,height,yaw,color) {
  const c=Math.cos(yaw),s=Math.sin(yaw);
  const verts=[[-length/2,-width/2,0],[length/2,-width/2,0],[length/2,width/2,0],[-length/2,width/2,0],[-length/2,-width/2,height],[length/2,-width/2,height],[length/2,width/2,height],[-length/2,width/2,height]].map(([a,b,d])=>[x+a*c-b*s,y+a*s+b*c,z+d]);
  const faces=[[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7],[4,5,6,7]];
  const visible=[];
  for (const face of faces) {
    const a=verts[face[0]],b=verts[face[1]],c=verts[face[2]];
    const u=b.map((v,i)=>v-a[i]),v=c.map((p,i)=>p-a[i]);
    const n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
    if (view3d ? n[0]*.09-n[1]*.64+n[2] > 0 : n[2] > 0) {
      const light = n[2] > 0 ? 1.08 : n[0] > 0 ? .72 : .85;
      visible.push({face,light,depth:face.reduce((sum,i)=>sum+verts[i][1],0)/4});
    }
  }
  visible.sort((a,b)=>b.depth-a.depth).forEach(f=>polygon(f.face.map(i=>project(...verts[i])),shade(color,f.light),shade(color,.65)));
}
function routePoints(route) { return [data.instance.depot,...route.map(n=>data.instance.coords[n-1]),data.instance.depot]; }
function routePose(points,t) {
  const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
  let d=t*lengths.reduce((a,b)=>a+b,0);
  for(let i=0;i<lengths.length;i++) {
    if(d<=lengths[i] || i===lengths.length-1) {
      const f=lengths[i] ? d/lengths[i] : 0;
      return {x:points[i][0]+(points[i+1][0]-points[i][0])*f,y:points[i][1]+(points[i+1][1]-points[i][1])*f,yaw:Math.atan2(points[i+1][1]-points[i][1],points[i+1][0]-points[i][0])};
    }
    d-=lengths[i];
  }
  return {x:0,y:0,yaw:0};
}
function van(p,color) {
  const ground=project(p.x,p.y);
  ctx.save();ctx.translate(...ground);ctx.scale(1,.5);ctx.beginPath();ctx.ellipse(0,4,S*.49,S*.26,0,0,Math.PI*2);ctx.fillStyle='#00000066';ctx.fill();ctx.restore();
  const dx=Math.cos(p.yaw),dy=Math.sin(p.yaw);
  for (const a of [-.24,.24]) for(const b of [-.2,.2]) box(p.x+dx*a-dy*b,p.y+dy*a+dx*b,.04,.15,.09,.16,p.yaw,'#0b1212');
  box(p.x,p.y,.17,.82,.38,.35,p.yaw,color);
  box(p.x+dx*.26,p.y+dy*.26,.38,.27,.35,.17,p.yaw,'#c8dcd0');
  box(p.x+dx*.30,p.y+dy*.30,.40,.15,.36,.09,p.yaw,'#344e53');
  box(p.x-dx*.13,p.y-dy*.13,.52,.42,.30,.025,p.yaw,shade(color,1.13));
}
function drawMap() {
  if (!data || !selected) return;
  const sz=sizeCanvas(canvas); W=sz.w;H=sz.h;S=Math.min(W/16.8,H/9.2);
  ctx.setTransform(sz.ratio,0,0,sz.ratio,0,0);ctx.clearRect(0,0,W,H);
  ctx.lineJoin='round';ctx.lineCap='round';
  // Abstract neighborhood blocks are decoration, never a road-network claim.
  for(let y=8;y>=-7;y--) for(let x=-9;x<=9;x++) {
    const noise=Math.abs(Math.sin(x*43.7+y*17.9));
    if(noise>.57 && Math.hypot(x,y)>1 && !data.instance.coords.some(p=>Math.hypot(p[0]-x,p[1]-y)<.75)) {
      const high=view3d ? .08+noise*.19 : 0;
      box(x+.12,y+.12,0,.64,.64,high,0,noise>.85?'#283d2d':'#213329');
    }
  }
  for(let x=-10;x<=10;x++) line([project(x,-8),project(x,9)],'#34513c55',.7);
  for(let y=-8;y<=9;y++) line([project(-10,y),project(10,y)],'#34513c55',.7);
  const row=current();
  if($('ghost').checked) for(const key of ['A','B']) line(routePoints(data.candidates[0].routes[key]).map(p=>project(...p)), '#d6dbc866',1.3,[5,6]);
  ['A','B'].forEach((key,i)=>{
    const path=routePoints(row.routes[key]).map(p=>project(...p,.025));
    ctx.save();ctx.shadowColor=COLORS[i];ctx.shadowBlur=10;line(path,COLORS[i]+'22',7);ctx.restore();line(path,COLORS[i]+'cc',2.3);
  });
  projectedStops=[];
  const points=[data.instance.depot,...data.instance.coords];
  points.forEach((p,i)=>{
    const pos=project(...p,.04),color=i ? COLORS[row.assignment[i-1]]:'#e2d9af';
    projectedStops.push(pos);
    ctx.beginPath();ctx.ellipse(pos[0],pos[1]+3,13,view3d?6:12,0,0,Math.PI*2);ctx.fillStyle=color+'19';ctx.fill();
    if(i===0) {
      box(...p,0,.52,.52,.45,0,'#c4bd99');box(...p,.45,.68,.65,.09,0,'#e3d8ac');
      const label=project(...p,.78); ctx.font='9px Consolas,monospace';ctx.textAlign='center';ctx.fillStyle='#e2d9af';ctx.fillText('DEPOT',label[0],label[1]);
    } else {
      line([pos,project(...p,.22)],color,1.5);const label=project(...p,.36);
      ctx.beginPath();ctx.arc(label[0],label[1],10,0,Math.PI*2);ctx.fillStyle='#18251c';ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.stroke();
      ctx.font='bold 10px Segoe UI,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(String(i),label[0],label[1]);ctx.textBaseline='alphabetic';
      ctx.font='8px Consolas,monospace';ctx.fillStyle='#a7bcac';ctx.fillText(`${data.instance.demands[i-1]} units`,label[0],label[1]-17);
    }
  });
  const poses=['A','B'].map((key,i)=>({...routePose(routePoints(row.routes[key]),progress),color:COLORS[i],i}));
  poses.sort((a,b)=>b.y-a.y).forEach(p=>{van(p,p.color); const pos=project(p.x,p.y,.93);ctx.font='bold 9px Consolas,monospace';ctx.textAlign='center';ctx.fillStyle=p.color;ctx.fillText(p.i?'B':'A',...pos);});
}
function drawChart() {
  const {w,h,ratio}=sizeCanvas(chart);cc.setTransform(ratio,0,0,ratio,0,0);cc.clearRect(0,0,w,h);
  const values=polling && liveHistory.length ? liveHistory : history;
  if(!values.length) {cc.fillStyle='#91a398';cc.font='11px Segoe UI';cc.textAlign='center';cc.fillText('Select a quantum result to see its optimizer history.',w/2,h/2);return;}
  const left=51,right=w-18,top=13,bottom=h-13;
  let min=Math.min(...values),max=Math.max(...values);if(max===min){max+=1;min-=1;}
  for(let i=0;i<3;i++){const y=top+(bottom-top)*i/2;cc.beginPath();cc.moveTo(left,y);cc.lineTo(right,y);cc.strokeStyle='#344335';cc.lineWidth=.6;cc.stroke();cc.font='8px Consolas';cc.textAlign='right';cc.fillStyle='#869a8a';cc.fillText(fmt(max-(max-min)*i/2,0),left-9,y+3);}
  const coords=values.map((v,i)=>[left+(right-left)*i/Math.max(1,values.length-1),bottom-(v-min)/(max-min)*(bottom-top)]);
  cc.beginPath();cc.moveTo(left,bottom);coords.forEach(p=>cc.lineTo(...p));cc.lineTo(right,bottom);cc.closePath();const grad=cc.createLinearGradient(0,top,0,bottom);grad.addColorStop(0,'#b9a4e32a');grad.addColorStop(1,'#b9a4e300');cc.fillStyle=grad;cc.fill();
  cc.beginPath();coords.forEach((p,i)=>i?cc.lineTo(...p):cc.moveTo(...p));cc.strokeStyle='#b9a4e3';cc.lineWidth=1.7;cc.stroke();
}
function animate(time) {
  if(lastFrame && playing && data){progress=(progress+Math.min(time-lastFrame,100)*speed/24000)%1;$('timeline').value=Math.round(progress*1000);}
  lastFrame=time;drawMap();requestAnimationFrame(animate);
}
async function pollJob() {
  try {
    const job=await api('/api/job');
    if(job.status==='running') {
      if(!polling){polling=true;$('run').disabled=true;$('preset').disabled=true;}
      const events=job.events;const latest=events.at(-1);liveHistory=events.map(e=>e.energy);
      $('job-status').textContent=latest ? `Running · p=${latest.reps} · evaluation ${latest.evaluation} · energy ${fmt(latest.energy,1)}` : 'Building QUBO and checking the exact ground state…';
      $('run').firstElementChild.textContent='Quantum solver running…';$('chart-mode').textContent='LIVE ENERGY';$('chart-mode').classList.add('live-dot');drawChart();
      setTimeout(pollJob,700);
    } else if(polling) {
      polling=false;$('run').disabled=false;$('preset').disabled=false;$('run').firstElementChild.textContent='Run quantum solver';
      $('chart-mode').classList.remove('live-dot');
      if(job.status==='complete') {await load();$('job-status').textContent=`Complete in ${fmt(job.elapsed,1)} s · session results loaded.`;}
      else {$('job-status').textContent='Run failed. Previous results are still available.';toast(job.error || 'Quantum run failed.');$('chart-mode').textContent='RECORDED';drawChart();}
    }
  } catch(e){polling=false;$('run').disabled=false;$('preset').disabled=false;$('run').firstElementChild.textContent='Run quantum solver';toast('Lost connection to the local server. '+e.message);}
}
$('run').onclick=async()=>{try{$('toast').hidden=true;$('run').disabled=true;await api('/api/run',{preset:$('preset').value});polling=true;liveHistory=[];jobStarted=Date.now();pollJob();}catch(e){$('run').disabled=false;toast(e.message);}};
$('preset').onchange=()=>{$('preset-info').textContent={quick:'1 layer · seed 0 · 60 evaluations max',balanced:'1–2 layers · seeds 0–1 · 120 evaluations max',full:'1–3 layers · seeds 0–4 · 200 evaluations max'}[$('preset').value];};
$('view3d').onclick=()=>{view3d=true;$('view3d').classList.add('active');$('view2d').classList.remove('active');};
$('view2d').onclick=()=>{view3d=false;$('view2d').classList.add('active');$('view3d').classList.remove('active');};
$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',playing?'Pause route playback':'Play route playback');};
$('speed').onclick=()=>{speed=speed===1?2:speed===2?4:1;$('speed').textContent=speed+'×';};
$('timeline').oninput=e=>{progress=Number(e.target.value)/1000;};$('replay').onclick=()=>{progress=0;};
$('edit').onchange=()=>{if(!data)return;$('customer-editor').hidden=!$('edit').checked;if(!$('edit').checked){manual=null;renderSelection();renderCandidates();}$('map-note').textContent=$('edit').checked?'CLICK A CUSTOMER OR USE THE BUTTONS BELOW TO SWITCH VANS':'SELECT A SOLVER TO EXPLORE ITS ROUTES';};
canvas.onclick=e=>{if(!$('edit').checked)return;const r=canvas.getBoundingClientRect();let best=-1,distance=30;projectedStops.forEach((p,i)=>{if(!i)return;const d=Math.hypot(e.clientX-r.left-p[0],e.clientY-r.top-(p[1]-.4*S));if(d<distance){best=i-1;distance=d;}});if(best>=0)switchStop(best);};
document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));if(data)renderCandidates();});
$('explain').onclick=()=>$('about').showModal();$('about').querySelector('.close').onclick=()=>$('about').close();$('about').onclick=e=>{if(e.target===$('about') && (e.offsetX<0 || e.offsetY<0 || e.offsetX>e.target.clientWidth || e.offsetY>e.target.clientHeight))$('about').close();};$('overview').onclick=()=>scrollTo({top:0,behavior:'smooth'});
window.addEventListener('resize',()=>drawChart());$('play').textContent=playing?'Ⅱ':'▶';
load().then(()=>pollJob()).catch(e=>toast('Unable to load results. '+e.message));requestAnimationFrame(animate);
