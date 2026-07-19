import Link from "next/link";
import {
  startHere,
  prerequisitesOf,
  unlocks,
  hrefFor,
  slugify,
} from "@/lib/knowledge.server";

export const metadata = {
  title: "Start Here — k8s knowledge compiler",
  description:
    "A guided, prerequisite-ordered onboarding path through Kubernetes, compiled from the documentation.",
};

export default function StartPage() {
  const path = startHere(12);

  return (
    <article>
      <h1>Start Here</h1>
      <p className="muted">
        A guided onboarding path through Kubernetes, ordered so you learn the
        foundational concepts first. Each step builds on what came before it
        (prerequisites were inferred from the documentation at compile time). This
        page is server-rendered — every concept and its learning path is in the HTML.
      </p>

      <h2>The path</h2>
      <ol className="startpath">
        {path.map((n, i) => {
          const href = hrefFor(n.id) || `/docs/${slugify(n.id)}/`;
          const prereqs = prerequisitesOf(n.id);
          const post = unlocks(n.id);
          return (
            <li key={n.id}>
              <Link href={href}>{i + 1}. {n.title}</Link>
              {n.summary ? <span className="muted"> — {n.summary}</span> : null}
              {prereqs.length ? (
                <div className="muted" style={{ marginLeft: 12 }}>
                  understand first:{" "}
                  {prereqs.map((p, j) => (
                    <span key={p.id}>
                      {j > 0 ? ", " : ""}
                      <Link href={hrefFor(p.id) || `/docs/${slugify(p.id)}/`}>
                        {p.title}
                      </Link>
                    </span>
                  ))}
                </div>
              ) : null}
              {post.length ? (
                <div className="muted" style={{ marginLeft: 12 }}>
                  unlocks:{" "}
                  {post.map((p, j) => (
                    <span key={p.id}>
                      {j > 0 ? ", " : ""}
                      <Link href={hrefFor(p.id) || `/docs/${slugify(p.id)}/`}>
                        {p.title}
                      </Link>
                    </span>
                  ))}
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>

      <p style={{ marginTop: 18 }}>
        <Link href="/docs/">Browse all compiled docs →</Link>
      </p>
    </article>
  );
}
