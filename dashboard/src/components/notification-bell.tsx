"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type { NotificationList } from "@/lib/types";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<NotificationList | null>(null);

  useEffect(() => {
    void fetch("/api/proxy/notifications")
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => setData(body))
      .catch(() => setData({ items: [], unread: 0 }));
  }, []);

  const unread = data?.unread ?? 0;

  async function dismiss(id: string) {
    await fetch(`/api/proxy/notifications/${id}/dismiss`, { method: "POST" });
    setData((current) => {
      if (!current) return current;
      const items = current.items.filter((item) => item.id !== id);
      return { items, unread: items.filter((item) => !item.readAt).length };
    });
  }

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        className="loom-btn loom-btn-secondary h-10"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={unread > 0 ? `Nudges, ${unread} unread` : "Nudges"}
      >
        Nudges{unread > 0 ? ` · ${unread}` : ""}
      </button>
      {open ? (
        <div className="loom-glass loom-sheen-tr absolute right-0 z-20 mt-sm w-80 p-md">
          {(data?.items.length ?? 0) === 0 ? (
            <p className="text-sm text-text-secondary">No nudges right now.</p>
          ) : (
            <ul className="flex flex-col gap-md">
              {data?.items.map((item) => (
                <li key={item.id} className="flex flex-col gap-xs">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-text-secondary">{item.body}</p>
                  <div className="flex gap-md">
                    {item.href ? (
                      <Link
                        href={item.href}
                        className="text-xs text-text-secondary underline decoration-border underline-offset-2 transition-colors duration-fast hover:text-text-primary"
                      >
                        Open
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      className="text-xs text-text-secondary underline decoration-border underline-offset-2 hover:text-text-primary"
                      onClick={() => void dismiss(item.id)}
                    >
                      Dismiss
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
