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


def emit_all(g: KnowledgeGraph, out_dir: str, emit_json_: bool = True,
             emit_sqlite_: bool = True, emit_gexf_: bool = True,
             emit_web_: bool = True) -> dict:
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
    return paths
