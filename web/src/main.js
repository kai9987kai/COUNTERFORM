import './style.css';
import { icon } from './icons.js';
import { createApparatus } from './scene.js';
import { escapeHTML as esc, number as fmt, compact, lineChart } from './charts.js';
import { finiteValue, recordedProtocol, worldOptions, modelName, auditMetrics, recommendationView, rankCandidates, acquisitionSelection, validPlayback, tabDestination } from './study-data.js';
import { renderEvidenceHTML, comparisonMarkup } from './evidence-view.js';

const names={linear:'Linear oscillator',cubic:'Cubic stiffness',friction:'Smooth friction',unmodelled:'Combined nonlinearities',memory:'Relaxing force memory',passive:'Passive',random:'Random',active:'Disagreement',counterform:'COUNTERFORM'};
const state={job:null,resultJob:null,result:null,runs:[],busy:false,tab:'lab',timer:null,playing:!window.matchMedia('(prefers-reduced-motion: reduce)').matches,hasPlayback:false,experiment:0,pollGeneration:0,comparison:null,compareId:'',compareBusy:false,compareError:'',compareGeneration:0};
document.querySelector('#app').innerHTML=`
<aside class="sidebar">
  <a class="brand" href="#lab" aria-label="COUNTERFORM home">${icon('mark')}<span>COUNTER<span class="brand-form">FORM</span><small>RESEARCH SYSTEMS / 001</small></span></a>
  <div class="sidebar-group-label">WORKSPACE</div>
  <nav aria-label="Main navigation">
    <button class="nav-item active" data-tab="lab">${icon('lab')}<span>Laboratory</span><kbd>01</kbd></button>
    <button class="nav-item" data-tab="evidence">${icon('evidence')}<span>Evidence</span><kbd>02</kbd></button>
    <button class="nav-item" data-tab="protocol">${icon('protocol')}<span>Protocol</span><kbd>03</kbd></button>
  </nav>
  <div class="sidebar-rule"></div>
  <button class="nav-item history-toggle">${icon('history')}<span>Study history</span><span id="history-count" class="count">0</span></button>
  <div class="sidebar-note"><div class="small-cross">+</div><p>Physics is a hypothesis.<br>Give it a counterexample.</p><span>FINITE MODELS. OPEN EVIDENCE.</span></div>
  <div class="engine-status"><i id="connection-dot"></i><div><span id="connection-text">Connecting to local engine</span><small>CPU LOCAL · v0.1.0</small></div></div>
</aside>
<main>
  <header class="topbar"><div class="breadcrumb"><span>Workspace</span><span>/</span><strong id="breadcrumb-current">Laboratory</strong></div><div class="header-actions"><span class="local-badge">${icon('sun')} SYNTHETIC MECHANICS</span><button class="icon-button history-toggle mobile-history" title="Study history" aria-label="Study history">${icon('history')}</button><button class="button quiet" id="export-toggle" disabled>${icon('download')}<span>Export study</span>${icon('chevron')}</button><div class="export-menu" id="export-menu" hidden><div class="menu-label">CURRENT STUDY</div><a data-export="report">${icon('external')} Evidence report <span>HTML</span></a><a data-export="receipt">${icon('evidence')} Canonical receipt <span>JSON</span></a><a data-export="bundle">${icon('layers')} Complete evidence <span>ZIP</span></a><a data-export="design.stl">${icon('download')} Conceptual assembly <span>STL</span></a><a data-export="design.json">${icon('download')} Parametric design <span>JSON</span></a></div></div></header>
  <div class="page-content">
  <div class="global-error" id="global-error" role="alert" hidden><span></span><button id="dismiss-error" aria-label="Dismiss error">${icon('close')}</button></div>
  <section id="tab-lab" class="tab-page">
    <div class="page-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span> THE FALSIFICATION LAB</div><h1>Question the model.<br><em>Challenge the design.</em></h1><p>Discover what the evidence supports. Build for what remains uncertain.</p></div><div class="study-id"><span id="study-mode">READY FOR A QUESTION</span><strong id="study-number">NEW STUDY <span>↗</span></strong><small>FORCED OSCILLATOR / 1D</small></div></div>
    <div class="lab-grid">
      <div class="instrument panel">
        <div class="panel-heading"><div><span class="section-index">01</span><h2>Mechanical test bed</h2></div><span class="live-tag" id="scene-badge"><i></i>ILLUSTRATIVE PREVIEW</span></div>
        <div class="scene-wrap"><div id="scene"></div><div class="scene-topline"><span>TUNED MASS ABSORBER</span><span>CONCEPTUAL ASSEMBLY</span></div><div class="object-label label-primary"><i></i>PRIMARY MASS <b>m₁</b></div><div class="object-label label-absorber"><i></i>ABSORBER <b>m₂</b></div><div class="scene-coordinates">Y<br><span>└── X</span><small>z</small></div><div class="orbit-hint">DRAG TO ORBIT · SCROLL TO ZOOM</div><button class="icon-button camera-reset" id="camera-reset" title="Reset camera" aria-label="Reset 3D camera">${icon('reset')}</button></div>
        <div class="playback-bar"><button class="play-button" id="play-toggle" aria-label="Pause illustrative motion">${icon('pause')}</button><div class="playback-track"><label id="playback-label" for="playback-seek">Preview motion <span id="playback-time">—</span></label><input type="range" min="0" max="1000" value="0" id="playback-seek" aria-label="Playback position" disabled></div><select id="playback-speed" aria-label="Playback speed"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option></select><span class="playback-divider"></span><div class="motion-value"><small>x₁ DISPLACEMENT</small><strong id="displacement">Preview</strong></div></div>
        <div class="scene-footnote"><span id="motion-note">Illustrative motion only. Run a study for simulated traces.</span><span>m · kg · N · s</span></div>
      </div>
      <form id="study-form" class="setup panel">
        <div class="panel-heading"><div><span class="section-index">02</span><h2>Define the study</h2></div>${icon('lab')}</div>
        <div class="setup-body"><div class="study-context"><label class="field-label" for="protocol">RESEARCH PROTOCOL</label><div class="select-wrap"><select id="protocol" name="protocol" aria-describedby="protocol-help"><option value="0.2.0" selected>v0.2 · Decision-risk study</option><option value="0.1.0">v0.1 · Legacy study</option></select>${icon('chevron')}</div><p class="field-help" id="protocol-help">Eight laws, parameter particles and independent force/forecast audits.</p><label class="field-label" for="world">HIDDEN PHYSICAL WORLD <span title="The learner sees measured trajectories, not hidden physical coefficients.">ⓘ</span></label><div class="select-wrap"><select id="world" name="world" aria-describedby="world-help"></select>${icon('chevron')}</div><p class="field-help" id="world-help"></p></div>
        <fieldset><legend class="field-label">EXPERIMENT STRATEGY</legend><div class="strategy-options"><label><input type="radio" name="strategy" value="passive"><span><b>Passive</b><small>Low excitation</small></span></label><label><input type="radio" name="strategy" value="random"><span><b>Random</b><small>Uniform exploration</small></span></label><label><input type="radio" name="strategy" value="active"><span><b>Disagreement</b><small>Predictive spread</small></span></label><label><input type="radio" name="strategy" value="counterform" checked><span><b>COUNTERFORM <i>↗</i></b><small>Decision-sensitive</small></span></label></div></fieldset>
        <div class="budget-control"><div class="budget-label"><label class="field-label" for="budget">EXPERIMENT BUDGET</label><output id="budget-value" for="budget">5 <span>experiments</span></output></div><input id="budget" name="budget" type="range" min="2" max="8" step="1" value="5"><div class="range-labels"><span>2 / focused</span><span>8 / exploratory</span></div></div>
        <div class="config-bottom"><div><label class="field-label" for="seed">RANDOM SEED</label><input id="seed" name="seed" type="number" min="0" max="2147483647" step="1" value="42" required></div><div><label class="field-label" for="noise">NOISE LEVEL</label><div class="noise-input"><input id="noise" name="noise" type="number" min="0" max="0.05" step="0.001" value="0.01" required><span>σ</span></div></div></div>
        <div class="run-control"><button type="submit" class="run-button" id="run-button"><span>${icon('play')} Run study</span><span>↗</span></button><p class="run-help" id="run-help">Local computation. Reproducible by seed.</p><div id="run-progress" hidden aria-live="polite"><div class="progress-copy"><span id="progress-message">Queued</span><strong id="progress-value">0%</strong></div><progress id="progress" max="1" value="0" aria-label="Study progress"></progress><button type="button" class="cancel-button" id="cancel-run">Cancel study</button><p id="cancel-note" class="field-help" hidden>Cancellation waits for the current numerical checkpoint.</p></div></div>
        </div>
      </form>
    </div>
    <div id="result-verdict" hidden></div>
    <div class="metric-grid" id="metrics"><div class="metric"><span>AGGREGATE RMS REDUCTION</span><strong>—<small>%</small></strong><p>Pooled challenge RMS vs. no absorber</p></div><div class="metric"><span>WORST CHALLENGE</span><strong>—<small>%</small></strong><p>The design’s most difficult test</p></div><div class="metric"><span>MODEL ADEQUACY</span><strong class="text-metric">Awaiting evidence</strong><p>Independent audit, separate from fitting</p></div><div class="metric"><span>SOLVER DISAGREEMENT</span><strong>—<small>%</small></strong><p>First held-out selected-design trajectory</p></div></div>
    <div class="analysis-grid"><section class="panel models-panel"><div class="panel-heading"><div><span class="section-index">03</span><h2>Competing explanations</h2></div><span class="panel-meta">FINITE LAW LIBRARY</span></div><div class="model-list" id="models"><div class="model-placeholder"><div><b>01</b><span>Linear oscillator<small>k x + c v</small></span><span class="model-status">UNTESTED</span></div><div><b>02</b><span>Cubic stiffness<small>k x + c v + α x³</small></span><span class="model-status">UNTESTED</span></div><div><b>03</b><span>Smooth friction<small>k x + c v + f tanh(v / ε)</small></span><span class="model-status">UNTESTED</span></div></div></div><div class="panel-footnote">Weights compare candidates. Adequacy asks whether any candidate is good enough.</div></section>
    <section class="panel response-panel"><div class="panel-heading"><div><span class="section-index">04</span><h2>Predicted frequency response</h2></div><span class="panel-meta">DESIGN APPROXIMATION</span></div><div id="response-chart" class="chart-body"><div class="empty-response"><div class="empty-waves"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><h3>Let the experiment speak.</h3><p>Run your first study to compare response curves<br>and see what the current models can explain.</p></div></div></section></div>
    <section class="panel experiment-panel"><div class="panel-heading"><div><span class="section-index">05</span><h2>Experiment trail</h2></div><span class="panel-meta" id="experiment-count">NO EXPERIMENTS YET</span></div><div id="experiment-content"><div class="trail-empty"><span>Observe</span><i>→</i><span>Compare</span><i>→</i><span>Choose a test</span><i>→</i><span>Challenge the design</span><p>Every acquisition, model update and design decision leaves a trace.</p></div></div></section>
    <div class="page-footer"><span>COUNTERFORM / A FINITE-MODEL RESEARCH PROTOTYPE</span><button data-tab="protocol">Know the limits ${icon('arrow')}</button></div>
  </section>
  <section id="tab-evidence" class="tab-page" hidden><div class="page-heading compact-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span> INSPECTABLE BY DESIGN</div><h1>Show your <em>working.</em></h1><p>Independent challenges, numerical checks and the record behind every result.</p></div><button class="button quiet history-toggle">${icon('history')} Open study history</button></div><div id="evidence-content"><div class="panel evidence-empty">${icon('evidence')}<h2>Evidence begins with an experiment.</h2><p>Complete a study in the laboratory to inspect its held-out challenges,<br>audit errors, design parameters and reproducible record.</p><button class="button primary" data-tab="lab">Go to the laboratory ${icon('arrow')}</button></div></div></section>
  <section id="tab-protocol" class="tab-page" hidden><div class="page-heading compact-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span> SCOPE & SCIENTIFIC CONTRACT</div><h1>A method with <em>boundaries.</em></h1><p>A small, inspectable loop from competing explanations to challenged design.</p></div><span class="version-chip">PROTOCOL v0.1.0</span></div><div class="protocol-flow"><span><b>01</b> Observe</span>${icon('arrow')}<span><b>02</b> Falsify</span>${icon('arrow')}<span><b>03</b> Design</span>${icon('arrow')}<span><b>04</b> Challenge</span></div><div class="protocol-grid"><article class="panel prose-panel"><div class="eyebrow">THE EXPERIMENT</div><h2>Three laws. One hidden world.</h2><p>A forced, one-dimensional oscillator has a known primary mass. Instrumented synthetic measurements include position, velocity, acceleration and applied force.</p><p>The learner fits nonnegative physical coefficients in a finite library: linear damping and stiffness, cubic stiffness, and smooth Coulomb friction. Hidden truth coefficients are excluded from model fitting, acquisition and selected-design search.</p><p>Combined nonlinearities create an intentionally out-of-library case. A concentrated model weight can still accompany a rejected audit.</p></article><article class="panel prose-panel"><div class="eyebrow">THE ACQUISITION</div><h2>Ask a consequential question.</h2><p>Passive, random, predictive disagreement and COUNTERFORM strategies share observation and design budgets.</p><p>COUNTERFORM uses a <strong>decision-sensitive disagreement heuristic</strong>: it favours experiments whose model differences matter to the absorber decision. It is not exact Bayesian information gain.</p><p>Independent audit experiments assess adequacy. They are held separate from experiment acquisition. The audit threshold can reject every model.</p></article><article class="panel prose-panel"><div class="eyebrow">THE DESIGN</div><h2>Robust to the remaining doubt.</h2><p>A finite grid searches absorber mass, stiffness and damping using a frequency-response approximation across plausible models.</p><p>Separate nonlinear simulations challenge the selected design with changed load, forcing frequency and component tolerance. Controls include no absorber, nominal fit and a finite-grid oracle diagnostic.</p><p>Percentage reductions are conditional on the simulated challenge set. Negative values mean the selected absorber increased vibration.</p></article><article class="panel prose-panel limits-panel"><div class="eyebrow">THE LIMITS</div><h2>Evidence is bounded.</h2><p>This prototype does not establish free-form symbolic discovery, neural world modelling, topology invention, cross-domain transfer or physical safety.</p><p>STL and parametric JSON exports describe a <strong>conceptual assembly</strong>. Dimensions are illustrative; they do not qualify spring manufacture, fatigue life or hardware performance.</p><p>Replayable receipts and SHA-256 manifests support evidence inspection. Numerical checks do not replace physical validation.</p></article></div><div class="protocol-end">${icon('info')} All computation runs locally on your CPU. No cloud model, credentials or GPU required.</div></section>
  </div>
</main>
<nav class="mobile-navigation" aria-label="Mobile navigation"><button class="mobile-tab active" data-tab="lab">${icon('lab')}<span>Laboratory</span></button><button class="mobile-tab" data-tab="evidence">${icon('evidence')}<span>Evidence</span></button><button class="mobile-tab" data-tab="protocol">${icon('protocol')}<span>Protocol</span></button></nav>
<div class="drawer-backdrop" id="drawer-backdrop" hidden></div><aside class="history-drawer" id="history-drawer" aria-label="Study history" role="dialog" aria-modal="true" hidden><div class="drawer-heading"><div><div class="eyebrow">YOUR LOCAL RECORD</div><h2>Study history</h2></div><button class="icon-button" id="history-close" aria-label="Close history">${icon('close')}</button></div><div class="drawer-subhead"><span>Saved on this machine</span><button class="text-button" id="history-refresh">${icon('reset')} Refresh</button></div><div id="history-list"></div><div class="drawer-footnote">Select a study to inspect its result and export its evidence.</div></aside><div id="toast" role="status" aria-live="polite" hidden></div>`;

const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const percent=value=>finiteValue(value)===null?null:Number(value)*100;
const displayName=value=>names[value]||modelName(value);
const scope=r=>r.validation?.solver_scope||'First held-out selected-design trajectory';
const currentProtocol=()=>$('#protocol').value;

function updateWorldHelp(){
  $('#world-help').textContent=worldOptions(currentProtocol()).find(world=>world.value===$('#world').value)?.help||'';
}
function configureProtocol(protocol,world=$('#world').value||'cubic'){
  $('#protocol').value=protocol;
  const options=worldOptions(protocol);
  $('#world').innerHTML=options.map(item=>`<option value="${esc(item.value)}">${esc(item.name)}</option>`).join('');
  $('#world').value=options.some(item=>item.value===world)?world:'cubic';
  $('#protocol-help').textContent=protocol==='0.2.0'?'Eight laws, parameter particles and independent force/forecast audits.':'Frozen three-law library and the original force audit.';
  $('.strategy-options input[value="counterform"]+span small').textContent=protocol==='0.2.0'?'Expected decision risk':'Decision-sensitive';
  updateWorldHelp();
  renderProtocol(protocol);
  if(!state.result)renderModelPlaceholder(protocol);
}
function renderModelPlaceholder(protocol){
  const candidates=protocol==='0.2.0'?['linear','cubic','friction','drag','cubic_friction','cubic_drag','friction_drag','cubic_friction_drag']:['linear','cubic','friction'];
  $('#models').classList.toggle('expanded-library',protocol==='0.2.0');
  $('#models').innerHTML=candidates.map((name,index)=>`<div class="model-card model-untested"><div class="model-title"><span class="model-number">${String(index+1).padStart(2,'0')}</span><h3>${esc(modelName(name))}</h3><span class="model-status">UNTESTED</span></div></div>`).join('');
}
function renderProtocol(protocol){
  const modern=protocol==='0.2.0';
  $('#tab-protocol .version-chip').textContent=`PROTOCOL v${protocol}`;
  const articles=$$('#tab-protocol .protocol-grid article');
  articles[0].innerHTML=`<div class="eyebrow">THE EXPERIMENT</div><h2>${modern?'Eight laws. Measured uncertainty.':'Three laws. One hidden world.'}</h2><p>A forced, one-dimensional oscillator has a known primary mass. Synthetic sensors provide position, velocity, acceleration and applied force. Hidden coefficients are excluded from fitting, acquisition and selected-design search.</p><p>${modern?'The finite library enumerates cubic stiffness, smooth friction and quadratic drag compositions. Measured-data refits create deterministic parameter particles; their weights are heuristic, not calibrated posterior probabilities. Combined nonlinearities are covered. A relaxing-force memory world remains outside the instantaneous library.':'The frozen library contains linear, cubic and smooth-friction laws. Combined nonlinearities are intentionally outside this three-law library. Original v0.1 results retain their recorded numerical protocol.'}</p>`;
  articles[1].innerHTML=`<div class="eyebrow">THE ACQUISITION</div><h2>Ask a consequential question.</h2><p>Passive, random, predictive disagreement and COUNTERFORM use equal acquisition counts. Operational overhead is recorded separately.</p><p>${modern?'COUNTERFORM estimates finite expected decision-risk reduction: fantasy observations reweight parameter particles, then the actual downstream design rule is applied on one fixed grid. Every candidate score and deterministic tie rule is retained, including negative scores.':'COUNTERFORM uses a decision-sensitive disagreement heuristic. It is not exact Bayesian information gain. Independent audit experiments remain separate from acquisition.'}</p><p>${modern?'One identical candidate must pass both independent force-residual and free-running forecast checks. Thresholds are engineering diagnostics, not calibrated error guarantees.':'An independent force-residual audit can reject all candidates, even when one has a concentrated model weight.'}</p>`;
  articles[2].innerHTML=`<div class="eyebrow">THE DESIGN</div><h2>Robust to the remaining doubt.</h2><p>${modern?'A shared physical grid contains 30 absorber designs. The downstream loss combines weighted tail risk with mean approximate vibration loss over a declared forcing envelope.':'A finite grid searches absorber mass, stiffness and damping using a frequency-response approximation across plausible models.'}</p><p>${modern?'A pre-challenge recommendation records candidate or abstain. An abstained design remains exploratory; held-out outcomes do not revise the frozen recommendation.':'Rejected model sets retain exploratory designs without promoting them as supported results.'}</p><p>Separate nonlinear challenges retain selected, nominal and no-absorber controls. Negative reduction means the selected absorber increased vibration. Oracles are retrospective finite-grid diagnostics.</p>`;
}

function showError(message){$('#global-error span').textContent=message;$('#global-error').hidden=false;}
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;setTimeout(()=>$('#toast').hidden=true,5000);}
async function api(path,options){const r=await fetch(`/api${path}`,options);if(!r.ok){let detail;try{const body=await r.json();detail=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail??body);}catch{detail=r.statusText;}throw new Error(`${r.status}: ${detail}`);}return r.json();}
function setTab(tab){state.tab=tab;$$('.tab-page').forEach(p=>p.hidden=p.id!==`tab-${tab}`);$$('.nav-item[data-tab], .mobile-tab[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===tab);if(b.dataset.tab===tab)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});$('#breadcrumb-current').textContent={lab:'Laboratory',evidence:'Evidence',protocol:'Protocol'}[tab];history.replaceState(null,'',`#${tab}`);$('#export-menu').hidden=true;}
$$('[data-tab]').forEach(b=>b.addEventListener('click',()=>setTab(b.dataset.tab)));
$('.brand').addEventListener('click',e=>{e.preventDefault();setTab('lab');});
$('#dismiss-error').addEventListener('click',()=>$('#global-error').hidden=true);
$('#world').addEventListener('change',updateWorldHelp);
$('#protocol').addEventListener('change',()=>configureProtocol(currentProtocol()));
$('#budget').addEventListener('input',()=>$('#budget-value').innerHTML=`${$('#budget').value} <span>experiments</span>`);
$('#export-toggle').addEventListener('click',()=>$('#export-menu').hidden=!$('#export-menu').hidden);
document.addEventListener('click',e=>{if(!e.target.closest('.header-actions'))$('#export-menu').hidden=true;});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeHistory();$('#export-menu').hidden=true;}});

const apparatus=createApparatus($('#scene'),frame=>{
  if(!state.result||!state.hasPlayback)return;
  $('#playback-time').textContent=`${fmt(frame.time,1)} / ${fmt(frame.duration,1)} s`;
  if(document.activeElement!==$('#playback-seek'))$('#playback-seek').value=frame.duration?frame.time/frame.duration*1000:0;
  $('#displacement').textContent=`${fmt(frame.primary*1000,2)} mm`;
  $('#motion-note').textContent=`Simulated challenge trace · motion scaled ${fmt(frame.scale,1)}× for visibility`;
});
$('#camera-reset').addEventListener('click',()=>{apparatus.reset();toast('Camera returned to the overview.');});
function updatePlay(){const b=$('#play-toggle');b.innerHTML=icon(state.playing?'pause':'play');b.setAttribute('aria-label',`${state.playing?'Pause':'Play'} ${state.result?'simulation':'illustrative motion'}`);b.disabled=!!state.result&&!state.hasPlayback;apparatus.setPlaying(state.playing&&(!state.result||state.hasPlayback));}
$('#play-toggle').addEventListener('click',()=>{state.playing=!state.playing;updatePlay();});
$('#playback-speed').addEventListener('change',e=>apparatus.setSpeed(Number(e.target.value)));
$('#playback-seek').addEventListener('input',e=>apparatus.seek(Number(e.target.value)/1000));
updatePlay();

function setBusy(busy){state.busy=busy;$$('#study-form input, #study-form select, #run-button').forEach(i=>i.disabled=busy);$('#run-button').innerHTML=busy?`<span><i class="spinner"></i> Study in progress</span><span>↗</span>`:`<span>${icon('play')} Run study</span><span>↗</span>`;$('#run-progress').hidden=!busy;$('#run-help').hidden=busy;$('#cancel-run').disabled=!busy||!state.job||!!state.job.cancel_requested;}
function progress(job){const cancelling=job.cancel_requested===true;$('#progress').value=job.progress??0;$('#progress-value').textContent=`${Math.round((job.progress??0)*100)}%`;$('#progress-message').textContent=cancelling?'Cancellation requested · waiting for checkpoint':job.message||'Queued for local computation';$('#study-mode').textContent=cancelling?'CANCELLATION REQUESTED':job.status==='queued'?'QUEUED':'COMPUTING EVIDENCE';$('#cancel-run').disabled=cancelling;$('#cancel-run').textContent=cancelling?'Cancellation requested':'Cancel study';$('#cancel-note').hidden=!cancelling;}
$('#study-form').addEventListener('submit',async e=>{e.preventDefault();if(state.busy)return;const fd=new FormData(e.target);const config={protocol:fd.get('protocol'),world:fd.get('world'),strategy:fd.get('strategy'),budget:Number(fd.get('budget')),seed:Number(fd.get('seed')),noise:Number(fd.get('noise'))};$('#global-error').hidden=true;state.job=null;setBusy(true);$('#cancel-run').disabled=true;$('#cancel-note').hidden=true;$('#progress').value=0;$('#progress-value').textContent='0%';$('#progress-message').textContent='Starting local study…';try{const job=await api('/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)});state.job=job;progress(job);poll(job.id);loadHistory();}catch(error){setBusy(false);showError(`The study could not start. ${error.message}`);}});
$('#cancel-run').addEventListener('click',async()=>{if(!state.busy||!state.job||state.job.cancel_requested)return;const id=state.job.id;$('#cancel-run').disabled=true;try{const job=await api(`/runs/${encodeURIComponent(id)}/cancel`,{method:'POST'});if(state.job?.id!==id)return;state.job=job;if(job.status==='cancelled')finishCancelled();else progress(job);loadHistory();}catch(error){if(state.job?.id===id){$('#cancel-run').disabled=false;showError(`Cancellation could not be requested. ${error.message}`);}}});
function finishCancelled(){setBusy(false);$('#study-mode').textContent=state.result?'PREVIOUS RESULT · LATEST CANCELLED':'STUDY CANCELLED';if(!state.result&&state.job)$('#study-number').textContent=String(state.job.id).slice(0,12).toUpperCase();toast(`Study cancelled. No partial evidence was saved.${state.result?' The previous completed study remains displayed.':''}`);loadHistory();}

async function poll(id,generation=++state.pollGeneration){clearTimeout(state.timer);try{const job=await api(`/runs/${encodeURIComponent(id)}`);if(generation!==state.pollGeneration)return;state.job=job;if(job.status==='complete'){setBusy(false);loadResult(job);loadHistory();toast('Study complete. The evidence is ready to inspect.');return;}if(job.status==='cancelled'){finishCancelled();return;}if(job.status==='failed'){setBusy(false);$('#study-mode').textContent='STUDY FAILED';showError(`Study failed: ${typeof job.error==='string'?job.error:JSON.stringify(job.error||job.message)}. Adjust the study controls or start a new run.`);loadHistory();return;}progress(job);state.timer=setTimeout(()=>poll(id,generation),900);}catch(error){if(generation!==state.pollGeneration)return;setBusy(false);showError(`Connection to the study was interrupted. ${error.message}. Open Study history and select this run to reconnect.`);loadHistory();}}

function loadResult(job){
  const r=job.result;
  if(!r){showError('This completed study has no result payload.');return;}
  state.job=job;state.resultJob=job;state.result=r;state.comparison=null;state.compareError='';state.compareGeneration++;state.compareBusy=false;
  const c=r.config;
  configureProtocol(recordedProtocol(job),c.world);
  $('#seed').value=c.seed;$('#noise').value=c.noise;$('#budget').value=c.budget;$('#budget-value').innerHTML=`${c.budget} <span>experiments</span>`;
  const radio=$(`input[name="strategy"][value="${c.strategy}"]`);if(radio)radio.checked=true;
  $('#study-mode').textContent=`COMPLETED · v${recordedProtocol(job)}`;
  $('#study-number').textContent=String(job.id).slice(0,12).toUpperCase();
  $('#export-toggle').disabled=false;
  $$('[data-export]').forEach(a=>{a.href=`/api/runs/${encodeURIComponent(job.id)}/${a.dataset.export}`;a.setAttribute('download','');});
  state.hasPlayback=validPlayback(r.playback);
  apparatus.setData(state.hasPlayback?r.playback:null);
  $('#scene-badge').innerHTML=state.hasPlayback?'<i></i>SIMULATED RESULT':'<i></i>TRACE UNAVAILABLE';
  $('#scene-badge').classList.toggle('computed',state.hasPlayback);
  $('#playback-label').firstChild.textContent=state.hasPlayback?'Challenge playback ':'No playback trace ';
  $('#playback-seek').disabled=!state.hasPlayback;$('#playback-speed').disabled=!state.hasPlayback;
  $('#playback-seek').value=0;$('#playback-time').textContent='—';$('#displacement').textContent='—';
  $('#motion-note').textContent=state.hasPlayback?'Simulated challenge trace.':'This study has no valid playback trace. Charts and evidence remain available.';
  updatePlay();renderMetrics(r);renderModels(r);renderResponse(r);state.experiment=0;renderExperiments(r);renderEvidence(r);
}

function renderMetrics(r){const s=r.summary,rec=recommendationView(r),joint=r.models.some(m=>finiteValue(m.forecast_nrmse)!==null);$('#metrics').innerHTML=`<div class="metric"><span>SELECTED-DESIGN RMS REDUCTION</span><strong class="${s.reduction_pct<0?'negative-text':''}">${fmt(s.reduction_pct,1)}<small>%</small></strong><p>${rec.status==='abstain'?'Exploratory design · recommendation abstained':'Pooled challenge RMS vs. no absorber'}</p></div><div class="metric"><span>WORST CHALLENGE</span><strong class="${s.worst_reduction_pct<0?'negative-text':''}">${fmt(s.worst_reduction_pct,1)}<small>%</small></strong><p>${fmt(s.constraint_violations,0)} constraint violation${s.constraint_violations===1?'':'s'} in the challenge set</p></div><div class="metric"><span>MODEL ADEQUACY</span><strong class="text-metric ${s.adequate?'positive-text':'negative-text'}">${s.adequate?'Supported':'Rejected'}</strong><p>${joint?(s.adequate?'One candidate passes both independent audits':'No single candidate passes both audits'):(s.adequate?'At least one candidate passes the force audit':'No candidate passes the force audit')}</p></div><div class="metric"><span>SOLVER DISAGREEMENT</span><strong>${fmt(percent(r.validation.solver_relative_error),3)}<small>%</small></strong><p>${esc(scope(r))}</p></div>`;
  const verdict=$('#result-verdict');verdict.hidden=false;verdict.className=`verdict-banner ${rec.status==='abstain'||(rec.status==='legacy'&&!s.adequate)?'rejected':'adequate'}`;verdict.innerHTML=`${icon(rec.status==='candidate'?'check':'info')}<div><strong>${esc(rec.title)}</strong><span>${esc(rec.message)}</span>${rec.selectedControl?`<small>Recorded recommendation: ${rec.selectedControl==='no_absorber'?'no absorber':'absorber candidate'} · frozen before held-out challenges</small>`:''}</div><button data-go-evidence>Inspect evidence ${icon('arrow')}</button>`;verdict.querySelector('button').addEventListener('click',()=>{setTab('evidence');window.scrollTo({top:0,behavior:'smooth'});});
}
function renderModels(r){
  $('#models').classList.toggle('expanded-library',r.models.length>3);
  $('#models').innerHTML=r.models.map((m,i)=>{const audit=auditMetrics(m,r.validation);return `<div class="model-card ${m.adequate?'model-adequate':'model-rejected'}"><div class="model-title"><span class="model-number">${String(i+1).padStart(2,'0')}</span><h3>${esc(modelName(m.name))}</h3><span class="audit-pill ${m.adequate?'passed':'failed'}">${m.adequate?'PASS':'REJECTED'}</span><strong>${fmt(percent(m.weight),1)}<small>%</small></strong></div><div class="model-equation">${esc(m.equation)}</div><div class="model-weight"><i style="width:${Math.max(0,Math.min(100,percent(m.weight)??0))}%"></i></div><div class="model-audits"><span>Force NRMSE <b>${compact(audit.force)}</b><small> / ${compact(audit.forceThreshold)}</small></span>${audit.forecast!==null?`<span>Forecast NRMSE <b>${compact(audit.forecast)}</b><small> / ${compact(audit.forecastThreshold)}</small></span>`:'<span class="legacy-audit-note">Forecast not recorded</span>'}</div><details class="model-parameters"><summary>Fitted coefficients${m.parameter_intervals?' & intervals':''}</summary><dl>${Object.entries(m.parameters||{}).map(([key,value])=>`<div><dt>${esc(key)}</dt><dd>${compact(value)}${m.parameter_intervals?.[key]?` <span>[${m.parameter_intervals[key].map(compact).join(', ')}]</span>`:''}</dd></div>`).join('')}</dl></details></div>`;}).join('');
}
function renderResponse(r){const exploratory=recommendationView(r).status==='abstain';$('#response-chart').innerHTML=lineChart({x:r.response.frequencies,series:[{name:'No absorber',values:r.response.baseline,color:'#8f9b93',dash:true},{name:exploratory?'Exploratory selected design':'Selected design',values:r.response.selected,color:'#e6b66a'},{name:'Nominal fit',values:r.response.nominal,color:'#8cbbaa'}],xLabel:'Frequency / rad s⁻¹',yLabel:'Peak displacement / m',title:'Approximate peak displacement response of no absorber, selected design and nominal-fit absorber'})+`<p class="response-caption">Highest-weight ${esc(modelName(r.summary.best_model))} model${finiteValue(r.response.amplitude)!==null?` · ${fmt(r.response.amplitude,1)} N excitation`:''}. Approximate response; held-out simulation determines reported reductions.${exploratory?' The recorded recommendation abstains.':''}</p>`;}
function renderExperiments(r){
  $('#experiment-count').textContent=`${r.experiments.length} EXPERIMENTS / ${displayName(r.config.strategy)}`;
  $('#experiment-content').innerHTML=`<div class="experiment-tabs" role="tablist" aria-label="Acquisition experiments">${r.experiments.map((e,i)=>`<button class="experiment-chip" id="experiment-tab-${i}" role="tab" aria-selected="false" tabindex="-1" aria-controls="experiment-detail" data-experiment="${i}"><small>EXPERIMENT ${String(e.index).padStart(2,'0')}</small><strong>${fmt(e.frequency,2)} <span>rad s⁻¹</span></strong><span>${fmt(e.amplitude,2)} N ${icon('arrow')}</span></button>`).join('')}</div><div id="experiment-detail" role="tabpanel" tabindex="0"></div>`;
  $$('[data-experiment]').forEach(button=>{button.addEventListener('click',()=>selectExperiment(r,Number(button.dataset.experiment)));button.addEventListener('keydown',event=>{const next=tabDestination(event.key,Number(button.dataset.experiment),r.experiments.length);if(next===null)return;event.preventDefault();selectExperiment(r,next,true);});});
  selectExperiment(r,state.experiment);
}
function selectExperiment(r,index,focus=false){
  const e=r.experiments[index];if(!e)return;
  state.experiment=index;
  $$('[data-experiment]').forEach(button=>{const selected=Number(button.dataset.experiment)===index;button.classList.toggle('active',selected);button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;});
  const panel=$('#experiment-detail');panel.setAttribute('aria-labelledby',`experiment-tab-${index}`);
  const scored=acquisitionSelection(e).kind==='menu';
  panel.innerHTML=`<div class="experiment-rationale"><span class="eyebrow">WHY THIS EXPERIMENT?</span><p>${esc(e.reason)}</p><span>${scored?esc(e.selector?.score_label||'Acquisition score'):'Selection record'} <b>${scored?compact(e.score):Array.isArray(e.candidates)?'Predefined / warm-up':'Legacy score '+compact(e.score)}</b></span></div><div class="experiment-plot">${lineChart({x:e.trace?.t,series:[{name:'Observed displacement',values:e.trace?.x,color:'#e6b66a'}],xLabel:'Time / s',yLabel:'Displacement / m',title:`Observed displacement during experiment ${e.index}`,height:165})}</div>${renderCandidates(e)}`;
  if(focus)$(`#experiment-tab-${index}`).focus();
}
function renderCandidates(experiment){
  if(!Array.isArray(experiment.candidates))return '<div class="candidate-section candidate-empty">Candidate rankings were not recorded by the legacy protocol.</div>';
  if(!experiment.candidates.length)return `<div class="candidate-section candidate-empty"><strong>Predefined acquisition</strong><p>This experiment was specified without a scored candidate search. ${esc(experiment.selector?.name||'Warm-up or control selection')}.</p></div>`;
  const selection=acquisitionSelection(experiment),candidates=rankCandidates(experiment.candidates),label=selection.kind==='predefined'?'Diagnostic menu values':experiment.selector?.score_label||'Acquisition score';
  const shown=candidates.slice(0,6),selected=candidates.find(candidate=>candidate.selected===true);
  if(selected&&!shown.includes(selected))shown.push(selected);
  const extent=Math.max(...shown.map(candidate=>Math.abs(finiteValue(candidate.score)??0)),Number.MIN_VALUE);
  return `<section class="candidate-section" aria-label="Acquisition candidate ranking"><div class="candidate-heading"><div><span class="eyebrow">CANDIDATE RANKING</span><h3>${esc(label)}</h3></div><span>${candidates.length} candidates · ${selected?'selected identity recorded':'scheduled choice outside menu'}</span></div><div class="candidate-bars">${shown.map(candidate=>{const score=finiteValue(candidate.score),width=score===null?0:Math.abs(score)/extent*50;return `<div class="candidate-score-row ${candidate.selected===true?'selected':''}"><span>${fmt(candidate.frequency,2)} rad/s · ${fmt(candidate.amplitude,2)} N${candidate.selected===true?'<b>SELECTED</b>':''}</span><div class="candidate-score-track"><i class="candidate-zero"></i><i class="candidate-score-fill ${score<0?'negative':''}" style="left:${score<0?50-width:50}%;width:${width}%"></i></div><strong>${compact(score)}</strong></div>`;}).join('')}</div><p class="candidate-note">${selection.kind==='predefined'?selection.message:'Signed scores are retained. Higher is ranked first; the highlighted candidate is the recorded choice.'} ${esc(experiment.selector?.tie_rule||'')}</p><details class="candidate-details"><summary>Inspect all ${candidates.length} candidates and score components</summary><div class="table-scroll"><table><thead><tr><th scope="col">Candidate</th><th scope="col">Frequency / rad s⁻¹</th><th scope="col">Amplitude / N</th><th scope="col">Score</th><th scope="col">Disagreement</th><th scope="col">Decision gain</th><th scope="col">Risk before</th><th scope="col">Risk after</th><th scope="col">Fantasies</th></tr></thead><tbody>${candidates.map(candidate=>`<tr class="${candidate.selected===true?'selected-candidate':''}"><td>${esc(candidate.id)}${candidate.selected===true?'<small>Selected</small>':''}</td><td>${fmt(candidate.frequency,3)}</td><td>${fmt(candidate.amplitude,3)}</td><td>${compact(candidate.score)}</td><td>${compact(candidate.disagreement)}</td><td>${compact(candidate.decision_gain)}</td><td>${compact(candidate.risk_before)}</td><td>${compact(candidate.risk_after)}</td><td>${fmt(candidate.fantasy_count,0)}</td></tr>`).join('')}</tbody></table></div></details></section>`;
}

function renderEvidence(r){
  $('#evidence-content').innerHTML=renderEvidenceHTML(r,state.resultJob,names);
  renderComparisonPanel();
}

function renderComparisonPanel(){
  const panel=$('#comparison-panel');if(!panel||!state.resultJob)return;
  const choices=state.runs.filter(job=>job.status==='complete'&&job.id!==state.resultJob.id);
  if(!choices.some(job=>job.id===state.compareId))state.compareId='';
  panel.innerHTML=`<div class="panel-heading"><div>${icon('layers')}<h2>Compare two studies</h2></div><span class="panel-meta">CURRENT STUDY = A</span></div><form id="comparison-form" class="comparison-controls"><div><label class="field-label" for="comparison-run">COMPARISON STUDY · B</label><div class="select-wrap"><select id="comparison-run" ${state.compareBusy||!choices.length?'disabled':''}><option value="">${choices.length?'Choose a completed study':'Complete another study to compare'}</option>${choices.map(job=>`<option value="${esc(job.id)}" ${job.id===state.compareId?'selected':''}>${esc(displayName(job.config?.world))} · ${esc(displayName(job.config?.strategy))} · seed ${esc(job.config?.seed)} · v${esc(recordedProtocol(job))} · ${esc(String(job.id).slice(0,8))}</option>`).join('')}</select>${icon('chevron')}</div></div><button class="button quiet" type="submit" id="compare-button" ${state.compareBusy||!state.compareId?'disabled':''}>${state.compareBusy?'<i class="spinner"></i> Comparing…':'Compare evidence '+icon('arrow')}</button></form><div id="comparison-result" aria-live="polite">${state.compareError?`<p class="comparison-error" role="alert">${esc(state.compareError)}</p>`:state.comparison?comparisonMarkup(state.comparison,names):'<p class="comparison-note">Compare verified completed evidence. Matching recorded settings unlock paired deltas; differing settings remain descriptive.</p>'}</div>`;
  $('#comparison-run').addEventListener('change',event=>{state.compareId=event.target.value;state.comparison=null;state.compareError='';$('#compare-button').disabled=!state.compareId;$('#comparison-result').innerHTML='<p class="comparison-note">Ready to compare. The current study, exports and playback stay selected.</p>';});
  $('#comparison-form').addEventListener('submit',event=>{event.preventDefault();compareStudies();});
}
async function compareStudies(){
  if(state.compareBusy||!state.resultJob||!state.compareId)return;
  const currentId=state.resultJob.id,otherId=state.compareId;
  if(currentId===otherId){state.compareError='Choose a different completed study; a study cannot be compared with itself.';renderComparisonPanel();return;}
  const generation=++state.compareGeneration;state.compareBusy=true;state.compareError='';state.comparison=null;renderComparisonPanel();
  try{
    const result=await api('/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_ids:[currentId,otherId]})});
    if(generation!==state.compareGeneration||state.resultJob?.id!==currentId)return;
    state.comparison=result;
  }catch(error){
    if(generation!==state.compareGeneration||state.resultJob?.id!==currentId)return;
    state.compareError=/duplicat/i.test(error.message)?'These studies contain duplicate evidence. Choose a different independent run.':`The evidence could not be compared. ${error.message}`;
  }finally{if(generation===state.compareGeneration){state.compareBusy=false;renderComparisonPanel();}}
}


let drawerReturnFocus=null;
async function openHistory(){drawerReturnFocus=document.activeElement;$('#history-drawer').hidden=false;$('#drawer-backdrop').hidden=false;document.body.classList.add('drawer-open');$('#history-close').focus();await loadHistory();}
function closeHistory(){if($('#history-drawer').hidden)return;$('#history-drawer').hidden=true;$('#drawer-backdrop').hidden=true;document.body.classList.remove('drawer-open');drawerReturnFocus?.focus();}
$$('.history-toggle').forEach(b=>b.addEventListener('click',openHistory));$('#history-close').addEventListener('click',closeHistory);$('#drawer-backdrop').addEventListener('click',closeHistory);$('#history-refresh').addEventListener('click',loadHistory);
$('#history-drawer').addEventListener('keydown',e=>{if(e.key!=='Tab')return;const items=[...$('#history-drawer').querySelectorAll('button,a[href]')].filter(el=>!el.disabled);if(e.shiftKey&&document.activeElement===items[0]){e.preventDefault();items.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===items.at(-1)){e.preventDefault();items[0].focus();}});
async function loadHistory(){try{const data=await api('/runs');state.runs=data.runs;$('#history-count').textContent=data.runs.length;renderHistory();renderComparisonPanel();}catch(error){$('#history-list').innerHTML=`<div class="history-empty"><h3>History is unavailable.</h3><p>${esc(error.message)}</p><p>Check that the local server is running, then refresh.</p></div>`;}}
function renderHistory(){
  $('#history-list').innerHTML=state.runs.length?state.runs.map(j=>`<button class="history-card ${j.id===state.resultJob?.id||j.id===state.job?.id?'selected':''}" data-run="${esc(j.id)}"><div><span class="job-status ${esc(j.status)}"><i></i>${j.cancel_requested&&['queued','running'].includes(j.status)?'cancel requested':esc(j.status)}</span><time>${esc(new Date(j.created_at).toLocaleString('en-GB',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}))}</time></div><h3>${esc(displayName(j.config?.world)||'Study')}</h3><p>${esc(displayName(j.config?.strategy)||'')} · seed ${esc(j.config?.seed??'—')} · ${esc(j.config?.budget??'—')} experiments</p><span class="history-id"><span>v${esc(recordedProtocol(j))} / ${esc(String(j.id).slice(0,12).toUpperCase())}</span> ${icon('arrow')}</span></button>`).join(''):`<div class="history-empty">${icon('history')}<h3>A clean research record.</h3><p>Your completed and running studies will appear here. Start with a question in the laboratory.</p></div>`;
  $$('[data-run]').forEach(button=>button.addEventListener('click',async()=>{
    try{
      const job=await api(`/runs/${encodeURIComponent(button.dataset.run)}`);clearTimeout(state.timer);state.pollGeneration++;state.job=job;
      if(job.status==='complete'){setBusy(false);loadResult(job);}
      else if(job.status==='failed'){setBusy(false);$('#study-mode').textContent='STUDY FAILED';showError(`This study failed: ${typeof job.error==='string'?job.error:JSON.stringify(job.error||job.message)}`);}
      else if(job.status==='cancelled'){finishCancelled();}
      else{setBusy(true);progress(job);poll(job.id);}
      closeHistory();setTab('lab');window.scrollTo({top:0,behavior:'smooth'});
    }catch(error){showError(`Could not open study. ${error.message}`);closeHistory();}
  }));
}

async function connect(){try{const data=await api('/health');$('#connection-dot').classList.add('connected');$('#connection-text').textContent=`Local engine connected`;if(data.version)document.querySelector('.engine-status small').textContent=`CPU LOCAL · v${data.version}`;}catch{$('#connection-dot').classList.add('disconnected');$('#connection-text').textContent='Local engine unavailable';showError('The local engine is unavailable. Start the COUNTERFORM Python server to run experiments. This page must be served by that server.');}loadHistory();}
configureProtocol('0.2.0');setTab(['lab','evidence','protocol'].includes(location.hash.slice(1))?location.hash.slice(1):'lab');connect();
