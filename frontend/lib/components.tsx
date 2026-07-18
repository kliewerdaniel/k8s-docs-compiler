"use client";

import type { Node, Edge, Provenance } from "@/lib/types";

export function Prov({ p }: { p?: Provenance }) {
  if (!p) return null;
  return (
    <div className="prov">
      source: {p.source}
      {p.url ? (
        <>
          {" · "}
          <a href={p.url} target="_blank" rel="noreferrer">
            doc
          </a>
        </>
      ) : null}
      {p.quote ? <> — “{p.quote.slice(0, 200)}”</> : null}
    </div>
  );
}

export function NodeCard({ n, onPick }: { n: Node; onPick?: (id: string) => void }) {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong style={{ fontSize: 15 }}>{n.title}</strong>
        <span className="mono">[{n.type}]</span>
      </div>
      {n.summary ? <div className="muted" style={{ marginTop: 4 }}>{n.summary}</div> : null}
      <div style={{ marginTop: 6 }}>
        {n.tags?.map((t) => (
          <span key={t} className="tag">{t}</span>
        ))}
      </div>
      {n.provenance?.[0] ? <Prov p={n.provenance[0]} /> : null}
      {onPick ? (
        <div style={{ marginTop: 8 }}>
          <button onClick={() => onPick(n.id)}>inspect</button>
        </div>
      ) : null}
    </div>
  );
}

export function EdgeList({ edges, byId }: { edges: Edge[]; byId: Map<string, Node> }) {
  if (!edges.length) return <p className="muted">No recorded relationships.</p>;
  return (
    <div>
      {edges.map((e, i) => {
        const title = (id: string) => byId.get(id)?.title ?? id;
        return (
          <div key={i} className="edge">
            <span className="etype">{e.type}</span>{" "}
            <strong>{title(e.from_id)}</strong>
            {" → "}
            <strong>{title(e.to_id)}</strong>
            {e.label ? <span className="muted"> — {e.label}</span> : null}
            <span className="mono"> conf={e.confidence}</span>
          </div>
        );
      })}
    </div>
  );
}
