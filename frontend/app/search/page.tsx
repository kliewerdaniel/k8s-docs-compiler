import Link from "next/link";
import { getGraph, hrefFor, slugify } from "@/lib/knowledge.server";
import SearchClient from "./SearchClient";

export const metadata = {
  title: "Search — k8s knowledge compiler",
  description:
    "Full-text search across every compiled node, with provenance. The full index is also reachable as flat static pages under /docs, /api, /rbac, /relationships.",
};

export default function SearchPage() {
  const g = getGraph();
  const sample = g.nodes.slice(0, 60);

  return (
    <article>
      <h1>Search</h1>
      <p className="muted">
        Full-text search across {g.nodes.length} compiled nodes. No LLM — instant,
        deterministic. Type a term for live results (requires JS). The full corpus is
        also reachable as flat static pages — every node has its own URL under{" "}
        <Link href="/docs/">/docs/</Link>, <Link href="/api/">/api/</Link>,{" "}
        <Link href="/rbac/">/rbac/</Link>, and <Link href="/relationships/">/relationships/</Link>.
      </p>

      <SearchClient />

      <h2>Browse the index (no JS required)</h2>
      <p className="muted">A sample of all compiled nodes — each links to its static page:</p>
      <ul className="idx">
        {sample.map((n) => {
          const href = hrefFor(n.id) || `/docs/${slugify(n.id)}/`;
          return (
            <li key={n.id}>
              <Link href={href}>{n.title}</Link>{" "}
              <span className="mono">[{n.type}]</span>
              {n.summary ? <span className="muted"> — {n.summary.slice(0, 90)}</span> : null}
            </li>
          );
        })}
      </ul>
      <p className="muted">
        …and {g.nodes.length - sample.length} more. See{" "}
        <Link href="/sitemap.xml">sitemap.xml</Link> for every URL.
      </p>
    </article>
  );
}
