# Build Plan — Phased Milestones

Sequenced so the **business-track demo ships first**; research-track items are explicitly
deferred. Each phase ends in something demoable.

## Phase 0 — ONE task, demonstrably easier (highest priority)
**Goal:** prove value on a single question before touching the whole corpus.
- Pick: **"How do I expose a Deployment with an Ingress?"**
- Ingest ONLY the pages needed: Deployments, Services, Ingress, Pods, ReplicaSet + their
  glossary terms. (A few dozen pages, not 1,674.)
- Produce a minimal graph + a single answer page that walks Deployment → Service → Ingress.
- **Success:** a user answers that question faster here than on kubernetes.io.
- No RL, no agents, no autonomous adaptation.

## Phase 1 — The multi-view explorer (MVP)
Expand ingest to the full `content/en/docs` (1,674 pages) + glossary (163) + swagger (564/780).
Ship compile targets:
- Concept Graph (1)
- Decision Explorer (2) seeded with the Phase-0 question + a few more
- API Explorer (5)
- Search (7)
- Basic Resource Relationships (3) + Learning Paths (6)
Validate `dataset.json` via the SANITY-CHECK gate before LLM enrichment.

## Phase 2 — Deploy & case study
- `next export` → Vercel (`k8s-compile.vercel.app`), mirror `chatgpt-compile.vercel.app`.
- Capture metrics (`METRICS_CASE_STUDY.md`); publish the case-study post.
- Attribution footer (CC-BY-4.0).

## Phase 3 — Business-track expansion (monetization)
- "Upload your docs" (Confluence/Notion/GitHub/internal MD) → same compiler → deployable
  knowledge app. This is the consulting/product wedge from the conversation.

## Research track (nights/weekends — NEVER block Phases 0–3)
- Incremental compilation (rebuild only changed nodes).
- User-feedback-driven ranking.
- Plugin-based / agent-authored compiler passes.
- Continuous compilation pipeline (CI cron re-ingest).
- Self-improving compilation heuristics (the RL idea from the conversation).

## Definition of done for MVP
1. Full corpus ingested deterministically; `dataset.json` passes sanity-check.
2. ≥4 views render from one corpus.
3. Deployed on Vercel, reachable, attribution present.
4. Metrics captured and reproducible.
