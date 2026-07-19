import Link from "next/link";
import { controlPlane, hrefFor } from "@/lib/knowledge.server";

export const metadata = {
  title: "Resource Relationships — k8s knowledge compiler",
  description:
    "Ownership chains (owner references), API→doc links, and the control-plane graph, compiled deterministically from documented facts.",
};

export default function RelationshipsIndex() {
  const controllers = controlPlane();
  const g = require("@/lib/knowledge.server").getGraph();
  const owns = g.edges.filter((e: any) => e.type === "owns");
  const apiFor = g.edges.filter((e: any) => e.type === "api_for");

  return (
    <article>
      <h1>Resource Relationships</h1>
      <p className="muted">
        Ownership chains (owner references), API→doc links, and the control-plane
        graph. These are compiled deterministically from documented facts.
      </p>

      <h2>Ownership chain: Deployment</h2>
      <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>
        {"Pod\n └─ owned by ReplicaSet\n     └─ owned by Deployment (api:Deployment)"}
      </pre>
      <div>
        {owns.slice(0, 30).map((e: any, i: number) => {
          const fh = hrefFor(e.from_id);
          const th = hrefFor(e.to_id);
          const ft = require("@/lib/knowledge.server").titleFor(e.from_id);
          const tt = require("@/lib/knowledge.server").titleFor(e.to_id);
          return (
            <div key={i} className="edge">
              <span className="etype">owns</span>{" "}
              {fh ? <Link href={fh}>{ft}</Link> : <strong>{ft}</strong>} →{" "}
              {th ? <Link href={th}>{tt}</Link> : <strong>{tt}</strong>}
            </div>
          );
        })}
      </div>

      <h2>Control plane ({controllers.length})</h2>
      <ul className="idx">
        {controllers.map((c) => {
          const href = hrefFor(c.id);
          return (
            <li key={c.id}>
              {href ? <Link href={href}>{c.title}</Link> : <span>{c.title}</span>}
              {c.summary ? <span className="muted"> — {c.summary}</span> : null}
            </li>
          );
        })}
      </ul>

      <h2>API → doc edges ({apiFor.length})</h2>
      <p className="muted">Sample of api_for edges linking API objects to docs:</p>
      <div>
        {apiFor.slice(0, 40).map((e: any, i: number) => {
          const fh = hrefFor(e.from_id);
          const th = hrefFor(e.to_id);
          const ft = require("@/lib/knowledge.server").titleFor(e.from_id);
          const tt = require("@/lib/knowledge.server").titleFor(e.to_id);
          return (
            <div key={i} className="edge">
              <span className="etype">api_for</span>{" "}
              {fh ? <Link href={fh}>{ft}</Link> : <strong>{ft}</strong>} →{" "}
              {th ? <Link href={th}>{tt}</Link> : <strong>{tt}</strong>}
            </div>
          );
        })}
      </div>
    </article>
  );
}
