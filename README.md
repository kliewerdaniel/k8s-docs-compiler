# k8s-docs-compiler

> **A Kubernetes Knowledge Compiler that transforms the Kubernetes ecosystem into a
> static, queryable knowledge graph.**

`k8s-docs-compiler` applies **compile-time AI** to the Kubernetes documentation: it moves
intelligence out of runtime query-time computation and into a *build step*, producing
**deterministic, inspectable, versioned** knowledge artifacts (JSON / SQLite / GEXF) that
are deployable **without any backend inference**.

No chatbot. A compiler for knowledge.

---

## Why

Kubernetes documentation is large (1,674 English pages, 163 glossary terms, 564 API paths /
780 types), deeply interconnected, constantly changing, and hard for newcomers to navigate.
This compiler turns that corpus into a knowledge graph you can *query, diff, and ship* — and
every fact is traceable back to its source document.

## What it produces

| Artifact | Purpose | Runtime LLM? |
|----------|---------|--------------|
| `dataset.json` | Full IR (nodes + typed edges + provenance + stats) | No |
| `knowledge.db` | SQLite — queryable knowledge base, no server | No |
| `knowledge.gexf` | Graph exchange format (Gephi / cytoscape) | No |
| `index.json` | Lightweight search index | No |
| `build_manifest.json` | Content hash for incremental compilation | No |

## The five compiler phases

```
  SOURCES            PHASE 1          PHASE 2             PHASE 3                PHASE 4         PHASE 5
kubernetes/website ─▶ INGEST ─▶ PARSE/IR ─▶ KNOWLEDGE PASSES ─▶ OPTIMIZE ─▶ ARTIFACTS
(content/en/docs  +   fetch &      front-matter,    glossary edges,        dedupe,        JSON / SQLite /
 swagger.json)       normalize,     shortcodes,      API objects, RBAC,     compress,      GEXF / index
                   provenance      concepts,        ownership, control-     drop orphans
                                  api paths        plane, kubectl flow
                                                       │
                                  OPTIONAL AI PASS (off by default): summaries, prerequisites, clusters
```

Every fact carries `provenance` (source doc + line + quote) and a `confidence` score.
Deterministic passes produce `confidence=1.0`; optional AI passes mark `derived_by="ai:…"`
and lower confidence. **The build is reproducible: same input → identical `ir_hash`.**

## Quick start

```bash
pip install -r requirements.txt

# 1) Offline demo (bundled fixtures, no K8s repo needed):
python -m compiler.cli demo --out out
#    -> out/dataset.json, out/knowledge.db, out/knowledge.gexf, out/index.json

# 2) Query the artifact (no LLM at runtime):
python -m compiler.cli query "What resources are related to Deployments?" --db out/knowledge.db
python -m compiler.cli query "What permissions does this manifest require?" --db out/knowledge.db
python -m compiler.cli query "What happens internally when kubectl apply runs?" --db out/knowledge.db

# 3) Compile the real corpus (needs a checkout + swagger):
git clone --depth 1 https://github.com/kubernetes/website.git
curl -sL https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json -o swagger.json
python -m compiler.cli compile \
    --docs-root kubernetes/website/content/en/docs \
    --swagger swagger.json --version v1.34 --out out

# 4) Validate / diff versions:
python -m compiler.cli validate out/dataset.json
python -m compiler.cli diff out/v1.33/dataset.json out/v1.34/dataset.json
```

## AI synthesis pass (compile-time, opt-in)

The deterministic build extracts a *graph of fragments* (titles, short summaries,
extracted quotes). To turn that scaffolding into a **readable knowledge resource**,
opt into the AI synthesis pass. It runs **once, at compile time**, on a local
inference endpoint — never at runtime.

```bash
python -m compiler.cli compile \
    --docs-root kubernetes/website/content/en/docs \
    --swagger swagger.json --version v1.34 --out out \
    --ai --ai-passes synthesis \
    --ai-url http://localhost:11434 --ai-model llama3.1:8b
```

What it does:
- For each glossary / API-object / page node that lacks a substantial body, it
  sends the node's **extracted source quotes** to the local model and asks for a
  structured knowledge card (overview, why-it-matters, key facts, pitfalls, related).
- The card is stored as the node `body` (rendered in the frontend **Docs** view) and
  a one-line `summary`. Nodes that already have rich deterministic content are skipped.
- Synthesis is **batched** (N cards per model call) and **cached by content hash**, so
  re-runs are free and reproducible.
- Every synthesized fact is tagged `derived_by="ai:<model>"` with `confidence < 1.0`
  and remains tied to its source provenance — it explains the docs, it does not invent
  them.

Pluggable passes: `synthesis`, `prerequisites`, `clusters` — toggle individually
(`--ai-passes synthesis,prerequisites`) or run all (`--ai`). Different use cases add or
remove LLM calls without touching the deterministic core. The endpoint is
endpoint-agnostic: OpenAI-compatible (`/v1/chat/completions`, e.g. llama.cpp on :8080)
or Ollama (`/api/generate`). A thinking model that emits only `reasoning_content` is
handled via a fallback.

## CLI

| Command | Description |
|---------|-------------|
| `demo` | Compile bundled fixtures → `out/` (offline) |
| `compile` | Compile from a `kubernetes/website` checkout + swagger |
| `validate` | Check graph integrity + provenance of a `dataset.json` |
| `query` | Answer a question against the SQLite artifact (no LLM) |
| `diff` | Compare two builds (version differences) |

## Principles

- **Intelligence at build time, not query time.** The LLM (if used) runs only during
  compilation. Runtime queries are graph/SQL lookups — cheap, deterministic, inspectable.
- **Traceable.** Every node and edge records its source document, line, and supporting quote.
- **Versioned.** Each node carries a `version`; diff two builds to see what changed.
- **Deterministic by default.** AI passes are opt-in (`--ai`); the default build is fully
  reproducible and needs no network.

## Project layout

```
compiler/            The compile-time knowledge compiler (Python)
  ir.py            Intermediate Representation (Node/Edge/KnowledgeGraph)
  config.py        Configuration system (defaults < yaml < env < CLI)
  util.py          Hashing, front-matter, Hugo shortcode normalization, cache
  ingestion.py     Phase 1 — fetch/load sources + provenance
  parser.py        Phase 2 — parse → IR (glossary, pages, concepts, api)
  k8s_passes.py    Phase 3 — K8s-specific knowledge (ownership, RBAC, control-plane, ...)
  optimize.py      Phase 4 — dedupe, compress, drop orphans, manifest
  artifacts.py     Phase 5 — JSON / SQLite / GEXF / search index / web
  web.py           Standalone static HTML explorer (no build step)
  ai_passes.py     Optional AI-assisted passes (clearly separated, off by default)
  compiler.py      Orchestrator
  cli.py           Command-line interface (compile/validate/query/diff/demo)
  tests/           Unit + integration tests (pytest)
fixtures/          Sample K8s docs + minimal swagger (offline demo + tests)
corpus/            Cloned kubernetes/website + fetched swagger.json (git-ignored; build input)
frontend/          Next.js static-export app consuming dataset.json (the deployable product)
  app/             Routes: / graph explore api relationships learn rbac search about
  lib/             KnowledgeStore query engine + types (no runtime LLM)
  scripts/         copy-artifacts.js (dataset.json -> public/)
docs/              Strategy, research, and architecture narrative
out_real/          Example build from the real corpus (git-ignored)
```

## Real-corpus results (measured)

Compiling the full Kubernetes documentation (`v1.34`, 1,632 docs after excluding
`contribute/`, 163 glossary terms, swagger with 628 API objects / 564 paths):

| Metric | Value |
|--------|-------|
| Build time | ~9 s (single pass, deterministic) |
| Nodes | 7,021 (1,411 pages, 4,800 concepts, 628 api_objects, 162 glossary, 15 roles, 5 controllers) |
| Edges | 10,228 (7,657 part_of, 949 related_to, 835 references, 717 api_for, …) |
| Validation | clean (no dangling edges, confidence in range) |
| Artifacts | `dataset.json`, `knowledge.db` (SQLite), `knowledge.gexf`, `knowledge.html`, `index.json` |

The compiled `dataset.json` drives both the CLI `query` engine and the Next.js frontend.

## Testing

```bash
python -m pytest compiler/tests -q
```

Tests prove: documents compile, artifacts are reproducible (`ir_hash` stable),
source provenance is preserved, and graph relationships are valid (no dangling edges,
confidence in range).

## License & attribution

The Kubernetes documentation is **CC-BY-4.0**. Any deployment built from it must attribute
Kubernetes and link to source pages (each node carries its `url`).
