# Data Model — The Compiled Knowledge Graph

All compile targets read from one canonical `dataset.json` (or the same structure in a DB).
Nodes are typed; edges are typed and directed. Every node carries a `version` for diffing.

## Node types

| type | key | required fields | source |
|------|-----|-----------------|--------|
| `page` | `page:<path>` | title, section, body, url, version | each `.md` |
| `glossary` | `gloss:<id>` | id, title, short_description, full_link, tags | glossary `*.md` |
| `api_object` | `api:<group>/<version>.<Kind>` | kind, group, version, fields[] | `swagger.json` |
| `api_path` | `apipath:<method> <path>` | method, path, operationId | `swagger.json` |
| `concept` | `concept:<slug>` | title, summary, aliases[] | extracted/LLM from pages |
| `task` | `task:<path>` | title, goal, steps[] | `tasks/*.md` |
| `tutorial` | `tut:<path>` | title, goal | `tutorials/*.md` |

## Edge types

| type | from → to | meaning | extracted from |
|------|-----------|---------|----------------|
| `references` | page/concept → glossary | page mentions a glossary term | `glossary_tooltip term_id=` |
| `defines` | page → glossary | page inlines a term definition | `glossary_definition term_id=` |
| `links_to` | page → page | Markdown link to another doc | `[..](/docs/..)` |
| `prerequisite_of` | node → node | A must be understood before B | heading "Before you begin", LLM, or explicit `related` |
| `related_to` | node ↔ node | symmetric related | `tags`, see-also sections |
| `api_for` | api_object ↔ page | doc explains/uses this API object | heading/text match + LLM confirm |
| `version_of` | node@v1 → node@v2 | same logical node, different version | diff by `key` across `version` |
| `part_of` | node → section | hierarchical membership | directory / front-matter `weight` |

## `dataset.json` top-level shape

```json
{
  "meta": {
    "corpus": "kubernetes",
    "version": "v1.34",
    "source_repo": "kubernetes/website@main",
    "generated_at": "2026-07-18T...Z",
    "stats": { "pages": 1674, "glossary": 163, "api_paths": 564, "api_objects": 780,
               "edges": 0, "graph_density": 0.0 }
  },
  "nodes": [ { "id":"gloss:pod", "type":"glossary", "title":"Pod", "short_description":"...",
               "tags":["core-object","fundamental"], "version":"v1.34",
               "url":"https://kubernetes.io/docs/reference/glossary/pod/" }, ... ],
  "edges": [ { "from":"page:concepts/workloads/pods", "to":"gloss:pod",
               "type":"references", "context":"A Pod represents a set of running containers" }, ... ]
}
```

## Why these types

- **`glossary` nodes are the backbone** of the Concept Graph — 163 controlled terms that
  everything else links to. Anchor navigation and search on them.
- **`api_object` + `api_path`** power the API Explorer and the cross-link to docs.
- **`prerequisite_of`** powers Learning Paths and "explain this prerequisite chain."
- **`version_of`** powers Version Differences (diff two `dataset.json` by `key`).
- **`tags`** on glossary terms enable "show everything related to RBAC" filters.

## Graph density metric

`graph_density = edges / (nodes * (nodes - 1))` (or out-degree avg). Tracked in `meta.stats`
for the case-study (`METRICS_CASE_STUDY.md`).

## Storage options

- **MVP:** single `dataset.json` (or split `nodes.json` + `edges.json`) consumed at build.
- **Scale:** GEXF/CSV for graph tooling; optional SQLite for query; optional vector store
  for the semantic index (embeddings of node text). All derivable from `dataset.json`.
