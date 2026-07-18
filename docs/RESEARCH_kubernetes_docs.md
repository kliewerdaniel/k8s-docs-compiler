# Research: The Kubernetes Documentation Corpus

Authoritative facts gathered 2026-07-18 from `kubernetes/website` (branch `main`) and the
live docs site. These numbers are the basis for sizing the compiler and its build targets.

## 1. Where the docs live

- **Repository:** `https://github.com/kubernetes/website`
- **Docs content path:** `content/en/docs/` (Hugo-based static site, built with Goldmark)
- **Source of truth for ingestion:** clone the repo and read `content/en/docs/**/*.md`
- **Live site:** `https://kubernetes.io/docs/`
- **Multilingual:** `content/<lang>/docs/...` (e.g. `bn`, `zh`, …). English is the MVP target.

## 2. Corpus scale (English, `content/en/docs`)

| Section | Markdown pages | Notes |
|---------|---------------:|-------|
| **reference** | 1,164 | Largest section |
| &nbsp;&nbsp;├ kubernetes-api | 157 | One page per API group/version |
| &nbsp;&nbsp;├ kubectl | 120 | Generated command reference |
| &nbsp;&nbsp;├ access-authn-authz | 19 | Includes RBAC |
| &nbsp;&nbsp;├ labels-annotations-taints | 2 | |
| **tasks** | 222 | How-to procedures |
| **concepts** | 176 | Conceptual explanations (workloads/: 36) |
| **tutorials** | 43 | Guided walkthroughs |
| **setup** | 22 | Install/cluster bootstrap |
| **contribute** | 42 | Docs contributor guide (NOT user-facing K8s knowledge) |
| **home** | 2 | Landing/index |
| **doc-contributor-tools** | 1 | |
| **TOTAL** | **1,674** | Excludes contributor tooling if desired |

## 3. Glossary — the semantic graph source

- **163 glossary terms** at `content/en/docs/reference/glossary/*.md`.
- Each term file format:

```markdown
---
title: Pod
id: pod
full_link: /docs/concepts/workloads/pods/
short_description: >
  A Pod represents a set of running containers in your cluster.
aka:
tags:
- core-object
- fundamental
---
 The smallest and simplest Kubernetes object. A Pod represents a set of running
 {{< glossary_tooltip text="containers" term_id="container" >}} on your cluster.
<!--more-->
...
```

- `id` is the canonical node key. `tags` (e.g. `core-object`, `fundamental`) are useful
  for clustering/filtering the concept graph.
- This is the **controlled vocabulary** of Kubernetes. The compiled Concept Graph should
  be anchored on these 163 terms + the page-level concepts.

## 4. The semantic edges: `glossary_tooltip` shortcode

Every doc page references glossary terms inline via:

```
{{< glossary_tooltip text="pod" term_id="pod" >}}
{{< glossary_tooltip text="Service" term_id="service" >}}
```

- `term_id` points to a glossary node → **this is a direct, extractable edge** from a page
  (or another concept) to a glossary term.
- Sample of 60 concept/reference files contained **180 `glossary_tooltip`** references and
  **16 `glossary_definition`** embeds — confirming the graph is densely cross-linked and
  machine-extractable.
- `glossary_definition term_id="kube-apiserver" length="all"` inlines a term's definition
  into a page → treat as another edge + inline content.

## 5. Document format details (critical for the parser)

### Front-matter (YAML between `---`)
Common keys: `title`, `weight` (nav order), `no_list`, `description`, `toc_hide`,
`card`, `slug`, `reviewers`. Glossary adds: `id`, `full_link`, `short_description`,
`aka`, `tags`.

### Hugo shortcodes used in K8s docs
`glossary_tooltip`, `glossary_definition`, `figure`, `details`, `mermaid`, `table`,
`tabs`, `note`, `warning`, `caution`, `feature`, `param`, `highlight`, `comment`,
`api`, `skew`. The compiler must **strip or normalize** these to render clean Markdown/HTML.
Priorities:
- `glossary_tooltip` / `glossary_definition` → **extract as graph edges + inline defs** (highest value).
- `mermaid` → render to SVG or extract as a diagram node.
- `figure` → image reference.
- `note/warning/caution` → styled callouts.
- `tabs/table` → structured content.

### Intra-doc links
Standard Markdown links to `/docs/...` and `/docs/<version>/...` paths → **page-to-page
edges** for the graph and for "prerequisite chain" computation.

## 6. Kubernetes API (OpenAPI / swagger) — the API Explorer source

- **Spec URL:** `https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json`
  (OpenAPI v2; ~4.1 MB; OpenAPI v3 path returns 404 at this location).
- **Scale:** 564 API paths, 780 type definitions.
- **Top-level groups:** `/apis` (445 paths), `/api` (114 paths), plus `/logs`,
  `/.well-known`, `/openid`, `/version`.
- This is **generated** and should be ingested separately from prose, then cross-linked to
  the docs (e.g. a Deployment page ↔ the `apps/v1.Deployment` definition).

## 7. Versioning — the Version Differences source

- `kubernetes.io/docs` is versioned; the version switcher exposes many minor versions
  (observed `v1.86` … `v1.99` in the live switcher; exact current set changes per release).
- Each version corresponds to a git tag/branch of `kubernetes/website`.
- **Implication:** the corpus is versioned. A `version` field on every node enables the
  "What's new since v1.34?" compile target via diffing node sets / front-matter between
  two ingested versions.
- "Supported doc versions" page: `https://kubernetes.io/docs/home/supported-doc-versions/`

## 8. Why this corpus is a strong demonstration

- It is one of the **hardest** doc sets to navigate (the user's own words), so success is
  credible and differentiating.
- It is **open and scrapeable** (single public repo, permissive license) — no auth, no ToS
  wall, ideal for a deterministic compile.
- It is **structured enough** (glossary IDs, OpenAPI, front-matter) that a graph can be
  extracted *without* heavy LLM use — keeping the fast, local, cheap compile path.

## 9. Ingestion caution

- Do **not** ingest `contribute/` as user-facing K8s knowledge (it is docs-process docs).
  Either drop it or tag it `meta`.
- Respect license/attribution in the deployed app (K8s docs are CC-BY-4.0; surface a
  footer/attribution and link back to source pages).
