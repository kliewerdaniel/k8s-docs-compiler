import Link from "next/link";
import { getNodesByType, slugify, hrefFor } from "@/lib/knowledge.server";

export const metadata = {
  title: "API Explorer — k8s knowledge compiler",
  description:
    "Every Kubernetes API object and API path extracted from the OpenAPI specification, cross-linked to the docs that explain them.",
};

export default function ApiIndex() {
  const objects = getNodesByType("api_object").sort((a, b) =>
    a.title.localeCompare(b.title)
  );
  const paths = getNodesByType("api_path").sort((a, b) =>
    a.title.localeCompare(b.title)
  );

  const groups = Array.from(
    new Set(objects.map((o) => (o.meta?.group as string) || "core"))
  ).sort();

  return (
    <article>
      <h1>API Explorer</h1>
      <p className="muted">
        {objects.length} API objects and {paths.length} API paths, extracted from the
        OpenAPI specification and cross-linked to the docs that explain them. Each
        object has a static page with its fields and related docs.
      </p>
      <p>
        <Link href="/search">Search the graph →</Link>
      </p>

      <h2>API objects by group</h2>
      {groups.map((grp) => {
        const objs = objects.filter(
          (o) => (o.meta?.group as string) || "core" === grp
        );
        return (
          <section key={grp} style={{ marginTop: 12 }}>
            <h3>
              {grp} ({objs.length})
            </h3>
            <ul className="idx">
              {objs.map((o) => {
                const href = hrefFor(o.id);
                const ver = (o.meta?.version as string) || "";
                return (
                  <li key={o.id}>
                    {href ? (
                      <Link href={href}>
                        {o.title}{" "}
                        <span className="mono">
                          {grp}/{ver}
                        </span>
                      </Link>
                    ) : (
                      <span>{o.title}</span>
                    )}
                    {o.summary ? (
                      <span className="muted"> — {o.summary.slice(0, 120)}</span>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}

      <h2>API paths ({paths.length})</h2>
      <ul className="idx">
        {paths.map((p) => {
          const href = hrefFor(p.id);
          return (
            <li key={p.id}>
              {href ? <Link href={href}>{p.title}</Link> : <span>{p.title}</span>}
              {p.summary ? <span className="muted"> — {p.summary}</span> : null}
            </li>
          );
        })}
      </ul>
    </article>
  );
}
