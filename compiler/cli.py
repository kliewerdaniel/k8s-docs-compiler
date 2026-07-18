"""k8s-docs-compiler — command line interface.

Subcommands:
  compile    Build knowledge artifacts from a kubernetes/website checkout.
  validate   Validate an existing dataset.json (graph integrity + provenance).
  query      Answer a question against the SQLite artifact (no LLM at runtime).
  diff       Compare two dataset.json builds (version differences).
  demo       Compile the bundled fixtures -> out/ (offline, no K8s repo needed).

Examples:
  python -m compiler.cli demo
  python -m compiler.cli compile --docs-root ~/kubernetes/website/content/en/docs \
      --swagger ~/swagger.json --version v1.34
  python -m compiler.cli query "What resources are related to Deployments?"
  python -m compiler.cli diff out/v1.33/dataset.json out/v1.34/dataset.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys

from .config import CompilerConfig
from .compiler import Compiler
from .logging_setup import setup_logging, get_logger


def _resolve_package_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------
# compile / demo
# --------------------------------------------------------------------------

def cmd_compile(args) -> int:
    cfg = CompilerConfig.load(args.config, overrides={
        "docs_root": args.docs_root, "swagger_path": args.swagger,
        "version": args.version, "out_dir": args.out,
        "enable_ai": args.ai, "log_level": args.log_level,
    })
    c = Compiler(cfg)
    g = c.compile()
    c.save(g)
    return 0


def cmd_demo(args) -> int:
    root = _resolve_package_root()
    fx = os.path.join(root, "fixtures", "k8s_sample")
    swagger = os.path.join(root, "fixtures", "swagger_min.json")
    cfg = CompilerConfig.load(args.config, overrides={
        "version": "fixture", "out_dir": args.out,
        "emit_gexf": True, "log_level": args.log_level,
        "swagger_path": swagger if os.path.exists(swagger) else None,
    })
    c = Compiler(cfg)
    g = c.compile_fixtures(fx, swagger_path=swagger if os.path.exists(swagger) else None)
    c.save(g)
    print("\nDemo build complete. Artifacts in:", os.path.abspath(args.out))
    print("Try:  python -m compiler.cli query \"What resources are related to Deployments?\" --db",
          os.path.join(args.out, "knowledge.db"))
    return 0


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------

def cmd_validate(args) -> int:
    setup_logging(args.log_level)
    log = get_logger()
    with open(args.dataset, "r", encoding="utf-8") as f:
        data = json.load(f)
    ids = {n["id"] for n in data["nodes"]}
    errs = []
    for n in data["nodes"]:
        if "id" not in n or "type" not in n:
            errs.append(f"node missing id/type: {n}")
        if not (0 <= n.get("confidence", 1) <= 1):
            errs.append(f"node {n['id']} confidence out of range")
    for e in data["edges"]:
        if e["from_id"] not in ids:
            errs.append(f"edge from unknown {e['from_id']}")
        if e["to_id"] not in ids:
            errs.append(f"edge to unknown {e['to_id']}")
        if not (0 <= e.get("confidence", 1) <= 1):
            errs.append(f"edge {e['from_id']}->{e['to_id']} confidence out of range")
    if errs:
        for e in errs:
            log.error("INVALID: %s", e)
        print(f"VALIDATION FAILED: {len(errs)} errors")
        return 1
    print("VALIDATION OK:", len(data["nodes"]), "nodes,", len(data["edges"]), "edges")
    return 0


# --------------------------------------------------------------------------
# query (runtime, no LLM)
# --------------------------------------------------------------------------

def cmd_query(args) -> int:
    db = args.db or os.path.join(args.out, "knowledge.db")
    if not os.path.exists(db):
        print("SQLite artifact not found:", db, "(run `demo` or `compile` first)")
        return 1
    con = sqlite3.connect(db)
    cur = con.cursor()
    q = args.question
    ql = q.lower()
    print(f"\n=== Query: {q} ===\n")

    # ---- intent routing for the canonical questions ----
    if "kubectl apply" in ql or ("internally" in ql and "kubectl" in ql):
        _print_kubectl_flow(cur)
        con.close(); return 0
    if any(k in ql for k in ("permission", "rbac", "manifest", "role")):
        _print_rbac(cur)
        con.close(); return 0
    if "related to" in ql:
        term = ql.split("related to", 1)[1].strip(" ?.")
        _print_related(cur, term)
        con.close(); return 0
    if "depend" in ql and ("api" in ql or "object" in ql or "concept" in ql):
        # concepts depending on an API object
        m = re.search(r"(deployment|pod|service|ingress|replicaset|statefulset|daemonset|job|cronjob|node|namespace|secret|configmap)", ql)
        if m:
            _print_depends_on(cur, m.group(1))
            con.close(); return 0

    # 1) best-matching concept(s) by keyword overlap
    keywords = [w.strip("?.,").lower() for w in q.replace("/", " ").split()
                if len(w) > 2 and w.lower() not in
                ("what", "which", "resources", "related", "does", "this", "with", "from",
                 "into", "that", "when", "how", "are", "the", "for", "and", "concepts",
                 "kubernetes", "object", "api")]

    placeholders = " OR ".join(["title LIKE ? OR summary LIKE ?"] * max(1, len(keywords)))
    params = []
    for kw in keywords or ["kubernetes"]:
        params += ["%" + kw + "%", "%" + kw + "%"]
    sql = ("SELECT id,type,title,section FROM nodes WHERE " + placeholders +
           " ORDER BY type,title LIMIT 15")
    rows = cur.execute(sql, params).fetchall()
    if rows:
        print("[Matching concepts]")
        for r in rows:
            print(f"  - {r[1]:10} {r[2]}  ({r[3] or '-'})  [{r[0]}]")
    else:
        print("[No direct concept match — showing top-level concepts]")
        rows = cur.execute(
            "SELECT id,type,title FROM nodes WHERE type='glossary' LIMIT 15").fetchall()
        for r in rows:
            print(f"  - {r[1]:10} {r[2]}  [{r[0]}]")

    # 2) relationship walk from the top match
    top = rows[0] if rows else None
    if top:
        top_id = top[0]
        # prefer a glossary/page/api_object match over secondary types for the walk
        ranked = sorted(rows, key=lambda r: {"glossary":0,"page":1,"api_object":2,
                                              "concept":3,"role":4}.get(r[1], 9))
        top = ranked[0]
        top_id = top[0]
        print(f"\n[Resources related to '{top[2]}']")
        rel = cur.execute(
            "SELECT type,from_title,to_title,label,confidence FROM edge_view "
            "WHERE from_id=? OR to_id=? ORDER BY confidence DESC LIMIT 25",
            (top_id, top_id)).fetchall()
        if rel:
            for e in rel:
                print(f"  - ({e[0]}) {e[1]} -> {e[2]}  [{e[3]}] conf={e[4]}")
        else:
            print("  (no recorded relationships)")

    # 3) RBAC / permission specific
    if any(k in q.lower() for k in ("permission", "rbac", "manifest", "role")):
        print("\n[RBAC roles / permissions — what each resource requires]")
        rbac = cur.execute(
            "SELECT id,title,meta FROM nodes WHERE type='role' ORDER BY title").fetchall()
        for r in rbac:
            import json as _json
            m = _json.loads(r[2] or "{}")
            verbs = ",".join((m.get("verbs") or [])[:6])
            print(f"  - {r[1]}  group={m.get('apiGroup','core')}  verbs=[{verbs}…]  [{r[0]}]")

    # 4) kubectl apply internal flow
    if "kubectl apply" in q.lower() or "internally" in q.lower():
        print("\n[Internal flow of `kubectl apply`]")
        flow = cur.execute(
            "SELECT title, summary FROM nodes WHERE id LIKE 'flow:%' "
            "ORDER BY CASE id "
            "WHEN 'flow:kubectl' THEN 1 "
            "WHEN 'flow:kube-apiserver' THEN 2 "
            "WHEN 'flow:etcd' THEN 3 "
            "WHEN 'flow:kube-controller-manager_scheduler' THEN 4 "
            "WHEN 'flow:kubelet' THEN 5 ELSE 9 END").fetchall()
        for i, f in enumerate(flow, 1):
            print(f"  {i}. {f[0]} — {f[1]}")
    con.close()
    return 0


# --------------------------------------------------------------------------
# query helpers (intent-specific printers)
# --------------------------------------------------------------------------

def _print_kubectl_flow(cur):
    print("[Internal flow of `kubectl apply`]")
    flow = cur.execute(
        "SELECT title, summary FROM nodes WHERE id LIKE 'flow:%' "
        "ORDER BY CASE id "
        "WHEN 'flow:kubectl' THEN 1 "
        "WHEN 'flow:kube-apiserver' THEN 2 "
        "WHEN 'flow:etcd' THEN 3 "
        "WHEN 'flow:kube-controller-manager_scheduler' THEN 4 "
        "WHEN 'flow:kubelet' THEN 5 ELSE 9 END").fetchall()
    for i, f in enumerate(flow, 1):
        print(f"  {i}. {f[0]} — {f[1]}")


def _print_rbac(cur):
    print("[RBAC roles / permissions — what each resource requires]")
    rbac = cur.execute(
        "SELECT id,title,meta FROM nodes WHERE type='role' ORDER BY title").fetchall()
    for r in rbac:
        m = json.loads(r[2] or "{}")
        verbs = ",".join((m.get("verbs") or [])[:6])
        print(f"  - {r[1]}  group={m.get('apiGroup','core')}  verbs=[{verbs}…]  [{r[0]}]")


def _print_related(cur, term):
    like = "%" + term + "%"
    rows = cur.execute(
        "SELECT id,type,title FROM nodes WHERE lower(title)=? OR title LIKE ? OR id LIKE ? "
        "ORDER BY CASE WHEN lower(title)=? THEN 0 ELSE 1 END, "
        "CASE type WHEN 'glossary' THEN 0 WHEN 'api_object' THEN 1 WHEN 'page' THEN 2 "
        "WHEN 'concept' THEN 3 ELSE 9 END, length(title), title LIMIT 5",
        (term, like, like, term)).fetchall()
    if not rows:
        print(f"[No concept matches '{term}']")
        return
    top = rows[0]
    print(f"[Resources related to '{top[2]}']")
    rel = cur.execute(
        "SELECT type,from_title,to_title,label,confidence FROM edge_view "
        "WHERE from_id=? OR to_id=? "
        "ORDER BY CASE type WHEN 'references' THEN 0 WHEN 'related_to' THEN 1 "
        "WHEN 'api_for' THEN 2 WHEN 'owns' THEN 3 WHEN 'requires' THEN 4 "
        "WHEN 'prerequisite_of' THEN 5 ELSE 9 END, confidence DESC LIMIT 25",
        (top[0], top[0])).fetchall()
    for e in rel:
        print(f"  - ({e[0]}) {e[1]} -> {e[2]}  [{e[3]}] conf={e[4]}")


def _print_depends_on(cur, kind):
    row = cur.execute(
        "SELECT id,title FROM nodes WHERE type='api_object' AND "
        "(title LIKE ? OR id LIKE ?) LIMIT 1",
        ("%" + kind + "%", "%" + kind + "%")).fetchone()
    if not row:
        print(f"[No API object found for '{kind}']")
        return
    print(f"[Concepts depending on {row[1]} (api:{row[1]})]")
    deps = cur.execute(
        "SELECT DISTINCT f.title, e.type FROM edge_view e "
        "JOIN nodes f ON f.id=e.from_id "
        "WHERE e.to_id=? AND e.type IN ('api_for','references','related_to') "
        "ORDER BY e.type LIMIT 20", (row[0],)).fetchall()
    if not deps:
        deps = cur.execute(
            "SELECT DISTINCT t.title, e.type FROM edge_view e "
            "JOIN nodes t ON t.id=e.to_id WHERE e.from_id=? LIMIT 20", (row[0],)).fetchall()
    for d in deps:
        print(f"  - ({d[1]}) {d[0]}")


# --------------------------------------------------------------------------
# diff (version differences)
# --------------------------------------------------------------------------

def cmd_diff(args) -> int:
    a = json.load(open(args.old, "r", encoding="utf-8"))
    b = json.load(open(args.new, "r", encoding="utf-8"))
    ia = {n["id"]: n for n in a["nodes"]}
    ib = {n["id"]: n for n in b["nodes"]}
    added = [n["id"] for n in b["nodes"] if n["id"] not in ia]
    removed = [n["id"] for n in a["nodes"] if n["id"] not in ib]
    print(f"=== Version diff: {args.old} -> {args.new} ===")
    print(f"Nodes: {len(ia)} -> {len(ib)} (+{len(added)} / -{len(removed)})")
    print(f"Edges: {len(a['edges'])} -> {len(b['edges'])}")
    if added:
        print("\nADDED nodes:")
        for i in added[:40]:
            print("  +", ib[i]["type"], ib[i].get("title", i))
    if removed:
        print("\nREMOVED nodes:")
        for i in removed[:40]:
            print("  -", ia[i]["type"], ia[i].get("title", i))
    return 0


# --------------------------------------------------------------------------
# argparse
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="k8s-docs-compiler",
        description="Compile the Kubernetes documentation into a static, "
                    "queryable knowledge graph (compile-time AI).")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compile", help="Compile from a kubernetes/website checkout")
    c.add_argument("--docs-root", default=None)
    c.add_argument("--swagger", dest="swagger", default=None)
    c.add_argument("--version", default="main")
    c.add_argument("--out", default="out")
    c.add_argument("--config", default=None)
    c.add_argument("--ai", action="store_true", help="Enable optional AI passes")
    c.add_argument("--log-level", default="INFO")
    c.set_defaults(func=cmd_compile)

    d = sub.add_parser("demo", help="Compile bundled fixtures (offline)")
    d.add_argument("--out", default="out")
    d.add_argument("--config", default=None)
    d.add_argument("--log-level", default="INFO")
    d.set_defaults(func=cmd_demo)

    v = sub.add_parser("validate", help="Validate a dataset.json")
    v.add_argument("dataset")
    v.add_argument("--log-level", default="INFO")
    v.set_defaults(func=cmd_validate)

    q = sub.add_parser("query", help="Query the SQLite artifact (no LLM)")
    q.add_argument("question")
    q.add_argument("--db", default=None)
    q.add_argument("--out", default="out")
    q.add_argument("--log-level", default="INFO")
    q.set_defaults(func=cmd_query)

    df = sub.add_parser("diff", help="Diff two dataset.json builds")
    df.add_argument("old")
    df.add_argument("new")
    df.add_argument("--log-level", default="INFO")
    df.set_defaults(func=cmd_diff)
    return p


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
