# Extraction — From Parsed Docs to the Knowledge Graph

Turns `parsed/` into the typed `nodes` + `edges` of `DATA_MODEL.md`. Mostly deterministic;
LLM used only for summaries, tags, and implicit prerequisite detection.

## 1. Glossary edges (fully deterministic)

For every page/concept body, the captured `_glossary_refs` / `_glossary_defs` become edges:

```python
for ref in node["_glossary_refs"]:
    edges.append({ "from": node["id"], "to": f"gloss:{ref}", "type":"references",
                   "context": snippet_around(body, ref) })
for d in node["_glossary_defs"]:
    edges.append({ "from": node["id"], "to": f"gloss:{d}", "type":"defines" })
```

Validate every `term_id` resolves to a `glossary` node; otherwise flag as a broken edge
(the K8s docs occasionally reference terms that were renamed).

## 2. Page-to-page links (deterministic)

Every `[text](/docs/...)` becomes a `links_to` edge. Resolve the target path to a `page` id.
Flag dangling links (page moved/renamed) for the sanity-check report.

## 3. Concept extraction (hybrid)

- `glossary` nodes ARE the primary concept set (163).
- Additionally, derive `concept` nodes from H2/H3 section headings across pages where a
  heading introduces a distinct idea (e.g. "ReplicaSet", "StatefulSet" as sub-concepts).
  Detect via heading + glossary co-occurrence, or LLM labeling of major headings.

## 4. API object cross-linking (deterministic + LLM confirm)

- Parse `swagger.json` → `api_object` nodes (Kind from definition name, e.g. `io.k8s.api.apps.v1.Deployment` → `Deployment`, group `apps`, version `v1`).
- Link `api_for`: a page whose title/body strongly matches a Kind gets `api_for` → that object.
  Use deterministic keyword match first (title contains Kind), then optional LLM confirm for
  ambiguous cases. This powers "API Explorer ↔ concept" navigation.

## 5. Prerequisite detection (the hard, high-value part)

Powers **Learning Paths** and "explain this prerequisite chain."

Sources (in priority order):
1. **Explicit "Before you begin" sections** — many K8s task/tutorial pages have one. Parse
   its bullet list; each bullet referencing a doc/glossary term → `prerequisite_of` edge.
2. **Section hierarchy** — `concepts/overview` precedes `concepts/architecture`, etc. Use
   directory depth + front-matter `weight` as a weak signal.
3. **LLM inference (fast path)** — for pages without explicit prereqs, ask `llama3.1:8b`
   to list 1–3 prerequisite glossary terms, returning strict JSON:
   `{"prerequisites":["pod","service"]}`. Validate each against known glossary ids.

Keep LLM inference OFF the critical path for the MVP; ship with (1)+(2), add (3) as a
quality improvement.

## 6. LLM enrichment (fast local path only)

Model: **Ollama `llama3.1:8b` @ `http://localhost:11434`** (~1.5s/call, clean JSON).
Reserved LLM tasks:
- `summary`: 1–2 sentence concept summary for cards/search snippets.
- `tags`: extend glossary `tags` with topical labels (e.g. `networking`, `security`).
- `prerequisites`: as above.
- `decision_question`: for Decision Explorer, the question a node answers
  (e.g. pod → "How do I run a single container?").

**Never** use the slow path (`llama.cpp` 35B @ `:8080`, ~90s/call) on the critical path.
Reserve it for optional premium summaries.

Every LLM call returns schema-validated JSON; on failure, fall back to deterministic data
(no summary) rather than blocking the build.

## 7. Version tagging

Stamp every node with `version` (e.g. `v1.34`) from the ingested repo tag. This makes
`version_of` edges and the Version Differences target possible later.

## 8. Output

`dataset.json` per `DATA_MODEL.md`. Hand to the SANITY-CHECK gate, then COMPILE TARGETS.
