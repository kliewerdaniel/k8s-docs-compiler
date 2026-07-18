# Product Specification — k8s-docs-compiler

> Derived directly from the ChatGPT conversation `6a5bb343-eee4-83ea-9521-9d74edf9d5f2`
> ("Compile-time AI Insights", GPT-5.5). Read `SOURCE_conversation.md` for the raw text.

## 1. Vision

Kubernetes documentation is:

- **Large** (1,674 English Markdown pages; 163 glossary terms; 564 API paths / 780 types).
- **Deeply interconnected** (every page links concepts via glossary tooltips).
- **Constantly changing** (per-minor-version docs, new releases continuously).
- **Difficult for newcomers to navigate** (reference, concepts, tasks, tutorials are siloed).
- **Mostly referenced rather than read front-to-back**.

The product compiles that corpus into an **interactive knowledge application** that makes
one common task *noticeably easier* than the official docs.

## 2. Core thesis (distribution > technology)

The conversation is emphatic: this is no longer a research project to monetize — it is
**proof you can solve a business problem**. Stop selling "Compile-Time AI." Sell the
outcome:

> "I turn years of documentation into an interactive website your team can actually navigate."

Framing that lands with buyers: **"a static site generator for knowledge"** — just as Hugo
or Jekyll compile Markdown into static sites, this compiles *knowledge* into interactive
knowledge applications. The compiler is invisible; **the compiled artifact is the product.**

## 3. Product name & category

- Internal name: `k8s-docs-compiler`
- Market category: **Knowledge Applications** / **Documentation Transformation**
- Mental model to reuse in copy: *Static AI* — compile knowledge once, query many times.

```
knowledge  ──compile once──▶  serve forever   (low cost, deterministic, no LLM at runtime)
   vs.
knowledge  ──LLM every request──▶  answer     (high cost, nondeterministic)
```

## 4. The killer demo (define success as ONE task)

Do **not** try to compile all of Kubernetes first. Pick one task and make it faster than
the official docs:

> **"How do I expose a Deployment with an Ingress?"**

If the compiled artifact answers that faster than `kubernetes.io`, the value is proven.
Everything else is expansion.

## 5. Compile targets (the views, all from one source)

The demo opens to a menu of views, each a different "build target" from the same corpus:

```
Kubernetes
  ├── Concept Graph          (navigate concepts + their relationships)
  ├── Decision Explorer      ("where should I start?", decision trees)
  ├── Resource Relationships (objects ↔ objects, owner references, selectors)
  ├── Version Differences    ("what's new since v1.34?")
  ├── API Explorer           (browse 564 API paths / 780 types from OpenAPI)
  ├── Learning Paths         (guided prerequisite chains)
  └── Dependency Graph       (prerequisite / dependent concept chains)
```

Plus reusable explorations the conversation calls out:
- "Explain this prerequisite chain."
- "Show everything related to RBAC."
- "What's new since v1.34?"

## 6. Differentiated capability

The genuinely novel part: **compile one corpus into multiple views.** Search, knowledge
graph, decision tree, dependency explorer, API explorer, learning paths are all *compile
targets*. The compiler emits several outputs, not one.

## 7. Future (business) track — engineering teams

Same compiler, different input. Teams upload:
- Confluence, Notion, GitHub docs, internal Markdown.

Compiler emits:
- static website
- JSON knowledge package
- graph
- embeddings
- REST API
- sitemap
- semantic index

This is **infrastructure they plug into existing tooling** — the monetizable expansion.
(Out of scope for the MVP; documented so the architecture does not preclude it.)

## 8. Out of scope for MVP (explicit non-goals)

From the conversation, these are the *research track* (nights/weekends), NOT the business
track, and must not block the demo:
- self-compiling / autonomous-evolving systems
- reinforcement-learning-based doc updating
- agent-authored compiler passes
- continuous autonomous adaptation

## 9. Success metrics (to publish as a case study)

See `METRICS_CASE_STUDY.md`. Concrete, measurable results establish credibility:
build time, artifact size, concepts extracted, graph density, query latency, pages
processed, relationships discovered, incremental rebuild time.

## 10. Non-negotiable build order

1. One task demonstrably easier (Ingress + Deployment).
2. The explorer with multiple views.
3. Deploy to Vercel, mirror `chatgpt-compile.vercel.app`.
4. Case-study metrics.
5. *Then* research-track features.
