# k8s-docs-compiler — Frontend

A static-export Next.js (App Router) knowledge application that consumes the
compiler's `dataset.json`. **No runtime LLM** — every view is a graph/keyword
lookup over the prebuilt artifact.

## Prerequisites
- Node 18+
- A compiled `dataset.json` from the Python compiler (see repo root README).

## Build

```bash
# 1) compile the corpus (from repo root)
python -m compiler.cli compile \
    --docs-root ../corpus/kubernetes-website/content/en/docs \
    --swagger ../corpus/swagger.json --version v1.34 --out ../out_real

# 2) copy dataset.json into this app's public/ (auto-detects out_real/out/out_demo)
node scripts/copy-artifacts.js

# 3) build the static export
npm install
npm run build        # emits out/ (static HTML + JS + dataset.json)
```

## Deploy

`out/` is a fully static site. Deploy to Vercel, GitHub Pages, Netlify, or any
static host:

```bash
npx vercel deploy out --prod     # Vercel
# or:  npx serve out             # local preview
```

This mirrors the `chatgpt-compile.vercel.app` deployment pattern.

## Views (compile targets)

| Route | View |
|-------|------|
| `/` | Home: stats + view menu |
| `/graph` | Concept Graph (canvas force layout) |
| `/explore` | Decision Explorer (walk the graph to answer operational questions) |
| `/api` | API Explorer (628 API objects, OpenAPI-sourced) |
| `/relationships` | Resource Relationships (ownership chains, control plane) |
| `/learn` | Learning Paths (prerequisite chains) |
| `/rbac` | RBAC & Permissions (what a manifest requires) |
| `/search` | Full-text Search with provenance |
| `/docs` | Docs — the synthesized knowledge card for a node (open from Search/API/Graph) |

## Architecture

- `lib/store.ts` — `KnowledgeStore`: loads `dataset.json`, builds indexes and
  adjacency maps, exposes `search`, `relatedTo`, `dependsOn`, `rbacRoles`,
  `kubectlFlow`, `controlPlane`.
- `lib/useGraph.ts` — fetches `/dataset.json` at runtime (static, no server).
- `app/<route>/page.tsx` — one component per view; all client-rendered against
  the in-browser graph.
- `app/layout.tsx` — shared shell + nav + CC-BY-4.0 attribution footer.
