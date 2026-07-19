import Link from "next/link";
import {
  getNodesByType,
  slugify,
  hrefFor,
  getNode,
} from "@/lib/knowledge.server";

export const metadata = {
  title: "Docs — k8s knowledge compiler",
  description:
    "Every compiled Kubernetes node — glossary terms, documentation pages, and concepts — with sources and relationships.",
};

const TYPES = [
  { type: "glossary", label: "Glossary terms" },
  { type: "page", label: "Documentation pages" },
  { type: "concept", label: "Concepts" },
];

export default function DocsIndex() {
  const groups = TYPES.map((t) => ({
    ...t,
    nodes: getNodesByType(t.type).sort((a, b) => a.title.localeCompare(b.title)),
  }));

  return (
    <article>
      <h1>Docs</h1>
      <p className="muted">
        The full compiled knowledge graph, indexed by node. Each page is a static,
        server-rendered knowledge card with its synthesized body, provenance, and
        typed relationships (rendered as links to the other static pages). No runtime
        LLM is involved in serving this content.
      </p>
      <p>
        <Link href="/search">Search the graph →</Link>
      </p>

      {groups.map((g) => (
        <section key={g.type} style={{ marginTop: 18 }}>
          <h2>
            {g.label} ({g.nodes.length})
          </h2>
          <ul className="idx">
            {g.nodes.map((n) => {
              const href = hrefFor(n.id);
              return (
                <li key={n.id}>
                  {href ? (
                    <Link href={href}>{n.title}</Link>
                  ) : (
                    <span>{n.title}</span>
                  )}
                  {n.summary ? <span className="muted"> — {n.summary}</span> : null}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </article>
  );
}
