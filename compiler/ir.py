"""Intermediate Representation (IR) for the Kubernetes Knowledge Compiler.

This is the single source of truth for the structure of compiled knowledge.
Every artifact (JSON / SQLite / GEXF) is a serialization of `KnowledgeGraph`.

Design principles (per compile-time-AI architecture):
  * Every fact carries `provenance` (source doc + line) and a `confidence` score.
  * Deterministic passes produce `confidence=1.0`; optional AI passes may lower it
    and MUST record `derived_by="ai:<model>"`.
  * DAG identity is content-addressed: identical inputs -> identical IR hashes
    (given deterministic config). This makes builds reproducible and diffable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------

class NodeType(str, Enum):
    PAGE = "page"                 # a docs page (concepts/tasks/tutorials/reference/setup)
    GLOSSARY = "glossary"         # a controlled glossary term (163 of them)
    API_OBJECT = "api_object"     # a Kubernetes API type (Deployment, Pod, ...)
    API_PATH = "api_path"         # an API endpoint (GET /apis/apps/v1/deployments)
    CONCEPT = "concept"           # a derived concept (heading-level idea)
    MANIFEST = "manifest"         # an analyzed YAML manifest (for permission analysis)
    ROLE = "role"                 # RBAC Role/ClusterRole (permissions)
    CONTROLLER = "controller"     # a control-plane / add-on controller
    OPERATOR = "operator"         # an operator (controller + CRD pattern)
    CRD = "crd"                   # CustomResourceDefinition


class EdgeType(str, Enum):
    REFERENCES = "references"             # page/concept mentions a glossary term
    DEFINES = "defines"                   # page inlines a glossary definition
    LINKS_TO = "links_to"                 # doc links to another doc
    PREREQUISITE_OF = "prerequisite_of"   # A must be understood before B
    RELATED_TO = "related_to"             # symmetric relatedness
    API_FOR = "api_for"                   # doc explains/uses this API object
    OWNS = "owns"                         # owner-reference chain (Pod <- ReplicaSet ...)
    SELECTS = "selects"                   # label selector match (Service -> Pods)
    PART_OF = "part_of"                   # hierarchical / group membership
    VERSION_OF = "version_of"             # same logical node, different version
    PERMITS = "permits"                   # RBAC Role permits verbs on resources
    REQUIRES = "requires"                 # manifest/action requires permission
    CONTROLS = "controls"                 # controller reconciles an object kind
    INSTALLS = "installs"                 # operator/helm installs a CRD


# --------------------------------------------------------------------------
# Core dataclasses
# --------------------------------------------------------------------------

@dataclass
class Provenance:
    """Traceability: every fact points back to source documents."""
    source: str                 # doc path within repo, or "swagger.json", or "manifest:<file>"
    url: Optional[str] = None   # canonical public URL
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    quote: Optional[str] = None  # the exact source snippet supporting the fact


@dataclass
class Node:
    id: str
    type: str
    title: str
    summary: str = ""
    body: str = ""              # normalized markdown (may be trimmed for size)
    body_trimmed: bool = False
    version: str = "unknown"
    section: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    url: Optional[str] = None
    meta: Dict = field(default_factory=dict)   # type-specific extras (fields, group, ...)
    provenance: List[Provenance] = field(default_factory=list)
    confidence: float = 1.0
    derived_by: str = "deterministic"

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["type"] = self.type
        return d


@dataclass
class Edge:
    from_id: str
    to_id: str
    type: str
    label: str = ""
    weight: float = 1.0
    confidence: float = 1.0
    derived_by: str = "deterministic"
    provenance: List[Provenance] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def key(self) -> str:
        return f"{self.from_id}|{self.type}|{self.to_id}"


@dataclass
class GraphStats:
    pages: int = 0
    glossary: int = 0
    api_objects: int = 0
    api_paths: int = 0
    concepts: int = 0
    manifests: int = 0
    roles: int = 0
    controllers: int = 0
    operators: int = 0
    crds: int = 0
    edges: int = 0
    edge_types: Dict[str, int] = field(default_factory=dict)
    graph_density: float = 0.0
    duplicate_removed: int = 0
    build_seconds: float = 0.0


@dataclass
class KnowledgeGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)
    stats: GraphStats = field(default_factory=GraphStats)

    # ---- lookups ----
    def node_index(self) -> Dict[str, Node]:
        return {n.id: n for n in self.nodes}

    def neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        return [e for e in self.edges if e.from_id == node_id and
                (edge_type is None or e.type == edge_type)]

    def incoming(self, node_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        return [e for e in self.edges if e.to_id == node_id and
                (edge_type is None or e.type == edge_type)]

    # ---- mutation ----
    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        # de-duplicate identical edges (idempotent passes)
        for ex in self.edges:
            if ex.key == edge.key:
                # keep the higher-confidence / provenance-merged edge
                if edge.confidence > ex.confidence:
                    ex.confidence = edge.confidence
                    ex.derived_by = edge.derived_by
                ex.provenance.extend(edge.provenance)
                return
        self.edges.append(edge)

    # ---- stats / validation ----
    def compute_stats(self) -> GraphStats:
        counts = {}
        for n in self.nodes:
            counts[n.type] = counts.get(n.type, 0) + 1
        s = GraphStats(
            pages=counts.get(NodeType.PAGE.value, 0),
            glossary=counts.get(NodeType.GLOSSARY.value, 0),
            api_objects=counts.get(NodeType.API_OBJECT.value, 0),
            api_paths=counts.get(NodeType.API_PATH.value, 0),
            concepts=counts.get(NodeType.CONCEPT.value, 0),
            manifests=counts.get(NodeType.MANIFEST.value, 0),
            roles=counts.get(NodeType.ROLE.value, 0),
            controllers=counts.get(NodeType.CONTROLLER.value, 0),
            operators=counts.get(NodeType.OPERATOR.value, 0),
            crds=counts.get(NodeType.CRD.value, 0),
        )
        s.edges = len(self.edges)
        et: Dict[str, int] = {}
        for e in self.edges:
            et[e.type] = et.get(e.type, 0) + 1
        s.edge_types = et
        n = len(self.nodes)
        s.graph_density = (len(self.edges) / (n * (n - 1))) if n > 1 else 0.0
        self.stats = s
        return s

    def validate(self) -> List[str]:
        """Return a list of validation errors (empty == valid)."""
        errors: List[str] = []
        ids = {n.id for n in self.nodes}
        seen = set()
        for n in self.nodes:
            if n.id in seen:
                errors.append(f"duplicate node id: {n.id}")
            seen.add(n.id)
            if n.confidence < 0 or n.confidence > 1:
                errors.append(f"node {n.id}: confidence out of range {n.confidence}")
        for e in self.edges:
            if e.from_id not in ids:
                errors.append(f"edge from unknown node: {e.from_id} -> {e.to_id}")
            if e.to_id not in ids:
                errors.append(f"edge to unknown node: {e.from_id} -> {e.to_id}")
            if e.confidence < 0 or e.confidence > 1:
                errors.append(f"edge {e.key}: confidence out of range {e.confidence}")
        return errors

    def ir_hash(self) -> str:
        """Content-addressed identity of the graph (reproducibility)."""
        payload = json.dumps(
            {"nodes": [n.to_dict() for n in self.nodes],
             "edges": sorted([e.to_dict() for e in self.edges], key=lambda x: x["from_id"])},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        self.compute_stats()
        return {
            "meta": self.meta,
            "stats": asdict(self.stats),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
