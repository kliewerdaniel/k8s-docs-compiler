"""Phase 1 — Ingestion.

Fetches/loads Kubernetes documentation sources and the API spec, preserving
provenance (source path, canonical URL, content hash). Deterministic: no LLM.

Supports two source modes:
  * local  : a checkout of kubernetes/website at content/en/docs
  * fixture: a directory of sample .md files (used by tests / offline demos)

The swagger spec can come from a local path or a URL.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

from .util import split_front_matter, normalize_shortcodes, sha256_text, \
    section_from_doc_path, content_hash
from . import util
from .logging_setup import get_logger

logger = get_logger()

DOCS_BASE_URL = "https://kubernetes.io"


@dataclass
class RawDoc:
    """A single unparsed source document."""
    rel_path: str            # path relative to content/en/docs (or fixtures root)
    front_matter: Optional[str]
    body_raw: str
    body_norm: str
    refs: List[Dict]         # glossary_tooltip / glossary_definition references
    content_hash: str
    url: Optional[str] = None


@dataclass
class RawCorpus:
    docs: List[RawDoc]
    swagger: Optional[Dict]
    version: str
    source_label: str
    provenance_meta: Dict


# --------------------------------------------------------------------------
# Local checkout ingestion
# --------------------------------------------------------------------------

def ingest_local(docs_root: str, swagger_path: Optional[str], version: str,
                 exclude_sections: Optional[List[str]] = None) -> RawCorpus:
    exclude_sections = exclude_sections or []
    docs: List[RawDoc] = []
    if not os.path.isdir(docs_root):
        raise FileNotFoundError(f"docs_root not found: {docs_root}")

    for root, _dirs, files in os.walk(docs_root):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, docs_root)
            section = util.section_from_doc_path("docs/" + rel)
            if section in exclude_sections:
                continue
            with open(full, "r", encoding="utf-8") as f:
                text = f.read()
            fm, body = split_front_matter(text)
            # Always normalize so we get refs even before parsing.
            body_norm, refs = normalize_shortcodes(body)
            url = DOCS_BASE_URL + "/docs/" + rel.replace(".md", "/")
            docs.append(RawDoc(
                rel_path=rel,
                front_matter=fm,
                body_raw=body,
                body_norm=body_norm,
                refs=refs,
                content_hash=sha256_text(text),
                url=url,
            ))
    logger.info("ingested %d docs from %s", len(docs), docs_root)
    swagger = _load_swagger(swagger_path)
    return RawCorpus(
        docs=docs,
        swagger=swagger,
        version=version,
        source_label=f"local:{docs_root}",
        provenance_meta={"docs_root": docs_root, "version": version},
    )


# --------------------------------------------------------------------------
# Fixture ingestion (tests / offline demo)
# --------------------------------------------------------------------------

def ingest_fixtures(fixtures_dir: str, version: str = "fixture",
                    swagger_path: Optional[str] = None) -> RawCorpus:
    docs: List[RawDoc] = []
    if not os.path.isdir(fixtures_dir):
        raise FileNotFoundError(f"fixtures_dir not found: {fixtures_dir}")
    for root, _dirs, files in os.walk(fixtures_dir):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, fixtures_dir)
            with open(full, "r", encoding="utf-8") as f:
                text = f.read()
            fm, body = split_front_matter(text)
            body_norm, refs = normalize_shortcodes(body)
            docs.append(RawDoc(
                rel_path=rel,
                front_matter=fm,
                body_raw=body,
                body_norm=body_norm,
                refs=refs,
                content_hash=sha256_text(text),
                url=None,
            ))
    swagger = _load_swagger(swagger_path)
    return RawCorpus(
        docs=docs,
        swagger=swagger,
        version=version,
        source_label=f"fixtures:{fixtures_dir}",
        provenance_meta={"fixtures_dir": fixtures_dir, "version": version},
    )


# --------------------------------------------------------------------------
# Swagger loader
# --------------------------------------------------------------------------

def _load_swagger(swagger_path: Optional[str]) -> Optional[Dict]:
    if not swagger_path:
        return None
    if swagger_path.startswith("http://") or swagger_path.startswith("https://"):
        logger.info("fetching swagger from %s", swagger_path)
        with urllib.request.urlopen(swagger_path, timeout=30) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8"))
    if os.path.exists(swagger_path):
        with open(swagger_path, "r", encoding="utf-8") as f:
            return json.load(f)
    logger.warning("swagger_path not found: %s", swagger_path)
    return None
