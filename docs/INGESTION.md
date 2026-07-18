# Ingestion — Fetching & Parsing the Raw Corpus

Deterministic, no LLM. Output: `parsed/` with one JSON per source document + `swagger.json`.

## 1. Source repos

```bash
# Docs (Hugo Markdown)
git clone --depth 1 https://github.com/kubernetes/website.git
# Pin to a version tag for reproducibility, e.g.:
#   git checkout v1.34.0   (then ingest content/en/docs)

# API spec (OpenAPI v2)
curl -sL https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json \
  -o ingest/swagger.json
```

## 2. Walk the docs tree

Target path: `kubernetes/website/content/en/docs/**/*.md`

- Skip `contribute/` unless you want docs-process nodes (tag them `meta`).
- Skip `_index.md` partials only where they duplicate section landing content (keep them as
  `page` nodes for navigation — they carry section descriptions).

## 3. Per-file parse (deterministic)

For each `.md`:

```python
import re, yaml

def parse_md(path):
    text = open(path, encoding="utf-8").read()
    # 1. Front-matter
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    fm = yaml.safe_load(m.group(1)) if m else {}
    body = m.group(2) if m else text
    # 2. Identify glossary term file
    if "id" in fm and "/reference/glossary/" in path:
        node = { "type":"glossary", "id": fm["id"], "title": fm.get("title"),
                 "short_description": fm.get("short_description"),
                 "full_link": fm.get("full_link"), "tags": fm.get("tags", []) }
    else:
        node = { "type":"page", "section": section_from_path(path),
                 "title": fm.get("title"), "weight": fm.get("weight"),
                 "description": fm.get("description"), "body": body }
    # 3. Extract shortcode edges (DONE IN EXTRACTION STAGE, but capture raw here)
    node["_glossary_refs"] = re.findall(r'glossary_tooltip[^>]*term_id="([^"]+)"', body)
    node["_glossary_defs"] = re.findall(r'glossary_definition[^>]*term_id="([^"]+)"', body)
    node["_links"] = re.findall(r'\]\((/docs/[^)#?]+)', body)
    return node
```

## 4. Shortcode normalization (render-clean)

Replace Hugo shortcodes before storing `body` for display:

| shortcode | action |
|-----------|--------|
| `glossary_tooltip text="X" term_id="Y"` | keep as `<a data-gloss="Y">X</a>` (link to glossary node) |
| `glossary_definition term_id="Y"` | inline the glossary `short_description` |
| `figure src=... alt=... caption=...` | `<img>` + caption |
| `mermaid` ... `{{< /mermaid >}}` | extract diagram source → render or store |
| `details summary="..."` ... `{{< /details >}}` | `<details>` collapsible |
| `note/warning/caution` | styled `<div class="callout">` |
| `tabs`, `table`, `param`, `feature`, `skew`, `highlight`, `comment`, `api` | normalize to HTML/MD |

A robust approach: use the **Hugo** toolchain itself if available (`hugo` can render to
HTML), OR a targeted shortcode stripper. For the MVP, a regex/shortcode stripper is enough
because we mostly need text + the glossary edges.

## 5. OpenAPI parse

```python
import json
spec = json.load(open("ingest/swagger.json"))
api_paths = [ {"method":m, "path":p, "operationId": v.get("operationId")}
              for p, ops in spec["paths"].items()
              for m, v in ops.items() if m in {"get","post","put","delete","patch"} ]
api_objects = [ {"name":k, **v} for k,v in spec["definitions"].items() ]
```

- 564 paths, 780 definitions (measured).
- Cross-link to docs: match API object Kind (e.g. `Deployment`) to pages/glossary that
  mention it (done in EXTRACTION).

## 6. Output contract

Write `parsed/pages.json`, `parsed/glossary.json`, `parsed/api.json`, plus
`parsed/swagger.json`. These feed the SANITY-CHECK gate before any LLM call.

## 7. Reproducibility

- Record `source_repo`, commit SHA, and `version` in `meta`.
- Pin the clone (`--depth 1` + tag) so builds are reproducible.
- Never call the LLM in this stage.
