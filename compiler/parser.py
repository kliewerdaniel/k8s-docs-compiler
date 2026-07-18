"""Phase 2 — Parsing & IR construction (deterministic).

Turns a RawCorpus into a KnowledgeGraph:
  * glossary terms   -> GLOSSARY nodes (+ tags)
  * docs pages       -> PAGE nodes (+ headings -> CONCEPT nodes)
  * swagger spec     -> API_OBJECT + API_PATH nodes
  * baseline edges   -> references / defines / links_to / api_for / part_of

All facts are traceable to source (Provenance) and deterministic (confidence 1.0).
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

import yaml

from .ir import (
    Node, Edge, KnowledgeGraph, Provenance, NodeType, EdgeType,
)
from .ingestion import RawCorpus, RawDoc
from .util import content_hash, section_from_doc_path
from .logging_setup import get_logger

logger = get_logger()

_GLOSSARY_DIR = "reference/glossary"
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
_H3_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
_LINK_RE = re.compile(r"\]\((/docs/[^)#?]+)")


def _fm(text: Optional[str]) -> Dict:
    if not text:
        return {}
    try:
        return yaml.safe_load(text) or {}
    except Exception as e:  # malformed front matter -> treat as empty
        logger.warning("front-matter parse failed: %s", e)
        return {}


def _line_of(body: str, snippet: str) -> Optional[int]:
    idx = body.find(snippet)
    if idx == -1:
        return None
    return body.count("\n", 0, idx) + 1


# --------------------------------------------------------------------------
# Glossary
# --------------------------------------------------------------------------

def build_glossary_nodes(corpus: RawCorpus, g: KnowledgeGraph) -> Dict[str, str]:
    """Return mapping term_id -> node id."""
    id_map: Dict[str, str] = {}
    for d in corpus.docs:
        if _GLOSSARY_DIR not in d.rel_path:
            continue
        fm = _fm(d.front_matter)
        term_id = fm.get("id") or os.path.splitext(os.path.basename(d.rel_path))[0]
        node_id = "gloss:" + term_id
        prov = Provenance(
            source=d.rel_path, url=d.url,
            line_start=_line_of(d.body_raw, "title:"),
            quote=(fm.get("short_description") or "").strip(),
        )
        node = Node(
            id=node_id,
            type=NodeType.GLOSSARY.value,
            title=fm.get("title", term_id),
            summary=(fm.get("short_description") or "").strip(),
            body=d.body_norm,
            version=corpus.version,
            tags=fm.get("tags", []) or [],
            url=fm.get("full_link") or d.url,
            provenance=[prov],
        )
        g.add_node(node)
        id_map[term_id] = node_id
    logger.info("glossary nodes: %d", len(id_map))
    return id_map


# --------------------------------------------------------------------------
# Pages + concepts + baseline edges
# --------------------------------------------------------------------------

def build_page_nodes(corpus: RawCorpus, g: KnowledgeGraph, glossary_ids: Dict[str, str],
                     trim_bodies: bool = True, body_max: int = 4000) -> Dict[str, str]:
    page_map: Dict[str, str] = {}
    for d in corpus.docs:
        if _GLOSSARY_DIR in d.rel_path:
            continue  # already handled
        fm = _fm(d.front_matter)
        section = section_from_doc_path("docs/" + d.rel_path)
        node_id = "page:" + d.rel_path.replace(".md", "")
        title = fm.get("title") or os.path.splitext(os.path.basename(d.rel_path))[0]
        body = d.body_norm
        trimmed = False
        if trim_bodies and len(body) > body_max:
            body = body[:body_max] + "\n…(trimmed)"
            trimmed = True
        prov = Provenance(source=d.rel_path, url=d.url,
                          quote=title)
        node = Node(
            id=node_id,
            type=NodeType.PAGE.value,
            title=title,
            summary=fm.get("description", "") or "",
            body=body,
            body_trimmed=trimmed,
            version=corpus.version,
            section=section,
            tags=[section],
            url=d.url,
            meta={"weight": fm.get("weight"),
                  "rel_path": d.rel_path},
            provenance=[prov],
        )
        g.add_node(node)
        page_map[d.rel_path] = node_id

        # glossary references -> edges (THE backbone of the concept graph)
        for ref in d.refs:
            if ref.get("kind") != "glossary_tooltip":
                continue
            tid = ref["term_id"]
            if tid in glossary_ids:
                line = _line_of(d.body_raw, "term_id=\"" + tid + "\"")
                g.add_edge(Edge(
                    from_id=node_id, to_id=glossary_ids[tid],
                    type=EdgeType.REFERENCES.value,
                    label=ref.get("text", tid),
                    provenance=[Provenance(source=d.rel_path, url=d.url, line_start=line,
                                           quote=ref.get("text", ""))],
                ))
        # definitions
        for ref in d.refs:
            if ref.get("kind") == "glossary_definition" and ref["term_id"] in glossary_ids:
                g.add_edge(Edge(
                    from_id=node_id, to_id=glossary_ids[ref["term_id"]],
                    type=EdgeType.DEFINES.value,
                    provenance=[Provenance(source=d.rel_path, url=d.url)],
                ))
        # intra-doc links
        for target in _LINK_RE.findall(d.body_raw):
            trel = target.strip("/").replace("/docs/", "", 1)
            trel = trel + (".md" if not trel.endswith(".md") else "")
            tnode = page_map.get(trel)
            if tnode:
                g.add_edge(Edge(
                    from_id=node_id, to_id=tnode,
                    type=EdgeType.LINKS_TO.value,
                    label=target,
                    provenance=[Provenance(source=d.rel_path, url=d.url)],
                ))
        # derived concepts from H2/H3 headings
        for m in list(_H2_RE.finditer(d.body_raw)) + list(_H3_RE.finditer(d.body_raw)):
            heading = m.group(1).strip()
            slug = util_slug(heading)
            cid = "concept:" + slug
            if not any(n.id == cid for n in g.nodes):
                cnode = Node(
                    id=cid, type=NodeType.CONCEPT.value, title=heading,
                    summary="", version=corpus.version, section=section,
                    tags=[section],
                    provenance=[Provenance(source=d.rel_path, url=d.url,
                                           line_start=m.start() // max(1, 0) + 1)],
                )
                g.add_node(cnode)
            g.add_edge(Edge(
                from_id=node_id, to_id=cid,
                type=EdgeType.PART_OF.value, label="describes",
                provenance=[Provenance(source=d.rel_path, url=d.url,
                                        line_start=_line_of(d.body_raw, heading))],
            ))
    return page_map


def util_slug(text: str) -> str:
    from .util import slugify
    return slugify(text)


# --------------------------------------------------------------------------
# Swagger -> API nodes
# --------------------------------------------------------------------------

def build_api_nodes(corpus: RawCorpus, g: KnowledgeGraph,
                    page_map: Dict[str, str]) -> Dict[str, str]:
    """swagger.json -> API_OBJECT + API_PATH nodes; cross-link to docs (api_for)."""
    api_map: Dict[str, str] = {}
    spec = corpus.swagger
    if not spec:
        return api_map
    # definitions -> API_OBJECT
    for name, defn in (spec.get("definitions") or {}).items():
        # name like io.k8s.api.apps.v1.Deployment
        parts = name.split(".")
        kind = parts[-1]
        group = parts[-3] if len(parts) >= 3 else "core"
        version = parts[-2] if len(parts) >= 3 else "v1"
        node_id = "api:" + kind
        fields = list((defn.get("properties") or {}).keys())
        node = Node(
            id=node_id, type=NodeType.API_OBJECT.value, title=kind,
            summary=defn.get("description", "") or "",
            version=corpus.version,
            tags=[group],
            meta={"group": group, "version": version, "fields": fields[:50],
                  "field_count": len(fields), "def_name": name},
            provenance=[Provenance(source="swagger.json", quote=name)],
        )
        g.add_node(node)
        api_map[kind] = node_id

    # paths -> API_PATH
    for path, ops in (spec.get("paths") or {}).items():
        for method, op in ops.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue
            node_id = "apipath:" + method.lower() + " " + path
            # infer the API object kind from the path (e.g. .../v1/deployments -> Deployment)
            seg = [s for s in path.split("/") if s and "{" not in s]
            kind = seg[-1].split(".")[0].split("-")[0].split("(")[0].capitalize() \
                if seg else method
            title = op.get("operationId", method + " " + path)
            g.add_node(Node(
                id=node_id, type=NodeType.API_PATH.value,
                title=title,
                summary=op.get("description", "") or "",
                body=f"{method.upper()} {path}",
                version=corpus.version,
                tags=[path.split("/")[1] if path.startswith("/apis/") else "core"],
                meta={"method": method.lower(), "path": path,
                      "operationId": op.get("operationId"), "kind": kind},
                provenance=[Provenance(source="swagger.json", quote=path)],
            ))
            # link the API path to its API object (keeps it connected, not an orphan)
            if kind in api_map:
                g.add_edge(Edge(
                    from_id=node_id, to_id=api_map[kind],
                    type=EdgeType.RELATED_TO.value, label="exposes API object",
                    provenance=[Provenance(source="swagger.json", quote=path)],
                ))
    # cross-link: pages whose title matches a Kind get api_for edge
    linked = 0
    for node in g.nodes:
        if node.type != NodeType.PAGE.value:
            continue
        kind = _match_kind(node.title, api_map)
        if kind:
            g.add_edge(Edge(
                from_id=node.id, to_id=api_map[kind],
                type=EdgeType.API_FOR.value, label="documents API object",
                provenance=[Provenance(source=node.meta.get("rel_path", ""), url=node.url)],
            ))
            linked += 1
    logger.info("api objects: %d, api paths linked to docs: %d",
                len(api_map), linked)
    return api_map


def _match_kind(title: str, api_map: Dict[str, str]) -> Optional[str]:
    t = title.strip()
    for kind in api_map:
        if t == kind or t.lower().startswith(kind.lower() + " ") or \
           (kind.lower() in t.lower()):
            return kind
    return None


# --------------------------------------------------------------------------
# Orchestrate parsing
# --------------------------------------------------------------------------

def parse_corpus(corpus: RawCorpus, trim_bodies: bool = True,
                 body_max: int = 4000) -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.meta = dict(corpus.provenance_meta)
    g.meta["corpus"] = "kubernetes"
    g.meta["version"] = corpus.version
    g.meta["source_label"] = corpus.source_label
    g.meta["generator"] = "k8s-docs-compiler"
    glossary_ids = build_glossary_nodes(corpus, g)
    page_map = build_page_nodes(corpus, g, glossary_ids, trim_bodies, body_max)
    build_api_nodes(corpus, g, page_map)
    g.compute_stats()
    return g
