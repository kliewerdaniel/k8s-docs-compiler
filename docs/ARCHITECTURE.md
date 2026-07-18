# Architecture — The Compile Pipeline

Mirrors the proven `chatgpt-compile` workflow: deterministic ingest first, LLM enrichment
last, artifacts built, then deploy. The LLM is part of the **build**, never the runtime.

```
            ┌─────────────────────────────────────────────────────────────┐
            │                       CORPUS (source)                        │
            │  kubernetes/website  content/en/docs/**   +  kubernetes      │
            │  (git clone)             (1,674 .md)      /api/openapi-spec  │
            └───────────────────────────────┬─────────────────────────────┘
                                            │  (1) INGEST — deterministic, no LLM
                                            ▼
            ┌─────────────────────────────────────────────────────────────┐
            │  raw/  →  parsed/  (Markdown + front-matter + shortcodes)    │
            └───────────────────────────────┬─────────────────────────────┘
                                            │  (2) SANITY-CHECK dataset.json
                                            │      (validate BEFORE any LLM call)
                                            ▼
            ┌─────────────────────────────────────────────────────────────┐
            │  EXTRACT — concepts, glossary edges, API objects, links       │
            │  (mostly deterministic; LLM used only for summaries/labels)   │
            └───────────────────────────────┬─────────────────────────────┘
                                            │  (3) LLM enrichment — Ollama llama3.1:8b
                                            │      @ :11434  (~1.5s/call, clean JSON)
                                            ▼
            ┌─────────────────────────────────────────────────────────────┐
            │  KNOWLEDGE GRAPH  (nodes + edges)  →  dataset.json            │
            └───────────────────────────────┬─────────────────────────────┘
                                            │  (4) COMPILE TARGETS
              ┌──────────────┬──────────────┼──────────────┬───────────────┐
              ▼              ▼              ▼              ▼               ▼
        static site    JSON package    graph (GEXF/    semantic index   REST API
        (Next.js)      (knowledge)     JSON/CSV)       (embeddings)     (optional)
              └──────────────┴──────────────┴──────────────┴───────────────┘
                                            │  (5) DEPLOY — next export → Vercel
                                            ▼
                              chatgpt-compile.vercel.app  ──▶  k8s-compile.vercel.app
```

## Stage responsibilities

### (1) Ingest — deterministic, NO LLM
Clone `kubernetes/website`, walk `content/en/docs/**/*.md`, plus fetch
`kubernetes/kubernetes` `swagger.json`. Parse front-matter (YAML) and body. Normalize
Hugo shortcodes (see `INGESTION.md`). Produce `parsed/*.json`.

### (2) Sanity-check `dataset.json`
Validate the extracted structure **before** any LLM pass. This is the gating step from the
prior project: a malformed dataset must fail the build, not silently poison enrichment.
Checks: required fields present, glossary `term_id`s resolve, link targets exist or are
flagged, no empty bodies, counts within expected ranges (≈1,674 pages, 163 glossary, etc.).

### (3) Extract + LLM enrichment
Deterministic extraction handles graph edges (glossary tooltips, links, API defs). The LLM
(`llama3.1:8b` local, fast path) is used **only** for: short concept summaries, auto tags,
"prerequisite" detection where implicit, decision-tree node phrasing. Every LLM output is
schema-validated JSON. The slow path (llama.cpp 35B @ :8080, ~90s/call) is reserved for
optional high-quality summaries and is NOT on the critical path.

### (4) Knowledge graph → `dataset.json`
Single canonical artifact: nodes (page, glossary-term, api-object, task, tutorial, concept)
and typed edges (references, defines, prerequisite-of, related-to, api-for, version-of).
All compile targets read from this one graph.

### (5) Compile targets + deploy
Next.js static export consumes `dataset.json` and renders the views in `COMPILE_TARGETS.md`.
`next export` → Vercel, identical to `chatgpt-compile.vercel.app`.

## Design principles (carried from the conversation)

- **Compiler is infrastructure; the artifact is the product.** Optimize for the served
  experience, not for compiler cleverness.
- **One corpus → many targets.** Adding a view = adding a reader of `dataset.json`, not a
  new pipeline.
- **No runtime LLM.** Queries are graph/keyword/semantic-index lookups against a built
  artifact. Cheap, deterministic, inspectable.
- **Versioned corpus.** Every node carries `version` so diffing is a first-class operation.
- **Local-first, reproducible.** Deterministic ingest + local model = reproducible builds,
  no cloud dependency.

## Proven workflow mapping (from `chatgpt-compile`)

| chatgpt-compile | k8s-docs-compiler |
|-----------------|-------------------|
| ChatGPT JSON export | git clone `kubernetes/website` + `swagger.json` |
| P1 deterministic ingest | Parse MD + front-matter + shortcodes |
| sanity-check `dataset.json` | validate graph before LLM |
| Ollama `llama3.1:8b` @ :11434 | same fast path for summaries/tags |
| `next export` → Vercel | same deploy target |
| conversation → site | docs → knowledge application |
