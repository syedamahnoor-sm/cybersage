import type { Metadata } from "next";
import { Suspense } from "react";
import { AssistantWorkspace } from "@/components/assistant-workspace";
export const metadata: Metadata = { title: "AI Assistant" };
export default function AssistantPage() {
  return (
    <Suspense fallback={<p role="status">Preparing assistant workspace…</p>}>
      <AssistantWorkspace />
    </Suspense>
  );
}
