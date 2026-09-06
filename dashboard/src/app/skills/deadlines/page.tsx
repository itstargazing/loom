import { ErrorPanel, PageHeader } from "@/components/panel";
import { DeadlinesCalendar } from "@/components/deadlines-calendar";
import { getSkillEntries } from "@/lib/api";
import type { Deadline } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Deadlines — LOOM",
};

export default async function DeadlinesPage() {
  const deadlines = await getSkillEntries<Deadline>("deadlines", { limit: 200 });

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Deadlines"
        description="Every dated obligation from pages and PDFs you opened, on one calendar. Low-confidence rows need a click before they count as certain."
      />

      {!deadlines.ok ? (
        <ErrorPanel title="Could not load deadlines" error={deadlines.error} />
      ) : (
        <DeadlinesCalendar initialDeadlines={deadlines.data} />
      )}
    </div>
  );
}
