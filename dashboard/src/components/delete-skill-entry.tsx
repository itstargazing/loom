"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DeleteSkillEntry({
  slug,
  id,
  label,
}: {
  slug: string;
  id: string;
  label: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    if (!window.confirm(`Delete this ${label}?`)) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/proxy/skills/${slug}/${id}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : `Delete failed (${response.status})`,
        );
      }
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        className="text-xs text-error underline"
        disabled={busy}
        onClick={() => void remove()}
      >
        Delete
      </button>
      {error ? <p className="text-xs text-error">{error}</p> : null}
    </div>
  );
}
