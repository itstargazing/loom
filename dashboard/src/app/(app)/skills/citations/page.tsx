import { ErrorPanel, PageHeader } from "@/components/panel";
import { CitationsBrowser } from "@/components/citations-browser";
import { getCollections, getSkillEntries } from "@/lib/api";
import type { Citation } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Citations — LOOM",
};

export default async function CitationsPage() {
  const [citations, collections] = await Promise.all([
    getSkillEntries<Citation>("citations", { limit: 200, sort: "recent" }),
    getCollections(),
  ]);

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Citations"
        description="Quoted passages captured while browsing, formatted as APA or MLA from the source metadata. File them into a collection and export a bibliography."
      />

      {!citations.ok ? (
        <ErrorPanel title="Could not load citations" error={citations.error} />
      ) : (
        <CitationsBrowser
          initialCitations={citations.data}
          initialCollections={collections.ok ? collections.data : []}
          collectionsError={collections.ok ? null : collections.error}
        />
      )}
    </div>
  );
}
