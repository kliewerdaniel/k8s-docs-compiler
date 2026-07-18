"""Phase 4 — Optimization passes.

Deterministic transformations that improve artifact quality and retrieval
efficiency without losing information:
  * dedupe        : merge nodes that resolve to the same logical entity
  * confidence_rank: lower-confidence edges sink (used by clients for ranking)
  * compress      : trim oversized bodies (already done at parse; re-applied here
                    if config changes) and drop empty/orphan nodes
  * cache_manifest: write a build manifest (ir_hash + corpus hash) for incremental
                    compilation (Phase 7 readiness)
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

from .ir import KnowledgeGraph, Node, Edge, NodeType
from .util import content_hash, atomic_write
from .logging_setup import get_logger

logger = get_logger()


def pass_dedupe(g: KnowledgeGraph) -> int:
    """Merge duplicate nodes by id (idempotent safety net)."""
    seen: Dict[str, Node] = {}
    unique: List[Node] = []
    dup = 0
    for n in g.nodes:
        if n.id in seen:
            dup += 1
            seen[n.id].provenance.extend(n.provenance)
        else:
            seen[n.id] = n
            unique.append(n)
    g.nodes = unique
    # drop edges referencing removed nodes
    valid = {n.id for n in g.nodes}
    g.edges = [e for e in g.edges if e.from_id in valid and e.to_id in valid]
    logger.info("dedupe removed %d duplicate nodes", dup)
    return dup


def pass_compress(g: KnowledgeGraph, body_max: int = 4000) -> int:
    trimmed = 0
    for n in g.nodes:
        if n.body and len(n.body) > body_max and not n.body_trimmed:
            n.body = n.body[:body_max] + "\n…(trimmed)"
            n.body_trimmed = True
            trimmed += 1
    logger.info("compressed %d bodies", trimmed)
    return trimmed


def pass_drop_orphans(g: KnowledgeGraph) -> int:
    """Drop nodes with no edges and no meaningful content (keeps graph clean).
    Nodes derived from the API spec (swagger.json) or with structured meta are
    always retained even if currently unlinked — they are primary artifacts.
    """
    connected = {e.from_id for e in g.edges} | {e.to_id for e in g.edges}
    keep: List[Node] = []
    removed = 0
    for n in g.nodes:
        if n.id in connected or (n.body and len(n.body) > 40) or n.meta or \
           any(p.source == "swagger.json" for p in n.provenance):
            keep.append(n)
        else:
            removed += 1
    g.nodes = keep
    # drop edges referencing removed nodes
    valid = {n.id for n in g.nodes}
    g.edges = [e for e in g.edges if e.from_id in valid and e.to_id in valid]
    return removed


def write_build_manifest(g: KnowledgeGraph, out_dir: str, corpus_hash: str) -> str:
    manifest = {
        "ir_hash": g.ir_hash(),
        "corpus_hash": corpus_hash,
        "node_count": len(g.nodes),
        "edge_count": len(g.edges),
        "version": g.meta.get("version"),
        "generator": g.meta.get("generator"),
    }
    path = os.path.join(out_dir, "build_manifest.json")
    atomic_write(path, json.dumps(manifest, indent=2))
    return path


def changed_since(out_dir: str, corpus_hash: str) -> bool:
    """Incremental compilation: True if corpus changed since last build."""
    path = os.path.join(out_dir, "build_manifest.json")
    if not os.path.exists(path):
        return True
    try:
        prev = json.load(open(path, "r", encoding="utf-8"))
        return prev.get("corpus_hash") != corpus_hash
    except Exception:
        return True
