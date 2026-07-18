"use client";

import { useMemo, useState } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";

export default function ApiExplorer() {
  const { graph } = useGraph();
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("all");
  if (!graph) return <p className="muted">Loading…</p>;
  const store = useMemo(() => new KnowledgeStore(graph), [graph]);
  const objs = graph.nodes.filter((n) => n.type === "api_object");
  const groups = ["all", ...Array.from(new Set(objs.map((o) => (o.meta?.group as string) || "core")))];
  const filtered = objs
    .filter((o) => group === "all" || (o.meta?.group as string) === group)
    .filter((o) => !q || o.title.toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => a.title.localeCompare(b.title));

  const selected = filtered.find((o) => o.title.toLowerCase() === q.toLowerCase());

  return (
    <>
      <h1>API Explorer</h1>
      <p className="muted">
        {objs.length} API objects and {graph.nodes.filter((n) => n.type === "api_path").length} API paths,
        extracted from the OpenAPI specification. Cross-linked to the docs that explain them.
      </p>
      <div className="row" style={{ marginBottom: 10 }}>
        <input placeholder="filter by Kind…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          {groups.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
      </div>
      <div className="grid2">
        <div style={{ maxHeight: "70vh", overflow: "auto" }}>
          {filtered.map((o) => (
            <div key={o.id} className="card" onClick={() => setQ(o.title)} style={{ cursor: "pointer" }}>
              <strong>{o.title}</strong> <span className="mono">{(o.meta?.group as string) || "core"}/{o.meta?.version as string}</span>
              {o.summary ? <div className="muted" style={{ fontSize: 12 }}>{o.summary.slice(0, 120)}</div> : null}
            </div>
          ))}
        </div>
        <div>
          <h2>Object detail</h2>
          {selected ? (
            <div className="card">
              <strong style={{ fontSize: 16 }}>{selected.title}</strong>
              <div className="muted">{selected.summary}</div>
              <div style={{ marginTop: 6 }}>
                <span className="tag">group: {(selected.meta?.group as string) || "core"}</span>
                <span className="tag">version: {selected.meta?.version as string}</span>
                <span className="tag">fields: {selected.meta?.field_count as number}</span>
              </div>
              {Array.isArray(selected.meta?.fields) ? (
                <>
                  <h2>Fields</h2>
                  {(selected.meta?.fields as string[]).map((f) => (
                    <div key={f} className="mono">{f}</div>
                  ))}
                </>
              ) : null}
              <h2>Related</h2>
              {store.neighbors(selected.id, "related_to").map((e, i) => (
                <div key={i} className="edge">
                  <span className="etype">related_to</span> → <strong>{store.byId.get(e.to_id)?.title ?? e.to_id}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">Select an object.</p>
          )}
        </div>
      </div>
    </>
  );
}
