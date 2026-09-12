import { Suspense } from "react";

import { AskChat } from "@/components/ask-chat";
import { PageHeader } from "@/components/panel";

export const dynamic = "force-dynamic";

export const metadata = { title: "Ask Your Browsing — LOOM" };

export default function AskPage() {
  return (
    <div className="flex w-full flex-col gap-lg">
      <PageHeader
        title="Ask Your Browsing"
        description="Semantic search over what LOOM has captured. Generate brief writes a one-page note from those same sources."
      />
      <Suspense fallback={<p className="text-sm text-text-secondary">Loading…</p>}>
        <AskChat />
      </Suspense>
    </div>
  );
}
