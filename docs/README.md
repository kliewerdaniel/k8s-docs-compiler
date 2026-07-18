# k8s-docs-compiler — Documentation Index

This folder is the single source of truth for building **k8s-docs-compiler**: an
application that compiles the Kubernetes documentation corpus into an interactive,
deployable **knowledge application** (Next.js static export on Vercel), using the
same compile-time-AI pipeline proven by the `chatgpt-compile` project.

The approach is *compile-time AI* (a.k.a. "Static AI"): expensive reasoning about the
corpus happens **once, at build time**, and the result is served as a deterministic,
inspectable, deployable artifact — not a per-request chatbot.

## How to read these docs

| File | Audience | Purpose |
|------|----------|---------|
| `PRODUCT_SPEC.md` | Everyone | What we are building and why, distilled from the source conversation. |
| `RESEARCH_kubernetes_docs.md` | Architect / ingestion | Authoritative facts about the K8s docs corpus we compile. |
| `ARCHITECTURE.md` | Architect / agent | The end-to-end compile pipeline and its stages. |
| `DATA_MODEL.md` | Backend / extractor | Nodes and edges of the compiled knowledge graph. |
| `INGESTION.md` | Ingestion engineer | How to fetch & parse raw K8s docs. |
| `EXTRACTION.md` | Extractor engineer | Turning parsed docs into structured concepts, glossary links, API objects. |
| `COMPILE_TARGETS.md` | Frontend / product | The 7+ views produced from one corpus (the "compile targets"). |
| `FRONTEND.md` | Frontend engineer | Next.js app structure, components, search, graph rendering. |
| `DEPLOYMENT.md` | DevOps | Vercel static-export deploy, mirroring chatgpt-compile.vercel.app. |
| `METRICS_CASE_STUDY.md` | Product / author | The measurable results to publish as a credibility case study. |
| `BUILD_PLAN.md` | PM / agent | Phased milestones; phase 0 is ONE task, not the whole corpus. |
| `AGENT_HANDOFF.md` | Coding agent / team | Executable instructions to build the MVP without further clarification. |
| `SOURCE_conversation.md` | Context | The verbatim ChatGPT conversation that seeded this project. |
| `APPENDIX_research_data.md` | Reference | Exact counts, URLs, and commands used during research. |

## One-line definition (use this in all external copy)

> **k8s-docs-compiler** turns the Kubernetes documentation into an interactive
> knowledge application — search, concept graph, decision explorer, API explorer,
> and learning paths — compiled once and deployed anywhere.

## The single most important constraint (from the source conversation)

> Build the best Kubernetes documentation explorer you can. No RL, no agents, no
> autonomous adaptation. Just something that is clearly better than browsing
> Markdown or using keyword search.

Ship the explorer first. Research directions (incremental compilation, agent-authored
compiler passes, RL-based doc updates) are explicitly a *separate, lower-priority
track* and must not block the demo.

## Relationship to the prior project

This reuses the proven `chatgpt-compile` workflow:

1. **Deterministic ingest (P1)** — parse the corpus; no LLM involved.
2. **Sanity-check `dataset.json`** — validate the extracted structure *before* any LLM pass.
3. **LLM enrichment (fast local path)** — Ollama `llama3.1:8b` at `:11434` (~1.5s/call, clean JSON).
4. **Build artifacts** — static site, JSON knowledge package, graph, semantic index.
5. **Deploy** — `next export` → Vercel, like `chatgpt-compile.vercel.app`.

See `AGENT_HANDOFF.md` for the exact mapping.
