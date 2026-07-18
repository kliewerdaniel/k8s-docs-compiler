"use client";

import { useGraph } from "@/lib/useGraph";
import Link from "next/link";

const VIEWS = [
  { href: "/graph", title: "Concept Graph", desc: "Force-directed graph of Kubernetes concepts and their relationships." },
  { href: "/explore", title: "Decision Explorer", desc: "Answer 'How do I expose a Deployment with an Ingress?' by walking the compiled graph." },
  { href: "/api", title: "API Explorer", desc: "Browse 628 API objects and 564 API paths from the OpenAPI spec." },
  { href: "/relationships", title: "Resource Relationships", desc: "Ownership chains and dependencies between Kubernetes resources." },
  { href: "/learn", title: "Learning Paths", desc: "Prerequisite chains — 'what should I understand before X?'" },
  { href: "/rbac", title: "RBAC & Permissions", desc: "What permissions does a given manifest require?" },
  { href: "/search", title: "Search", desc: "Full-text search across every compiled node, with provenance." },
];

export default function Home() {
  const { graph, error } = useGraph();
  const s = graph?.stats;
  return (
    <>
      <h1>Kubernetes Knowledge Compiler</h1>
      <p className="muted">
        A static, queryable knowledge graph compiled from the Kubernetes documentation.
        Intelligence is computed <strong>once, at build time</strong>; the app serves it
        deterministically with <strong>no runtime LLM</strong>. Every fact links back to
        its source.
      </p>

      {error && <div className="warning">Could not load dataset.json: {error}</div>}

      {s && (
        <div className="stat-row" style={{ margin: "16px 0" }}>
          <div><div className="stat">{s.pages}</div><div className="muted">pages</div></div>
          <div><div className="stat">{s.glossary}</div><div className="muted">glossary terms</div></div>
          <div><div className="stat">{s.api_objects}</div><div className="muted">API objects</div></div>
          <div><div className="stat">{s.edges}</div><div className="muted">relationships</div></div>
          <div><div className="stat">{s.build_seconds}s</div><div className="muted">build time</div></div>
        </div>
      )}

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
    </>
  );
}
