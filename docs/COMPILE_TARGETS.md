# Compile Targets — The Views Produced from One Corpus

Each target is a *reader* of `dataset.json`. Adding a view never touches the ingest or
extraction pipeline — this is the core architectural promise ("one corpus → many targets").

## 1. Concept Graph
- Force-directed graph of `glossary` + `concept` nodes, edges = `references`/`related_to`.
- Interactions: hover (summary), click (detail + neighbors), filter by `tags`
  (e.g. "show everything related to RBAC" → filter nodes carrying `security`/`rbac` tags).
- Library: `react-force-graph-2d` / `cytoscape` / `d3-force`. Data: edges subset of `dataset.json`.

## 2. Decision Explorer
- Surfaces decision points: "Where should I start?", "How do I expose a Deployment?"
- Implement as a guided Q&A over the graph: each node optionally carries a
  `decision_question` (from LLM enrichment) and `prerequisite_of` edges to next steps.
- MVP: a curated entry set of 5–10 common questions → graph walks. Example seed question:
  **"How do I expose a Deployment with an Ingress?"** → Deployment → Service → Ingress path.

## 3. Resource Relationships
- Object-to-object view: Pods ↔ ReplicaSets ↔ Deployments ↔ Services ↔ Ingress, plus
  owner-references and label/selector matching.
- Derive from `api_for` + `references` + page content. Render as a relationship diagram with
  the canonical K8s ownership chain. (Maps to the conversation's "Dependency Graph".)

## 4. Version Differences
- Diff two `dataset.json` files (e.g. `v1.33` vs `v1.34`) by node `key`.
- Surfaces added/removed/changed nodes and edges → "What's new since v1.34?"
- Requires the versioned corpus (every node has `version`). Re-ingest per version to build.

## 5. API Explorer
- Browse 564 API paths / 780 types from `swagger.json`.
- Group by API group (`apps`, `core`, `rbac.authorization.k8s.io`, …). Filter by Kind.
- Cross-link each object to the docs page that explains it (`api_for` edge).
- Render field tables from `definitions`. Reuse the OpenAPI spec directly.

## 6. Learning Paths
- Generated from `prerequisite_of` edges: topological order of concepts for a topic.
- "Explain this prerequisite chain" = walk `prerequisite_of` from a target node back to roots.
- MVP: a few hand-seeded paths (e.g. "From container to production Ingress") plus the
  computed prerequisite chains.

## 7. Search (baseline, must ship)
- Full-text over node titles/bodies + glossary terms. Optional semantic (embeddings) layer.
- This is the "clearly better than keyword search" bar the conversation sets — combine
  keyword + glossary-graph expansion (query "ingress" also surfaces Service, LoadBalancer).

## 8. Bonus / future targets (documented, not MVP)
- Semantic index (embeddings) → `RESOURCE` type output.
- REST API output (serve `dataset.json` over HTTP for team tooling integration).
- Sitemap + JSON knowledge package for offline/embedded use.

## Acceptance for MVP
Ship targets **1, 2, 5, 7** solidly + a basic **3 and 6**, on the single Ingress+Deployment
task. That satisfies "one task noticeably easier" + "multiple views from one source."
