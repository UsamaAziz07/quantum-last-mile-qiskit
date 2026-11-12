import * as THREE from '/vendor/three.module.js';

const $ = id => document.getElementById(id);
const COLORS = ['#6398c8','#56a5a3','#d4a16c','#c88fa9','#8e9bc4','#b5ad70','#a394bb','#8ca88a'];
const fmt = (v,d=2) => Number(v).toFixed(d);
const empty = () => ({type:'FeatureCollection',features:[]});
let presets, draft, scene=null, chosen=-1, roads=null, markers=[], busy=false, routeToken=0;
let progress=0, playing=!matchMedia('(prefers-reduced-motion: reduce)').matches, speed=1,lastTime=0,loaded=false;
let routePaths=[], selectedRow=null, quantumPolling=false;
const vans=[];
const vehicleMarkers=[];
let dropoffMarkers=[];

async function api(path,body) {
  const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const value=await response.json();if(!response.ok)throw Error(value.error||`Request failed (${response.status})`);return value;
}
function notice(message) {$('city-toast').textContent=message;$('city-toast').hidden=false;}
function status(message) {$('city-status').textContent=message;}
const map = new maplibregl.Map({container:'real-map',style:'https://tiles.openfreemap.org/styles/liberty',center:[73.0479,33.698],zoom:12.8,pitch:52,bearing:-15,antialias:true,maxZoom:19,minZoom:9,attributionControl:true});
map.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'top-right');
map.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left');
map.on('error',e=>{if(!loaded){$('map-loading').hidden=false;$('map-loading').textContent='Map tiles could not load. Check your connection; the free map service may be temporarily unavailable.';}console.warn('Map service:',e.error?.message);});
map.on('load',()=>{
  loaded=true;$('map-loading').hidden=true;
  map.addSource('delivery-routes',{type:'geojson',data:empty()});
  map.addLayer({id:'route-glow',type:'line',source:'delivery-routes',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':['get','color'],'line-width':10,'line-opacity':.25}});
  map.addLayer({id:'route-line',type:'line',source:'delivery-routes',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':['get','color'],'line-width':4,'line-opacity':.95}});
  map.addSource('dropoff-links',{type:'geojson',data:empty()});
  map.addLayer({id:'dropoff-links-line',type:'line',source:'dropoff-links',paint:{'line-color':'#e58f86','line-width':2,'line-dasharray':[2,2]}});
  const building=map.getStyle().layers.find(l=>l['source-layer']==='building'&&l.source);
  if(building)map.addLayer({id:'city-buildings-3d',source:building.source,'source-layer':'building',type:'fill-extrusion',minzoom:14,paint:{'fill-extrusion-color':'#c5cbbb','fill-extrusion-height':['coalesce',['get','render_height'],['get','height'],8],'fill-extrusion-base':['coalesce',['get','render_min_height'],['get','min_height'],0],'fill-extrusion-opacity':.65}});
  createVehicleMarkers();
  if(roads)drawRoads();
  markDropoffs();
});
map.on('click',e=>{
  const place=$('placement').value;if(place===''||busy)return;
  const i=Number(place);draft.points[i]=[e.lngLat.lng,e.lngLat.lat];markers[i].setLngLat(draft.points[i]);invalidate();
});

function fit() {
  const points=roads?[...roads.routes.flatMap(r=>r.geometry.coordinates),...(scene?.dropoffs||[]).map(d=>d.requested)]:draft?.points;
  if(!points?.length)return;const bounds=new maplibregl.LngLatBounds();points.forEach(p=>bounds.extend(p));
  map.fitBounds(bounds,{padding:{top:75,bottom:80,left:65,right:65},duration:900,maxZoom:15});
}
function markStops() {
  markers.forEach(m=>m.remove());markers=[];
  draft.points.forEach((p,i)=>{
    const el=document.createElement('div');el.className='stop-marker'+(i===0?' depot-marker':'');
    el.textContent=i?String(i):'D';el.setAttribute('aria-label',i?`Drag delivery stop ${i}`:'Drag depot');
    const title=document.createElement('span');title.className='marker-title';title.textContent=i?`${draft.demands[i-1]} units`:'DEPOT';el.append(title);
    const marker=new maplibregl.Marker({element:el,draggable:!busy}).setLngLat(p).addTo(map);
    marker.on('dragend',()=>{const pos=marker.getLngLat();draft.points[i]=[pos.lng,pos.lat];invalidate();});markers.push(marker);
  });
}
function invalidate() {
  scene=null;chosen=-1;roads=null;selectedRow=null;routePaths=[];routeToken++;
  if(loaded)map.getSource('delivery-routes').setData(empty());vans.forEach(v=>v.visible=false);
  dropoffMarkers.forEach(m=>m.remove());dropoffMarkers=[];
  if(loaded)map.getSource('dropoff-links').setData(empty());
  markers.forEach((m,i)=>{if(!i)return;const el=m.getElement();el.classList.remove('inaccessible-stop');el.firstChild.textContent=String(i);el.title='';el.style.borderColor='';el.style.color='';el.querySelector('.marker-title').textContent=`${draft.demands[i-1]} units`;});
  $('city-source').textContent='Draft';$('city-run').disabled=true;
  $('city-count').textContent='0 results';$('city-candidates').innerHTML='<div class="empty-state">Scenario changed.<br>Solve again to compare fresh results.</div>';
  for(const id of ['model-distance','city-gap','city-objective','road-distance','road-duration'])$(id).textContent='—';
  $('city-selection').textContent='No plan selected';$('city-feasible').textContent='—';
  $('city-benchmark').innerHTML='— <small>straight-line km</small>';
  $('city-insight').textContent='Model distance uses straight-line coordinates. Road estimates are shown separately.';
  $('city-job').textContent='Solve a scenario first.';
  $('road-caption').textContent='Routes follow the selected plan. Travel estimates exclude live traffic.';
  $('access-adjustments').hidden=true;$('access-count').textContent='0';
  $('allocation-summary').innerHTML=`${draft.allocation_mode==='manual'?'Manual':'Automatic'} <small>${draft.allocation_mode==='manual'?'selected vehicle assignments':'capacity-aware planning'}</small>`;
  $('city-vans').innerHTML='';
  $('load-total').textContent=`${draft.demands.reduce((a,b)=>a+b,0)} load units`;
  markers.forEach(m=>m.getElement().classList.remove('van-a','van-b'));
  status('Scenario updated. Select Solve to calculate a plan.');
}
function usePreset(key) {
  draft={city:key,points:presets[key].points.map(p=>[...p]),demands:[3,2,3,1,2,1],fleet_size:2,capacity:7,allocation_mode:'auto',assignments:[0,1,0,1,0,1]};
  $('delivery-count').value=6;$('fleet-size').value=2;$('vehicle-capacity').value=7;$('allocation-mode').value='auto';
  $('city-name').innerHTML=`${presets[key].name} <small>6 stops + depot</small>`;
  $('map-heading').firstChild.textContent=presets[key].name+' ';
  deliveryFields();scenarioSummary();
  markStops();invalidate();map.flyTo({center:presets[key].center,zoom:13,pitch:52,bearing:-15,duration:1100});
}
function scenarioSummary(){
  $('city-name').innerHTML=`${presets[draft.city].name} <small>${draft.demands.length} stops + depot</small>`;
  document.querySelector('.metrics article:nth-child(2) strong').innerHTML=`${draft.fleet_size} × ${draft.capacity} <small id="load-total">${draft.demands.reduce((a,b)=>a+b,0)} load units</small>`;
}
function deliveryFields(){
  const manual=draft.allocation_mode==='manual';
  if(manual)document.querySelector('.delivery-details').open=true;
  $('loads').innerHTML=draft.demands.map((v,i)=>`<label for="load-${i}">Stop ${i+1}<input id="load-${i}" aria-label="Stop ${i+1} load" type="number" min="1" max="60" step="1" value="${v}">${manual?`<select aria-label="Stop ${i+1} vehicle" data-assign="${i}">${Array.from({length:draft.fleet_size},(_,j)=>`<option value="${j}" ${draft.assignments[i]===j?'selected':''}>Van ${String.fromCharCode(65+j)}</option>`).join('')}</select>`:''}</label>`).join('');
  $('loads').querySelectorAll('input').forEach((input,i)=>input.onchange=()=>{draft.demands[i]=Number(input.value);markStops();invalidate();});
  $('loads').querySelectorAll('[data-assign]').forEach(input=>input.onchange=()=>{draft.assignments[Number(input.dataset.assign)]=Number(input.value);invalidate();});
  $('loads').querySelectorAll('input,select').forEach(input=>input.disabled=busy);
  $('placement').innerHTML='<option value="">Pan & explore</option><option value="0">Depot</option>'+draft.demands.map((_,i)=>`<option value="${i+1}">Stop ${i+1}</option>`).join('');
}
function resizeScenario(){
  const n=Number($('delivery-count').value),fleet=Number($('fleet-size').value),capacity=Number($('vehicle-capacity').value);
  if(!Number.isInteger(n)||n<1||n>40||!Number.isInteger(fleet)||fleet<1||fleet>8||!Number.isInteger(capacity)||capacity<1||capacity>120){notice('Use 1–40 deliveries, 1–8 vehicles, and a capacity from 1 to 120.');return false;}
  while(draft.points.length<n+1){const i=draft.points.length;const a=i*2.39996323,r=.009+.002*Math.floor(i/7);draft.points.push([draft.points[0][0]+r*Math.cos(a),draft.points[0][1]+r*.7*Math.sin(a)]);draft.demands.push(1);}
  draft.points=draft.points.slice(0,n+1);draft.demands=draft.demands.slice(0,n);draft.fleet_size=fleet;draft.capacity=capacity;
  draft.assignments=draft.demands.map((_,i)=>(draft.assignments[i]??i%fleet)%fleet);
  $('city-name').innerHTML=`${presets[draft.city].name} <small>${n} stops + depot</small>`;
  document.querySelector('.metrics article:nth-child(2) strong').innerHTML=`${fleet} × ${capacity} <small id="load-total">${draft.demands.reduce((a,b)=>a+b,0)} load units</small>`;
  deliveryFields();markStops();invalidate();return true;
}
function setBusy(value) {
  busy=value;for(const id of ['city-select','placement','solve-city','city-preset','delivery-count','fleet-size','vehicle-capacity','allocation-mode','new-scenario'])$(id).disabled=value;
  $('loads').querySelectorAll('input,select').forEach(i=>i.disabled=value);markers.forEach(m=>m.setDraggable(!value));
  $('city-run').disabled=value||!scene||!scene.quantum_enabled;
}
function candidates() {
  const rows=scene.candidates.map((r,i)=>({...r,index:i})).sort((a,b)=>a.true_route_length-b.true_route_length||a.index-b.index);
  $('city-count').textContent=`${rows.length} result${rows.length===1?'':'s'}`;
  $('city-candidates').innerHTML=rows.map(r=>`<button class="candidate ${r.index===chosen?'selected':''}" data-index="${r.index}" aria-pressed="${r.index===chosen}"><span class="candidate-head"><span class="candidate-name"><span class="${r.family}-mark">${r.family==='quantum'?'✳':'◇'}</span> ${r.label}</span><span class="candidate-km">${fmt(r.true_route_length)} <small>km</small></span></span><span class="candidate-foot"><span>MODEL DISTANCE</span><span>${r.family==='quantum'?fmt(r.prob_optimum*100,1)+'% P(opt)':fmt(r.runtime_s*1000,1)+' ms'}</span></span></button>`).join('');
  $('city-candidates').querySelectorAll('button').forEach(b=>b.onclick=()=>choose(Number(b.dataset.index)));
}
function solutionDetails(row) {
  $('city-selection').textContent=row.label;$('city-feasible').textContent=row.feasible?'CAPACITY FEASIBLE':'OVER CAPACITY';
  $('model-distance').textContent=fmt(row.true_route_length)+' km';$('city-gap').textContent=scene.optimum==null?'Not certified':fmt(Math.max(0,100*(row.true_route_length/scene.optimum-1)))+'%';$('city-objective').textContent=fmt(row.model_objective);
  $('city-insight').textContent=row.family==='quantum'?`QAOA · Feasible probability ${fmt(row.prob_feasible*100,1)}% · Optimum probability ${fmt(row.prob_optimum*100,1)}%.`:scene.allocation_mode==='manual'?'Manual allocation with capacity validation and optimized stop order.':scene.exact?'Exact result for the displayed planning model.':'Classical heuristic. Global optimality is not certified for this scenario size.';
  $('city-vans').innerHTML=Object.keys(row.routes).map((v,i)=>`<article class="van-card"><div class="van-top"><i class="dot" style="background:${COLORS[i]}"></i><strong>Van ${v}</strong><span>${row.loads[i]} / ${scene.instance.capacity} units</span></div><div class="van-route">${row.routes[v].length?'D '+row.routes[v].map(n=>'→ '+n).join(' ')+' → D':'At depot · no deliveries'}</div><div class="load-bar"><i style="width:${row.loads[i]/scene.instance.capacity*100}%;background:${COLORS[i]}"></i></div><div class="allocation-manifest">${row.routes[v].map(n=>`Stop ${n}: ${scene.instance.demands[n-1]} units`).join(' · ')||'Idle vehicle'}</div></article>`).join('');
  markers.forEach((m,i)=>{if(!i)return;const el=m.getElement();el.style.borderColor=COLORS[row.assignment[i-1]];el.style.color=COLORS[row.assignment[i-1]];});
  document.querySelector('.real-map-key').innerHTML=Object.keys(row.routes).map((v,i)=>`<span><i class="dot" style="background:${COLORS[i]}"></i>Van ${v}</span>`).join('');
  markDropoffs();
}
function markDropoffs(){
  dropoffMarkers.forEach(m=>m.remove());dropoffMarkers=[];
  if(!scene)return;
  const features=[];
  for(const drop of scene.dropoffs||[]){
    const el=markers[drop.id]?.getElement();
    if(el){el.classList.add('inaccessible-stop');el.firstChild.textContent='×';el.title=`Stop ${drop.id}: ${drop.reason}`;el.querySelector('.marker-title').textContent=`${drop.id} · pickup ${fmt(drop.offset_m,0)} m away`;}
    const pickup=document.createElement('div');pickup.className='stop-marker pickup-marker';pickup.textContent=String(drop.id);pickup.title=drop.reason;
    const title=document.createElement('span');title.className='marker-title';title.textContent=drop.kind==='depot_collection'?'DEPOT COLLECTION':'DROP-OFF';pickup.append(title);
    dropoffMarkers.push(new maplibregl.Marker({element:pickup}).setLngLat(drop.location).addTo(map));
    features.push({type:'Feature',properties:{},geometry:{type:'LineString',coordinates:[drop.requested,drop.location]}});
  }
  if(loaded)map.getSource('dropoff-links').setData({type:'FeatureCollection',features});
  $('access-count').textContent=String(scene.dropoffs?.length||0);
  const adjustments=$('access-adjustments');adjustments.hidden=!scene.dropoffs?.length;
  if(scene.dropoffs?.length){
    adjustments.innerHTML='<h3>Road-access adjustments</h3>'+scene.dropoffs.map((d,i)=>`<div class="access-item"><div>Stop ${d.id} · ${d.kind==='depot_collection'?'Depot collection':'Road-side drop-off'}<small>${fmt(d.offset_m,0)} m from requested destination · parcel retained</small></div><button data-focus-drop="${i}">Locate ↗</button></div>`).join('');
    adjustments.querySelectorAll('button').forEach(b=>b.onclick=()=>{const drop=scene.dropoffs[Number(b.dataset.focusDrop)];const bounds=new maplibregl.LngLatBounds().extend(drop.requested).extend(drop.location);map.fitBounds(bounds,{padding:90,duration:800,maxZoom:16});});
  }
  if(scene.dropoffs?.length)$('map-instruction').textContent=`${scene.dropoffs.length} road-access adjustment${scene.dropoffs.length===1?'':'s'}. × marks the requested destination; the numbered square is the collection point.`;
  else $('map-instruction').textContent='Drag stops to update delivery locations.';
}
async function choose(index) {
  if(!scene)return;chosen=index;selectedRow=scene.candidates[index];progress=0;roads=null;routePaths=[];vans.forEach(v=>v.visible=false);
  if(loaded)map.getSource('delivery-routes').setData(empty());
  candidates();solutionDetails(selectedRow);$('road-distance').textContent='—';$('road-duration').textContent='—';
  $('road-caption').textContent='Loading street connections for the selected plan…';
  const token=++routeToken;
  try {
    const result=await api('/api/city/route',{id:scene.id,index});if(token!==routeToken)return;
    roads=result;routePaths=result.routes.map(r=>preparePath(r.geometry.coordinates));drawRoads();
    $('road-distance').textContent=fmt(result.distance_km)+' km';$('road-duration').textContent=fmt(result.duration_minutes,1)+' min';
    $('road-caption').textContent=scene.dropoffs?.length?`All ${scene.instance.demands.length} deliveries retained. Dashed links show off-road collection gaps.`:'Selected stop order preserved · illustrative vehicle scale · no live traffic';
  } catch(e) {if(token!==routeToken)return;$('road-caption').textContent='Street connections unavailable. The selected plan remains available below.';notice(e.message);}
}
function drawRoads() {
  if(!loaded||!roads)return;
  map.getSource('delivery-routes').setData({type:'FeatureCollection',features:roads.routes.map((r,i)=>({type:'Feature',properties:{color:COLORS[i],van:r.van},geometry:r.geometry}))});
}
$('solve-city').onclick=async()=>{
  if(busy)return;
  // Commit form values on submit as well as on change, including number fields
  // that are still focused or have been filled by assistive/browser controls.
  $('loads').querySelectorAll('input').forEach((input,i)=>draft.demands[i]=Number(input.value));
  $('loads').querySelectorAll('[data-assign]').forEach(input=>draft.assignments[Number(input.dataset.assign)]=Number(input.value));
  if(Number($('delivery-count').value)!==draft.demands.length||Number($('fleet-size').value)!==draft.fleet_size||Number($('vehicle-capacity').value)!==draft.capacity){if(!resizeScenario())return;}
  draft.allocation_mode=$('allocation-mode').value;
  setBusy(true);$('city-toast').hidden=true;status('Checking road access, then calculating allocations and routes…');
  try {scene=await api('/api/city/scenario',draft);$('city-source').textContent=scene.allocation_mode==='manual'?'MANUAL ALLOCATION':scene.exact?'EXACT PLAN':'HEURISTIC PLAN';$('city-benchmark').innerHTML=scene.optimum==null?'— <small>heuristic / manual plan</small>':fmt(scene.optimum)+' <small>straight-line km</small>';status(scene.feasible_count?`${scene.feasible_count} feasible partitions evaluated. Loads allocated by route.`:'Capacity-feasible allocation generated.');$('city-job').textContent=scene.quantum_reason;candidates();await choose(0);}
  catch(e){notice(e.message);status('Scenario could not be solved. Check the stops and loads.');}
  finally{setBusy(false);}
};
async function pollQuantum() {
  try {
    const job=await api('/api/job');
    if(job.status==='running') {
      if(!quantumPolling){quantumPolling=true;setBusy(true);}
      const latest=job.events.at(-1);$('city-job').textContent=latest?`QAOA p=${latest.reps} · evaluation ${latest.evaluation} · energy ${fmt(latest.energy,1)}`:'Building the city QUBO and checking its ground state…';
      setTimeout(pollQuantum,750);return;
    }
    if(!quantumPolling)return;quantumPolling=false;setBusy(false);
    if(job.status==='failed'){notice(job.error||'Quantum solver failed.');$('city-job').textContent='Experiment failed. Classical results remain available.';return;}
    const result=await api('/api/city');if(!scene||result.scene?.id!==scene.id)return;scene=result.scene;
    const qs=scene.candidates.map((r,i)=>({...r,index:i})).filter(r=>r.family==='quantum');
    const best=qs.reduce((a,b)=>!a||b.prob_optimum>a.prob_optimum?b:a,null);
    $('city-source').textContent='QAOA + CLASSICAL';$('city-job').textContent=`Complete in ${fmt(job.elapsed,1)} s · ${qs.length} feasible quantum result${qs.length===1?'':'s'}.`;candidates();if(best)await choose(best.index);
  }catch(e){quantumPolling=false;setBusy(false);notice(e.message);}
}
$('city-run').onclick=async()=>{try{setBusy(true);$('city-toast').hidden=true;await api('/api/city/run',{id:scene.id,preset:$('city-preset').value});quantumPolling=true;pollQuantum();}catch(e){setBusy(false);notice(e.message);}};
$('city-select').onchange=()=>usePreset($('city-select').value);
$('new-scenario').onclick=()=>{$('city-toast').hidden=true;usePreset($('city-select').value);};
$('workflow').onclick=()=>$('workflow-dialog').showModal();
$('workflow-dialog').querySelector('.close').onclick=()=>$('workflow-dialog').close();
for(const id of ['delivery-count','fleet-size','vehicle-capacity'])$(id).onchange=resizeScenario;
$('allocation-mode').onchange=()=>{draft.allocation_mode=$('allocation-mode').value;if(selectedRow)draft.assignments=[...selectedRow.assignment];deliveryFields();invalidate();};
$('placement').onchange=()=>{const i=$('placement').value;markers.forEach((m,j)=>m.getElement().classList.toggle('active-move',i!==''&&Number(i)===j));$('map-instruction').textContent=i===''?'Drag numbered stops to customize your scenario.':`Click the map to move ${i==='0'?'the depot':'stop '+i}.`;};
$('city-3d').onclick=()=>{map.easeTo({pitch:55,bearing:-15,duration:700});$('city-3d').classList.add('active');$('city-2d').classList.remove('active');};
$('city-2d').onclick=()=>{map.easeTo({pitch:0,bearing:0,duration:700});$('city-2d').classList.add('active');$('city-3d').classList.remove('active');};
$('city-play').onclick=()=>{playing=!playing;$('city-play').textContent=playing?'Ⅱ':'▶';$('city-play').setAttribute('aria-label',playing?'Pause van playback':'Play van playback');};
$('city-speed').onclick=()=>{speed=speed===1?2:speed===2?4:1;$('city-speed').textContent=speed+'×';};
$('city-replay').onclick=()=>{progress=0;};$('city-timeline').oninput=e=>{progress=Number(e.target.value)/1000;};$('fit-map').onclick=fit;

function preparePath(coords) {
  let length=0;const cumulative=[0];for(let i=1;i<coords.length;i++){const a=coords[i-1],b=coords[i];length+=Math.hypot((b[0]-a[0])*Math.cos(a[1]*Math.PI/180),b[1]-a[1]);cumulative.push(length);}
  return {coords,cumulative,length};
}
function pose(path,t) {
  if(!path)return null;
  if(!path.length){const p=path.coords[0];return {lng:p[0],lat:p[1],from:p,to:[p[0]+.00001,p[1]]};}
  const target=t*path.length;
  let lo=1,hi=path.cumulative.length-1;while(lo<hi){const m=(lo+hi)>>1;if(path.cumulative[m]<target)lo=m+1;else hi=m;}
  const a=path.coords[lo-1],b=path.coords[lo],span=path.cumulative[lo]-path.cumulative[lo-1];const f=span?(target-path.cumulative[lo-1])/span:0;
  return {lng:a[0]+(b[0]-a[0])*f,lat:a[1]+(b[1]-a[1])*f,from:a,to:b};
}
function createVan(color) {
  const group=new THREE.Group();
  function block(x,y,z,l,w,h,c){const mesh=new THREE.Mesh(new THREE.BoxGeometry(l,w,h),new THREE.MeshStandardMaterial({color:c,roughness:.55}));mesh.position.set(x,y,z);group.add(mesh);}
  block(-.35,0,1.15,3.6,1.85,1.7,color);block(1.65,0,1.0,1.45,1.8,1.4,color);
  block(1.65,0,1.85,1.2,1.72,.45,'#d3e4e1');block(1.85,0,1.75,.55,1.78,.55,'#264a57');
  block(-.4,0,2.04,3.2,1.65,.12,color);block(2.4,0,.8,.09,1.5,.28,'#d3d8c9');
  for(const x of [-1.25,1.5])for(const y of [-.96,.96]){
    const wheel=new THREE.Mesh(new THREE.CylinderGeometry(.4,.4,.23,12),new THREE.MeshStandardMaterial({color:'#17201d',roughness:.9}));wheel.position.set(x,y,.43);group.add(wheel);
  }
  group.visible=false;return group;
}
// Actual Three.js meshes in transparent map markers keep vehicles readable at
// city zoom levels. Marker size is illustrative, not a physical vehicle footprint.
function createVehicleMarkers(){
  COLORS.forEach((color,i)=>{
    const el=document.createElement('div');el.className='vehicle-marker';el.style.display='none';
    const label=document.createElement('span');label.textContent='VAN '+String.fromCharCode(65+i);label.style.color=color;el.append(label);
    const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(68,54);el.append(renderer.domElement);
    const visualScene=new THREE.Scene();visualScene.add(new THREE.AmbientLight('#ffffff',1.9));const light=new THREE.DirectionalLight('#ffffff',2.4);light.position.set(-3,-5,10);visualScene.add(light);
    const camera=new THREE.OrthographicCamera(-4.5,4.5,4.5*54/68,-4.5*54/68,.1,100);camera.up.set(0,0,1);camera.position.set(0,-9,8);camera.lookAt(0,0,1);
    const mesh=createVan(color);visualScene.add(mesh);vans.push(mesh);
    camera.updateMatrixWorld();
    const ground=new THREE.Vector3(0,0,0).project(camera);
    const groundPixel=[(ground.x+1)*68/2,(1-ground.y)*54/2];
    const marker=new maplibregl.Marker({element:el,anchor:'center',offset:[34-groundPixel[0],27-groundPixel[1]]}).setLngLat(draft?.points[0]||[73.0479,33.698]).addTo(map);
    vehicleMarkers.push({el,renderer,visualScene,camera,mesh,marker});
  });
}
function frame(time){
  if(lastTime&&playing&&roads){progress=(progress+Math.min(time-lastTime,100)*speed/30000)%1;$('city-timeline').value=Math.round(progress*1000);}lastTime=time;
  vehicleMarkers.forEach((v,i)=>{const p=pose(routePaths[i],progress);v.el.style.display=p?'':'none';if(!p)return;const a=map.project(p.from),b=map.project(p.to);v.marker.setLngLat([p.lng,p.lat]);v.mesh.visible=true;v.mesh.rotation.z=Math.atan2(-(b.y-a.y)/(7/Math.sqrt(130)),b.x-a.x);v.renderer.render(v.visualScene,v.camera);});
  requestAnimationFrame(frame);
}

async function init(){setBusy(true);try{const result=await api('/api/city');presets=result.presets;usePreset('islamabad');
  if(result.scene){usePreset(result.scene.city);scene=result.scene;draft={city:scene.city,points:(scene.requested_points||scene.points).map(p=>[...p]),demands:[...scene.instance.demands],fleet_size:scene.fleet_size||2,capacity:scene.instance.capacity,allocation_mode:scene.allocation_mode||'auto',assignments:[...scene.candidates[0].assignment]};$('city-select').value=scene.city;$('delivery-count').value=draft.demands.length;$('fleet-size').value=draft.fleet_size;$('vehicle-capacity').value=draft.capacity;$('allocation-mode').value=draft.allocation_mode;deliveryFields();scenarioSummary();markStops();$('city-source').textContent='SESSION SOLUTIONS';$('city-benchmark').innerHTML=scene.optimum==null?'— <small>heuristic / manual</small>':fmt(scene.optimum)+' <small>straight-line km</small>';candidates();await choose(0);$('city-run').disabled=!scene.quantum_enabled;$('city-job').textContent=scene.quantum_reason;status('Scenario restored.');fit();}
  const job=await api('/api/job');if(job.status==='running'&&job.mode==='city'){quantumPolling=true;setBusy(true);pollQuantum();}
  }finally{if(!quantumPolling)setBusy(false);}
}
init().catch(e=>notice('Unable to load the city lab. '+e.message));$('city-play').textContent=playing?'Ⅱ':'▶';requestAnimationFrame(frame);
