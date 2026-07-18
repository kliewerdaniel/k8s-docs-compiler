export interface Provenance {
  source: string;
  url?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  quote?: string | null;
}

export interface Node {
  id: string;
  type: string;
  title: string;
  summary: string;
  body: string;
  body_trimmed: boolean;
  version: string;
  section: string | null;
  tags: string[];
  aliases: string[];
  url: string | null;
  meta: Record<string, unknown>;
  provenance: Provenance[];
  confidence: number;
  derived_by: string;
}

export interface Edge {
  from_id: string;
  to_id: string;
  type: string;
  label: string;
  weight: number;
  confidence: number;
  derived_by: string;
  provenance: Provenance[];
}

export interface GraphStats {
  pages: number;
  glossary: number;
  api_objects: number;
  api_paths: number;
  concepts: number;
  edges: number;
  edge_types: Record<string, number>;
  graph_density: number;
  build_seconds: number;
}

export interface KnowledgeGraph {
  meta: Record<string, unknown>;
  stats: GraphStats;
  nodes: Node[];
  edges: Edge[];
}
