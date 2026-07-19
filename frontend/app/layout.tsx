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
