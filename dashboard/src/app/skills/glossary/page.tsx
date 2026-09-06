import { ErrorPanel, PageHeader } from "@/components/panel";
import { GlossaryBrowser } from "@/components/glossary-browser";
import { getCollections, getSkillEntries } from "@/lib/api";
import type { GlossaryTerm } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Glossary — LOOM",
};

export default async function GlossaryPage() {
  const [terms, collections] = await Promise.all([
    getSkillEntries<GlossaryTerm>("glossary", { limit: 200, sort: "alpha" }),
    getCollections(),
  ]);

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Glossary"
        description="Terms highlighted while reading, defined from the surrounding sentence, grouped into collections if you file them."
      />

      {!terms.ok ? (
        <ErrorPanel title="Could not load glossary" error={terms.error} />
      ) : (
        <GlossaryBrowser
          initialTerms={terms.data}
          initialCollections={collections.ok ? collections.data : []}
          collectionsError={collections.ok ? null : collections.error}
        />
      )}
    </div>
  );
}
