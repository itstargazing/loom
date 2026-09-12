import { ErrorPanel, PageHeader } from "@/components/panel";
import { FormFillerBrowser } from "@/components/form-filler-browser";
import { getFormDocuments, getFormProfiles } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Form Filler — LOOM",
};

export default async function FormFillerPage() {
  const [profiles, documents] = await Promise.all([
    getFormProfiles(),
    getFormDocuments(),
  ]);

  const error = !profiles.ok
    ? profiles.error
    : !documents.ok
      ? documents.error
      : null;

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Form Filler"
        description="Keep named profiles of common values, batch-match them onto fillable PDFs, and download a zip. Fields below the confidence threshold stay blank for you to fill in."
      />

      {error ? (
        <ErrorPanel title="Could not load form filler" error={error} />
      ) : (
        <FormFillerBrowser
          initialProfiles={profiles.ok ? profiles.data : []}
          initialDocuments={documents.ok ? documents.data : []}
        />
      )}
    </div>
  );
}
