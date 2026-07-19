// Client-side loader + query engine over the compiled dataset.json.
// No runtime LLM: all answers are graph/keyword lookups against the built artifact.

import type { KnowledgeGraph } from "./types";

export type NodeT = KnowledgeGraph["nodes"][number];
export type EdgeT = KnowledgeGraph["edges"][number];

export class KnowledgeStore {
  graph: KnowledgeGraph;
  byId: Map<string, NodeT>;
  edgesByFrom: Map<string, EdgeT[]>;
  edgesByTo: Map<string, EdgeT[]>;
  index: { i: number; t: string; n: NodeT }[];

  constructor(graph: KnowledgeGraph) {
    this.graph = graph;
    this.byId = new Map(graph.nodes.map((n) => [n.id, n]));
    this.edgesByFrom = new Map();
    this.edgesByTo = new Map();
    for (const e of graph.edges) {
      (this.edgesByFrom.get(e.from_id) ?? this.edgesByFrom.set(e.from_id, []).get(e.from_id)!).push(e);
      (this.edgesByTo.get(e.to_id) ?? this.edgesByTo.set(e.to_id, []).get(e.to_id)!).push(e);
    }
    this.index = graph.nodes.map((n, i) => ({
      i,
      t: `${n.title} ${(n.summary || "")} ${(n.tags || []).join(" ")}`.toLowerCase(),
      n,
    }));
  }

  search(q: string, limit = 40): NodeT[] {
    const ql = q.toLowerCase().trim();
    if (!ql) return [];
    const terms = ql.split(/\s+/).filter((t) => t.length > 1);
    return this.index
      .filter((o) => terms.every((t) => o.t.includes(t)))
      .slice(0, limit)
      .map((o) => o.n);
  }

  out(id: string): EdgeT[] {
    return this.edgesByFrom.get(id) || [];
  }
  in(id: string): EdgeT[] {
    return this.edgesByTo.get(id) || [];
  }
  neighbors(id: string, type?: string): EdgeT[] {
    const all = [...this.out(id), ...this.in(id)];
    return type ? all.filter((e) => e.type === type) : all;
  }

  // What resources are related to node X?
  relatedTo(id: string, limit = 25): EdgeT[] {
    return [...this.out(id), ...this.in(id)]
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, limit);
  }

  // K8s-specific: API objects a concept depends on
  dependsOn(id: string): NodeT[] {
    const ids = new Set<string>();
    for (const e of this.out(id)) {
      if (["api_for", "references", "related_to", "owns"].includes(e.type)) ids.add(e.to_id);
    }
    return [...ids].map((i) => this.byId.get(i)!).filter(Boolean);
  }

  // RBAC roles (what each resource requires)
  rbacRoles(): NodeT[] {
    return this.graph.nodes.filter((n) => n.type === "role");
  }

  // kubectl apply internal flow
  kubectlFlow(): NodeT[] {
    return this.graph.nodes.filter((n) => n.id.startsWith("flow:")).sort((a, b) => a.id.localeCompare(b.id));
  }

  // control plane components
  controlPlane(): NodeT[] {
    return this.graph.nodes.filter((n) => n.type === "controller");
  }

  // Learning path: nodes that are prerequisites of `id` (one hop back via
  // prerequisite_of edges), then the node itself.
  prerequisitesOf(id: string): NodeT[] {
    const ids = new Set<string>();
    for (const e of this.in(id)) {
      if (e.type === "prerequisite_of") ids.add(e.from_id);
    }
    return [...ids].map((i) => this.byId.get(i)).filter(Boolean) as NodeT[];
  }

  // Learning path: nodes for which `id` is a prerequisite (what it unlocks).
  unlocks(id: string): NodeT[] {
    const ids = new Set<string>();
    for (const e of this.out(id)) {
      if (e.type === "prerequisite_of") ids.add(e.to_id);
    }
    return [...ids].map((i) => this.byId.get(i)).filter(Boolean) as NodeT[];
  }

  // Build an ordered "Start Here" onboarding path: take the glossary nodes that
  // have the most prerequisites (i.e. are foundational), dedupe, and order by
  // prerequisite depth (fewest prerequisites first = learn first).
  startHere(limit = 12): NodeT[] {
    const prereqCount = (n: NodeT) => this.prerequisitesOf(n.id).length;
    const candidates = this.graph.nodes.filter(
      (n) => n.type === "glossary" && this.unlocks(n.id).length > 0
    );
    return candidates
      .sort((a, b) => prereqCount(a) - prereqCount(b) || a.title.localeCompare(b.title))
      .slice(0, limit);
  }
}
