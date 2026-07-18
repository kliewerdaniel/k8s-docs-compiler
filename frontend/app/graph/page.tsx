"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";

// Lightweight force-directed layout (no external lib needed for correctness;
// uses a simple velocity Verlet simulation on canvas).
interface P { x: number; y: number; vx: number; vy: number; id: string; title: string; type: string; }

export default function Graph() {
  const { graph } = useGraph();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [query, setQuery] = useState("deployment");
  const [hover, setHover] = useState<string | null>(null);
  const store = useMemo(() => (graph ? new KnowledgeStore(graph) : null), [graph]);

  const nodes: P[] = useMemo(() => {
    if (!graph) return [];
    const q = query.toLowerCase().trim();
    const subset = q
      ? graph.nodes.filter((n) => n.title.toLowerCase().includes(q)).slice(0, 220)
      : graph.nodes.slice(0, 220);
    const ids = new Set(subset.map((n) => n.id));
    return subset.map((n, i) => ({
      id: n.id,
      title: n.title,
      type: n.type,
      x: Math.cos(i) * 180 + 400,
      y: Math.sin(i) * 180 + 300,
      vx: 0,
      vy: 0,
    }));
  }, [graph, query]);

  const edges = useMemo(() => {
    if (!graph || !store) return [];
    const ids = new Set(nodes.map((n) => n.id));
    return graph.edges
      .filter((e) => ids.has(e.from_id) && ids.has(e.to_id))
      .slice(0, 400)
      .map((e) => ({ from: e.from_id, to: e.to_id }));
  }, [graph, nodes, store]);

  useEffect(() => {
    if (!canvasRef.current || !nodes.length) return;
    const cv = canvasRef.current;
    const ctx = cv.getContext("2d")!;
    const pos = new Map(nodes.map((n) => [n.id, n]));
    let raf = 0;
    const W = cv.width, H = cv.height;

    function step() {
      for (const p of nodes) {
        let fx = (W / 2 - p.x) * 0.0009;
        let fy = (H / 2 - p.y) * 0.0009;
        for (const e of edges) {
          const a = pos.get(e.from), b = pos.get(e.to);
          if (!a || !b) continue;
          const dx = a.x - b.x, dy = a.y - b.y;
          const d = Math.hypot(dx, dy) || 1;
          const f = (d - 70) * 0.0015;
          fx += (dx / d) * f; fy += (dy / d) * f;
        }
        p.vx = (p.vx + fx) * 0.86;
        p.vy = (p.vy + fy) * 0.86;
        p.x += p.vx; p.y += p.vy;
      }
      ctx.clearRect(0, 0, W, H);
      ctx.strokeStyle = "#30363d";
      for (const e of edges) {
        const a = pos.get(e.from), b = pos.get(e.to);
        if (!a || !b) continue;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      for (const p of nodes) {
        ctx.fillStyle = p.id === hover ? "#58a6ff" : "#388bfd";
        ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, 7); ctx.fill();
        if (p.id === hover) {
          ctx.fillStyle = "#e6edf3"; ctx.font = "11px system-ui";
          ctx.fillText(p.title, p.x + 6, p.y - 6);
        }
      }
      raf = requestAnimationFrame(step);
    }
    step();
    return () => cancelAnimationFrame(raf);
  }, [nodes, edges, hover]);

  const onMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    let found: string | null = null;
    for (const p of nodes) {
      if (Math.hypot(p.x - mx, p.y - my) < 8) { found = p.id; break; }
    }
    setHover(found);
  };

  if (!graph) return <p className="muted">Loading…</p>;
  const hov = hover && store ? store.byId.get(hover) : null;

  return (
    <>
      <h1>Concept Graph</h1>
      <p className="muted">
        Force-directed view of the compiled knowledge graph. Hover a node for its title;
        the full graph has {graph.nodes.length} nodes and {graph.edges.length} edges.
      </p>
      <input
        style={{ width: 320 }}
        placeholder="filter by concept (e.g. deployment, ingress)…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <canvas
        ref={canvasRef}
        width={1140}
        height={620}
        onMouseMove={onMove}
        style={{ width: "100%", background: "#0a0e13", borderRadius: 10, marginTop: 12 }}
      />
      {hov ? (
        <div className="card">
          <strong>{hov.title}</strong> <span className="mono">[{hov.type}]</span>
          {hov.summary ? <div className="muted">{hov.summary}</div> : null}
          {hov.provenance?.[0] ? (
            <div className="prov">source: {hov.provenance[0].source}{hov.provenance[0].url ? ` · ${hov.provenance[0].url}` : ""}</div>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
