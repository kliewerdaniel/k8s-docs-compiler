"""Tests for the Kubernetes Knowledge Compiler.

Run:  pytest compiler/tests/

Coverage:
  * unit: shortcode normalization, front-matter, config coercion, hashing
  * integration: full fixture compile produces valid, reproducible graph
  * provenance: every edge/node carries source traceability
  * graph validity: no dangling edges, confidence in range
  * reproducibility: same input -> identical ir_hash
  * K8s passes: ownership, RBAC, control-plane, domain tagging produce edges
"""
import json
import os
import sqlite3

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "fixtures", "k8s_sample")
SWAG = os.path.join(ROOT, "fixtures", "swagger_min.json")

from compiler.config import CompilerConfig
from compiler.compiler import Compiler
from compiler.util import normalize_shortcodes, split_front_matter, content_hash
from compiler.ir import KnowledgeGraph, Node, Edge, NodeType, EdgeType, Provenance


# --------------------------------------------------------------------------
# UNIT
# --------------------------------------------------------------------------

def test_shortcode_glossary_tooltip():
    body = "A {{< glossary_tooltip text=\"pod\" term_id=\"pod\" >}} runs."
    norm, refs = normalize_shortcodes(body)
    assert "[pod](#gloss:pod)" in norm
    assert refs[0]["term_id"] == "pod"
    assert refs[0]["kind"] == "glossary_tooltip"


def test_shortcode_paired_note():
    body = "{{< note >}}Careful.{{< /note >}}"
    norm, refs = normalize_shortcodes(body)
    assert "> **Note:** Careful." in norm


def test_shortcode_mermaid():
    body = "{{< mermaid >}}graph TD; A-->B{{< /mermaid >}}"
    norm, _ = normalize_shortcodes(body)
    assert "```mermaid" in norm and "A-->B" in norm


def test_front_matter_split():
    fm, body = split_front_matter("---\ntitle: X\n---\nHello")
    assert fm is not None and "title: X" in fm
    assert body.strip() == "Hello"


def test_content_hash_stable():
    assert content_hash({"a": 1, "b": [1, 2]}) == content_hash({"b": [1, 2], "a": 1})


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("K8S_CC_VERSION", "v1.34")
    monkeypatch.setenv("K8S_CC_ENABLE_AI", "true")
    cfg = CompilerConfig.load()
    assert cfg.version == "v1.34"
    assert cfg.enable_ai is True


# --------------------------------------------------------------------------
# INTEGRATION
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph():
    cfg = CompilerConfig.load(overrides={
        "version": "fixture", "out_dir": "out_test", "swagger_path": SWAG})
    c = Compiler(cfg)
    g = c.compile_fixtures(FIX, swagger_path=SWAG)
    return g


def test_compile_produces_nodes(graph):
    assert len(graph.nodes) > 10
    types = {n.type for n in graph.nodes}
    assert NodeType.GLOSSARY.value in types
    assert NodeType.PAGE.value in types
    assert NodeType.API_OBJECT.value in types


def test_compile_creates_glossary_nodes(graph):
    gloss = [n for n in graph.nodes if n.type == NodeType.GLOSSARY.value]
    ids = {n.id for n in gloss}
    assert "gloss:pod" in ids
    assert "gloss:deployment" in ids


def test_references_edges_present(graph):
    refs = [e for e in graph.edges if e.type == EdgeType.REFERENCES.value]
    assert len(refs) > 0
    # deployment page references pod glossary
    dep_page = [n for n in graph.nodes if n.type == NodeType.PAGE.value
                and "run-deployment" in n.id][0]
    linked = {e.to_id for e in graph.edges
              if e.from_id == dep_page.id and e.type == EdgeType.REFERENCES.value}
    assert "gloss:pod" in linked


def test_rbac_requires_edges(graph):
    rbac = [e for e in graph.edges if e.type == EdgeType.REQUIRES.value]
    assert len(rbac) > 0


def test_control_plane_edges(graph):
    ctrl = [e for e in graph.edges if e.type == EdgeType.CONTROLS.value]
    assert len(ctrl) > 0


def test_api_relationship_edges(graph):
    rel = [e for e in graph.edges if e.type == EdgeType.RELATED_TO.value]
    assert len(rel) > 0


def test_domain_tagging(graph):
    net = [n for n in graph.nodes if "networking" in n.tags]
    assert len(net) > 0


def test_provenance_present(graph):
    # every node has at least one provenance entry
    for n in graph.nodes:
        assert n.provenance, f"node {n.id} has no provenance"
    # every edge has provenance unless it's a self/synthetic edge
    missing = [e for e in graph.edges if not e.provenance]
    # control-plane/ownership synthetic edges carry provenance too
    assert not missing, f"{len(missing)} edges lack provenance"


def test_validation_clean(graph):
    errs = graph.validate()
    assert errs == [], f"validation errors: {errs}"


def test_reproducible_ir_hash(graph):
    cfg = CompilerConfig.load(overrides={
        "version": "fixture", "out_dir": "out_test2", "swagger_path": SWAG})
    g2 = Compiler(cfg).compile_fixtures(FIX, swagger_path=SWAG)
    assert g2.ir_hash() == graph.ir_hash()


def test_sqlite_artifact_queryable(graph, tmp_path):
    from compiler import artifacts
    out = str(tmp_path / "out")
    paths = artifacts.emit_all(graph, out)
    db = paths["sqlite"]
    con = sqlite3.connect(db)
    cur = con.cursor()
    n = cur.execute("SELECT count(*) FROM nodes").fetchone()[0]
    e = cur.execute("SELECT count(*) FROM edges").fetchone()[0]
    assert n == len(graph.nodes)
    assert e == len(graph.edges)
    # edge_view join works
    rows = cur.execute(
        "SELECT from_title,to_title,type FROM edge_view LIMIT 3").fetchall()
    assert len(rows) == 3
    con.close()


def test_gexf_well_formed(graph, tmp_path):
    import xml.dom.minidom as minidom
    from compiler import artifacts
    out = str(tmp_path / "out")
    path = artifacts.emit_gexf(graph, out)
    doc = minidom.parse(path)  # raises if malformed XML
    assert doc.getElementsByTagName("gexf")


def test_incremental_manifest(graph, tmp_path):
    from compiler import optimize, artifacts
    out = str(tmp_path / "out")
    artifacts.emit_json(graph, out)
    optimize.write_build_manifest(graph, out, "hashabc")
    assert optimize.changed_since(out, "hashabc") is False
    assert optimize.changed_since(out, "different") is True


def test_ai_disabled_by_default_deterministic(graph):
    # no AI-derived nodes/edges should exist in a default build
    ai = [n for n in graph.nodes if n.derived_by.startswith("ai:")]
    ai_e = [e for e in graph.edges if e.derived_by.startswith("ai:")]
    assert not ai and not ai_e


# -------------------------------------------------------------------------
# AI SYNTHESIS PASS (offline: fake client, no network)
# -------------------------------------------------------------------------

class _FakeClient:
    """Returns scripted JSON so we can test the synthesis pass without a model.
    The batched pass expects a {"cards":[{id, ...}]} response."""
    def __init__(self):
        self.calls = 0
        self.model = "fake"
    def chat_json(self, system, user, max_tokens=700, temperature=0.3):
        self.calls += 1
        # one card per node we feed it (the test feeds a single-node batch)
        return {
            "cards": [{
                "id": "gloss:pod",
                "overview": "A Pod is the smallest deployable unit in Kubernetes.",
                "why_it_matters": "Pods are how your containers actually run.",
                "key_facts": ["Wraps one or more containers", "Shares storage/network"],
                "pitfalls": ["Don't run one-container-per-Pod blindly"],
                "related": ["Deployment", "ReplicaSet"],
            }]
        }


def test_synthesis_pass_populates_body():
    from compiler import ai_passes
    cfg = CompilerConfig.load(overrides={"cache_dir": "out_test_ai"})
    g = KnowledgeGraph(meta={"corpus_version": "t", "build_seconds": 0,
                              "source_url": "", "generated_at": "", "ir_version": 1})
    n = Node(id="gloss:pod", type=NodeType.GLOSSARY.value, title="Pod",
             summary="", body="",
             provenance=[Provenance(source="reference/glossary/pod.md",
                                    quote="Pods are the smallest deployable units.")])
    g.add_node(n)
    client = _FakeClient()
    done = ai_passes.pass_synthesis(g, client, cfg.cache_dir)
    assert done == 1
    assert "why it matters" in n.body.lower()
    assert n.summary
    assert n.derived_by.startswith("ai:")
    assert n.confidence < 1.0


def test_synthesis_skips_nodes_with_real_body():
    from compiler import ai_passes
    cfg = CompilerConfig.load(overrides={"cache_dir": "out_test_ai"})
    g = KnowledgeGraph(meta={"corpus_version": "t", "build_seconds": 0,
                              "source_url": "", "generated_at": "", "ir_version": 1})
    n = Node(id="page:x", type=NodeType.PAGE.value, title="Big Page",
             body="X" * 900)  # already has substantial deterministic content
    g.add_node(n)
    client = _FakeClient()
    done = ai_passes.pass_synthesis(g, client, cfg.cache_dir)
    assert done == 0  # skipped, no network call
    assert len(n.body) == 900


def test_pass_registry_toggle():
    from compiler import ai_passes
    assert ai_passes.resolve_passes(False, None) == []
    assert ai_passes.resolve_passes(True, None) == ["synthesis", "prerequisites", "clusters"]
    assert ai_passes.resolve_passes(True, "synthesis") == ["synthesis"]
    assert ai_passes.resolve_passes(True, "synthesis,bogus") == ["synthesis"]
