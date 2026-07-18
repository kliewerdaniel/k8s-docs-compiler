"""Compiler orchestrator — wires the 5 phases into one reproducible pipeline.

Usage:
    from compiler.compiler import Compiler
    c = Compiler(config)
    graph = c.compile()          # or c.compile_fixtures(dir)
    c.save(graph)
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

from .config import CompilerConfig
from .logging_setup import setup_logging, get_logger
from . import ingestion, parser, k8s_passes, optimize, artifacts, ai_passes
from .ir import KnowledgeGraph, NodeType
from .util import content_hash


class Compiler:
    def __init__(self, config: CompilerConfig):
        self.cfg = config
        setup_logging(config.log_level, config.log_file)
        self.log = get_logger()
        os.makedirs(config.out_dir, exist_ok=True)
        os.makedirs(config.cache_dir, exist_ok=True)

    # ---- build from local checkout ----
    def compile(self) -> KnowledgeGraph:
        t0 = time.time()
        self.log.info("=== k8s-docs-compiler: COMPILE ===")
        corpus = ingestion.ingest_local(
            self.cfg.docs_root or "content/en/docs",
            self.cfg.swagger_path, self.cfg.version,
            exclude_sections=self.cfg.exclude_sections,
        )
        graph = self._build(corpus, t0)
        return graph

    # ---- build from fixtures (tests / offline demo) ----
    def compile_fixtures(self, fixtures_dir: str,
                         swagger_path: Optional[str] = None) -> KnowledgeGraph:
        t0 = time.time()
        self.log.info("=== k8s-docs-compiler: COMPILE (fixtures) ===")
        corpus = ingestion.ingest_fixtures(fixtures_dir, version=self.cfg.version,
                                           swagger_path=swagger_path)
        return self._build(corpus, t0)

    def _build(self, corpus, t0: float) -> KnowledgeGraph:
        # Phase 2: parse -> IR
        graph = parser.parse_corpus(corpus, trim_bodies=self.cfg.trim_bodies,
                                    body_max=self.cfg.body_max_chars)
        glossary_ids = {n.id.split(":", 1)[1]: n.id
                        for n in graph.nodes if n.type == NodeType.GLOSSARY.value}

        # Phase 3: K8s-specific knowledge passes (deterministic)
        k8s_passes.pass_ownership_chain(graph, corpus.version)
        k8s_passes.pass_api_relationships(graph, corpus.swagger)
        k8s_passes.pass_rbac_graph(graph)
        k8s_passes.pass_control_plane(graph, corpus.version)
        k8s_passes.pass_domain_concepts(graph)
        k8s_passes.pass_kubectl_flow(graph, corpus.version)

        # Optional AI passes (deterministic if disabled)
        ai_passes.run_ai_passes(graph, self.cfg, glossary_ids)

        # Phase 4: optimization
        optimize.pass_dedupe(graph)
        optimize.pass_compress(graph, self.cfg.body_max_chars)
        optimize.pass_drop_orphans(graph)

        # stats + validation
        graph.compute_stats()
        errors = graph.validate()
        if errors:
            for e in errors:
                self.log.warning("validation: %s", e)
        else:
            self.log.info("validation: OK (no errors)")

        graph.stats.build_seconds = round(time.time() - t0, 3)
        self.log.info("build complete in %.3fs — nodes=%d edges=%d density=%.4f",
                      graph.stats.build_seconds, len(graph.nodes),
                      len(graph.edges), graph.stats.graph_density)
        return graph

    # ---- Phase 5 + manifest ----
    def save(self, graph: KnowledgeGraph) -> Dict[str, str]:
        corpus_hash = content_hash(graph.meta)
        paths = artifacts.emit_all(
            graph, self.cfg.out_dir,
            emit_json_=self.cfg.emit_json,
            emit_sqlite_=self.cfg.emit_sqlite,
            emit_gexf_=self.cfg.emit_gexf,
            emit_web_=self.cfg.emit_web,
        )
        manifest = optimize.write_build_manifest(graph, self.cfg.out_dir, corpus_hash)
        paths["manifest"] = manifest
        self.log.info("artifacts: %s", ", ".join(f"{k}={v}" for k, v in paths.items()))
        return paths
