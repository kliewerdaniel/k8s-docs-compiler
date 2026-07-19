"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

// Live full-text search over dataset.json. Progressive enhancement over the
// server-rendered index on /search.
export default function SearchClient() {
  const [graph, setGraph] = useState<any>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    fetch("/dataset.json")
      .then((r) => r.json())
      .then(setGraph)
      .catch(() => {});
  }, []);

  const hits = useMemo(() => {
    if (!graph || !q.trim()) return [];
    const ql = q.toLowerCase().trim();
    const terms = ql.split(/\s+/).filter((t: string) => t.length > 1);
    return graph.nodes
      .filter((n: any) =>
        terms.every((t: string) =>
          `${n.title} ${n.summary || ""} ${(n.tags || []).join(" ")}`.toLowerCase().includes(t)
        )
      )
      .slice(0, 50);
  }, [graph, q]);

  if (!graph) return <p className="muted">Live search box requires JavaScript (the full index above is readable without it).</p>;

  return (
    <div>
      <input
        style={{ width: "100%" }}
        placeholder="e.g. Ingress, RBAC, Pod lifecycle, Deployment strategy"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div style={{ marginTop: 10 }}>
        <h3>Results ({hits.length})</h3>
        {hits.map((n: any) => (
          <div key={n.id}>
            <Link href={`/docs/${n.id.replace(/:/g, "-").replace(/\//g, "-")}/`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="card">
                <strong>{n.title}</strong> <span className="mono">[{n.type}]</span>
                {n.summary ? <div className="muted" style={{ fontSize: 12 }}>{n.summary.slice(0, 120)}</div> : null}
              </div>
            </Link>
          </div>
        ))}
        {q && !hits.length ? <p className="muted">No matches.</p> : null}
      </div>
    </div>
  );
}
