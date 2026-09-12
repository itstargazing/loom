import { ErrorPanel, PageHeader } from "@/components/panel";
import { PrivacySettingsBrowser } from "@/components/privacy-settings-browser";
import { getPrivacySettings } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Local-only mode — LOOM",
};

export default async function PrivacyPage() {
  const settings = await getPrivacySettings();

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Local-only mode"
        description="Sensitive domains skip cloud AI and classify with heuristics only. This may be less accurate than the cloud model — that tradeoff is intentional and visible."
      />

      {!settings.ok ? (
        <ErrorPanel title="Could not load privacy settings" error={settings.error} />
      ) : (
        <PrivacySettingsBrowser initial={settings.data} />
      )}
    </div>
  );
}
