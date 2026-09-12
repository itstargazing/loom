import { AccountBrowser } from "@/components/account-browser";
import { ExtensionTokenCopy } from "@/components/extension-token-copy";
import { ErrorPanel, PageHeader } from "@/components/panel";
import { getAccount } from "@/lib/api";
import { isClerkConfigured } from "@/lib/auth-mode";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Account — LOOM",
};

export default async function AccountPage() {
  const account = await getAccount();
  const clerk = isClerkConfigured();

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Account"
        description={
          clerk
            ? "Your Clerk identity drives every API call. Profile fields below are LOOM-side metadata for this user id."
            : "Local stub authentication. Set Clerk keys to replace the shared bearer with real sign-in."
        }
      />

      {clerk ? <ExtensionTokenCopy /> : null}

      {!account.ok ? (
        <ErrorPanel title="Could not load account" error={account.error} />
      ) : (
        <AccountBrowser initial={account.data} />
      )}
    </div>
  );
}
