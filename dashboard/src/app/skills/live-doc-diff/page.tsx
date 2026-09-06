import { ErrorPanel, PageHeader } from "@/components/panel";
import { LiveDocDiffBrowser } from "@/components/live-doc-diff-browser";
import { getWatchedSets } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Live Doc Diff — LOOM",
};

export default async function LiveDocDiffPage() {
  const sets = await getWatchedSets();

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Live Doc Diff"
        description="Watch two or more document URLs as a set. LOOM snapshots text from captures (or a pasted draft), diffs them, and flags meaningful divergence — not just spacing changes."
      />

      {!sets.ok ? (
        <ErrorPanel title="Could not load watched sets" error={sets.error} />
      ) : (
        <LiveDocDiffBrowser initialSets={sets.data} />
      )}
    </div>
  );
}
