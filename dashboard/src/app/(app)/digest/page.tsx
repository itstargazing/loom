import { ErrorPanel, PageHeader } from "@/components/panel";
import { DigestBrowser } from "@/components/digest-browser";
import { getDigest } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = { title: "Daily digest — LOOM" };

export default async function DigestPage() {
  const digest = await getDigest();

  return (
    <div className="flex w-full flex-col gap-lg">
      <PageHeader
        title="Daily digest"
        description="Everything classified in the last 24 hours. Accept, reassign, or discard — corrections become labeled training data."
      />
      {!digest.ok ? (
        <ErrorPanel title="Could not load digest" error={digest.error} />
      ) : (
        <DigestBrowser initial={digest.data} />
      )}
    </div>
  );
}
