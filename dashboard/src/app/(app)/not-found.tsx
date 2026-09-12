import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col gap-md">
      <h1 className="font-display text-xl font-semibold tracking-tight">Not found</h1>
      <p className="text-sm text-text-secondary">
        That page does not exist. Pick a skill from the sidebar, or head back to
        the overview.
      </p>
      <Link href="/" className="loom-btn self-start">
        Overview
      </Link>
    </div>
  );
}
