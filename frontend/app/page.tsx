import Link from "next/link";
import { getGraph, getNodesByType } from "@/lib/knowledge.server";

export const metadata = {
  title: "Kubernetes Knowledge Compiler",
  description:
    "A static, queryable knowledge graph compiled from the Kubernetes documentation — a compile-time AI knowledge artifact with no runtime LLM.",
};

const VIEWS = [
  { href: "/graph", title: "Concept Graph", desc: "Force-directed graph of Kubernetes concepts and their relationships." },
  { href: "/explore", title: "Decision Explorer", desc: "Walk the compiled graph to answer operational questions." },
  { href: "/api", title: "API Explorer", desc: "Browse API objects and API paths from the OpenAPI spec." },
  { href: "/relationships", title: "Resource Relationships", desc: "Ownership chains and dependencies between Kubernetes resources." },
  { href: "/learn", title: "Learning Paths", desc: "Prerequisite chains — 'what should I understand before X?'" },
  { href: "/rbac", title: "RBAC & Permissions", desc: "What permissions does a given manifest require?" },
  { href: "/search", title: "Search", desc: "Full-text search across every compiled node, with provenance." },
  { href: "/docs", title: "Docs", desc: "The synthesized knowledge card for any node — readable documentation with sources." },
  { href: "/start", title: "Start Here", desc: "A guided, prerequisite-ordered onboarding path through Kubernetes." },
];

export default function Home() {
  const g = getGraph();
  const s = g.stats;
  const aiCount = g.nodes.filter((n) => n.derived_by.startsWith("ai:")).length;

  return (
    <article>
      <h1>Kubernetes Knowledge Compiler</h1>
      <p className="muted">
        A static, queryable knowledge graph compiled from the Kubernetes documentation.
        Intelligence is computed <strong>once, at build time</strong>; the app serves it
        deterministically with <strong>no runtime LLM</strong>. Every fact links back to
        its source.
      </p>

      <div className="stat-row" style={{ margin: "16px 0" }}>
        <div><div className="stat">{s.pages}</div><div className="muted">pages</div></div>
        <div><div className="stat">{s.glossary}</div><div className="muted">glossary terms</div></div>
        <div><div className="stat">{s.api_objects}</div><div className="muted">API objects</div></div>
        <div><div className="stat">{s.edges}</div><div className="muted">relationships</div></div>
        <div><div className="stat">{s.build_seconds}s</div><div className="muted">build time</div></div>
        <div><div className="stat">{aiCount}</div><div className="muted">AI-synthesized</div></div>
      </div>

      <h2>Views (compile targets)</h2>
      <div className="grid2">
        {VIEWS.map((v) => (
          <Link key={v.href} href={v.href} style={{ textDecoration: "none" }}>
            <div className="card" style={{ height: "100%" }}>
              <strong style={{ fontSize: 15 }}>{v.title}</strong>
              <div className="muted" style={{ marginTop: 4 }}>{v.desc}</div>
            </div>
          </Link>
        ))}
      </div>

      <h2 style={{ marginTop: 18 }}>Corpus at a glance</h2>
      <ul className="idx">
        <li><Link href="/docs/">{getNodesByType("glossary").length + getNodesByType("page").length + getNodesByType("concept").length} docs nodes (glossary + pages + concepts)</Link></li>
        <li><Link href="/api/">{getNodesByType("api_object").length} API objects · {getNodesByType("api_path").length} API paths</Link></li>
        <li><Link href="/rbac/">{getNodesByType("role").length} RBAC roles</Link></li>
        <li><Link href="/relationships/">{getNodesByType("controller").length} control-plane components</Link></li>
        <li><Link href="/llms.txt">llms.txt — machine-readable index</Link></li>
        <li><Link href="/dataset.json">dataset.json — full structured graph</Link></li>
        <li><Link href="/sitemap.xml">sitemap.xml — every static page</Link></li>
      </ul>
    </article>
  );
}
