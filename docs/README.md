# Documentation Index — k8s-docs-compiler

This folder is the single source of truth for building and understanding
**k8s-docs-compiler**. As of 2026-07-18 the **compiler is implemented** under
`compiler/` (not just docs) — see `README.md` (repo root) and `ARCHITECTURE.md`.

| File | Audience | Purpose |
|------|----------|---------|
| `../README.md` | Everyone | Repo overview, quick start, CLI, project layout |
| `ARCHITECTURE.md` | Architect / agent | **Implemented** 5-phase pipeline + IR |
| `DIAGRAM.md` | Everyone | Pipeline, runtime-query, and concept-graph diagrams |
| `PRODUCT_SPEC.md` | Everyone | What we build & why (from the source conversation) |
| `RESEARCH_kubernetes_docs.md` | Architect / ingestion | Authoritative K8s corpus facts |
| `DATA_MODEL.md` | Backend / extractor | (Narrative) node/edge concepts — the code of record is `compiler/ir.py` |
| `INGESTION.md` | Ingestion engineer | (Narrative) — implemented in `compiler/ingestion.py` + `compiler/parser.py` |
| `EXTRACTION.md` | Extractor engineer | (Narrative) — see `compiler/parser.py` + `compiler/k8s_passes.py` |
| `COMPILE_TARGETS.md` | Frontend / product | The views produced from one corpus |
| `FRONTEND.md` | Frontend engineer | Next.js app structure (planned; compiler + artifacts are the current deliverable) |
| `DEPLOYMENT.md` | DevOps | Vercel static-export deploy |
| `METRICS_CASE_STUDY.md` | Product / author | Measurable-results case study |
| `BUILD_PLAN.md` | PM / agent | Phased milestones |
| `AGENT_HANDOFF.md` | Coding agent / team | Executable build instructions |
| `SOURCE_conversation.md` | Context | Verbatim ChatGPT conversation that seeded the project |
| `APPENDIX_research_data.md` | Reference | Exact counts, URLs, commands |

## Note on doc vs code

The narrative docs (`DATA_MODEL.md`, `INGESTION.md`, `EXTRACTION.md`) describe the design
intent. The **authoritative implementation** lives in `compiler/`:
- `ir.py` — the real data model
- `ingestion.py` / `parser.py` — ingest + parse
- `k8s_passes.py` — K8s-specific knowledge passes
- `optimize.py` / `artifacts.py` — optimize + emit
- `ai_passes.py` — optional AI layer
- `cli.py` / `compiler.py` — orchestration

When the narrative and code disagree, **code wins**; update the narrative to match.
