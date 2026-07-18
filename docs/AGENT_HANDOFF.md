# Agent Handoff — Build the MVP Without Further Clarification

This file lets a coding agent or team build the MVP from `dataset.json` → deployed Vercel app
using only these docs. It assumes the chatgpt-compile pipeline already exists and is the
reference implementation.

## Context the agent must hold
- We compile Kubernetes docs into an interactive Next.js knowledge app (compile-time AI).
- Reuse the `chatgpt-compile` workflow: deterministic ingest → sanity-check `dataset.json` →
  local LLM (`llama3.1:8b` @ `:11434`) enrichment → `next export` → Vercel.
- **Build the explorer, not research features.** No RL/agents/autonomy in MVP.
- The single success question: *"How do I expose a Deployment with an Ingress?"* must be
  answerable faster than kubernetes.io.

## Step-by-step

### A. Ingest (deterministic, no LLM)
1. `git clone --depth 1 --branch <v1.34 tag> https://github.com/kubernetes/website.git`.
2. Walk `content/en/docs/**/*.md` (skip `contribute/` or tag `meta`).
3. Parse front-matter (YAML) + body. Capture:
   - `glossary` nodes from `reference/glossary/*.md` (`id`, `title`, `short_description`,
     `tags`, `full_link`).
   - `page` nodes elsewhere (`title`, `section`, `weight`, `description`, `body`).
   - `glossary_tooltip term_id=` → `references` edge.
   - `glossary_definition term_id=` → `defines` edge.
   - `[..](/docs/..)` → `links_to` edge.
   - Normalize Hugo shortcodes to clean HTML/MD (see `INGESTION.md` table).
4. Fetch `swagger.json` from `kubernetes/kubernetes` → `api_object` (780) + `api_path` (564)
   nodes; cross-link Kinds to pages via title match.
5. Stamp every node with `version`.

### B. Sanity-check `dataset.json` (GATE — before any LLM)
Validate: required fields; every `term_id` resolves; link targets exist or flagged;
non-empty bodies; counts ≈ pages 1,674 / glossary 163 / api_paths 564 / api_objects 780.
Fail the build on violation. (Mirrors chatgpt-compile's P1 deterministic check.)

### C. LLM enrichment (fast path ONLY)
- Ollama `llama3.1:8b` @ `http://localhost:11434`, ~1.5s/call, strict JSON out.
- Tasks: `summary` (concept cards), `tags` (topical), `prerequisites` (glossary ids),
  `decision_question` (per node). On LLM failure → fall back to deterministic data.
- **Never** put the slow model (llama.cpp 35B @ `:8080`, ~90s) on the critical path.

### D. Emit `dataset.json` (shape in `DATA_MODEL.md`)
Include `meta.stats` (pages, glossary, api_paths, api_objects, edges, graph_density).

### E. Frontend (Next.js static export)
- Reuse `chatgpt-compile` build/deploy/theme. `output: "export"`.
- Routes: `/`, `/graph`, `/decide`, `/api`, `/search`, `/resource/[id]`, `/learn/[topic]`.
- Ship: Concept Graph, Decision Explorer (seed the Ingress+Deployment walk), API Explorer,
  Search, basic Resource Relationships + Learning Paths.
- Trim `dataset.json` for bundle size (summaries + edges inline; full bodies split per node).
- Render normalized HTML; glossary tooltips → inline node links. Attribution footer (CC-BY-4.0).

### F. Deploy
- `npm run build && npm run export` → `out/` → Vercel project `k8s-compile`.
- Mirror `chatgpt-compile.vercel.app` settings. Custom domain optional.
- Local preview: `npx serve out/`.

### G. Metrics
- Record build time, artifact size, concepts, graph density, query latency, pages, edges.
- Output the `METRICS_CASE_STUDY.md` table with real numbers.

## Hard constraints
- No LLM at runtime. No RL/agents/autonomy in MVP. Deterministic ingest first.
- Attribute Kubernetes docs (CC-BY-4.0). Pin corpus version.
- Ship the explorer before any research-track feature.

## Definition of done
Full corpus ingested; `dataset.json` passes sanity-check; ≥4 views render from one corpus;
deployed on Vercel with attribution; metrics captured and reproducible.
