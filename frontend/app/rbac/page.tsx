"use client";

import { useMemo } from "react";
import { useGraph } from "@/lib/useGraph";

export default function Rbac() {
  const { graph } = useGraph();
  if (!graph) return <p className="muted">Loading…</p>;
  const roles = graph.nodes.filter((n) => n.type === "role");
  const requires = graph.edges.filter((e) => e.type === "requires");

  return (
    <>
      <h1>RBAC &amp; Permissions</h1>
      <p className="muted">
        Compiled from the RBAC reference: each resource maps to the verbs (permissions) a
        Role/ClusterRole must grant. Directly answers “what permissions does this manifest
        require?”
      </p>
      <div className="grid2">
        <div>
          <h2>Roles / permissions ({roles.length})</h2>
          {roles.map((r) => {
            const m = r.meta as Record<string, unknown>;
            const verbs = (m?.verbs as string[]) || [];
            const grp = (m?.apiGroup as string) || "core";
            return (
              <div key={r.id} className="card">
                <strong>{r.title.replace("permissions:", "")}</strong>{" "}
                <span className="mono">group={grp}</span>
                <div className="mono" style={{ marginTop: 4 }}>{verbs.join(", ")}</div>
              </div>
            );
          })}
        </div>
        <div>
          <h2>Manifest → required permission edges ({requires.length})</h2>
          {requires.slice(0, 60).map((e, i) => (
            <div key={i} className="edge">
              <span className="etype">requires</span> {e.from_id.replace("role:", "")} → {e.to_id.replace("api:", "")}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
