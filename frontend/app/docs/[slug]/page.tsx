import Link from "next/link";
import { nodeStaticParams, nodeMetadata, default as NodePage } from "@/app/_node/NodePage";
import type { StaticSection } from "@/lib/knowledge.server";

const SECTION: StaticSection = "docs";

export function generateStaticParams() {
  return nodeStaticParams(SECTION);
}
export function generateMetadata({ params }: { params: { slug: string } }) {
  return nodeMetadata(SECTION, params);
}
export default function Page({ params }: { params: { slug: string } }) {
  return <NodePage section={SECTION} params={params} />;
}
