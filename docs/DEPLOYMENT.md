# Deployment — Vercel Static Export

Goal: deploy `k8s-docs-compiler` the same way `chatgpt-compile.vercel.app` is deployed —
a Next.js static export on Vercel. No server runtime; the LLM never runs in production.

## 1. Build
```bash
# produce dataset.json (ingest → extract → sanity-check)
python build_pipeline.py --version v1.34 --out public/dataset.json

# build the static site
npm run build        # next build  (output: "export" configured in next.config.js)
npm run export       # next export → out/
```

`next.config.js`:
```js
module.exports = { output: "export", images: { unoptimized: true },
                   trailingSlash: true };
```

## 2. Vercel
- New Vercel project (e.g. `k8s-compile`), framework **Next.js**, build command
  `npm run build && npm run export`, output dir `out/`.
- OR push `out/` as a static deploy. Mirror the existing `chatgpt-compile` project settings.
- Custom domain optional (e.g. `k8s-compile.vercel.app`).

## 3. Reproducibility
- Pin `dataset.json` provenance in `meta` (repo SHA, version).
- The deployed artifact is deterministic given the same corpus + pipeline version.
- Re-run ingest + build to refresh (supports the future "continuous compilation" research track).

## 4. Attribution / licensing
- K8s docs are **CC-BY-4.0**. Deployed app MUST include a footer crediting Kubernetes docs
  and linking to source pages (each `page` node carries its `url`).
- Do not strip attribution.

## 5. Local preview
```bash
npx serve out/      # or `npx http-server out/`
```
Validate: graph renders, search returns, Ingress+Deployment task is answerable, links resolve.

## 6. CI (optional, future)
- GitHub Action: on `kubernetes/website` tag or weekly cron → ingest → build → deploy.
- This is the "continuous compilation pipeline" research-track item, NOT required for MVP.
