import { ErrorPanel, PageHeader } from "@/components/panel";
import { TrailBrowser } from "@/components/trail-browser";
import { getTrail } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = { title: "Research trail — LOOM" };

export default async function TrailPage() {
  const trail = await getTrail(80);

  return (
    <div className="flex w-full flex-col gap-lg">
      <PageHeader
        title="Research trail"
        description="How a session unfolded: timestamps and referring-page links. Read-only for now."
      />
      {!trail.ok ? (
        <ErrorPanel title="Could not load trail" error={trail.error} />
      ) : (
        <TrailBrowser trail={trail.data} />
      )}
    </div>
  );
}
