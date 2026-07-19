"use client";

import { useMemo, useState } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";
import { renderBody } from "@/lib/components";

export default function StartPage() {
  const { graph } = useGraph();
  const store = useMemo(() => (graph ? new KnowledgeStore(graph) : null), [graph]);
  const [sel, setSel] = useState<string | null>(null);

  if (!graph || !store) return <p className="muted">Loading…</p>;

  const path = store.startHere(12);
  const current = sel ? store.byId.get(sel) : null;
  const prereqs = current ? store.prerequisitesOf(current.id) : [];
  const unlocks = current ? store.unlocks(current.id) : [];

  return (
    <>
      <h1>Start Here</h1>
      <p className="muted">
        A guided onboarding path through Kubernetes, ordered so you learn the
        foundational concepts first. Each step builds on what came before it
        (prerequisites were inferred from the documentation at compile time).
        Click any concept to see what it requires and what it unlocks.
      </p>

      <h2>The path</h2>
      <ol className="startpath">
        {path.map((n, i) => (
          <li key={n.id}>
            <button
              className={"linkbtn" + (sel === n.id ? " active" : "")}
              onClick={() => setSel(n.id)}
            >
              {i + 1}. {n.title}
            </button>
            {n.summary ? <span className="muted"> — {n.summary}</span> : null}
          </li>
        ))}
      </ol>

      {current ? (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong style={{ fontSize: 16 }}>{current.title}</strong>
            <span className="mono">[{current.type}]</span>
          </div>
          {current.body ? (
            <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.55 }}>
              {renderBody(current.body)}
            </div>
          ) : null}

          <h3 style={{ marginTop: 14 }}>Learn first (prerequisites)</h3>
          {prereqs.length ? (
            <div className="row">
              {prereqs.map((p) => (
                <button key={p.id} className="tag btn" onClick={() => setSel(p.id)}>
                  {p.title}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">No recorded prerequisites — a foundational concept.</p>
          )}

          <h3 style={{ marginTop: 12 }}>Unlocks</h3>
          {unlocks.length ? (
            <div className="row">
              {unlocks.map((u) => (
                <button key={u.id} className="tag btn" onClick={() => setSel(u.id)}>
                  {u.title}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">Nothing recorded depends on this.</p>
          )}
          <p style={{ marginTop: 12 }}>
            <a href={`/docs?id=${encodeURIComponent(current.id)}`}>Open full documentation →</a>
          </p>
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 14 }}>
          Select a concept above to inspect its learning path.
        </p>
      )}
    </>
  );
}
