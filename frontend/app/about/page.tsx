"use client";

export default function About() {
  return (
    <>
      <h1>About</h1>
      <p>
        This site is the deployable artifact of <code>k8s-docs-compiler</code>, a
        compile-time knowledge compiler. It ingests the Kubernetes documentation and the
        OpenAPI specification, extracts a typed knowledge graph (concepts, API objects,
        RBAC, ownership chains, control-plane flow), and emits static artifacts — including
        this Next.js app — that require <strong>no backend inference</strong>.
      </p>
      <p className="muted">
        Source documentation: Kubernetes (CC-BY-4.0). Each node and edge carries provenance
        (source document, line, and supporting quote), so every displayed fact is traceable.
      </p>
    </>
  );
}
