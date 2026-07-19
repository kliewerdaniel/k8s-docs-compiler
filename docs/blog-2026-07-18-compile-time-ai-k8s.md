# Compile-Time AI in Practice: How We Built a Kubernetes Knowledge Compiler

*Published 2026-07-18 · Daniel Kliewer*

The smartest thing you can do with a model is to stop asking it questions at runtime.

That sentence is the whole thesis behind [`k8s-docs-compiler`](https://github.com/kliewerdaniel/k8s-docs-compiler) — a project that turns the entire Kubernetes documentation into a static, queryable, *readable* knowledge graph and ships it to [k8s-docs-compiler.vercel.app](https://k8s-docs-compiler.vercel.app/) with **zero inference at runtime**.

This post is a walkthrough of exactly how we built it, and why every design decision traces back to one idea: **intelligence belongs at compile time, not query time.**

> Full source: https://github.com/kliewerdaniel/k8s-docs-compiler
> Live demo: https://k8s-docs-compiler.vercel.app/

---

## The problem with "ask the docs a question"

Most "AI for docs" products are chatbots. You type a question, a model reads the
docs, a model generates an answer, a model decides what to cite. The model is
**in the loop every single request**. That means:

- Every answer costs a round-trip to a model (latency + tokens + money).
- Every answer is non-deterministic — the same question can yield a different
  answer tomorrow.
- Every answer is hard to audit — you're trusting a black box that may or may not
  have read the right page.
- The docs themselves never actually become *more useful*. The model is a
  flashlight pointed at a messy room; the room stays messy.

Compile-time AI flips the order. Instead of querying the model when someone asks,
we query the model **once, while building the artifact**. The model's
intelligence gets *baked into* the knowledge base. What we ship is a static
graph of facts — each one traceable to a source document — that any client can
read with a SQL query or a JSON fetch. No model is awake when a user visits.

> "If the loop is the product, observability becomes the OS."

That's the stance this project operationalizes.

---

## The architecture: a 5-phase compiler

We modeled the build like a real compiler. Sources go in one end; deterministic,
versioned, inspectable artifacts come out the other.

```
 SOURCES            PHASE 1        PHASE 2           PHASE 3              PHASE 4       PHASE 5
kubernetes/website ─▶ INGEST ─▶ PARSE / IR ─▶ KNOWLEDGE PASSES ─▶ OPTIMIZE ─▶ ARTIFACTS
(content/en/docs +   fetch &      front-matter,    glossary edges,      dedupe,      JSON / SQLite /
 swagger.json)       normalize,   shortcodes,      API objects, RBAC,   compress,    GEXF / index
                    provenance    concepts,        ownership, control-  drop orphans
                                  api paths        plane, kubectl flow
                                                      │
                                 OPTIONAL AI PASS (off by default):
                                 summaries · prerequisites · clusters
```

Every phase is pure Python. The output is a typed **Intermediate Representation**
(IR) — `Node` and `Edge` dataclasses — that the rest of the pipeline consumes.
Crucially, **the deterministic core never needs a model**. The AI pass is a
*separate, opt-in layer* bolted onto Phase 3.

### What the deterministic build actually extracts

From 1,632 Kubernetes docs (after excluding `contribute/`), 163 glossary terms,
and the OpenAPI `swagger.json` (628 API objects / 564 paths):

| Metric | Value |
|--------|-------|
| Build time | ~9 s (single deterministic pass) |
| Nodes | 7,021 (1,411 pages, 4,800 concepts, 628 api_objects, 162 glossary, 15 roles, 5 controllers) |
| Edges | 10,228 (part_of, related_to, references, api_for, RBAC `REQUIRES`, control-plane, kubectl-flow) |
| Validation | clean — no dangling edges, confidence in range |

Edges are where the value lives. The compiler doesn't just index pages — it
reconstructs the *relationships* between them:

- **glossary edges** — a page's Hugo `glossary_tooltip` shortcodes become
  machine edges (e.g. a Deployment page → `Pod`, `Service`, `Ingress`).
- **API objects** — parsed from `swagger.json`, cross-linked to docs by group/kind.
- **RBAC `REQUIRES`** — derived from manifest verbs and the control-plane schema.
- **control-plane + kubectl flow** — the "what actually happens when you run
  `kubectl apply`" path, as a walkable graph.
- **ownership / `part_of`** — concept→page→api-object hierarchy.

Every node and edge carries `provenance` — the source document, line, and the
supporting quote. Every deterministic fact is `confidence=1.0`.

---

## The AI pass: intelligence, baked in

The deterministic graph is a *scaffold*. It knows that "Pod" relates to
"Deployment," but the Deployment page itself might only have a title and a
one-line summary pulled from front-matter. For the resource to be genuinely
*readable* — the thing you'd actually send someone instead of a docs link — it
needs synthesized prose.

That's the one job we hand to a model, and we hand it **at compile time**.

### The method

We point the compiler at a **local inference endpoint** and let it synthesize a
structured knowledge card for every node that lacks a real body. The default is
Ollama on `localhost:11434` running `llama3.1:8b` — chosen because it returns
clean JSON reliably. (We also probed a 35B thinking model on `:8080`; it emits
empty `content` and only answers inside `reasoning_content`, so we made the
client endpoint-agnostic and fell back to the 8B for content generation.)

```bash
python -m compiler.cli compile \
    --docs-root kubernetes/website/content/en/docs \
    --swagger swagger.json --version v1.34 --out out \
    --ai --ai-passes synthesis,prerequisites,clusters \
    --ai-url http://localhost:11434 --ai-model llama3.1:8b
```

For each node, the pass sends **only the extracted source quotes** (not the whole
internet) and asks for a structured card:

> overview · why-it-matters · key facts · pitfalls · related

The card is stored as the node `body` (rendered in the frontend **Docs** view)
plus a one-line `summary`. Three design rules make this *compile-time AI* rather
than *chatbot AI*:

1. **Grounded, not generative.** The model explains quotes that already exist in
   the corpus. It does not invent Kubernetes behavior. Output is tagged
   `derived_by="ai:llama3.1:8b"` with `confidence < 1.0` and stays pinned to its
   source `provenance`.
2. **Batched + cached by content hash.** Nodes are synthesized N-at-a-time per
   model call. Results are cached by a hash of their source quotes, so a crash or
   a re-run costs nothing — only *new or changed* nodes hit the model. This is
   what turned a fragile 35-minute run into something resumable.
3. **Pluggable.** `synthesis`, `prerequisites`, `clusters` are separate passes in
   a registry. You add or remove LLM calls per use case without touching the
   deterministic core. `--ai-passes synthesis` runs one; `--ai` runs all.

The result on the real corpus: **1,210 AI-synthesized nodes** with readable
documentation, plus **382 `prerequisite_of` edges** (AI-suggested learning
paths) and **cluster tags** across 400+ nodes for topic-filtered browsing.

### Why this is the point

The model ran *once*, for ~7 minutes, on a laptop. It will never run again for
the life of the deployment. A visitor to the site gets a synthesized,
citation-backed explanation of any Kubernetes concept — and the bill for that
explanation was paid at build time.

---

## The product: a backend-free static site

The compiler emits `dataset.json` (the full IR), `knowledge.db` (SQLite),
`knowledge.gexf` (graph), and `index.json` (search). The frontend is a **Next.js
static export** that consumes `dataset.json` and renders:

- **Graph / Explore** — walk the knowledge graph.
- **API Explorer** — 628 API objects + 564 API paths.
- **Relationships / RBAC** — ownership chains and "what permissions does this
  manifest require?"
- **Learn / Start Here** — prerequisite-ordered onboarding paths.
- **Docs** — the synthesized knowledge card for any node, with Sources + Related.

No server. No API keys. No model. `npm run build` produces HTML/JS/JSON; Vercel
serves it. The `KnowledgeStore` on the client does graph lookups — it never
calls an LLM.

### Making it LLM-traversable too

Because the site is a knowledge resource, we also made it **readable by other
LLMs**, not just humans. The compiler emits a standard [`llms.txt`](https://llmstxt.org)
index plus per-type plain-text dumps (`llms-glossary.txt`, `llms-api-objects.txt`,
…) and a `knowledge.jsonl` stream — all static, all at the site root. Any external
agent can read `llms.txt`, then fetch only the slice it needs. This is the same
philosophy turned outward: the compiled artifact is useful *as a resource*, not
just as a UI.

---

## How you'd reproduce it

```bash
# 1. Offline demo (bundled fixtures, no K8s repo needed)
pip install -r requirements.txt
python -m compiler.cli demo --out out

# 2. Compile the real corpus
git clone --depth 1 https://github.com/kubernetes/website.git
curl -sL https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json -o swagger.json
python -m compiler.cli compile \
    --docs-root kubernetes/website/content/en/docs \
    --swagger swagger.json --version v1.34 --out out

# 3. Turn on compile-time AI (local model, runs once)
python -m compiler.cli compile --ai --ai-passes synthesis \
    --ai-url http://localhost:11434 --ai-model llama3.1:8b

# 4. Query it — no LLM at runtime
python -m compiler.cli query "What permissions does this manifest require?" --db out/knowledge.db

# 5. Ship the frontend
cd frontend && npm install && npm run build   # static export → deploy to Vercel
```

The build is reproducible: same inputs → identical `ir_hash`. AI or no AI, the
deterministic core is the source of truth.

---

## The principle, stated plainly

We didn't build a chatbot that reads Kubernetes docs. We built a **compiler that
turns Kubernetes docs into a graph of understood facts**, and we used a model
exactly once — as a build tool — to make that graph *readable*.

That's compile-time AI:

- **Intelligence moves to build time.** The model is a dependency of the artifact,
  not of the request.
- **Runtime is cheap, deterministic, inspectable.** Queries are graph/SQL
  lookups. You can `diff` two builds and see what changed between K8s v1.33 and
  v1.34.
- **Sovereignty by construction.** No data leaves the machine at runtime. The
  artifact is yours to host, fork, and audit.

The loop is the product. We just made sure the loop closes *before* anyone
visits.

---

*Source: [github.com/kliewerdaniel/k8s-docs-compiler](https://github.com/kliewerdaniel/k8s-docs-compiler) ·
Live: [k8s-docs-compiler.vercel.app](https://k8s-docs-compiler.vercel.app/)*
