import Link from "next/link";
import { rbacRoles, hrefFor } from "@/lib/knowledge.server";

export const metadata = {
  title: "RBAC & Permissions — k8s knowledge compiler",
  description:
    "Compiled from the RBAC reference: each resource maps to the verbs a Role/ClusterRole must grant.",
};

export default function RbacIndex() {
  const roles = rbacRoles();
  const requires = require("@/lib/knowledge.server")
    .getGraph()
    .edges.filter((e: any) => e.type === "requires");

  return (
    <article>
      <h1>RBAC &amp; Permissions</h1>
      <p className="muted">
        Compiled from the RBAC reference: each resource maps to the verbs
        (permissions) a Role/ClusterRole must grant. Directly answers &ldquo;what
        permissions does this manifest require?&rdquo;
      </p>

      <h2>Roles / permissions ({roles.length})</h2>
      <ul className="idx">
        {roles.map((r) => {
          const m = r.meta as Record<string, unknown>;
          const verbs = (m?.verbs as string[]) || [];
          const grp = (m?.apiGroup as string) || "core";
          const href = hrefFor(r.id);
          return (
            <li key={r.id}>
              {href ? (
                <Link href={href}>{r.title.replace("permissions:", "")}</Link>
              ) : (
                <span>{r.title.replace("permissions:", "")}</span>
              )}{" "}
              <span className="mono">group={grp}</span>
              <div className="mono" style={{ marginTop: 2 }}>
                {verbs.join(", ")}
              </div>
            </li>
          );
        })}
      </ul>

      <h2>Manifest → required permission edges ({requires.length})</h2>
      <p className="muted">A sample of the compiled requires edges:</p>
      <div>
        {requires.slice(0, 80).map((e: any, i: number) => (
          <div key={i} className="edge">
            <span className="etype">requires</span> {e.from_id.replace("role:", "")} →{" "}
            {e.to_id.replace("api:", "")}
          </div>
        ))}
      </div>
    </article>
  );
}
