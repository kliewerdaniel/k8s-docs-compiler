# Architecture — The Compile Pipeline (IMPLEMENTED)

This document describes the **implemented** architecture. The compiler package under
`compiler/` realizes the five-phase model. For a narrative/strategy view see `PRODUCT_SPEC.md`
and `SOURCE_conversation.md`.

```
            ┌──────────────────────────────────────────────────────────────┐
            │                       CORPUS (sources)                        │
            │  kubernetes/website  content/en/docs/**   +  kubernetes        │
            │  (git clone)             (1,674 .md)      /api/openapi-spec    │
            └───────────────────────────────┬──────────────────────────────┘
                                            │  PHASE 1 — INGESTION (deterministic, no LLM)
                                            │  fetch/load, normalize Hugo shortcodes,
                                            │  parse front-matter, capture glossary refs,
                                            │  record provenance (source path + url + hash)
                                            ▼
            ┌──────────────────────────────────────────────────────────────┐
            │  RawCorpus: docs[] (body_norm + refs) + swagger{}             │
            └───────────────────────────────┬──────────────────────────────┘
                                            │  PHASE 2 — PARSING → IR (deterministic)
                                            │  build_glossary_nodes  → GLOSSARY nodes
                                            │  build_page_nodes     → PAGE + CONCEPT nodes
                                            │  build_api_nodes      → API_OBJECT + API_PATH nodes
                                            │  baseline edges: references / defines / links_to / part_of / api_for
                                            ▼
            ┌──────────────────────────────────────────────────────────────┐
            │  KnowledgeGraph (nodes + typed edges)                          │
            └───────────────────────────────┬──────────────────────────────┘
                                            │  PHASE 3 — K8s KNOWLEDGE PASSES (deterministic)
                                            │  ownership_chain  : Pod<-ReplicaSet<-Deployment ...
                                            │  api_relationships: swagger $ref edges
                                            │  rbac_graph       : Role → REQUIRES → API object
                                            │  control_plane    : kube-apiserver/controller-manager/...
                                            │  domain_concepts  : networking/storage/security tags
                                            │  kubectl_flow     : documented `kubectl apply` steps
                                            │  ── OPTIONAL AI PASS (off by default) ──
                                            │  ai_summaries / ai_prerequisites / ai_clusters
                                            │  (marks derived_by="ai:…", confidence<1.0)
                                            ▼
            ┌──────────────────────────────────────────────────────────────┐
            │  KnowledgeGraph (enriched)                                     │
            └───────────────────────────────┬──────────────────────────────┘
                                            │  PHASE 4 — OPTIMIZATION (deterministic)
                                            │  dedupe → compress → drop_orphans → build_manifest
                                            ▼
            ┌──────────────────────────────────────────────────────────────┐
            │  PHASE 5 — ARTIFACTS (deployable, no backend inference)        │
            │  dataset.json | knowledge.db (SQLite) | knowledge.gexf | index.json
            └──────────────────────────────────────────────────────────────┘
```

## Phase responsibilities

### Phase 1 — Ingestion (`ingestion.py`)
- `ingest_local`: walk a `kubernetes/website` checkout of `content/en/docs`.
- `ingest_fixtures`: load sample `.md` (tests / offline demo).
- `normalize_shortcodes`: convert Hugo shortcodes to portable Markdown and extract
  `glossary_tooltip` / `glossary_definition` references (the backbone of the concept graph).
- Provenance is captured per document (source path, canonical URL, content hash).

### Phase 2 — Parsing & IR (`parser.py`, `ir.py`)
- Glossary `*.md` → `GLOSSARY` nodes (id, title, tags, short_description).
- Every other page → `PAGE` node; H2/H3 headings → `CONCEPT` nodes (`part_of` edge).
- `swagger.json` → `API_OBJECT` + `API_PATH` nodes; pages whose title matches a Kind get
  an `api_for` edge.
- Baseline edges are emitted with `Provenance` (source + line + quote).

### Phase 3 — Knowledge passes (`k8s_passes.py`)
Deterministic, rule-based enrichment that makes this a world-class K8s compiler:
- **ownership_chain**: canonical owner-reference chain (Pod ← ReplicaSet ← Deployment …).
- **api_relationships**: edges between API objects via swagger `$ref`.
- **rbac_graph**: `Role` nodes and `REQUIRES` edges to the API objects they manage —
  directly answers "what permissions does this manifest require?".
- **control_plane**: kube-apiserver / controller-manager / scheduler / etcd / kubelet flow.
- **domain_concepts**: networking / storage / security tagging from glossary keywords.
- **kubectl_flow**: documented internal steps of `kubectl apply`.

### Phase 4 — Optimization (`optimize.py`)
- `pass_dedupe`: merge duplicate ids; drop dangling edges.
- `pass_compress`: trim oversized bodies (configurable `body_max_chars`).
- `pass_drop_orphans`: remove isolated, content-free nodes.
- `write_build_manifest` / `changed_since`: content hash enables **incremental compilation**.

### Phase 5 — Artifacts (`artifacts.py`)
- `emit_json`: full IR (`dataset.json`).
- `emit_sqlite`: `knowledge.db` with `nodes`, `edges`, and an `edge_view` join — queryable
  at runtime with **zero LLM**.
- `emit_gexf`: graph format for visualization.
- `emit_search_index`: `index.json` for client-side search.

## Intermediate Representation (`ir.py`)

- `Node`: id, type, title, summary, body, version, tags, url, meta, provenance[], confidence,
  derived_by.
- `Edge`: from_id, to_id, type, label, weight, confidence, derived_by, provenance[].
- `KnowledgeGraph`: node/edge stores + lookups + `validate()` + `ir_hash()` (content
  address → reproducibility).
- `Provenance`: source, url, line_start/end, quote — every fact is traceable.

### Node & edge types

| Node types | Edge types |
|------------|------------|
| page, glossary, api_object, api_path, concept, manifest, role, controller, operator, crd | references, defines, links_to, prerequisite_of, related_to, api_for, owns, selects, part_of, version_of, permits, requires, controls, installs |

## AI separation

`ai_passes.py` is **strictly optional** and disabled unless `--ai` / `enable_ai: true`.
- Deterministic build: no network, fully reproducible, `derived_by="deterministic"`.
- AI build: only summaries / prerequisites / clusters; outputs marked `ai:<model>` with
  `confidence < 1.0`; on failure falls back to deterministic values (never blocks build).
- The fast local path (Ollama `llama3.1:8b`) is the default; the slow path is never on the
  critical path. The AI never runs at runtime.

## Reproducibility & incremental compilation

- `ir_hash()` is a content hash of the full graph → identical inputs produce identical hashes.
- `build_manifest.json` stores the corpus hash; `changed_since()` short-circuits rebuilds when
  the corpus is unchanged (Phase 7 readiness: changed-document detection + caching).

## Alignment with compile-time AI

- Intelligence is paid **once** at build time, then served forever (cheap, deterministic).
- The compiler is infrastructure; the **artifact is the product**.
- No runtime LLM: queries are graph/SQL lookups against a built artifact.
