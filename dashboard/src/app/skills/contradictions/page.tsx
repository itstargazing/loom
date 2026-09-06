import { ErrorPanel, PageHeader } from "@/components/panel";
import { ContradictionsBrowser } from "@/components/contradictions-browser";
import { apiGet } from "@/lib/api";
import type { Contradiction } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Contradictions — LOOM",
};

export default async function ContradictionsPage() {
  const contradictions = await apiGet<Contradiction[]>("/api/skills/contradictions", {
    limit: 100,
    include_dismissed: "true",
  });

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Contradictions"
        description="Claims from different sources on the same topic that appear to disagree. Dismiss a pair if it is not actually a conflict — the watcher will not re-flag that exact pairing."
      />

      {!contradictions.ok ? (
        <ErrorPanel title="Could not load contradictions" error={contradictions.error} />
      ) : (
        <ContradictionsBrowser initialEntries={contradictions.data} />
      )}
    </div>
  );
}
