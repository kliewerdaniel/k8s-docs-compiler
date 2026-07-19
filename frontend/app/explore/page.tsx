import Link from "next/link";
import {
  getGraph,
  rbacRoles,
  hrefFor,
  titleFor,
  slugify,
} from "@/lib/knowledge.server";
import ExploreClient from "./ExploreClient";

export const metadata = {
  title: "Decision Explorer — k8s knowledge compiler",
  description:
    "Walk the compiled graph to answer operational questions. Server-rendered seed answers plus an interactive explorer.",
};

const SEED = [
  { q: "Expose a Deployment with an Ingress", term: "deployment" },
  { q: "What permissions does this manifest require?", term: "role" },
  { q: "kubectl apply internal flow", term: "flow" },
  { q: "RBAC relationships", term: "role" },
];

export default function DecisionExplorer() {
  const g = getGraph();
  const flow = g.nodes.filter((n) => n.id.startsWith("flow:")).sort((a, b) => a.id.localeCompare(b.id));
  const rbac = rbacRoles().slice(0, 20);

  return (
    <article>
      <h1>Decision Explorer</h1>
      <p className="muted">
        Walk the compiled graph to answer operational questions. This page is
        server-rendered: the kubectl apply flow and the RBAC summary are in the HTML
        with JS disabled. The interactive explorer below (progressive enhancement)
        lets you traverse the graph live.
      </p>

      <h2>Seed questions</h2>
      <ul className="idx">
        {SEED.map((s) => {
          const m = g.nodes.find(
            (n) => n.title.toLowerCase().includes(s.term) || n.id.includes(s.term)
          );
          const href = m ? hrefFor(m.id) || `/docs/${slugify(m.id)}/` : null;
          return (
            <li key={s.q}>
              {href ? <Link href={href}>{s.q}</Link> : <span>{s.q}</span>}
            </li>
          );
        })}
      </ul>

      {flow.length ? (
        <>
          <h2>Internal flow: kubectl apply</h2>
          <ol>
            {flow.map((f) => (
              <li key={f.id}>
                <strong>{f.title.replace("kubectl apply: ", "")}</strong> —{" "}
                {f.summary}
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {rbac.length ? (
        <>
          <h2>RBAC: what each resource requires</h2>
          <ul className="idx">
            {rbac.map((r) => {
              const href = hrefFor(r.id);
              const grp = (r.meta as Record<string, unknown>)?.apiGroup as string || "core";
              return (
                <li key={r.id}>
                  {href ? <Link href={href}>{r.title.replace("permissions:", "")}</Link> : r.title.replace("permissions:", "")}{" "}
                  <span className="mono">group={grp}</span>
                </li>
              );
            })}
          </ul>
        </>
      ) : null}

      <h2>Interactive explorer</h2>
      <p className="muted">Pick a node to traverse its relationships live (requires JS).</p>
      <ExploreClient />
    </article>
  );
}
