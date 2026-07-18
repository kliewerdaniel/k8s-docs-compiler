# Diagrams

## 1. Compile-time pipeline (build)

```
 ┌─────────────────────────┐
 │ kubernetes/website       │  1,674 .md (content/en/docs)
 │ kubernetes/kubernetes    │  swagger.json (564 paths / 780 types)
 └────────────┬────────────┘
              │  PHASE 1 INGEST
              │  - load + normalize Hugo shortcodes
              │  - capture glossary_tooltip refs
              │  - provenance (source, url, hash)
              ▼
 ┌─────────────────────────┐
 │ RawCorpus                │  docs[] + swagger{}
 └────────────┬────────────┘
              │  PHASE 2 PARSE → IR
              │  - glossary → GLOSSARY
              │  - pages    → PAGE + CONCEPT
              │  - swagger  → API_OBJECT + API_PATH
              │  - baseline edges (references/links_to/api_for)
              ▼
 ┌─────────────────────────┐
 │ KnowledgeGraph (base)    │
 └────────────┬────────────┘
              │  PHASE 3 KNOWLEDGE PASSES
              │  ownership · api_relationships · rbac · control_plane
              │  domain_concepts · kubectl_flow
              │  [optional AI: summaries/prereqs/clusters — off by default]
              ▼
 ┌─────────────────────────┐
 │ KnowledgeGraph (rich)    │
 └────────────┬────────────┘
              │  PHASE 4 OPTIMIZE
              │  dedupe · compress · drop_orphans · manifest
              ▼
 ┌─────────────────────────┐
 │ PHASE 5 ARTIFACTS        │  dataset.json
 │ (no backend inference)   │  knowledge.db  (SQLite)
 │                          │  knowledge.gexf
 │                          │  index.json
 └────────────┬────────────┘
              ▼
        deploy (static) ──▶  Vercel / any static host
```

## 2. Runtime query (no LLM)

```
 user question
      │
      ▼
 ┌─────────────────────────┐
 │ query CLI / web frontend │  (Next.js static export)
 └────────────┬────────────┘
              │  SQL over knowledge.db  (or JSON graph walk)
              ▼
 ┌─────────────────────────┐
 │ deterministic answer    │  nodes + typed edges + provenance
 │ (cheap, reproducible)   │
 └────────────┬────────────┘
              ▼
   "What resources are related to Deployments?"
   → Deployment ─references→ Pod, Service, Ingress
   "What permissions does this manifest require?"
   → Role:deployments ─requires→ Deployment (verbs: get,list,...,delete)
   "What happens internally when kubectl apply runs?"
   → kubectl → kube-apiserver → etcd → controllers → kubelet
```

## 3. Concept graph (excerpt)

```
                 ┌──────────┐
                 │  Pod     │◄── owns ── ReplicaSet ◄── owns ── Deployment
                 └────┬─────┘
        references   │   references
              ┌──────┴──────┐
              ▼             ▼
        ┌──────────┐  ┌──────────┐
        │ Service  │  │ Container│
        └────┬─────┘  └──────────┘
     references │
              ▼
        ┌──────────┐  selects  ┌──────────┐
        │ Ingress  │──────────▶│  Pods    │
        └──────────┘           └──────────┘
              │
        requires (RBAC)  Role:deployments ──▶ Deployment
```
