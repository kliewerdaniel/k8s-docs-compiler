import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";

export const metadata = {
  title: "Kubernetes Knowledge Compiler",
  description:
    "An interactive knowledge application compiled from the Kubernetes documentation — a static, queryable knowledge graph (compile-time AI).",
};

const NAV = [
  { href: "/", label: "Home" },
  { href: "/graph", label: "Concept Graph" },
  { href: "/explore", label: "Decision Explorer" },
  { href: "/api", label: "API Explorer" },
  { href: "/relationships", label: "Resource Relationships" },
  { href: "/learn", label: "Learning Paths" },
  { href: "/rbac", label: "RBAC & Permissions" },
  { href: "/search", label: "Search" },
  { href: "/docs", label: "Docs" },
  { href: "/start", label: "Start Here" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="alternate" type="application/json" href="/dataset.json" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@graph": [
                {
                  "@type": "WebSite",
                  "@id": "https://k8s-docs-compiler.vercel.app/#website",
                  "url": "https://k8s-docs-compiler.vercel.app/",
                  "name": "Kubernetes Knowledge Compiler",
                  "description":
                    "A compiled, versioned knowledge graph of Kubernetes built from the official documentation and OpenAPI spec at compile time. Zero runtime inference; every fact is traceable to source and readable by any agent via plain HTTP GET.",
                  "inLanguage": "en",
                  "potentialAction": {
                    "@type": "SearchAction",
                    "target": {
                      "@type": "EntryPoint",
                      "urlTemplate":
                        "https://k8s-docs-compiler.vercel.app/search?q={search_term_string}",
                    },
                    "query-input": "required name=search_term_string",
                  },
                },
                {
                  "@type": "DataCatalog",
                  "@id": "https://k8s-docs-compiler.vercel.app/#catalog",
                  "name": "Kubernetes Compiled Knowledge Graph",
                  "url": "https://k8s-docs-compiler.vercel.app/",
                  "description":
                    "8,198 compiled nodes (glossary, docs, concepts, API objects/paths, RBAC roles, control-plane components) with 10,754 typed edges and provenance. Version v1.34.",
                  "keywords": [
                    "kubernetes",
                    "knowledge graph",
                    "compile-time AI",
                    "documentation",
                    "RBAC",
                    "API reference",
                  ],
                  "creator": {
                    "@type": "Person",
                    "name": "Daniel Kliewer",
                    "url": "https://danielkliewer.com",
                  },
                  "sameAs": "https://danielkliewer.com",
                  "distribution": [
                    {
                      "@type": "DataDownload",
                      "encodingFormat": "application/json",
                      "contentUrl": "https://k8s-docs-compiler.vercel.app/dataset.json",
                      "name": "dataset.json (full graph)",
                    },
                    {
                      "@type": "DataDownload",
                      "encodingFormat": "application/json",
                      "contentUrl": "https://k8s-docs-compiler.vercel.app/index.json",
                      "name": "index.json (lightweight index)",
                    },
                    {
                      "@type": "DataDownload",
                      "encodingFormat": "text/plain",
                      "contentUrl": "https://k8s-docs-compiler.vercel.app/llms.txt",
                      "name": "llms.txt",
                    },
                    {
                      "@type": "DataDownload",
                      "encodingFormat": "application/xml",
                      "contentUrl": "https://k8s-docs-compiler.vercel.app/sitemap.xml",
                      "name": "sitemap.xml",
                    },
                  ],
                },
              ],
            }),
          }}
        />
      </head>
      <body>
        <header className="topbar">
          <span className="brand">⎈ k8s knowledge compiler</span>
          <nav>
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}>
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
        <main>{children}</main>
        <footer className="foot">
          Compiled from the Kubernetes documentation (CC-BY-4.0). No runtime LLM — every fact
          is traceable to source. <Link href="/about">About</Link>
        </footer>
      </body>
    </html>
  );
}
