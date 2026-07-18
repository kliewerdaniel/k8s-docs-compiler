# Frontend — Next.js Knowledge Application

Mirrors `chatgpt-compile.vercel.app`: a **Next.js static export** (no server runtime) that
consumes `dataset.json` at build time. No LLM at runtime.

## 1. Stack
- **Next.js** (App Router or Pages Router — match `chatgpt-compile` for consistency).
- **Static export** (`next export` / `output: "export"`) → pure static hosting on Vercel.
- **TypeScript**, React 18+.
- Graph rendering: `react-force-graph-2d` (Concept Graph) or `cytoscape`.
- Styling: Tailwind (or reuse the chatgpt-compile theme for brand consistency).
- Search: client-side index (`flexsearch` / `minisearch`) over `dataset.json` nodes.

## 2. Build-time data injection
- Place `dataset.json` in `public/` or import via a generated TS module at build.
- All pages are statically generated from nodes; `getStaticPaths` over node ids.
- No API routes needed for MVP (optional REST API is a future target).

## 3. Routes
```
/                     landing: menu of views (Concept Graph, Decision Explorer, …)
/graph                Concept Graph (interactive)
/decide               Decision Explorer (guided Q&A)
/api                  API Explorer (grouped, filterable)
/search               Search (or global search box in header)
/resource/[id]        Any node detail (page/glossary/api_object/concept)
/learn/[topic]        Learning Path
/versions             Version Differences (future)
```

## 4. Key components
- `KnowledgeGraph.tsx` — force-directed graph from `edges` (filter by `type`/`tags`).
- `NodeDetail.tsx` — renders a node: title, summary, body (HTML from shortcode-normalized
  Markdown), neighbor list, outgoing/incoming edges.
- `DecisionWalk.tsx` — walks `prerequisite_of` / `decision_question` to answer a seed question.
- `ApiExplorer.tsx` — groups `api_object` nodes, field tables, doc cross-links.
- `SearchBox.tsx` — keyword + glossary-graph expansion.
- `Header.tsx` — view switcher + attribution footer (CC-BY-4.0, link to source pages).

## 5. Content rendering
- Store each page body as HTML (post shortcode-normalization, see `INGESTION.md`).
- Render with a sanitized HTML component (e.g. `dangerouslySetInnerHTML` after sanitize, or
  `react-markdown` if body kept as MD).
- Glossary tooltips become `<a data-gloss="pod">` that open the glossary node detail inline.

## 6. Performance budget
- `dataset.json` for full K8s corpus will be large (1,674 pages + bodies). For MVP, ship a
  **trimmed** `dataset.json`: nodes carry summaries + edge lists, full bodies lazy-loaded or
  split per-node (e.g. `public/bodies/<id>.json`). Keeps initial bundle small.
- Measure and report: artifact size, query latency (see `METRICS_CASE_STUDY.md`).

## 7. Reuse from chatgpt-compile
- Copy the deploy/build config, theme, and `dataset.json` loader pattern.
- Same `next export` → Vercel flow. Different data shape (graph vs conversation), same plumbing.
