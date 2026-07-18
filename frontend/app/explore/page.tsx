"use client";

import { useMemo, useState } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";

const SEED = [
  { q: "Expose a Deployment with an Ingress", term: "deployment" },
  { q: "What permissions does this manifest require?", term: "role" },
  { q: "kubectl apply internal flow", term: "flow" },
  { q: "RBAC relationships", term: "role" },
];

export default function DecisionExplorer() {
  const { graph } = useGraph();
  const [picked, setPicked] = useState<string | null>(null);
  const store = useMemo(() => (graph ? new KnowledgeStore(graph) : null), [graph]);
  if (!graph || !store) return <p className="muted">Loading…</p>;

  const node = picked ? store.byId.get(picked) : null;
  const related = picked ? store.relatedTo(picked, 30) : [];
  const flow = store.kubectlFlow();
  const rbac = store.rbacRoles();

  return (
    <>
      <h1>Decision Explorer</h1>
      <p className="muted">
        Walk the compiled graph to answer operational questions. Try a seed question, or
        inspect any node.
      </p>
      <div className="row">
        {SEED.map((s) => (
          <button key={s.q} onClick={() => {
            const m = graph.nodes.find((n) => n.title.toLowerCase().includes(s.term) || n.id.includes(s.term));
            setPicked(m?.id ?? null);
          }}>{s.q}</button>
        ))}
      </div>

      <div className="grid2" style={{ marginTop: 14 }}>
        <div>
          <h2>Selected</h2>
          {node ? (
            <div className="card">
              <strong style={{ fontSize: 16 }}>{node.title}</strong> <span className="mono">[{node.type}]</span>
              {node.summary ? <div className="muted" style={{ marginTop: 4 }}>{node.summary}</div> : null}
            </div>
          ) : <p className="muted">Pick a seed above.</p>}

          {flow.length ? (
            <>
              <h2>Internal flow: kubectl apply</h2>
              <ol>
                {flow.map((f) => (
                  <li key={f.id}><strong>{f.title.replace("kubectl apply: ", "")}</strong> — {f.summary}</li>
                ))}
              </ol>
            </>
          ) : null}
        </div>
        <div>
          <h2>Related concepts (graph traversal)</h2>
          {related.map((e, i) => {
            const other = e.from_id === picked ? e.to_id : e.from_id;
            const o = store.byId.get(other);
            return (
              <div key={i} className="edge" style={{ cursor: "pointer" }} onClick={() => setPicked(other)}>
                <span className="etype">{e.type}</span> → <strong>{o?.title ?? other}</strong>
                {e.label ? <span className="muted"> — {e.label}</span> : null}
              </div>
            );
          })}
          {rbac.length ? (
            <>
              <h2>RBAC: what each resource requires</h2>
              {rbac.slice(0, 10).map((r) => (
                <div key={r.id} className="edge">
                  <strong>{r.title.replace("permissions:", "")}</strong>{" "}
                  <span className="mono">group={(r.meta?.apiGroup as string) || "core"}</span>
                </div>
              ))}
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}
