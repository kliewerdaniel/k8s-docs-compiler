"use client";

import { useEffect, useState } from "react";
import type { KnowledgeGraph } from "@/lib/types";

export function useGraph(): { graph: KnowledgeGraph | null; error: string | null } {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch("/dataset.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setGraph)
      .catch((e) => setError(String(e)));
  }, []);
  return { graph, error };
}
