"use client";

import { useEffect, useMemo, useRef, useState } from "react";

interface MiniNode {
  id: string;
  title: string;
  type: string;
}

// Interactive force-directed canvas. This is a progressive enhancement: the
// parent (server) page already renders the full node/edge table in HTML, so
// the graph is readable without JS. This island just adds the live viz.
export default function GraphCanvas({ initialNodes }: { initialNodes: MiniNode[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [query, setQuery] = useState("deployment");
  const [hover, setHover] = useState<string | null>(null);

  // Re-fetch the full dataset client-side so the canvas isn't limited to the
  // initial 220 — the static table (server-rendered) already covers crawlability.
  const [allNodes, setAllNodes] = useState<MiniNode[]>(initialNodes);
  useEffect(() => {
    fetch("/dataset.json")
      .then((r) => r.json())
      .then((d: any) => {
        setAllNodes(
          (d.nodes || []).map((n: any) => ({ id: n.id, title: n.title, type: n.type }))
        );
      })
      .catch(() => {});
  }, []);

  const nodes = useMemo(() => {
    const q = query.toLowerCase().trim();
    const subset = q
      ? allNodes.filter((n) => n.title.toLowerCase().includes(q)).slice(0, 220)
      : allNodes.slice(0, 220);
    return subset.map((n, i) => ({
      ...n,
      x: Math.cos(i) * 180 + 400,
      y: Math.sin(i) * 180 + 300,
      vx: 0,
      vy: 0,
    }));
  }, [allNodes, query]);

  useEffect(() => {
    if (!canvasRef.current || !nodes.length) return;
    const cv = canvasRef.current;
    const ctx = cv.getContext("2d")!;
    const pos = new Map(nodes.map((n) => [n.id, n]));
    let raf = 0;
    const W = cv.width,
      H = cv.height;

    // Lightweight velocity-Verlet simulation over the first ~400 edges among the
    // visible subset (we don't need edges here for layout, just repulsion/attraction
    // among visible nodes — keeps it dependency-free and cheap).
    const visible = new Set(nodes.map((n) => n.id));

    function step() {
      for (const p of nodes) {
        let fx = (W / 2 - p.x) * 0.0009;
        let fy = (H / 2 - p.y) * 0.0009;
        for (const q2 of nodes) {
          if (q2 === p) continue;
          const dx = p.x - q2.x,
            dy = p.y - q2.y;
          const d = Math.hypot(dx, dy) || 1;
          const f = (d - 70) * 0.0015;
          fx += (dx / d) * f;
          fy += (dy / d) * f;
        }
        p.vx = (p.vx + fx) * 0.86;
        p.vy = (p.vy + fy) * 0.86;
        p.x += p.vx;
        p.y += p.vy;
      }
      ctx.clearRect(0, 0, W, H);
      ctx.strokeStyle = "#30363d";
      for (const p of nodes) {
        ctx.fillStyle = p.id === hover ? "#58a6ff" : "#388bfd";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, 7);
        ctx.fill();
        if (p.id === hover) {
          ctx.fillStyle = "#e6edf3";
          ctx.font = "11px system-ui";
          ctx.fillText(p.title, p.x + 6, p.y - 6);
        }
      }
      raf = requestAnimationFrame(step);
    }
    step();
    return () => cancelAnimationFrame(raf);
  }, [nodes, hover]);

  const onMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left,
      my = e.clientY - rect.top;
    let found: string | null = null;
    for (const p of nodes) {
      if (Math.hypot(p.x - mx, p.y - my) < 8) {
        found = p.id;
        break;
      }
    }
    setHover(found);
  };

  return (
    <div>
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
      {hover ? (
        <div className="muted">
          hovering: <strong>{nodes.find((n) => n.id === hover)?.title}</strong>{" "}
          <span className="mono">[{nodes.find((n) => n.id === hover)?.type}]</span>
        </div>
      ) : null}
    </div>
  );
}
