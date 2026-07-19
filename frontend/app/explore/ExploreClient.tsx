"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

// Interactive graph traversal. Progressive enhancement over the server-rendered
// decision content on /explore. Fetches dataset.json only for the live UX.
export default function ExploreClient() {
  const [graph, setGraph] = useState<any>(null);
  const [picked, setPicked] = useState<string | null>(null);

  useEffect(() => {
    fetch("/dataset.json")
      .then((r) => r.json())
      .then(setGraph)
      .catch(() => {});
  }, []);

  const byId = useMemo(() => {
    const m = new Map<string, any>();
    if (graph) for (const n of graph.nodes) m.set(n.id, n);
    return m;
  }, [graph]);

  const edgesByFrom = useMemo(() => {
    const m = new Map<string, any[]>();
    if (graph)
      for (const e of graph.edges) {
        if (!m.has(e.from_id)) m.set(e.from_id, []);
        m.get(e.from_id)!.push(e);
      }
    return m;
  }, [graph]);

  if (!graph) return <p className="muted">Interactive explorer requires JavaScript (the kubectl apply flow and RBAC summary above are fully readable without it).</p>;

  const node = picked ? byId.get(picked) : null;
  const related = picked ? (edgesByFrom.get(picked) || []).slice(0, 30) : [];

  return (
    <div className="grid2" style={{ marginTop: 6 }}>
      <div>
        <h3>Selected</h3>
        {node ? (
          <div className="card">
            <strong style={{ fontSize: 16 }}>{node.title}</strong>{" "}
            <span className="mono">[{node.type}]</span>
            {node.summary ? <div className="muted" style={{ marginTop: 4 }}>{node.summary}</div> : null}
          </div>
        ) : (
          <p className="muted">Pick a seed above.</p>
        )}
      </div>
      <div>
        <h3>Related concepts (graph traversal)</h3>
        {related.map((e: any, i: number) => {
          const other = e.from_id === picked ? e.to_id : e.from_id;
          const o = byId.get(other);
          return (
            <div key={i} className="edge" style={{ cursor: "pointer" }} onClick={() => setPicked(other)}>
              <span className="etype">{e.type}</span> → <strong>{o?.title ?? other}</strong>
              {e.label ? <span className="muted"> — {e.label}</span> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
