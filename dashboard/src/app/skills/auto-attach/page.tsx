import { ErrorPanel, PageHeader } from "@/components/panel";
import { AutoAttachBrowser } from "@/components/auto-attach-browser";
import { getRecentDocuments } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Auto-Attach — LOOM",
};

export default async function AutoAttachPage() {
  const documents = await getRecentDocuments();

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Auto-Attach"
        description="A lightweight index of documents you recently opened or uploaded. When an upload field appears, LOOM suggests a match — you confirm before anything is attached."
      />

      {!documents.ok ? (
        <ErrorPanel title="Could not load document index" error={documents.error} />
      ) : (
        <AutoAttachBrowser initialDocuments={documents.data} />
      )}
    </div>
  );
}
