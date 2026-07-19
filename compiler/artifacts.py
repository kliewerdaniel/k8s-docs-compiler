"""Phase 5 — Artifact generation.

Produces deployable, backend-free artifacts from the KnowledgeGraph:
  * dataset.json  : full IR (nodes + edges + meta + stats)
  * knowledge.db   : SQLite — queryable at runtime without an inference server
  * knowledge.gexf : graph exchange format (visualization in Gephi/cytoscape)
  * index.json     : lightweight search index (title/summary/tags + node refs)

No artifact requires an LLM at runtime. All are deterministic given the graph.
"""
from __future__ import annotations

import json
import os
import sqlite3

from .ir import KnowledgeGraph, NodeType
from .util import atomic_write
from .web import emit_web  # noqa: F401  (imported for convenience)
from .logging_setup import get_logger

logger = get_logger()


def emit_json(g: KnowledgeGraph, out_dir: str, filename: str = "dataset.json") -> str:
    path = os.path.join(out_dir, filename)
    atomic_write(path, json.dumps(g.to_dict(), indent=2, ensure_ascii=False))
    return path


def emit_gexf(g: KnowledgeGraph, out_dir: str, filename: str = "knowledge.gexf") -> str:
    """Graph Exchange Format — open in Gephi / cytoscape / networkx."""
    node_types = {}
    edges_xml = []
    for e in g.edges:
        edges_xml.append(
            f'    <edge id="{id(e)}" source="{_esc(e.from_id)}" target="{_esc(e.to_id)}" '
            f'type="directed" label="{_esc(e.type)}" weight="{e.weight}" '
            f'confidence="{e.confidence}"/>'
        )
    nodes_xml = []
    for i, n in enumerate(g.nodes):
        nodes_xml.append(
            f'    <node id="{_esc(n.id)}" label="{_esc(n.title)}">'
            f'<attvalues>'
            f'<attvalue for="type" value="{_esc(n.type)}"/>'
            f'<attvalue for="section" value="{_esc(n.section or "")}"/>'
            f'<attvalue for="confidence" value="{n.confidence}"/>'
            f'</attvalues></node>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gexf xmlns="http://gexf.net/1.3" version="1.3">\n'
        '  <graph mode="static" defaultedgetype="directed">\n'
        '    <attributes class="node">\n'
        '      <attribute id="type" title="type" type="string"/>\n'
        '      <attribute id="section" title="section" type="string"/>\n'
        '      <attribute id="confidence" title="confidence" type="double"/>\n'
        '    </attributes>\n'
        '    <nodes>\n' + "\n".join(nodes_xml) + '\n    </nodes>\n'
        '    <edges>\n' + "\n".join(edges_xml) + '\n    </edges>\n'
        '  </graph>\n</gexf>\n'
    )
    path = os.path.join(out_dir, filename)
    atomic_write(path, xml)
    return path


def emit_sqlite(g: KnowledgeGraph, out_dir: str, filename: str = "knowledge.db") -> str:
    """A self-contained, queryable knowledge base. No server, no LLM."""
    path = os.path.join(out_dir, filename)
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            type TEXT,
            title TEXT,
            summary TEXT,
            section TEXT,
            version TEXT,
            tags TEXT,
            url TEXT,
            confidence REAL,
            derived_by TEXT,
            meta TEXT,
            body TEXT,
            provenance TEXT
        )""")
    cur.execute("""
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id TEXT,
            to_id TEXT,
            type TEXT,
            label TEXT,
            weight REAL,
            confidence REAL,
            derived_by TEXT,
            provenance TEXT
        )""")
    cur.execute("CREATE INDEX idx_edges_from ON edges(from_id)")
    cur.execute("CREATE INDEX idx_edges_to ON edges(to_id)")
    cur.execute("CREATE INDEX idx_edges_type ON edges(type)")
    cur.execute("CREATE INDEX idx_nodes_type ON nodes(type)")
    cur.execute("CREATE INDEX idx_nodes_title ON nodes(title)")

    for n in g.nodes:
        cur.execute(
            "INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (n.id, n.type, n.title, n.summary, n.section, n.version,
             json.dumps(n.tags), n.url, n.confidence, n.derived_by,
             json.dumps(n.meta), n.body, json.dumps([p.__dict__ for p in n.provenance])),
        )
    for e in g.edges:
        cur.execute(
            "INSERT INTO edges (from_id,to_id,type,label,weight,confidence,derived_by,provenance) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (e.from_id, e.to_id, e.type, e.label, e.weight, e.confidence,
             e.derived_by, json.dumps([p.__dict__ for p in e.provenance])),
        )

    # A convenience view that joins edges to node titles (runtime queries).
    cur.execute("""
        CREATE VIEW edge_view AS
        SELECT e.from_id, f.title AS from_title, e.to_id, t.title AS to_title,
               e.type, e.label, e.confidence
        FROM edges e
        JOIN nodes f ON f.id = e.from_id
        JOIN nodes t ON t.id = e.to_id
    """)
    con.commit()
    con.close()
    logger.info("sqlite artifact: %s (%d nodes, %d edges)", path, len(g.nodes), len(g.edges))
    return path


def emit_search_index(g: KnowledgeGraph, out_dir: str, filename: str = "index.json") -> str:
    """Lightweight title/summary/tag index for client-side search."""
    entries = []
    for n in g.nodes:
        entries.append({
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "summary": n.summary,
            "tags": n.tags,
            "section": n.section,
            "url": n.url,
        })
    payload = {"count": len(entries), "entries": entries}
    path = os.path.join(out_dir, filename)
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))
    return path


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# LLM-traversability artifacts
#
# A deployed static site is only useful to an LLM agent if it can (a) discover
# what machine-readable resources exist and (b) fetch them in a form it can
# ingest. We emit the standard `llms.txt` index plus human/LLM-readable text
# dumps per node type (so an agent can pull only the slice it needs instead of
# the 17 MB dataset.json) and a JSONL stream. All static — no runtime server.
# ---------------------------------------------------------------------------

# Sections of the site an LLM agent can use (mirrors the frontend routes).
_LLM_VIEWS = [
    ("/", "Home — stats + view index"),
    ("/graph", "Concept Graph — force-directed visualization of the knowledge graph"),
    ("/explore", "Decision Explorer — walk the graph to answer operational questions"),
    ("/api", "API Explorer — 628 API objects and 564 API paths from the OpenAPI spec"),
    ("/relationships", "Resource Relationships — ownership chains and dependencies"),
    ("/learn", "Learning Paths — prerequisite chains"),
    ("/rbac", "RBAC & Permissions — what a manifest requires"),
    ("/search", "Search — full-text across every node, with provenance"),
    ("/docs", "Docs — the synthesized knowledge card for any node (?id=<node_id>)"),
    ("/start", "Start Here — a prerequisite-ordered onboarding path"),
]


def _node_text_block(n) -> str:
    """One plain-text block per node, LLM-friendly."""
    lines = [f"# {n.title}  [{n.type}]"]
    if n.tags:
        lines.append("tags: " + ", ".join(n.tags))
    if n.summary:
        lines.append("")
        lines.append(n.summary)
    if n.body:
        lines.append("")
        lines.append(n.body)
    if n.provenance:
        srcs = []
        for p in n.provenance[:3]:
            s = p.source
            if p.url:
                s += f" ({p.url})"
            srcs.append(s)
        if srcs:
            lines.append("")
            lines.append("sources: " + "; ".join(srcs))
    return "\n".join(lines)


def emit_llms_dumps(g: KnowledgeGraph, out_dir: str) -> dict:
    """Per-type plain-text knowledge dumps + a JSONL stream.

    Returns {filename: path}. An LLM agent reads llms.txt, then fetches only
    the slice it needs (e.g. llms-glossary.txt) instead of dataset.json.
    """
    by_type: dict = {}
    for n in g.nodes:
        by_type.setdefault(n.type, []).append(n)

    paths = {}
    # JSONL — one node per line, easiest for LLM tools to stream/parse.
    jsonl = os.path.join(out_dir, "knowledge.jsonl")
    with open(jsonl, "w", encoding="utf-8") as f:
        for n in g.nodes:
            f.write(json.dumps({
                "id": n.id, "type": n.type, "title": n.title,
                "summary": n.summary, "tags": n.tags, "body": n.body,
                "derived_by": n.derived_by, "confidence": n.confidence,
            }, ensure_ascii=False) + "\n")
    paths["jsonl"] = jsonl

    # Per-type text dumps (skip the millions-of-heading `concept` nodes — too noisy;
    # provide a capped sample instead).
    dump_types = {
        "glossary": "llms-glossary.txt",
        "api_object": "llms-api-objects.txt",
        "page": "llms-pages.txt",
        "role": "llms-rbac.txt",
        "controller": "llms-control-plane.txt",
    }
    for t, fname in dump_types.items():
        nodes = by_type.get(t, [])
        blocks = [_node_text_block(n) for n in nodes]
        text = f"# Kubernetes knowledge — {t} ({len(nodes)} entries)\n\n" + "\n\n---\n\n".join(blocks)
        p = os.path.join(out_dir, fname)
        atomic_write(p, text)
        paths[fname] = p

    # concept: capped sample (heading-derived; high volume, low individual value)
    concepts = by_type.get("concept", [])
    sample = concepts[:400]
    ctext = f"# Kubernetes knowledge — concept headings (sample of {len(sample)}/{len(concepts)})\n\n" + \
            "\n\n---\n\n".join(_node_text_block(n) for n in sample)
    cp = os.path.join(out_dir, "llms-concepts-sample.txt")
    atomic_write(cp, ctext)
    paths["llms-concepts-sample.txt"] = cp
    return paths


def emit_llms_txt(g: KnowledgeGraph, out_dir: str, base_url: str = "") -> str:
    """The standard `llms.txt` index (https://llmstxt.org).

    Points an LLM agent at the machine-readable resources and how to query them.
    """
    stats = g.stats
    version = g.meta.get("version", "unknown")
    base = base_url.rstrip("/")
    lines = [
        "# Kubernetes Knowledge Compiler",
        "",
        "> A compiled, versioned knowledge graph of Kubernetes, built from the "
        "official documentation and OpenAPI spec at **compile time**. Every fact "
        "is traceable to its source. No runtime LLM is involved in serving this "
        "site — it is a static, queryable knowledge resource.",
        "",
        f"Corpus version: {version}. Nodes: {len(g.nodes)}. "
        f"Relationships: {len(g.edges)}. "
        f"AI-synthesized documentation: "
        f"{sum(1 for n in g.nodes if n.derived_by.startswith('ai:'))}.",
        "",
        "## How to use this resource",
        "",
        "- The full structured knowledge base is `dataset.json` (nodes + typed "
        "edges + provenance). Fetch it and filter by `id` / `type`.",
        "- For lighter, human-readable reads, use the per-type `llms-*.txt` dumps "
        "below (one concept per block).",
        "- `knowledge.jsonl` is the same data, one node per line.",
        "- To read a single node's synthesized documentation, open "
        "`/docs?id=<node_id>` (e.g. `/docs?id=gloss:pod`).",
        "- Node ids look like `gloss:<term>`, `api:<Object>`, `page:<slug>`, "
        "`concept:<heading>`.",
        "",
        "## Machine-readable resources",
        "",
        f"- [dataset.json]({base}/dataset.json) — full knowledge graph (JSON)",
        f"- [knowledge.jsonl]({base}/knowledge.jsonl) — same data, one node per line",
        f"- [index.json]({base}/index.json) — lightweight title/summary/tag index",
        f"- [knowledge.db]({base}/knowledge.db) — SQLite (download + query locally)",
        f"- [knowledge.gexf]({base}/knowledge.gexf) — graph format (Gephi/cytoscape)",
        "",
        "### Per-type plain-text dumps",
        f"- [llms-glossary.txt]({base}/llms-glossary.txt) — glossary terms",
        f"- [llms-api-objects.txt]({base}/llms-api-objects.txt) — API objects",
        f"- [llms-pages.txt]({base}/llms-pages.txt) — documentation pages",
        f"- [llms-rbac.txt]({base}/llms-rbac.txt) — RBAC roles",
        f"- [llms-control-plane.txt]({base}/llms-control-plane.txt) — control-plane components",
        f"- [llms-concepts-sample.txt]({base}/llms-concepts-sample.txt) — concept headings (sample)",
        "",
        "## Interactive views",
        "",
    ]
    for href, desc in _LLM_VIEWS:
        lines.append(f"- [{href}]({base}{href}) — {desc}")
    lines.append("")
    lines.append(
        "## Note on provenance\n"
        "Nodes tagged `derived_by` starting with `ai:` were synthesized from source "
        "quotes at compile time (confidence < 1.0). All carry `provenance` pointing "
        "to the originating document. Prefer source quotes when available."
    )
    lines.append("")
    path = os.path.join(out_dir, "llms.txt")
    atomic_write(path, "\n".join(lines))
    return path


def emit_sitemap(g: KnowledgeGraph, out_dir: str, base_url: str = "https://k8s-docs-compiler.vercel.app") -> str:
    urls = [f"{base_url.rstrip('/')}{h}" for h, _ in _LLM_VIEWS]
    urls.append(f"{base_url.rstrip('/')}/docs")  # docs is id-driven; include the base
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"  <url><loc>{_esc(u)}</loc></url>")
    xml.append("</urlset>")
    path = os.path.join(out_dir, "sitemap.xml")
    atomic_write(path, "\n".join(xml))
    return path


def emit_robots(out_dir: str, base_url: str = "https://k8s-docs-compiler.vercel.app") -> str:
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {base_url.rstrip('/')}/sitemap.xml\n"
    )
    path = os.path.join(out_dir, "robots.txt")
    atomic_write(path, text)
    return path


def emit_all(g: KnowledgeGraph, out_dir: str, emit_json_: bool = True,
             emit_sqlite_: bool = True, emit_gexf_: bool = True,
             emit_web_: bool = True,
             base_url: str = "https://k8s-docs-compiler.vercel.app") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    if emit_json_:
        paths["json"] = emit_json(g, out_dir)
    paths["search_index"] = emit_search_index(g, out_dir)
    if emit_sqlite_:
        paths["sqlite"] = emit_sqlite(g, out_dir)
    if emit_gexf_:
        paths["gexf"] = emit_gexf(g, out_dir)
    if emit_web_:
        paths["web"] = emit_web(g, out_dir)
    # LLM-traversability layer
    paths["jsonl"] = emit_llms_dumps(g, out_dir)["jsonl"]
    paths.update(emit_llms_dumps(g, out_dir))
    paths["llms_txt"] = emit_llms_txt(g, out_dir, base_url)
    paths["sitemap"] = emit_sitemap(g, out_dir, base_url)
    paths["robots"] = emit_robots(out_dir, base_url)
    return paths
