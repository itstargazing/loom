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
        title="Local-only domains"
        description="These domains skip cloud AI and use heuristics instead. Events still sync to your LOOM cloud backend — this is not on-device-only storage. See Privacy Policy for details."
      />

      {!settings.ok ? (
        <ErrorPanel title="Could not load privacy settings" error={settings.error} />
      ) : (
        <PrivacySettingsBrowser initial={settings.data} />
      )}
    </div>
  );
}
