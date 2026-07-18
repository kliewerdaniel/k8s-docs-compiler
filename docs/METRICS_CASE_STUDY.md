# Metrics & Case Study — "Compile-Time AI vs. Runtime AI"

From the conversation: rather than another architecture post, publish **measurable results**
that establish credibility. These are the metrics to collect during the build and present as
**"Compile-Time AI vs. Runtime AI: A Case Study Using the Kubernetes Documentation."**

## Metrics to capture (automated in the pipeline)

| Metric | What it measures | Why it matters |
|--------|------------------|----------------|
| **Build time** | seconds to ingest + extract + emit `dataset.json` | compile cost is paid once |
| **Artifact size** | MB of `dataset.json` + static site | bandwidth/cost of serving |
| **Concepts extracted** | count of `glossary` + `concept` nodes | coverage of the corpus |
| **Graph density** | edges / (nodes·(nodes−1)) or avg out-degree | how interconnected the knowledge is |
| **Query latency** | ms for search / graph lookup at runtime | UX vs LLM-per-request latency |
| **Pages processed** | 1,674 (reference 1,164, tasks 222, concepts 176, tutorials 43, setup 22) | scale proven |
| **Relationships discovered** | total edge count (references, links, prerequisites) | the "compiled" structure |
| **Incremental rebuild time** | seconds to recompile after one doc change | future research-track KPI |

## Comparative framing (the punchline)

> A runtime-RAG chatbot re-invokes an LLM on **every** query (high $/latency,
> nondeterministic). Compile-Time AI reasons about the corpus **once** and serves a
> deterministic artifact (low $/latency, inspectable). The metrics above quantify that gap
> on a notoriously hard corpus (Kubernetes).

## Suggested published table (fill with real numbers post-build)

```
Corpus:            Kubernetes docs (1,674 pages, 163 glossary, 564 API paths)
Build (compile):   ___ s   (one-time)
Artifact size:     ___ MB
Concepts:          ___     Glossary edges: ___
Graph density:     ___
Runtime query:     ___ ms  (vs ~___ ms + $___ per LLM call)
```

## Bonus credibility artifacts
- A screenshot/recording: "How do I expose a Deployment with an Ingress?" answered faster
  in the compiled app than on `kubernetes.io`.
- Reproducible build (pinned SHA) so a reader can re-run and verify the numbers.
- The `dataset.json` stats block (`meta.stats`) is the single source for all figures.

## Publish target
- Blog post on `danielkliewer.com` (Next.js static export, 218 pages — same hosting pattern).
- Lead with the demo, not philosophy (per the conversation's distribution advice).
