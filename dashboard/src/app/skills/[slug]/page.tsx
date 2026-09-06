import { notFound } from "next/navigation";

import { EmptyState, ErrorPanel, PageHeader } from "@/components/panel";
import { SkillTable } from "@/components/skill-table";
import { getSkillEntries } from "@/lib/api";
import { getSkillView } from "@/lib/skills";
import type { SkillEntryBase } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 100;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const view = getSkillView((await params).slug);
  return { title: view ? `${view.label} — LOOM` : "LOOM Dashboard" };
}

export default async function SkillPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const view = getSkillView(slug);
  if (!view) notFound();

  const result = await getSkillEntries<SkillEntryBase>(slug, { limit: PAGE_SIZE });

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-lg">
      <PageHeader
        title={view.label}
        description={view.description}
        actions={
          result.ok ? (
            <span className="text-xs text-text-secondary">
              {result.data.length === PAGE_SIZE
                ? `Newest ${PAGE_SIZE}`
                : `${result.data.length} ${result.data.length === 1 ? "entry" : "entries"}`}
            </span>
          ) : null
        }
      />

      {!result.ok ? (
        <ErrorPanel title={`Could not load ${view.label}`} error={result.error} />
      ) : result.data.length === 0 ? (
        <EmptyState>
          No entries yet. This store fills in once matching content is captured
          and classified.
        </EmptyState>
      ) : (
        <SkillTable
          view={view}
          entries={result.data}
          canDelete={slug === "jobs" || slug === "contract-flags"}
        />
      )}
    </div>
  );
}
