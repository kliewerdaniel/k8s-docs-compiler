"use client";

import { useState } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";
import { NodeCard } from "@/lib/components";

export default function Search() {
  const { graph } = useGraph();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  if (!graph) return <p className="muted">Loading…</p>;
  const store = new KnowledgeStore(graph);
  const hits = q ? store.search(q, 50) : [];
  const selected = sel ? store.byId.get(sel) : null;
  return (
    <>
      <h1>Search</h1>
      <p className="muted">Full-text search across {graph.nodes.length} compiled nodes. No LLM — instant, deterministic.</p>
      <input
        style={{ width: "100%" }}
        placeholder="e.g. Ingress, RBAC, Pod lifecycle, Deployment strategy"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div className="grid2" style={{ marginTop: 14 }}>
        <div>
          <h2>Results ({hits.length})</h2>
          {hits.map((n) => (
            <div key={n.id} onClick={() => setSel(n.id)} style={{ cursor: "pointer" }}>
              <NodeCard n={n} />
            </div>
          ))}
          {q && !hits.length ? <p className="muted">No matches.</p> : null}
        </div>
        <div>
          <h2>Detail</h2>
          {selected ? (
            <div className="card">
              <strong style={{ fontSize: 16 }}>{selected.title}</strong> <span className="mono">[{selected.type}]</span>
              {selected.summary ? <div className="muted" style={{ marginTop: 4 }}>{selected.summary}</div> : null}
              {selected.body ? <pre className="mono" style={{ whiteSpace: "pre-wrap", maxHeight: 320, overflow: "auto" }}>{selected.body.slice(0, 1500)}</pre> : null}
            </div>
          ) : (
            <p className="muted">Pick a result to inspect.</p>
          )}
        </div>
      </div>
    </>
  );
}
