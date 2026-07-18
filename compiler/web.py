"""Phase 5 (extra) — Static web explorer artifact.

Emits a single self-contained `knowledge.html` (no build step, no server, no LLM
at runtime) that loads `dataset.json` and provides:
  * search across all nodes
  * a force-directed concept graph (canvas, no external libs)
  * click-to-inspect node detail with provenance
  * "related to <X>" traversal

This is the deployable, backend-free knowledge application the architecture promises.
It pairs with the (planned) Next.js app in docs/FRONTEND.md but works standalone.
"""
from __future__ import annotations

import json
import os

from .ir import KnowledgeGraph
from .util import atomic_write
from .logging_setup import get_logger

logger = get_logger()

_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kubernetes Knowledge Graph</title>
<style>
  :root{--bg:#0d1117;--fg:#e6edf3;--accent:#58a6ff;--muted:#8b949e;--card:#161b22;border:#30363d}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
  header{padding:12px 16px;border-bottom:1px solid var(--card);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  input{flex:1;min-width:240px;padding:8px 10px;border-radius:8px;border:1px solid var(--card);background:#0b0f14;color:var(--fg)}
  button{padding:8px 12px;border-radius:8px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer}
  main{display:grid;grid-template-columns:1fr 1fr;gap:0;height:calc(100vh - 56px)}
  @media(max-width:860px){main{grid-template-columns:1fr}}
  #graph,#detail{padding:8px;overflow:auto;border-right:1px solid var(--card)}
  canvas{width:100%;height:100%;display:block;background:#0a0e13;border-radius:8px}
  .node-card{background:var(--card);border:1px solid var(--border,#30363d);border-radius:8px;padding:10px 12px;margin:8px 0}
  .tag{display:inline-block;font-size:11px;background:#1f6feb22;color:var(--accent);border-radius:4px;padding:1px 6px;margin:2px}
  .prov{font-size:11px;color:var(--muted);margin-top:6px}
  h1{font-size:15px;margin:0} h2{font-size:13px;color:var(--muted);margin:8px 0 4px}
  a{color:var(--accent)}
  .muted{color:var(--muted)}
</style></head>
<body>
<header>
  <strong>Kubernetes Knowledge Graph</strong>
  <input id="q" placeholder="search concepts, e.g. Deployment, RBAC, Ingress…">
  <button onclick="runQuery()">Search</button>
  <button onclick="showGraph()">Graph</button>
</header>
<main>
  <section id="graph"><canvas id="cv"></canvas></section>
  <section id="detail"><div class="muted">Search or click a node to inspect. Every fact is traceable to source.</div></section>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const NODES = DATA.nodes, EDGES = DATA.edges;
const byId = Object.fromEntries(NODES.map(n=>[n.id,n]));
// index for search
const IDX = NODES.map((n,i)=>({i,t:(n.title+' '+(n.summary||'')+' '+(n.tags||[]).join(' ')).toLowerCase(),n}));

function runQuery(){
  const q = document.getElementById('q').value.toLowerCase().trim();
  if(!q){showGraph();return;}
  const hits = IDX.filter(o=>o.t.includes(q)).slice(0,40).map(o=>o.n);
  renderList(hits, 'Search results for "'+q+'"');
}
function showGraph(){ renderList(NODES.slice(0,40), 'Sample of '+NODES.length+' concepts (graph)'); drawGraph(); }

function renderList(nodes, title){
  const d = document.getElementById('detail');
  let html = '<h2>'+title+'</h2>';
  for(const n of nodes){
    const rel = EDGES.filter(e=>e.from_id===n.id||e.to_id===n.id).slice(0,12);
    const prov = (n.provenance||[])[0];
    html += '<div class="node-card" onclick="inspect(\''+n.id.replace(/'/g,"\\\\'")+'\')">'
      + '<strong>'+esc(n.title)+'</strong> <span class="muted">['+n.type+']</span>'
      + (n.summary?'<div class="muted">'+esc(n.summary.slice(0,160))+'</div>':'')
      + (n.tags?n.tags.slice(0,6).map(t=>'<span class="tag">'+esc(t)+'</span>').join(''):'')
      + (prov?'<div class="prov">src: '+esc(prov.source||'')+(prov.url?' · <a href="'+esc(prov.url)+'" target="_blank">doc</a>':'')+'</div>':'')
      + '</div>';
  }
  d.innerHTML = html;
}
function inspect(id){
  const n = byId[id]; if(!n) return;
  const ins = EDGES.filter(e=>e.from_id===id).map(e=>({dir:'→',other:e.to_id,type:e.type,label:e.label}));
  const outs = EDGES.filter(e=>e.to_id===id).map(e=>({dir:'←',other:e.from_id,type:e.type,label:e.label}));
  let html = '<h2>'+esc(n.title)+' <span class="muted">['+n.type+']</span></h2>'
    + (n.summary?'<p>'+esc(n.summary)+'</p>':'')
    + (n.tags?n.tags.map(t=>'<span class="tag">'+esc(t)+'</span>').join(''):'')
    + '<h2>Relationships</h2>';
  for(const r of ins.concat(outs)){
    const o = byId[r.other];
    html += '<div class="node-card" onclick="inspect(\''+r.other.replace(/'/g,"\\\\'")+'\')">'
      + r.dir+' <strong>'+esc(o?o.title:r.other)+'</strong> <span class="muted">'+r.type+'</span>'
      + (r.label?' <span class="muted">'+esc(r.label)+'</span>':'')+'</div>';
  }
  const prov=(n.provenance||[])[0];
  if(prov) html += '<div class="prov">provenance: '+esc(prov.source||'')+(prov.quote?' — "'+esc(prov.quote.slice(0,120))+'"':'')+'</div>';
  document.getElementById('detail').innerHTML = html;
}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

// ---- minimal force-directed graph on canvas ----
let sim=null;
function drawGraph(){
  const cv=document.getElementById('cv'); const ctx=cv.getContext('2d');
  cv.width=cv.clientWidth; cv.height=cv.clientHeight;
  const W=cv.width,H=cv.height;
  const sample=NODES.slice(0,120);
  const pos=sample.map((_,i)=>({x:W/2+Math.cos(i)*200,y:H/2+Math.sin(i)*200,vx:0,vy:0}));
  const idset=new Set(sample.map(n=>n.id));
  const E=EDGES.filter(e=>idset.has(e.from_id)&&idset.has(e.to_id)).slice(0,200);
  const idx=Object.fromEntries(sample.map((n,i)=>[n.id,i]));
  let t=0;
  function step(){
    for(let k=0;k<sample.length;k++){
      let fx=0,fy=0;
      for(const e of E){const a=idx[e.from_id],b=idx[e.to_id];if(a==null||b==null)continue;
        const dx=pos[a].x-pos[b].x,dy=pos[a].y-pos[b].y;const d=Math.hypot(dx,dy)||1;
        const f=(d-90)*0.002;fx+=dx/d*f;fy+=dy/d*f;}
      fx+=(W/2-pos[k].x)*0.0008; fy+=(H/2-pos[k].y)*0.0008;
      pos[k].vx=(pos[k].vx+fx)*0.85; pos[k].vy=(pos[k].vy+fy)*0.85;
      pos[k].x+=pos[k].vx; pos[k].y+=pos[k].vy;
    }
    ctx.clearRect(0,0,W,H);
    ctx.strokeStyle='#30363d';
    for(const e of E){const a=idx[e.from_id],b=idx[e.to_id];if(a==null||b==null)continue;
      ctx.beginPath();ctx.moveTo(pos[a].x,pos[a].y);ctx.lineTo(pos[b].x,pos[b].y);ctx.stroke();}
    for(let k=0;k<sample.length;k++){ctx.fillStyle='#58a6ff';ctx.beginPath();ctx.arc(pos[k].x,pos[k].y,3,0,7);ctx.fill();}
    if(t++<400) sim=requestAnimationFrame(step);
  }
  cancelAnimationFrame(sim); step();
}
cvInit();
function cvInit(){ if(document.getElementById('cv').clientWidth) drawGraph(); else setTimeout(cvInit,100); }
</script>
</body></html>"""


def emit_web(g: KnowledgeGraph, out_dir: str, filename: str = "knowledge.html") -> str:
    raw = json.dumps(g.to_dict(), ensure_ascii=False)
    # Prevent the embedded JSON from prematurely closing the <script> tag
    # (real doc bodies can contain "</script>" or "</html>").
    safe = raw.replace("</", "<\\/")
    html = _HTML.replace("__DATA__", safe)
    path = os.path.join(out_dir, filename)
    atomic_write(path, html)
    logger.info("web explorer artifact: %s (%.1f KB)", path, len(html) / 1024)
    return path
