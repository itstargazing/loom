"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function AskBar() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const query = q.trim();
    if (!query) {
      router.push("/ask");
      return;
    }
    router.push(`/ask?q=${encodeURIComponent(query)}`);
  }

  return (
    <form onSubmit={onSubmit} className="flex min-w-0 flex-1 items-center gap-sm">
      <label className="sr-only" htmlFor="ask-bar">
        Ask your browsing
      </label>
      <input
        id="ask-bar"
        value={q}
        onChange={(event) => setQ(event.target.value)}
        placeholder="Ask your browsing…"
        className="loom-input h-10 min-w-0 flex-1"
      />
      <button type="submit" className="loom-btn h-10 shrink-0">
        Ask
      </button>
    </form>
  );
}
