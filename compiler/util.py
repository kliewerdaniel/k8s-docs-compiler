"""Shared utilities: hashing, deterministic normalization, caching, YAML front-matter."""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(obj: Any) -> str:
    """Stable hash of an arbitrary JSON-serializable structure."""
    return sha256_text(json.dumps(obj, sort_keys=True, default=str))


# --------------------------------------------------------------------------
# Front-matter parsing (YAML delimited by --- on its own line)
# --------------------------------------------------------------------------

_FRONT_MATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


def split_front_matter(text: str) -> Tuple[Optional[str], str]:
    """Return (front_matter_yaml, body). front_matter is None if absent."""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), m.group(2)


# --------------------------------------------------------------------------
# Hugo shortcode normalization
# --------------------------------------------------------------------------
# K8s docs use Goldmark + Hugo shortcodes. We normalize them to portable
# Markdown and surface machine-readable references for graph extraction.
#
# Extracted references are returned as a list of dicts so the parser/IR
# builder can turn them into typed edges (no information is lost).

# Matches either:  {{< name attrs >}}   or   {{< name attrs />}}
_SHORTCODE_RE = re.compile(r"\{\{<\s*([a-zA-Z_]+)((?:\s+[^>]*?)?)(?:\s*/)?\s*>\}\}")
_CLOSE_RE = re.compile(r"\{\{<\s*/\s*([a-zA-Z_]+)\s*>\}\}")


def _attrs(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in re.findall(r'(\w+)\s*=\s*"([^"]*)"', raw):
        out[k] = v
    return out


def normalize_shortcodes(body: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Normalize Hugo shortcodes -> portable Markdown.

    Handles both `{{< ... >}}` and `{{% ... %}}` delimiters (K8s docs use both),
    paired and self-closing. Strips HTML comments. Returns (normalized_body, refs).
    """
    # Normalize {{% ... %}} to {{< ... >}} so the single tokenizer handles both.
    body = body.replace("{{%", "{{<").replace("%}}", ">}}")
    # Strip HTML comments (e.g. <!--more-->).
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    out_parts: List[str] = []
    refs: List[Dict[str, Any]] = []
    i = 0
    n = len(body)

    while i < n:
        m = _SHORTCODE_RE.search(body, i)
        if not m:
            out_parts.append(body[i:])
            break
        out_parts.append(body[i : m.start()])
        name = m.group(1)
        attrs = _attrs(m.group(2))

        if name == "glossary_tooltip":
            term_id = attrs.get("term_id", "")
            text = attrs.get("text", term_id)
            refs.append({"kind": "glossary_tooltip", "term_id": term_id, "text": text})
            out_parts.append("[" + text + "](#gloss:" + term_id + ")")
            i = m.end()
            continue
        if name == "glossary_definition":
            term_id = attrs.get("term_id", "")
            refs.append({"kind": "glossary_definition", "term_id": term_id})
            out_parts.append("[definition:" + term_id + "]")
            i = m.end()
            continue
        if name == "figure":
            src = attrs.get("src", "")
            alt = attrs.get("alt", "")
            cap = attrs.get("caption", "")
            if cap:
                out_parts.append("\n![" + alt + "](" + src + ") — " + cap + "\n")
            else:
                out_parts.append("\n![" + alt + "](" + src + ")\n")
            i = m.end()
            continue

        # Paired shortcode: find matching closer, keep inner content.
        close = "{{< /" + name + " >}}"
        end = body.find(close, m.end())
        if end == -1:
            # No closer found: drop the opener and continue.
            i = m.end()
            continue
        inner = body[m.end() : end]
        inner = _unfold_paired(name, attrs, inner)
        out_parts.append(inner)
        i = end + len(close)

    text = "".join(out_parts)
    # Clean up any stray shortcode fragments left by malformed input.
    return _strip_residual(text), refs


def _unfold_paired(name: str, attrs: Dict[str, str], inner: str) -> str:
    if name == "mermaid":
        return "\n```mermaid\n" + inner.strip() + "\n```\n"
    if name == "details":
        summary = attrs.get("summary", "")
        return "\n<details><summary>" + summary + "</summary>\n\n" + inner.strip() + "\n</details>\n"
    if name in ("note", "warning", "caution", "tip"):
        return "\n> **" + name.capitalize() + ":** " + inner.strip() + "\n"
    # generic: drop wrapper, keep inner
    return inner


_RESIDUAL_RE = re.compile(r"\{\{<[^>]*?(?:/>|>)\}\}")


def _strip_residual(text: str) -> str:
    return _RESIDUAL_RE.sub("", text)


# --------------------------------------------------------------------------
# Misc helpers
# --------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "untitled"


def section_from_doc_path(rel_path: str) -> str:
    """content/en/docs/<section>/... -> <section>"""
    parts = rel_path.split("/")
    try:
        idx = parts.index("docs")
        return parts[idx + 1] if idx + 1 < len(parts) else "root"
    except ValueError:
        return "root"


def atomic_write(path: str, data: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, path)



# Simple content-addressed cache (for expensive passes)
# --------------------------------------------------------------------------

class FileCache:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, key[:2], key + ".json")

    def get(self, key: str) -> Optional[Any]:
        p = self._path(key)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def put(self, key: str, value: Any) -> None:
        p = self._path(key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(value, f)

    def cached(self, key: str, compute, *args):
        hit = self.get(key)
        if hit is not None:
            return hit
        val = compute(*args)
        self.put(key, val)
        return val
