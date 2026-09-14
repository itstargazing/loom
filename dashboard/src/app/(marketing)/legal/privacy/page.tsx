import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How LOOM captures, stores, and deletes browsing memory.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="marketing-root">
    <main className="mk-wrap mx-auto max-w-3xl py-16 text-[var(--mk-text)]">
      <p className="mk-label">Legal</p>
      <h1 className="mk-font-display mt-3 text-3xl font-semibold tracking-tight">
        Privacy Policy
      </h1>
      <p className="mt-4 text-sm text-[var(--mk-dim)]">
        Last updated: 14 September 2026. This is a product privacy notice for
        soft launch. Have counsel review before regulated markets.
      </p>

      <section className="mt-10 space-y-4 text-sm leading-relaxed text-[var(--mk-dim)]">
        <h2 className="text-base font-semibold text-[var(--mk-text)]">What LOOM collects</h2>
        <p>
          The LOOM browser extension can capture browsing signals you enable
          (highlights, copies, page opens, dwell, PDF text, and related
          metadata such as URL and page title). Those events sync to your LOOM
          cloud account so classification, skill stores, and Ask can run.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">
          Local-only domains are not on-device-only
        </h2>
        <p>
          Domains marked local-only skip cloud AI classification and use
          heuristics instead. Capture events for those domains still upload to
          your LOOM backend. Do not treat local-only as “data never leaves the
          device.”
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Account and auth</h2>
        <p>
          Sign-in is handled by Clerk. LOOM stores a profile keyed by your auth
          subject id, plus captures and derived skill documents. Authentication
          tokens authorize the extension and dashboard against the API.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Retention</h2>
        <p>
          Captures and skill rows are retained for a configurable period
          (default 365 days) and purged by a background job. You can export or
          delete your data sooner from Account.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Your rights</h2>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            Export: download a JSON archive of your LOOM data from Account.
          </li>
          <li>
            Delete: permanently erase LOOM data for your user id from Account
            (type DELETE to confirm).
          </li>
          <li>
            Signal controls: disable capture signals in the extension; manage
            local-only domains under Local-only settings.
          </li>
        </ul>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Teams</h2>
        <p>
          Clerk Organizations support team membership and seat billing. Capture
          and skill data remain personal to each user until org-scoped stores
          ship.
        </p>
        <p>
          Contact: use your deployment support channel. Related:{" "}
          <Link href="/legal/terms" className="underline hover:text-[var(--mk-text)]">
            Terms of Service
          </Link>
          .
        </p>
      </section>
    </main>
    </div>
  );
}
