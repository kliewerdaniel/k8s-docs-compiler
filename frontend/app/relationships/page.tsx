"use client";

import { useMemo } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";

export default function Relationships() {
  const { graph } = useGraph();
  const store = useMemo(() => (graph ? new KnowledgeStore(graph) : null), [graph]);
  if (!graph || !store) return <p className="muted">Loading…</p>;
  const owns = graph.edges.filter((e) => e.type === "owns");
  const apiFor = graph.edges.filter((e) => e.type === "api_for");
  const controlPlane = graph.nodes.filter((n) => n.type === "controller");

  const chainTarget = "api:Deployment";
  const chain = store.neighbors(chainTarget, "owns");

  return (
    <>
      <h1>Resource Relationships</h1>
      <p className="muted">
        Ownership chains (owner references), API→doc links, and the control-plane graph.
        These are compiled deterministically from documented facts.
      </p>

      <h2>Ownership chain: Deployment</h2>
      <div className="card">
        <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>
{`Pod
 └─ owned by ReplicaSet   (${store.byId.get("api:ReplicaSet") ? "linked" : "n/a"})
     └─ owned by Deployment (api:Deployment)`}
        </pre>
        {chain.map((e, i) => (
          <div key={i} className="edge">
            <span className="etype">owns</span> {store.byId.get(e.from_id)?.title} → {store.byId.get(e.to_id)?.title}
          </div>
        ))}
      </div>

      <div className="grid2">
        <div>
          <h2>Ownership edges ({owns.length})</h2>
          {owns.slice(0, 30).map((e, i) => (
            <div key={i} className="edge">
              <strong>{store.byId.get(e.from_id)?.title}</strong> owns <strong>{store.byId.get(e.to_id)?.title}</strong>
            </div>
          ))}
        </div>
        <div>
          <h2>Control plane</h2>
          {controlPlane.map((c) => (
            <div key={c.id} className="card">
              <strong>{c.title}</strong>
              {c.summary ? <div className="muted">{c.summary}</div> : null}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
