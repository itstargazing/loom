"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { Badge } from "@/components/skill-table";
import { hostnameOf } from "@/lib/format";
import type { Deadline } from "@/lib/types";

type ViewMode = "month" | "list";

const KIND_LABELS: Record<string, string> = {
  assignment_due: "Assignment",
  exam: "Exam",
  payment_due: "Payment",
  rsvp: "RSVP",
  application_due: "Application",
  other: "Other",
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTHS_LONG = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const MONTHS_SHORT = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const WEEKDAYS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

async function proxy<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

function dayKey(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().slice(0, 10);
}

/** Fixed English UTC labels — avoids Node/browser locale ICU mismatches. */
function formatDay(iso: string | null): string {
  const key = dayKey(iso);
  if (!key) return "Date unresolved";
  const [year, month, day] = key.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const weekday = WEEKDAYS_SHORT[date.getUTCDay()];
  return `${weekday}, ${MONTHS_SHORT[month - 1]} ${day}, ${year}`;
}

function monthLabel(year: number, month: number): string {
  return `${MONTHS_LONG[month]} ${year}`;
}

function startOfCalendar(year: number, month: number): Date {
  const first = new Date(Date.UTC(year, month, 1));
  const weekday = (first.getUTCDay() + 6) % 7;
  first.setUTCDate(first.getUTCDate() - weekday);
  return first;
}

export function DeadlinesCalendar({
  initialDeadlines,
}: {
  initialDeadlines: Deadline[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [view, setView] = useState<ViewMode>("month");
  const [source, setSource] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sources = useMemo(() => {
    const names = new Map<string, string>();
    for (const entry of initialDeadlines) {
      const key = entry.pageTitle || hostnameOf(entry.sourceUrl);
      names.set(key, key);
    }
    return [...names.keys()].sort((a, b) => a.localeCompare(b));
  }, [initialDeadlines]);

  const visible = useMemo(() => {
    return initialDeadlines.filter((entry) => {
      if (source === "all") return true;
      const key = entry.pageTitle || hostnameOf(entry.sourceUrl);
      return key === source;
    });
  }, [initialDeadlines, source]);

  const dated = visible.filter((entry) => dayKey(entry.dueDate));
  const undated = visible.filter((entry) => !dayKey(entry.dueDate));

  const cursor = useMemo(() => {
    const first = dated
      .map((entry) => dayKey(entry.dueDate))
      .filter((key): key is string => Boolean(key))
      .sort()[0];
    if (first) {
      const [year, month] = first.split("-").map(Number);
      return { year, month: month - 1 };
    }
    const now = new Date();
    return { year: now.getUTCFullYear(), month: now.getUTCMonth() };
  }, [dated]);

  const [year, setYear] = useState(cursor.year);
  const [month, setMonth] = useState(cursor.month);

  const byDay = useMemo(() => {
    const map = new Map<string, Deadline[]>();
    for (const entry of dated) {
      const key = dayKey(entry.dueDate);
      if (!key) continue;
      const list = map.get(key) ?? [];
      list.push(entry);
      map.set(key, list);
    }
    return map;
  }, [dated]);

  const selected = visible.find((entry) => entry.id === selectedId) ?? null;

  const cells = useMemo(() => {
    const start = startOfCalendar(year, month);
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start);
      date.setUTCDate(start.getUTCDate() + index);
      const key = date.toISOString().slice(0, 10);
      return {
        key,
        day: date.getUTCDate(),
        inMonth: date.getUTCMonth() === month,
        items: byDay.get(key) ?? [],
      };
    });
  }, [year, month, byDay]);

  function refresh() {
    startTransition(() => router.refresh());
  }

  async function confirm(entry: Deadline) {
    setError(null);
    try {
      await proxy(`/skills/deadlines/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({ confirmed: true }),
      });
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not confirm");
    }
  }

  async function remove(entry: Deadline) {
    if (!window.confirm(`Delete “${entry.title}”?`)) return;
    setError(null);
    try {
      await proxy(`/skills/deadlines/${entry.id}`, { method: "DELETE" });
      if (selectedId === entry.id) setSelectedId(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  function shiftMonth(delta: number) {
    const next = new Date(Date.UTC(year, month + delta, 1));
    setYear(next.getUTCFullYear());
    setMonth(next.getUTCMonth());
  }

  const pendingCount = visible.filter((entry) => !entry.confirmed).length;

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap items-end gap-md">
        <div className="flex gap-sm" role="tablist" aria-label="Calendar view">
          {(["month", "list"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={view === mode}
              className={view === mode ? "loom-btn" : "loom-btn loom-btn-secondary"}
              onClick={() => setView(mode)}
            >
              {mode === "month" ? "Month" : "List"}
            </button>
          ))}
        </div>

        <label className="flex flex-col gap-1">
          <span className="font-mono text-xs text-text-secondary">
            Source document
          </span>
          <select
            value={source}
            onChange={(event) => setSource(event.target.value)}
            className="loom-input"
          >
            <option value="all">All sources</option>
            {sources.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>

        {pendingCount > 0 ? (
          <p className="text-xs text-warning">
            {pendingCount} {pendingCount === 1 ? "item needs" : "items need"} confirmation
          </p>
        ) : null}
      </div>

      {error ? <p className="text-sm text-error">{error}</p> : null}

      {visible.length === 0 ? (
        <EmptyState>
          {initialDeadlines.length === 0
            ? "No deadlines yet. Open a syllabus, contract, or event page with capture of page opens enabled."
            : "No deadlines from this source."}
        </EmptyState>
      ) : (
        <div className="grid gap-lg lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div>
            {view === "month" ? (
              <div className="flex flex-col gap-md">
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    className="text-xs text-text-secondary underline"
                    onClick={() => shiftMonth(-1)}
                  >
                    Previous
                  </button>
                  <h2 className="loom-display font-display text-sm font-medium">{monthLabel(year, month)}</h2>
                  <button
                    type="button"
                    className="text-xs text-text-secondary underline"
                    onClick={() => shiftMonth(1)}
                  >
                    Next
                  </button>
                </div>
                <div className="loom-glass loom-sheen-mid grid grid-cols-7 gap-px overflow-hidden bg-border">
                  {WEEKDAYS.map((label) => (
                    <div
                      key={label}
                      className="bg-background-secondary px-2 py-1 font-mono text-xs text-text-secondary"
                    >
                      {label}
                    </div>
                  ))}
                  {cells.map((cell) => (
                    <div
                      key={cell.key}
                      className={[
                        "min-h-[6.5rem] bg-background p-1",
                        cell.inMonth ? "" : "opacity-40",
                      ].join(" ")}
                    >
                      <p className="loom-mono text-xs text-text-secondary">{cell.day}</p>
                      <ul className="mt-1 flex flex-col gap-1">
                        {cell.items.map((entry) => (
                          <li key={entry.id}>
                            <button
                              type="button"
                              onClick={() => setSelectedId(entry.id)}
                              className={[
                                "w-full truncate px-1 py-0.5 text-left text-xs",
                                entry.confirmed
                                  ? "text-text-primary"
                                  : "bg-warning-muted text-warning",
                                selectedId === entry.id ? "underline" : "",
                              ].join(" ")}
                            >
                              {entry.title}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
                {undated.length > 0 ? (
                  <p className="text-xs text-text-secondary">
                    {undated.length} undated{" "}
                    {undated.length === 1 ? "item is" : "items are"} in the list view.
                  </p>
                ) : null}
              </div>
            ) : (
              <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
                {[...dated]
                  .sort((a, b) => (a.dueDate ?? "").localeCompare(b.dueDate ?? ""))
                  .concat(undated)
                  .map((entry) => (
                    <li key={entry.id} className="py-md">
                      <button
                        type="button"
                        onClick={() => setSelectedId(entry.id)}
                        className="flex w-full flex-col items-start gap-1 text-left"
                      >
                        <span className="text-sm font-medium">{entry.title}</span>
                        <span className="text-xs text-text-secondary">
                          {formatDay(entry.dueDate)}
                          {entry.kind ? ` · ${KIND_LABELS[entry.kind] ?? entry.kind}` : ""}
                          {` · ${entry.pageTitle || hostnameOf(entry.sourceUrl)}`}
                        </span>
                        {!entry.confirmed ? (
                          <Badge tone="warning">Needs confirmation</Badge>
                        ) : null}
                      </button>
                    </li>
                  ))}
              </ul>
            )}
          </div>

          <aside className="loom-card h-fit p-md">
            {selected ? (
              <div className="flex flex-col gap-sm">
                <p className="text-sm font-medium">{selected.title}</p>
                <p className="text-xs text-text-secondary">
                  {formatDay(selected.dueDate)}
                  {selected.dueText && selected.dueText !== dayKey(selected.dueDate)
                    ? ` · ${selected.dueText}`
                    : ""}
                </p>
                {selected.kind ? (
                  <p className="text-xs text-text-secondary">
                    {KIND_LABELS[selected.kind] ?? selected.kind}
                  </p>
                ) : null}
                <p className="text-xs text-text-secondary">
                  From {selected.pageTitle || hostnameOf(selected.sourceUrl)}
                </p>
                {selected.sourceUrl ? (
                  <a
                    href={selected.sourceUrl}
                    className="text-xs underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {hostnameOf(selected.sourceUrl)}
                  </a>
                ) : null}
                {selected.contextSnippet ? (
                  <p className="mt-sm text-sm text-text-primary">
                    “{selected.contextSnippet}”
                  </p>
                ) : (
                  <p className="text-xs text-text-secondary">
                    No surrounding sentence was stored for this row.
                  </p>
                )}
                {!selected.confirmed ? (
                  <button
                    type="button"
                    className="loom-btn mt-sm"
                    disabled={pending}
                    onClick={() => void confirm(selected)}
                  >
                    Confirm
                  </button>
                ) : (
                  <p className="text-xs text-success">Confirmed</p>
                )}
                <button
                  type="button"
                  className="text-xs text-error underline"
                  onClick={() => void remove(selected)}
                >
                  Delete
                </button>
              </div>
            ) : (
              <p className="text-sm text-text-secondary">
                Select a deadline to see the source document and the original sentence.
              </p>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
