"use client";

import { useMemo } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";
import { renderBody } from "@/lib/components";

export default function DocPage() {
  const { graph } = useGraph();
  const id = typeof window !== "undefined"
    ? new URLSearchParams(window.location.search).get("id") : null;
  const store = useMemo(() => (graph ? new KnowledgeStore(graph) : null), [graph]);
  if (!graph || !store) return <p className="muted">Loading…</p>;
  const n = id ? store.byId.get(id) : null;
  if (!n) {
    return (
      <>
        <h1>Documentation</h1>
        <p className="muted">Open any node from Search / API Explorer / Graph to read its synthesized documentation here.</p>
      </>
    );
  }
  const related = store.relatedTo(n.id, 12);
  return (
    <>
      <h1>{n.title}</h1>
      <div className="row">
        <span className="mono">[{n.type}]</span>
        {n.derived_by.startsWith("ai:") ? (
          <span className="tag" title="Synthesized at compile time from source quotes">
            ai-synthesized · conf {n.confidence}
          </span>
        ) : (
          <span className="tag">deterministic</span>
        )}
        {n.tags.map((t) => <span key={t} className="tag">{t}</span>)}
      </div>
      {n.body ? (
        <div className="card" style={{ marginTop: 12, fontSize: 14, lineHeight: 1.6 }}>
          {renderBody(n.body)}
        </div>
      ) : (
        <p className="muted">{n.summary || "No body available."}</p>
      )}
      {n.provenance?.length ? (
        <div style={{ marginTop: 10 }}>
          <h2>Sources</h2>
          {n.provenance.slice(0, 4).map((p, i) => (
            <div key={i} className="prov">
              {p.source}{p.url ? <> · <a href={p.url} target="_blank" rel="noreferrer">doc</a></> : null}
              {p.quote ? <> — “{p.quote.slice(0, 240)}”</> : null}
            </div>
          ))}
        </div>
      ) : null}
      <h2>Related</h2>
      {related.map((e, i) => {
        const other = e.from_id === n.id ? e.to_id : e.from_id;
        const o = store.byId.get(other);
        return (
          <div key={i} className="edge">
            <span className="etype">{e.type}</span>{" "}
            <a href={`/docs?id=${encodeURIComponent(other)}`}>{o?.title ?? other}</a>
          </div>
        );
      })}
    </>
  );
}
