import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms for using LOOM during public soft launch and GA.",
};

export default function TermsPage() {
  return (
    <div className="marketing-root">
    <main className="mk-wrap mx-auto max-w-3xl py-16 text-[var(--mk-text)]">
      <p className="mk-label">Legal</p>
      <h1 className="mk-font-display mt-3 text-3xl font-semibold tracking-tight">
        Terms of Service
      </h1>
      <p className="mt-4 text-sm text-[var(--mk-dim)]">
        Last updated: 14 September 2026. Soft-launch terms — have counsel
        review before Global GA in regulated jurisdictions.
      </p>

      <section className="mt-10 space-y-4 text-sm leading-relaxed text-[var(--mk-dim)]">
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Service</h2>
        <p>
          LOOM provides a browser extension, API, and dashboard that capture and
          organize browsing signals for personal research memory. Features may
          change during soft launch.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Accounts</h2>
        <p>
          You must keep credentials secure and use LOOM only for lawful
          purposes. You are responsible for content you capture, including
          material subject to workplace or third-party restrictions.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Plans and quotas</h2>
        <p>
          Free and Pro plans enforce daily capture and Ask quotas. Paid
          subscriptions are billed through Stripe. Failure to pay may downgrade
          you to free limits.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Acceptable use</h2>
        <p>
          Do not abuse the API, attempt unauthorized access, or use LOOM to
          violate others&apos; privacy or intellectual property rights. We may
          suspend accounts that threaten service integrity.
        </p>
        <h2 className="text-base font-semibold text-[var(--mk-text)]">Disclaimer</h2>
        <p>
          LOOM is provided as-is. Classification and Ask answers can be wrong.
          Do not rely on LOOM as the sole source for legal, medical, or
          financial decisions.
        </p>
        <p>
          See also the{" "}
          <Link href="/legal/privacy" className="underline hover:text-[var(--mk-text)]">
            Privacy Policy
          </Link>
          .
        </p>
      </section>
    </main>
    </div>
  );
}
