"use client";

import { useMemo, useState } from "react";
import { useGraph } from "@/lib/useGraph";
import { KnowledgeStore } from "@/lib/store";

export default function LearningPaths() {
  const { graph } = useGraph();
  const [sel, setSel] = useState<string | null>(null);
  const store = useMemo(() => (graph ? new KnowledgeStore(graph) : null), [graph]);
  if (!graph || !store) return <p className="muted">Loading…</p>;

  // Build prerequisite chains via BFS over prerequisite_of edges (incoming).
  const keyConcepts = graph.nodes
    .filter((n) => n.type === "glossary")
    .sort((a, b) => a.title.localeCompare(b.title));

  const selected = sel ? store.byId.get(sel) : null;
  const prereqs = selected ? store.in(selected.id).filter((e) => e.type === "prerequisite_of") : [];
  const leadsTo = selected ? store.out(selected.id).filter((e) => e.type === "prerequisite_of") : [];

  return (
    <>
      <h1>Learning Paths</h1>
      <p className="muted">
        Prerequisite chains compiled from “Before you begin” sections and concept hierarchy.
        Pick a concept to see what you should understand first, and what builds on it.
      </p>
      <div className="grid2">
        <div style={{ maxHeight: "70vh", overflow: "auto" }}>
          <h2>Glossary concepts</h2>
          {keyConcepts.map((n) => (
            <div key={n.id} className="card" style={{ cursor: "pointer" }} onClick={() => setSel(n.id)}>
              <strong>{n.title}</strong>
              {n.tags?.length ? <span className="tag">{n.tags[0]}</span> : null}
            </div>
          ))}
        </div>
        <div>
          <h2>{selected ? `Path for: ${selected.title}` : "Prerequisite chain"}</h2>
          {selected ? (
            <>
              <div className="card">
                <strong>Understand first (prerequisites):</strong>
                {prereqs.length ? (
                  <ul>
                    {prereqs.map((e) => (
                      <li key={e.from_id} style={{ cursor: "pointer" }} onClick={() => setSel(e.from_id)}>
                        {store.byId.get(e.from_id)?.title} <span className="mono">[{e.confidence}]</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No recorded prerequisites — a root concept.</p>
                )}
                <strong>Builds on it (leads to):</strong>
                {leadsTo.length ? (
                  <ul>
                    {leadsTo.map((e) => (
                      <li key={e.to_id} style={{ cursor: "pointer" }} onClick={() => setSel(e.to_id)}>
                        {store.byId.get(e.to_id)?.title}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No recorded dependents.</p>
                )}
              </div>
            </>
          ) : (
            <p className="muted">Pick a concept.</p>
          )}
        </div>
      </div>
    </>
  );
}
