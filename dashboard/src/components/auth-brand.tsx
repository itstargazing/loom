import { BrandLogo } from "@/components/brand-logo";

/** Shared header for sign-in / sign-up. */
export function AuthBrand() {
  return (
    <div className="flex flex-col items-center text-center">
      <BrandLogo size="lg" />
      <p className="loom-wordmark mt-sm font-display text-2xl font-semibold tracking-tight">
        LOOM
      </p>
      <p className="mt-1 font-mono text-[10px] tracking-[0.18em] text-text-faint">
        Capture · Classify · Route
      </p>
    </div>
  );
}

/** Minimal monochrome loading for auth route transitions. */
export function AuthLoading({ label = "Entering Loom" }: { label?: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 px-md">
      <div className="auth-load-mark">
        <BrandLogo size="lg" />
      </div>
      <div className="flex w-40 flex-col items-center gap-3">
        <div className="auth-load-track" aria-hidden>
          <span className="auth-load-bar" />
        </div>
        <p className="font-mono text-[10px] tracking-[0.22em] text-text-faint">
          {label}
        </p>
      </div>
    </div>
  );
}
