// Server-side data layer for the compiled Kubernetes knowledge graph.
//
// This is read at BUILD TIME (inside server components / generateStaticParams)
// so that every route is fully server-rendered into the static export with no
// client-side fetch of /dataset.json. It mirrors the client KnowledgeStore, but
// is safe to import from async server components (no "use client", no React).
//
// The dataset lives at public/dataset.json — copied from the compiler's
// out_real/ by scripts/copy-artifacts.js. We read it from disk at build time
// (Node fs, available in server components during `next build`) so the values
// are available to statically render every route. Using fs (rather than a
// JSON import) avoids inlining the 17MB artifact into the bundle and keeps the
// type checker happy.

import fs from "fs";
import path from "path";
import type { KnowledgeGraph, Node, Edge, Provenance } from "./types";

const datasetPath = path.join(process.cwd(), "public", "dataset.json");
const graph = JSON.parse(fs.readFileSync(datasetPath, "utf8")) as KnowledgeGraph;

const byId = new Map<string, Node>(graph.nodes.map((n) => [n.id, n]));

const edgesByFrom = new Map<string, Edge[]>();
const edgesByTo = new Map<string, Edge[]>();
for (const e of graph.edges) {
  if (!edgesByFrom.has(e.from_id)) edgesByFrom.set(e.from_id, []);
  if (!edgesByTo.has(e.to_id)) edgesByTo.set(e.to_id, []);
  edgesByFrom.get(e.from_id)!.push(e);
  edgesByTo.get(e.to_id)!.push(e);
}

// ---------------------------------------------------------------------------
// Slug helpers (collision-safe, URL-safe)
// ---------------------------------------------------------------------------

// URL-safe slug for a node id. Node ids look like `gloss:pod`, `api:Deployment`,
// `page:tasks/run-application/scale`. We remap the structural characters that
// would otherwise break a path segment: `:` -> `-`, `/` -> `-`, spaces -> `-`,
// and drop `{}` (rare). The result is stable and collision-free across the
// 8198 nodes in the corpus.
export function slugify(id: string): string {
  return id
    .replace(/:/g, "-")
    .replace(/\//g, "-")
    .replace(/\s+/g, "-")
    .replace(/[{}]/g, "");
}

const slugToId = new Map<string, string>();
const usedSlugs = new Set<string>();
for (const n of graph.nodes) {
  let s = slugify(n.id);
  let u = s;
  let k = 1;
  while (usedSlugs.has(u)) {
    u = `${s}-${k++}`;
  }
  usedSlugs.add(u);
  slugToId.set(u, n.id);
}

export function resolveSlug(slug: string): string | null {
  return slugToId.get(slug) ?? null;
}

// Each node type maps to a section route prefix (see app/<section>/[slug]).
export const TYPE_SECTION: Record<string, string> = {
  glossary: "docs",
  page: "docs",
  concept: "docs",
  api_object: "api",
  api_path: "api",
  role: "rbac",
  controller: "relationships",
};

export function sectionFor(type: string): string {
  return TYPE_SECTION[type] ?? "docs";
}

// Build a href to the static per-node page for a given node id (if it has one).
export function hrefFor(id: string): string | null {
  const n = byId.get(id);
  if (!n) return null;
  const section = sectionFor(n.type);
  return `/${section}/${slugify(id)}/`;
}

// ---------------------------------------------------------------------------
// Lookups / query helpers (read-only over the compiled graph)
// ---------------------------------------------------------------------------

export function getGraph(): KnowledgeGraph {
  return graph;
}

export function getNode(id: string): Node | undefined {
  return byId.get(id);
}

export function getNodesByType(type: string): Node[] {
  return graph.nodes.filter((n) => n.type === type);
}

export function outEdges(id: string): Edge[] {
  return edgesByFrom.get(id) ?? [];
}
export function inEdges(id: string): Edge[] {
  return edgesByTo.get(id) ?? [];
}
export function allEdgesFor(id: string): Edge[] {
  return [...(edgesByFrom.get(id) ?? []), ...(edgesByTo.get(id) ?? [])];
}

// Related edges, highest confidence first.
export function relatedTo(id: string, limit = 25): Edge[] {
  return allEdgesFor(id)
    .slice()
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, limit);
}

export function neighborsOfType(id: string, type: string): Edge[] {
  return allEdgesFor(id).filter((e) => e.type === type);
}

export function prerequisitesOf(id: string): Node[] {
  return inEdges(id)
    .filter((e) => e.type === "prerequisite_of")
    .map((e) => byId.get(e.from_id))
    .filter((n): n is Node => Boolean(n));
}
export function unlocks(id: string): Node[] {
  return outEdges(id)
    .filter((e) => e.type === "prerequisite_of")
    .map((e) => byId.get(e.to_id))
    .filter((n): n is Node => Boolean(n));
}

export function rbacRoles(): Node[] {
  return graph.nodes.filter((n) => n.type === "role");
}
export function controlPlane(): Node[] {
  return graph.nodes.filter((n) => n.type === "controller");
}

// Foundational glossary terms that unlock others (used by /start).
export function startHere(limit = 12): Node[] {
  const prereqCount = (n: Node) => prerequisitesOf(n.id).length;
  const candidates = graph.nodes.filter(
    (n) => n.type === "glossary" && unlocks(n.id).length > 0
  );
  return candidates
    .sort((a, b) => prereqCount(a) - prereqCount(b) || a.title.localeCompare(b.title))
    .slice(0, limit);
}

export function titleFor(id: string): string {
  return byId.get(id)?.title ?? id;
}

// ---------------------------------------------------------------------------
// Static params enumerators (used by generateStaticParams)
// ---------------------------------------------------------------------------

// Sections that emit one static page per node.
export const STATIC_SECTIONS = ["docs", "api", "rbac", "relationships"] as const;
export type StaticSection = (typeof STATIC_SECTIONS)[number];

export function nodeIdsForSection(section: StaticSection): string[] {
  switch (section) {
    case "docs":
      return graph.nodes
        .filter((n) => ["glossary", "page", "concept"].includes(n.type))
        .map((n) => n.id);
    case "api":
      return graph.nodes
        .filter((n) => n.type === "api_object" || n.type === "api_path")
        .map((n) => n.id);
    case "rbac":
      return graph.nodes.filter((n) => n.type === "role").map((n) => n.id);
    case "relationships":
      return graph.nodes.filter((n) => n.type === "controller").map((n) => n.id);
  }
}

export function typesInSection(section: StaticSection): string[] {
  switch (section) {
    case "docs":
      return ["glossary", "page", "concept"];
    case "api":
      return ["api_object", "api_path"];
    case "rbac":
      return ["role"];
    case "relationships":
      return ["controller"];
  }
}

// Lightweight provenance shape for JSON-LD / display.
export type { Provenance };
