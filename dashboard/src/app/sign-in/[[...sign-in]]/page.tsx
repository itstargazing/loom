import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-lg px-md">
      <div className="text-center">
        <p className="loom-display font-display text-2xl font-semibold tracking-tight">
          LOOM
        </p>
        <p className="mt-1 font-mono text-[10px] tracking-[0.18em] text-text-faint">
          Capture · Classify · Route
        </p>
      </div>
      <SignIn />
    </div>
  );
}
