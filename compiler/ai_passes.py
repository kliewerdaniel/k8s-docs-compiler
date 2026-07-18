"""Optional AI-assisted passes — the "synthesis" half of compile-time AI.

These passes are OPTIONAL and OFF by default. When enable_ai is False the
compiler is 100% deterministic and reproducible. When enabled, local inference
is used ONLY to synthesize readable documentation from the *already-extracted,
traceable source quotes* — it does not invent facts, it organizes and explains
them. Every AI-produced artifact is:
  * marked derived_by="ai:<model>" and given confidence < 1.0
  * grounded in node.provenance (source quote shown to the model)
  * cached by content hash (re-runs are free and reproducible)
  * schema-validated; on any failure we fall back to the deterministic value
    (the build never blocks on inference)

Pluggable design
----------------
Passes are registered in PASS_REGISTRY and toggled independently via the
`ai_passes` config list. Different use cases add/remove LLM calls without
touching the deterministic core. Examples:
  --ai                               # run all registered passes
  --ai-passes synthesis              # only synthesize knowledge cards
  --ai-passes synthesis,prerequisites # synthesize + discover prereqs
  --ai-passes ""                     # deterministic (same as no --ai)

Endpoints
---------
The client is endpoint-agnostic. It speaks both:
  * OpenAI-compatible /v1/chat/completions  (e.g. llama.cpp on :8080)
  * Ollama /api/generate                      (e.g. llama3.1:8b on :11434)
If a thinking model emits only reasoning_content (empty content), the client
falls back to the reasoning trace so the endpoint is not wasted.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from .ir import KnowledgeGraph, Edge, Node, Provenance, NodeType, EdgeType
from .config import CompilerConfig
from .util import content_hash
from .logging_setup import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Endpoint-agnostic inference client
# ---------------------------------------------------------------------------

class AIPassClient:
    """Talks to either an OpenAI-compatible /v1/chat/completions endpoint or an
    Ollama /api/generate endpoint. Returns parsed JSON or None on failure."""

    def __init__(self, url: str, model: str, timeout: float = 60.0,
                 kind: Optional[str] = None):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        if kind:
            self.kind = kind
        elif "11434" in self.url or self.url.rstrip("/").endswith("/api/generate"):
            self.kind = "ollama"
        else:
            self.kind = "openai"

    def chat_json(self, system: str, user: str,
                  max_tokens: int = 700, temperature: float = 0.3) -> Optional[dict]:
        try:
            if self.kind == "ollama":
                return self._ollama(system, user, max_tokens, temperature)
            return self._openai(system, user, max_tokens, temperature)
        except Exception as e:  # noqa: BLE001
            logger.warning("AI call failed (fallback to deterministic): %s", e)
            return None

    def _ollama(self, system, user, max_tokens, temperature) -> Optional[dict]:
        payload = json.dumps({
            "model": self.model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }).encode("utf-8")
        endpoint = self.url if self.url.rstrip("/").endswith("/api/generate") \
            else self.url + "/api/generate"
        req = urllib.request.Request(
            endpoint, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
            resp = json.loads(r.read().decode("utf-8"))
        return _extract_json(resp.get("response", ""))

    def _openai(self, system, user, max_tokens, temperature) -> Optional[dict]:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.url + "/v1/chat/completions",
            data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
            resp = json.loads(r.read().decode("utf-8"))
        msg = resp["choices"][0]["message"]
        text = msg.get("content") or ""
        # thinking-model fallback: llama.cpp builds sometimes put the answer in
        # reasoning_content and leave content empty
        if not text.strip() and msg.get("reasoning_content"):
            text = msg["reasoning_content"]
        return _extract_json(text)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Caching (reproducible: keyed by model + prompt hash)
# ---------------------------------------------------------------------------

def _cache_path(cache_dir: str, key: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "ai_" + key[:40] + ".json")


def _cached(fn: Callable[[], Optional[dict]], cache_dir: str, key: str
            ) -> Optional[dict]:
    p = _cache_path(cache_dir, key)
    if os.path.exists(p):
        try:
            return json.load(open(p, "r", encoding="utf-8"))
        except Exception:
            pass
    out = fn()
    if out is not None:
        try:
            json.dump(out, open(p, "w", encoding="utf-8"))
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Pass implementations
# ---------------------------------------------------------------------------

def _grounded_context(n: Node, max_quotes: int = 3) -> str:
    quotes = []
    for p in n.provenance[:max_quotes]:
        if p.quote:
            quotes.append(f'- "{p.quote[:300]}"  (source: {p.source})')
    if quotes:
        return "Source quotes (use these; do not invent others):\n" + "\n".join(quotes)
    if n.body:
        return "Extracted body:\n" + n.body[:1500]
    return f"Title: {n.title}"


def _render_card(card: dict) -> str:
    parts = []
    if card.get("overview"):
        parts.append(card["overview"].strip())
    if card.get("why_it_matters"):
        parts.append("\n**Why it matters**\n" + card["why_it_matters"].strip())
    if card.get("key_facts"):
        parts.append("\n**Key facts**")
        parts.append("\n".join(f"- {f}" for f in card["key_facts"] if f))
    if card.get("pitfalls"):
        parts.append("\n**Common pitfalls**")
        parts.append("\n".join(f"- {f}" for f in card["pitfalls"] if f))
    if card.get("related"):
        parts.append("\n**Related**\n" + ", ".join(str(x) for x in card["related"] if x))
    return "\n".join(parts).strip()


def pass_synthesis(g: KnowledgeGraph, client: Any, cache_dir: str,
                   max_nodes: int = 4000, max_workers: int = 4,
                   batch_size: int = 10,
                   include_types: Optional[tuple] = None) -> int:
    """Synthesize a grounded, readable knowledge card for each substantive node.
    Writes the card into node.body (so the frontend 'detail' view shows real
    documentation) and a one-line node.summary. Deterministic body is preserved
    as fallback when inference fails.

    By default we target glossary + page + api_object nodes (the high-value
    knowledge surfaces) and skip the thousands of low-value `concept` (heading)
    nodes. To keep corpus-scale compiles practical, nodes are synthesized in
    BATCHES (N cards per model call); results are cached per batch by content
    hash so re-runs are free and reproducible.
    """
    if include_types is None:
        include_types = (NodeType.GLOSSARY.value, NodeType.PAGE.value,
                         NodeType.API_OBJECT.value)
    system = (
        "You are a senior Kubernetes technical writer. Given a list of concepts "
        "with their source quotes, write a knowledge card for EACH as strict JSON: "
        "{\"cards\":[{\"id\":string,\"overview\":string,\"why_it_matters\":string,"
        "\"key_facts\":[string],\"pitfalls\":[string],\"related\":[string]}]}. "
        "Ground every claim in the provided source quotes. Be concise and accurate. "
        "Return one card per concept id. No preamble, JSON only."
    )

    def _jobs():
        for n in g.nodes:
            if n.type not in include_types:
                continue
            if n.body and len(n.body) > 600:  # already has real deterministic content
                continue
            yield n

    nodes = [n for n in _jobs()][:max_nodes]
    if not nodes:
        return 0
    model = getattr(client, "model", "client")
    by_id = {n.id: n for n in nodes}

    def _batch(b: List[Node]):
        items = []
        for n in b:
            ctx = _grounded_context(n)
            items.append(f"id={n.id}\nConcept: {n.title}\n{ctx}")
        user = ("Write a card for each concept below.\n\n" +
                "\n\n---\n\n".join(items) +
                f"\n\nReturn JSON with a 'cards' array; each card must include the "
                f"matching 'id'. ({len(b)} cards expected.)")
        key = content_hash({"m": model, "t": "synth_batch", "c": user})
        out = _cached(lambda: client.chat_json(system, user,
                                               max_tokens=700 * len(b)),
                      cache_dir, key)
        if not out:
            return
        cards = out.get("cards") or []
        for c in cards:
            cid = c.get("id")
            n = by_id.get(cid)
            if not n:
                continue
            body = _render_card(c)
            if not body:
                continue
            if not n.summary or len(n.summary) < 40:
                n.summary = (c.get("overview") or n.summary or "")[:200]
            n.body = body
            n.body_trimmed = False
            n.confidence = min(n.confidence, 0.82)
            n.derived_by = "ai:" + model

    batches = [nodes[i:i + batch_size] for i in range(0, len(nodes), batch_size)]
    done = 0
    if max_workers and max_workers > 1 and len(batches) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for _ in ex.map(_batch, batches):
                pass
    else:
        for b in batches:
            _batch(b)
    # count synthesized
    done = sum(1 for n in nodes if n.derived_by.startswith("ai:"))
    logger.info("synthesis cards generated: %d (batches=%d)", done, len(batches))
    return done


def pass_prerequisites(g: KnowledgeGraph, client: AIPassClient, cache_dir: str,
                       glossary_ids: Dict[str, str], max_nodes: int = 200) -> int:
    added = 0
    done = 0
    if not glossary_ids:
        return 0
    id_list = list(glossary_ids.keys())
    system = ("You map Kubernetes prerequisite relationships. Return strict JSON: "
              "{\"prerequisites\":[string]}. Only use ids from the provided list.")
    for n in g.nodes:
        if n.type != NodeType.GLOSSARY.value:
            continue
        if done >= max_nodes:
            break
        done += 1
        ids = ", ".join(id_list[:80])
        user = (f"Concept: {n.title}\nList up to 3 glossary ids a reader should "
                f"understand BEFORE it. Allowed ids: {ids}")
        key = content_hash({"m": getattr(client, "model", "client"), "t": "pre", "c": user})
        out = _cached(lambda: client.chat_json(system, user, max_tokens=300),
                      cache_dir, key)
        if not out:
            continue
        for pid in out.get("prerequisites", []) or []:
            if pid in glossary_ids and glossary_ids[pid] != n.id:
                g.add_edge(Edge(
                    from_id=glossary_ids[pid], to_id=n.id,
                    type=EdgeType.PREREQUISITE_OF.value,
                    label="ai-suggested prerequisite",
                    confidence=0.7, derived_by="ai:" + client.model,
                    provenance=[Provenance(source="ai:" + client.model,
                                           quote=f"prereq of {n.title}")],
                ))
                added += 1
    logger.info("ai prerequisite edges: %d", added)
    return added


def pass_clusters(g: KnowledgeGraph, client: AIPassClient, cache_dir: str,
                  max_nodes: int = 400) -> int:
    labelset = ["networking", "storage", "security", "scheduling", "observability",
                "workloads", "api", "cli", "extensibility"]
    done = 0
    system = ("Assign 1-3 topical labels from the given list. Return strict JSON: "
              "{\"labels\":[string]}.")
    for n in g.nodes:
        if any(t in labelset for t in n.tags):
            continue
        if done >= max_nodes:
            break
        done += 1
        user = f"Concept: {n.title}\nLabels: {', '.join(labelset)}"
        key = content_hash({"m": getattr(client, "model", "client"), "t": "clu", "c": user})
        out = _cached(lambda: client.chat_json(system, user, max_tokens=200),
                      cache_dir, key)
        if out:
            for lab in out.get("labels", []) or []:
                if lab in labelset and lab not in n.tags:
                    n.tags.append(lab)
    logger.info("ai cluster labels applied to %d nodes", done)
    return done


# ---------------------------------------------------------------------------
# Registry + orchestration
# ---------------------------------------------------------------------------

PASS_REGISTRY: Dict[str, Callable] = {
    "synthesis": pass_synthesis,
    "prerequisites": pass_prerequisites,
    "clusters": pass_clusters,
}


def resolve_passes(enabled: bool, ai_passes: Optional[str]) -> List[str]:
    if not enabled:
        return []
    if ai_passes:
        names = [p.strip() for p in ai_passes.split(",") if p.strip()]
        unknown = [n for n in names if n not in PASS_REGISTRY]
        if unknown:
            logger.warning("unknown AI passes ignored: %s", unknown)
        return [n for n in names if n in PASS_REGISTRY]
    return list(PASS_REGISTRY.keys())


def run_ai_passes(g: KnowledgeGraph, cfg: CompilerConfig,
                  glossary_ids: Dict[str, str]) -> None:
    names = resolve_passes(cfg.enable_ai, getattr(cfg, "ai_passes", None))
    if not names:
        logger.info("AI passes disabled (deterministic build)")
        return
    client = AIPassClient(cfg.ai_url, cfg.ai_model, cfg.ai_timeout_s)
    logger.info("AI passes enabled: %s (model=%s, url=%s)", names, cfg.ai_model, cfg.ai_url)
    for name in names:
        fn = PASS_REGISTRY[name]
        if name == "prerequisites":
            fn(g, client, cfg.cache_dir, glossary_ids)
        else:
            fn(g, client, cfg.cache_dir)
    logger.info("AI passes complete")
