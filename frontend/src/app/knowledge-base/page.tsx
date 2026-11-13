import type { Metadata } from "next";
import { KnowledgeWorkspace } from "@/components/knowledge-workspace";
export const metadata: Metadata = { title: "Knowledge Base" };
export default function KnowledgePage() {
  return <KnowledgeWorkspace />;
}
