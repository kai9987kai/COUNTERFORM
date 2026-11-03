import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { validPlayback } from './study-data.js';

export function createApparatus(container, onFrame) {
  let renderer;
  try { renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'}); }
  catch { container.innerHTML='<div class="webgl-message">The 3D view needs WebGL. Study controls, charts and evidence remain available.</div>'; return {setData(){},setPlaying(){},setSpeed(){},seek(){},reset(){},dispose(){}}; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
  renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFShadowMap;
  renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.25;
  container.appendChild(renderer.domElement); renderer.domElement.setAttribute('aria-label','Interactive 3D conceptual oscillator with primary mass, springs and tuned absorber. Drag to orbit, scroll to zoom.'); renderer.domElement.setAttribute('role','img');
  const scene=new THREE.Scene(); scene.fog=new THREE.Fog('#232c25',18,43);
  const camera=new THREE.PerspectiveCamera(37,1,.1,100);
  const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.minDistance=8;controls.maxDistance=25; controls.maxPolarAngle=Math.PI*.48; controls.target.set(0,.7,0); controls.enablePan=false;
  function reset(){camera.position.set(9.5,7.4,12);controls.target.set(0,.65,0);controls.update();}
  reset();
  scene.add(new THREE.HemisphereLight('#fff3dd','#3d4c3d',2.4));
  const key=new THREE.DirectionalLight('#fff4da',4.2);key.position.set(-4,9,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);key.shadow.camera.left=-8;key.shadow.camera.right=8;key.shadow.camera.top=6;key.shadow.camera.bottom=-6;key.shadow.normalBias=.035;scene.add(key);
  const rim=new THREE.DirectionalLight('#b5d6cb',2);rim.position.set(4,4,-6);scene.add(rim);
  const steel=new THREE.MeshStandardMaterial({color:'#b9c2b8',metalness:.78,roughness:.3});
  const graphite=new THREE.MeshStandardMaterial({color:'#455048',metalness:.65,roughness:.42});
  const ivory=new THREE.MeshStandardMaterial({color:'#dbddd0',metalness:.48,roughness:.32});
  const orange=new THREE.MeshStandardMaterial({color:'#e6aa52',metalness:.48,roughness:.31});
  const black=new THREE.MeshStandardMaterial({color:'#17201b',metalness:.35,roughness:.5});
  const floor=new THREE.Mesh(new THREE.PlaneGeometry(150,150),new THREE.MeshStandardMaterial({color:'#28332b',roughness:1,metalness:.1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.36;floor.receiveShadow=true;scene.add(floor);
  const grid=new THREE.GridHelper(48,48,'#566655','#3b493d');grid.position.y=-.35;grid.material.transparent=true;grid.material.opacity=.42;scene.add(grid);
  function box(w,h,d,mat,x,y,z,parent=scene){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
  function cylinder(radius,length,mat,x,y,z,parent=scene){const m=new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,length,20),mat);m.rotation.z=Math.PI/2;m.position.set(x,y,z);m.castShadow=true;parent.add(m);return m;}
  // Conceptual assembly: these proportions illustrate function, not manufacture.
  box(10.7,.28,3.6,graphite,-.15,-.12,0);
  box(10.85,.07,3.72,steel,-.15,-.295,0);
  for(const z of [-1.13,1.13]){cylinder(.07,9.8,steel,-.1,.22,z);box(10,.08,.12,black,-.1,.04,z);}
  for(const x of [-4.6,4.3])for(const z of [-1.4,1.4]){const bolt=new THREE.Mesh(new THREE.CylinderGeometry(.07,.07,.04,6),steel);bolt.position.set(x,.04,z);scene.add(bolt);}
  box(.4,2.05,2.8,graphite,-4.7,.9,0);box(.45,.12,2.95,steel,-4.7,1.96,0);
  for(const z of [-1.1,1.1])box(.12,1.55,.09,steel,-4.46,.93,z);
  const primary=new THREE.Group();scene.add(primary);primary.position.x=-.6;
  box(1.65,1.32,2.15,ivory,0,1,0,primary);box(1.65,.055,2.16,steel,0,1.69,0,primary);
  box(.24,1.17,.022,orange,-.55,1,-1.086,primary);box(.24,1.17,.022,orange,-.55,1,1.086,primary);
  for(const x of [-.53,.53])for(const z of [-1.1,1.1]){const r=cylinder(.21,.18,black,x,.3,z,primary);r.rotation.set(Math.PI/2,0,0);}
  for(const z of [-.8,.8]){const bolt=new THREE.Mesh(new THREE.CylinderGeometry(.06,.06,.04,6),graphite);bolt.position.set(.5,1.735,z);primary.add(bolt);}
  const absorber=new THREE.Group();scene.add(absorber);absorber.position.x=2.65;
  box(.85,.95,1.52,orange,0,.85,0,absorber);box(.88,.08,1.56,steel,0,1.36,0,absorber);
  box(.45,.35,.02,graphite,0,.93, .77,absorber);
  for(const x of [-.25,.25])for(const z of [-.76,.76]){const r=cylinder(.15,.12,black,x,.27,z,absorber);r.rotation.set(Math.PI/2,0,0);}
  function spring(radius,coils,mat){const pts=[];pts.push(new THREE.Vector3(0,0,0));for(let i=0;i<=coils*20;i++){const u=i/(coils*20);const taper=Math.min(1,u*12,(1-u)*12);pts.push(new THREE.Vector3(.08+.84*u,Math.cos(u*Math.PI*2*coils)*radius*taper,Math.sin(u*Math.PI*2*coils)*radius*taper));}pts.push(new THREE.Vector3(1,0,0));const mesh=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),coils*24,.032,7,false),mat);mesh.castShadow=true;scene.add(mesh);return mesh;}
  const k1=spring(.24,10,steel), k2=spring(.17,8,orange);
  const damperBody=cylinder(.1,1,graphite,0,.72,.63), damperRod=cylinder(.038,1,steel,0,.72,.63);
  // Ground markers make displacement and the fixed boundary legible.
  for(let i=0;i<9;i++)box(.014,.005,.16,steel,-4+i, .025,1.6);
  let data=null,playing=true,speed=1,time=0,elapsed=0,last=performance.now(),lastNotify=0,scale=1,disposed=false,animationId;
  function setData(d){data=validPlayback(d)?d:null;time=0;scale=1;playing=!!data;if(data){const max=Math.max(...data.primary.map(Math.abs),...data.absorber.map(Math.abs),.001);scale=Math.min(20,1/max);}}
  function sample(arr,index,mix){return (arr[index]??0)*(1-mix)+(arr[Math.min(index+1,arr.length-1)]??0)*mix;}
  function update(now){
    if(disposed)return;
    const dt=Math.min((now-last)/1000,.08);last=now;elapsed+=dt;
    let p=0,a=0,base=0,duration=0;
    if(data?.t?.length>1){duration=data.t.at(-1);if(playing)time=(time+dt*speed)%Math.max(duration,.001);let lo=0,hi=data.t.length-1;while(lo<hi-1){const mid=(lo+hi)>>1;if(data.t[mid]<=time)lo=mid;else hi=mid;}const mix=(time-data.t[lo])/(data.t[hi]-data.t[lo]||1);p=sample(data.primary,lo,mix);a=sample(data.absorber,lo,mix);base=sample(data.baseline,lo,mix);}
    else if(playing){p=Math.sin(elapsed*1.35)*.18;a=Math.sin(elapsed*1.35-.8)*.27;}
    primary.position.x=-.6+p*scale;absorber.position.x=2.65+a*scale;
    const start=-4.46,end=primary.position.x-.825;k1.position.set(start,1.22,-.2);k1.scale.x=Math.max(.25,end-start);
    const start2=primary.position.x+.825,end2=absorber.position.x-.425;k2.position.set(start2,1.1,0);k2.scale.x=Math.max(.25,end2-start2);
    damperBody.position.x=start+.8;damperBody.scale.y=1.5;damperRod.position.x=(start+end)/2;damperRod.scale.y=Math.max(.3,end-start);
    controls.update();renderer.render(scene,camera);
    if(now-lastNotify>80){onFrame?.({time,duration,primary:p,absorber:a,baseline:base,scale,playing});lastNotify=now;}
    animationId=requestAnimationFrame(update);
  }
  const ro=new ResizeObserver(()=>{const {width,height}=container.getBoundingClientRect();if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();});ro.observe(container);animationId=requestAnimationFrame(update);
  return {setData,setPlaying(v){playing=v;},setSpeed(v){speed=v;},seek(fraction){if(data)time=Math.max(0,Math.min(1,fraction))*data.t.at(-1);},reset,dispose(){disposed=true;cancelAnimationFrame(animationId);ro.disconnect();controls.dispose();scene.traverse(object=>{object.geometry?.dispose();if(Array.isArray(object.material))object.material.forEach(material=>material.dispose());else object.material?.dispose();});renderer.dispose();}};
}
