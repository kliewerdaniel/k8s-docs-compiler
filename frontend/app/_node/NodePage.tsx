import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  resolveSlug,
  getNode,
  relatedTo,
  sectionFor,
  hrefFor,
  titleFor,
  slugify,
  nodeIdsForSection,
  STATIC_SECTIONS,
  type StaticSection,
} from "@/lib/knowledge.server";
import { renderBody } from "@/lib/render.server";

const SECTION_LABEL: Record<StaticSection, string> = {
  docs: "Docs",
  api: "API Explorer",
  rbac: "RBAC & Permissions",
  relationships: "Resource Relationships",
};

// Shared node-detail renderer used by /docs/[slug], /api/[slug], /rbac/[slug],
// /relationships/[slug]. The page in each section route calls this with its own
// `section` value. Fully server-rendered: title, body, provenance, and related
// edges (as real <a> links to the other static pages) are all in the HTML.

export function nodeStaticParams(section: StaticSection) {
  return nodeIdsForSection(section).map((id) => ({ slug: slugify(id) }));
}

export function nodeMetadata(
  section: StaticSection,
  params: { slug: string }
): Metadata {
  const id = resolveSlug(params.slug);
  const n = id ? getNode(id) : undefined;
  if (!n) return { title: "Not found — k8s knowledge compiler" };
  return {
    title: `${n.title} — k8s knowledge compiler`,
    description: n.summary || `${n.title} (${n.type})`,
  };
}

function JsonLd({ n }: { n: ReturnType<typeof getNode> }) {
  if (!n) return null;
  const sameAs = (n.provenance || [])
    .map((p) => p.url)
    .filter((u): u is string => Boolean(u));
  const data = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    name: n.title,
    headline: n.title,
    description: n.summary || (n.body ? n.body.slice(0, 240) : n.type),
    about: "Kubernetes",
    keywords: (n.tags || []).join(", "),
    ...(sameAs.length ? { sameAs } : {}),
    isPartOf: {
      "@type": "DataCatalog",
      name: "Kubernetes Knowledge Compiler",
      url: "https://k8s-docs-compiler.vercel.app/",
    },
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export default function NodePage({
  section,
  params,
}: {
  section: StaticSection;
  params: { slug: string };
}) {
  const id = resolveSlug(params.slug);
  if (!id) notFound();
  const n = getNode(id);
  if (!n) notFound();
  if (sectionFor(n.type) !== section) notFound();

  const related = relatedTo(n.id, 25);
  const label = SECTION_LABEL[section];

  return (
    <article>
      <JsonLd n={n} />
      <div className="breadcrumb">
        <Link href="/">k8s</Link> / <Link href={`/${section}/`}>{label}</Link> /{" "}
        <span>{n.title}</span>
      </div>

      <h1>
        {n.title} <span className="mono">[{n.type}]</span>
        {n.derived_by.startsWith("ai:") ? (
          <span className="tag" title="Synthesized at compile time from source quotes">
            ai-synthesized · conf {n.confidence}
          </span>
        ) : (
          <span className="tag">deterministic</span>
        )}
      </h1>

      {n.summary ? <p className="muted">{n.summary}</p> : null}

      <div className="row" style={{ flexWrap: "wrap" }}>
        {n.tags.map((t) => (
          <span key={t} className="tag">
            {t}
          </span>
        ))}
      </div>

      {n.body ? (
        <div className="card" style={{ marginTop: 12, fontSize: 14, lineHeight: 1.6 }}>
          {renderBody(n.body)}
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 12 }}>
          {n.summary || "No synthesized body available — see sources and related nodes below."}
        </p>
      )}

      {n.provenance?.length ? (
        <div style={{ marginTop: 10 }}>
          <h2>Sources</h2>
          {n.provenance.slice(0, 4).map((p, i) => (
            <div key={i} className="prov">
              {p.source}
              {p.url ? (
                <>
                  {" · "}
                  <a href={p.url} target="_blank" rel="noreferrer">
                    doc
                  </a>
                </>
              ) : null}
              {p.quote ? (
                <>
                  {" — "}&ldquo;{p.quote.slice(0, 240)}&rdquo;
                </>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <h2>Related ({related.length})</h2>
      {related.length ? (
        <div>
          {related.map((e, i) => {
            const other = e.from_id === n.id ? e.to_id : e.from_id;
            const href = hrefFor(other);
            const t = titleFor(other);
            return (
              <div key={i} className="edge">
                <span className="etype">{e.type}</span>{" "}
                {href ? <Link href={href}>{t}</Link> : <strong>{t}</strong>}
                {e.label ? <span className="muted"> — {e.label}</span> : null}
                <span className="mono"> conf={e.confidence}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="muted">No recorded relationships.</p>
      )}

      <p style={{ marginTop: 28 }}>
        <Link href={`/${section}/`}>← all {label}</Link>
      </p>
    </article>
  );
}
