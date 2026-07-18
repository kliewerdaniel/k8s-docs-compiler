# Appendix — Research Data & Commands

Exact data and commands used during research on 2026-07-18. Reproduce or verify as needed.

## A. Corpus scale (kubernetes/website @ `main`, English `content/en/docs`)

Measured via GitHub `git/trees/main?recursive=1` over `content/en/docs/**/*.md`:

| Section | Pages |
|---------|------:|
| reference | 1,164 |
| tasks | 222 |
| concepts | 176 |
| tutorials | 43 |
| contribute | 42 |
| setup | 22 |
| home | 2 |
| doc-contributor-tools | 1 |
| **TOTAL** | **1,674** |

Sub-breakdowns: kubernetes-api 157, kubectl 120, access-authn-authz 19,
labels-annotations-taints 2, concepts/workloads 36, glossary **163 terms**.

## B. Glossary term file format (verbatim example: `reference/glossary/pod.md`)

```
---
title: Pod
id: pod
full_link: /docs/concepts/workloads/pods/
short_description: >
  A Pod represents a set of running containers in your cluster.
aka:
tags:
- core-object
- fundamental
---
 The smallest and simplest Kubernetes object. A Pod represents a set of running
 {{< glossary_tooltip text="containers" term_id="container" >}} on your cluster.
<!--more-->
A Pod is typically set up to run a single primary container...
```

## C. Shortcodes observed in K8s docs (sample of 60 concept/reference files)

`api`, `caution`, `comment`, `details`, `feature`, `figure`, `glossary_definition`,
`glossary_tooltip`, `highlight`, `mermaid`, `note`, `param`, `skew`, `table`, `tabs`,
`warning`.
- `glossary_tooltip` count in sample: 180
- `glossary_definition` count in sample: 16
- `figure` count in sample: 5

## D. OpenAPI / swagger (API Explorer source)

- URL: `https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json`
  (OpenAPI **v2**, ~4.1 MB). OpenAPI v3 path returned 404 at this location.
- **564 API paths**, **780 type definitions**.
- Top-level groups: `/apis` 445, `/api` 114, `/logs` 2, `/.well-known` 1, `/openid` 1,
  `/version` 1.

## E. Versioning

- Live version switcher on `kubernetes.io/docs` exposes many minor versions
  (`v1.86` … `v1.99` observed in page markup on capture date; the exact current set changes
  per release).
- Per-version docs = per git tag/branch of `kubernetes/website`.
- "Supported doc versions": `https://kubernetes.io/docs/home/supported-doc-versions/`

## F. Reproduction commands

```bash
# Docs repo (pin a version tag for reproducibility)
git clone --depth 1 https://github.com/kubernetes/website.git
cd website && git fetch --tags && git checkout v1.34.0

# API spec
curl -sL https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json -o swagger.json

# Count docs (after clone)
find content/en/docs -name '*.md' | wc -l
# Count glossary
ls content/en/docs/reference/glossary | wc -l

# GitHub API (unauthenticated; may rate-limit — use the recursive tree instead)
curl -sL "https://api.github.com/repos/kubernetes/website/git/trees/main?recursive=1"
```

## G. Key URLs

- Docs home: https://kubernetes.io/docs/
- Concepts: https://kubernetes.io/docs/concepts/
- Reference: https://kubernetes.io/docs/reference/
- Glossary: https://kubernetes.io/docs/reference/glossary/
- Kubernetes API: https://kubernetes.io/docs/reference/kubernetes-api/
- Supported versions: https://kubernetes.io/docs/home/supported-doc-versions/
- Source repo: https://github.com/kubernetes/website
- API spec repo: https://github.com/kubernetes/kubernetes (api/openapi-spec/)

## H. License note

Kubernetes documentation is licensed **CC-BY-4.0**. Any deployed compiled app must attribute
Kubernetes and link to source pages. Each `page` node carries its `url` for this purpose.
