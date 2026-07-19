import Link from "next/link";
import {
  getNodesByType,
  prerequisitesOf,
  unlocks,
  hrefFor,
  slugify,
} from "@/lib/knowledge.server";

export const metadata = {
  title: "Learning Paths — k8s knowledge compiler",
  description:
    "Prerequisite chains compiled from “Before you begin” sections and the concept hierarchy. Pick any concept to see what to learn first and what it unlocks.",
};

export default function LearnIndex() {
  const concepts = getNodesByType("glossary").sort((a, b) =>
    a.title.localeCompare(b.title)
  );

  return (
    <article>
      <h1>Learning Paths</h1>
      <p className="muted">
        Prerequisite chains compiled from &ldquo;Before you begin&rdquo; sections and
        the concept hierarchy. Each concept links to its static docs page, where the
        full prerequisite/unlock graph is rendered as crawlable links. This page
        itself is the server-rendered prerequisite tree — no JS required to read it.
      </p>

      <ul className="idx">
        {concepts.map((n) => {
          const href = hrefFor(n.id) || `/docs/${slugify(n.id)}/`;
          const pre = prerequisitesOf(n.id);
          const post = unlocks(n.id);
          return (
            <li key={n.id}>
              <Link href={href}>{n.title}</Link>
              {pre.length ? (
                <span className="muted">
                  {" "}
                  — understand first:{" "}
                  {pre.map((p, i) => (
                    <span key={p.id}>
                      {i > 0 ? ", " : ""}
                      <Link href={hrefFor(p.id) || `/docs/${slugify(p.id)}/`}>
                        {p.title}
                      </Link>
                    </span>
                  ))}
                </span>
              ) : null}
              {post.length ? (
                <span className="muted">
                  {" "}
                  · unlocks:{" "}
                  {post.map((p, i) => (
                    <span key={p.id}>
                      {i > 0 ? ", " : ""}
                      <Link href={hrefFor(p.id) || `/docs/${slugify(p.id)}/`}>
                        {p.title}
                      </Link>
                    </span>
                  ))}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </article>
  );
}
