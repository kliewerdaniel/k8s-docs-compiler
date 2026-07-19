import Link from "next/link";
import { getGraph, titleFor, hrefFor, slugify } from "@/lib/knowledge.server";
import GraphCanvas from "./GraphCanvas";

export const metadata = {
  title: "Concept Graph — k8s knowledge compiler",
  description:
    "Force-directed view of the compiled Kubernetes knowledge graph. A static node/edge table is rendered server-side for crawlers and no-JS readers.",
};

export default function GraphPage() {
  const g = getGraph();
  // Cap the server-rendered table for payload sanity; the full graph is in dataset.json.
  const nodes = g.nodes.slice(0, 400);
  const nodeIds = new Set(nodes.map((n) => n.id));
  const edges = g.edges
    .filter((e) => nodeIds.has(e.from_id) && nodeIds.has(e.to_id))
    .slice(0, 600);

  return (
    <article>
      <h1>Concept Graph</h1>
      <p className="muted">
        Force-directed view of the compiled knowledge graph. The full graph has{" "}
        {g.nodes.length} nodes and {g.edges.length} edges. The interactive canvas below
        requires JavaScript; the table beneath it is server-rendered and fully readable
        with JS disabled.
      </p>

      <GraphCanvas
        initialNodes={g.nodes.slice(0, 220).map((n) => ({ id: n.id, title: n.title, type: n.type }))}
      />

      <noscript>
        <p className="muted">
          (Interactive graph needs JavaScript. The full node/edge list is rendered below
          and in <Link href="/dataset.json">dataset.json</Link>.)
        </p>
      </noscript>

      <h2 id="node-table">Nodes ({g.nodes.length}) — first {nodes.length} shown</h2>
      <table className="graphtable">
        <thead>
          <tr><th>id</th><th>type</th><th>title</th></tr>
        </thead>
        <tbody>
          {nodes.map((n) => {
            const href = hrefFor(n.id) || `/docs/${slugify(n.id)}/`;
            return (
              <tr key={n.id}>
                <td className="mono">{n.id}</td>
                <td className="mono">{n.type}</td>
                <td><Link href={href}>{n.title}</Link></td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2 id="edge-table">Edges — first {edges.length} shown</h2>
      <table className="graphtable">
        <thead>
          <tr><th>type</th><th>from</th><th>to</th><th>conf</th></tr>
        </thead>
        <tbody>
          {edges.map((e, i) => {
            const fh = hrefFor(e.from_id);
            const th = hrefFor(e.to_id);
            return (
              <tr key={i}>
                <td className="mono">{e.type}</td>
                <td>
                  {fh ? <Link href={fh}>{titleFor(e.from_id)}</Link> : titleFor(e.from_id)}
                </td>
                <td>
                  {th ? <Link href={th}>{titleFor(e.to_id)}</Link> : titleFor(e.to_id)}
                </td>
                <td className="mono">{e.confidence}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </article>
  );
}
