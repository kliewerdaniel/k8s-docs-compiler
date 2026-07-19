// Copies the compiler artifacts into the frontend public dir so they are served
// at the site root (dataset.json, llms.txt, per-type dumps, sitemap, robots).
// Run after `python -m compiler.cli compile ...` produces out/dataset.json.
const fs = require("fs");
const path = require("path");

const roots = [
  path.join(__dirname, "..", "..", "out_real"),
  path.join(__dirname, "..", "..", "out"),
  path.join(__dirname, "..", "..", "out_demo"),
];

function find() {
  for (const r of roots) {
    const p = path.join(r, "dataset.json");
    if (fs.existsSync(p)) return r;
  }
  return null;
}

const srcDir = find();
if (!srcDir) {
  console.error("No dataset.json found in out_real/out/out_demo. Run the compiler first.");
  process.exit(1);
}

const destDir = path.join(__dirname, "..", "public");
fs.mkdirSync(destDir, { recursive: true });

// Files to mirror at the site root (the LLM-traversability layer + the KB).
const files = [
  "dataset.json",
  "knowledge.jsonl",
  "index.json",
  "llms.txt",
  "llms-glossary.txt",
  "llms-api-objects.txt",
  "llms-pages.txt",
  "llms-rbac.txt",
  "llms-control-plane.txt",
  "llms-concepts-sample.txt",
  "sitemap.xml",
  "robots.txt",
];

let copied = 0;
for (const f of files) {
  const s = path.join(srcDir, f);
  if (fs.existsSync(s)) {
    fs.copyFileSync(s, path.join(destDir, f));
    copied++;
    console.log("Copied", f, `(${(fs.statSync(s).size / 1024).toFixed(0)} KB)`);
  }
}
console.log(`Done — ${copied} artifacts copied from ${srcDir} -> public/`);
