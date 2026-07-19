// Server-safe markdown/body + provenance renderers.
//
// These are plain functions (NO "use client" directive) so they can be used
// inside async server components that statically render node content. They
// mirror the client-side helpers in lib/components.tsx but deliberately avoid
// React client hooks. `dangerouslySetInnerHTML` works identically on the server.

import type { Provenance } from "./types";

// Minimal markdown: **bold**, "- " bullets, blank-line paragraphs.
// Escape HTML first, then apply **bold** — no raw model HTML is trusted.
export function renderBody(body: string) {
  const blocks = body.split(/\n\n+/);
  return (
    <>
      {blocks.map((blk, bi) => {
        const trimmed = blk.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith("- ")) {
          const items = trimmed.split(/\n- /).map((s) => s.replace(/^- /, ""));
          return (
            <ul key={bi}>
              {items.map((it, i) => (
                <li key={i} dangerouslySetInnerHTML={{ __html: inline(it) }} />
              ))}
            </ul>
          );
        }
        return <p key={bi} dangerouslySetInnerHTML={{ __html: inline(trimmed) }} />;
      })}
    </>
  );
}

function inline(s: string): string {
  const esc = s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

export function Prov({ p }: { p?: Provenance }) {
  if (!p) return null;
  return (
    <div className="prov">
      source: {p.source}
      {p.url ? (
        <>
          {" · "}
          <a href={p.url} target="_blank" rel="noreferrer">
            doc
          </a>
        </>
      ) : null}
      {p.quote ? <> — &ldquo;{p.quote.slice(0, 200)}&rdquo;</> : null}
    </div>
  );
}
