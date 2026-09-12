import { ErrorPanel, PageHeader } from "@/components/panel";
import { ReadingBrowser } from "@/components/reading-browser";
import { getCollections, getSkillEntries } from "@/lib/api";
import type { ReadingCompilerEntry } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Reading Compiler — LOOM",
};

export default async function ReadingPage() {
  const [entries, collections] = await Promise.all([
    getSkillEntries<ReadingCompilerEntry>("reading", { limit: 200, sort: "recent" }),
    getCollections(),
  ]);

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Reading Compiler"
        description="Passages you actually lingered on, merged into one clean linear document. Filter by collection or time range, reorder, then export Markdown or PDF."
      />

      {!entries.ok ? (
        <ErrorPanel title="Could not load reading passages" error={entries.error} />
      ) : (
        <ReadingBrowser
          initialEntries={entries.data}
          initialCollections={collections.ok ? collections.data : []}
          collectionsError={collections.ok ? null : collections.error}
        />
      )}
    </div>
  );
}
