import type { MetadataRoute } from "next";
import {
  STATIC_SECTIONS,
  nodeIdsForSection,
  slugify,
} from "@/lib/knowledge.server";

const BASE = "https://k8s-docs-compiler.vercel.app";

// Enumerate every statically-generated page so a crawler/agent can discover the
// full corpus without executing JS or guessing URLs.
export default function sitemap(): MetadataRoute.Sitemap {
  const urls: MetadataRoute.Sitemap = [
    { url: `${BASE}/` },
    { url: `${BASE}/graph` },
    { url: `${BASE}/explore` },
    { url: `${BASE}/search` },
    { url: `${BASE}/docs/` },
    { url: `${BASE}/api/` },
    { url: `${BASE}/rbac/` },
    { url: `${BASE}/relationships/` },
    { url: `${BASE}/learn/` },
    { url: `${BASE}/start/` },
    { url: `${BASE}/about/` },
    { url: `${BASE}/dataset.json` },
    { url: `${BASE}/index.json` },
    { url: `${BASE}/llms.txt` },
  ];

  for (const section of STATIC_SECTIONS) {
    for (const id of nodeIdsForSection(section)) {
      urls.push({ url: `${BASE}/${section}/${slugify(id)}/` });
    }
  }

  return urls;
}
