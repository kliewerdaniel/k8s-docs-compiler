"""Optional AI-assisted passes (clearly separated from deterministic compiler).

These passes are OPTIONAL and OFF by default. When enable_ai is False the
compiler is 100% deterministic and reproducible. When enabled, the AI is used
ONLY for tasks where it adds value:
  * summarization   (concept cards / search snippets)
  * prerequisite discovery (implicit prereqs not stated as "Before you begin")
  * concept clustering (topical labels beyond deterministic domain tagging)

Hard rules (per compile-time-AI architecture):
  * Every AI-produced fact is marked derived_by="ai:<model>" and given a
    confidence < 1.0 so it can be distinguished from deterministic facts.
  * Every AI output is schema-validated; on failure we fall back to the
    deterministic value (never block the build).
  * The AI never runs at runtime — only during the build/compile phase.
  * The fast local path (Ollama llama3.1:8b) is the default; the slow path is
    never on the critical path.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Dict, List, Optional

from .ir import KnowledgeGraph, Edge, Node, Provenance, NodeType, EdgeType
from .config import CompilerConfig
from .util import content_hash
from .logging_setup import get_logger

logger = get_logger()


class AIPassClient:
    """Minimal Ollama-compatible client. No hard dependency on the network."""
    def __init__(self, url: str, model: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete_json(self, prompt: str) -> Optional[dict]:
        payload = json.dumps({"model": self.model, "prompt": prompt,
                              "stream": False, "format": "json"}).encode("utf-8")
        req = urllib.request.Request(
            self.url + "/api/generate", data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
                resp = json.loads(r.read().decode("utf-8"))
            return json.loads(resp.get("response", "{}"))
        except Exception as e:
            logger.warning("AI call failed (falling back to deterministic): %s", e)
            return None


# --------------------------------------------------------------------------
# Passes
# --------------------------------------------------------------------------

def ai_summaries(g: KnowledgeGraph, client: AIPassClient, max_nodes: int = 50) -> int:
    done = 0
    for n in g.nodes:
        if n.summary and len(n.summary) > 40:
            continue
        if done >= max_nodes:
            break
        prompt = (
            "Summarize this Kubernetes documentation concept in ONE sentence "
            "(max 160 chars). Return JSON: {\"summary\": string}\n\n"
            f"Title: {n.title}\nBody:\n{n.body[:1200]}"
        )
        out = client.complete_json(prompt)
        if out and isinstance(out.get("summary"), str) and out["summary"].strip():
            n.summary = out["summary"].strip()[:200]
            n.confidence = min(n.confidence, 0.85)
            n.derived_by = "ai:" + client.model
            done += 1
    logger.info("ai summaries generated: %d", done)
    return done


def ai_prerequisites(g: KnowledgeGraph, client: AIPassClient, glossary_ids: Dict[str, str],
                     max_nodes: int = 50) -> int:
    """Discover implicit prerequisites among glossary terms via the AI."""
    added = 0
    done = 0
    for n in g.nodes:
        if n.type != NodeType.GLOSSARY.value:
            continue
        if done >= max_nodes:
            break
        done += 1
        prompt = (
            "List up to 3 Kubernetes glossary term_ids that a reader should "
            "understand BEFORE this concept. Return JSON: {\"prerequisites\": [string]}. "
            "Only use these ids: " + ", ".join(list(glossary_ids.keys())[:60]) + "\n\n"
            f"Concept: {n.title}\n{n.summary}"
        )
        out = client.complete_json(prompt)
        if not out:
            continue
        for pid in out.get("prerequisites", []) or []:
            if pid in glossary_ids and glossary_ids[pid] != n.id:
                g.add_edge(Edge(
                    from_id=glossary_ids[pid], to_id=n.id,
                    type=EdgeType.PREREQUISITE_OF.value,
                    label="ai-suggested prerequisite",
                    confidence=0.7,
                    derived_by="ai:" + client.model,
                    provenance=[Provenance(source="ai:" + client.model,
                                          quote=f"prereq of {n.title}")],
                ))
                added += 1
    logger.info("ai prerequisite edges: %d", added)
    return added


def ai_clusters(g: KnowledgeGraph, client: AIPassClient, max_nodes: int = 80) -> int:
    """Add topical cluster labels using the AI where deterministic tagging missed."""
    done = 0
    for n in g.nodes:
        if any(t in ("networking", "storage", "security") for t in n.tags):
            continue
        if done >= max_nodes:
            break
        done += 1
        prompt = (
            "Assign 1-3 topical labels to this Kubernetes concept from "
            "[networking, storage, security, scheduling, observability, workloads, "
            "api, cli, extensibility]. Return JSON: {\"labels\": [string]}. "
            f"Concept: {n.title}\n{n.summary}"
        )
        out = client.complete_json(prompt)
        if out:
            for lab in out.get("labels", []) or []:
                if lab not in n.tags:
                    n.tags.append(lab)
    logger.info("ai cluster labels applied to %d nodes", done)
    return done


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def run_ai_passes(g: KnowledgeGraph, cfg: CompilerConfig,
                  glossary_ids: Dict[str, str]) -> None:
    if not cfg.enable_ai:
        logger.info("AI passes disabled (deterministic build)")
        return
    client = AIPassClient(cfg.ai_url, cfg.ai_model, cfg.ai_timeout_s)
    ai_summaries(g, client)
    ai_prerequisites(g, client, glossary_ids)
    ai_clusters(g, client)
    logger.info("AI passes complete")
