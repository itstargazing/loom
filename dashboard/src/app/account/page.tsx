import { AccountBrowser } from "@/components/account-browser";
import { ErrorPanel, PageHeader } from "@/components/panel";
import { getAccount } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Account — LOOM",
};

export default async function AccountPage() {
  const account = await getAccount();

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Account"
        description="Stub authentication for local development. Profile, session, and delete-account live here so a real IdP can replace the bearer token later without changing the rest of LOOM."
      />

      {!account.ok ? (
        <ErrorPanel title="Could not load account" error={account.error} />
      ) : (
        <AccountBrowser initial={account.data} />
      )}
    </div>
  );
}
