// Copies the compiler artifacts (dataset.json) into the frontend public dir.
// Run after `python -m compiler.cli compile ...` produces out/dataset.json.
const fs = require("fs");
const path = require("path");

const roots = [
  path.join(__dirname, "..", "..", "out_real"),
  path.join(__dirname, "..", "..", "out"),
  path.join(__dirname, "..", "..", "out_demo"),
];
const dest = path.join(__dirname, "..", "public", "dataset.json");

function find() {
  for (const r of roots) {
    const p = path.join(r, "dataset.json");
    if (fs.existsSync(p)) return p;
  }
  return null;
}

const src = find();
if (!src) {
  console.error("No dataset.json found in out_real/out/out_demo. Run the compiler first.");
  process.exit(1);
}
fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.copyFileSync(src, dest);
console.log("Copied", src, "->", dest, `(${(fs.statSync(src).size / 1024).toFixed(0)} KB)`);
