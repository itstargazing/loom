"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { apiErrorMessage } from "@/lib/api-error";
import { hostnameOf } from "@/lib/format";
import type { ProductCompare, ProductListing } from "@/lib/types";

async function proxyJson<T>(path: string, init?: RequestInit): Promise<T> {
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
    throw new Error(apiErrorMessage(body, `Request failed (${response.status})`));
  }
  return body as T;
}

function queryIds(ids: string[]): string {
  const params = new URLSearchParams();
  for (const id of ids) params.append("entry_id", id);
  return params.toString();
}

export function ProductCompareBrowser({
  initialEntries,
}: {
  initialEntries: ProductListing[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [entries, setEntries] = useState(initialEntries);
  const [selectedIds, setSelectedIds] = useState<string[]>(
    initialEntries.slice(0, 4).map((entry) => entry.id),
  );
  const [comparison, setComparison] = useState<ProductCompare | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEntries(initialEntries);
  }, [initialEntries]);

  const selected = useMemo(
    () => entries.filter((entry) => selectedIds.includes(entry.id)),
    [entries, selectedIds],
  );

  function refresh() {
    startTransition(() => router.refresh());
  }

  function toggle(id: string) {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  async function buildComparison() {
    setError(null);
    if (selectedIds.length === 0) {
      setError("Select at least one product");
      return;
    }
    try {
      const preview = await proxyJson<ProductCompare>(
        `/skills/products/compare?${queryIds(selectedIds)}`,
      );
      setComparison(preview);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not compare");
    }
  }

  async function downloadCsv() {
    setError(null);
    if (selectedIds.length === 0) {
      setError("Select at least one product");
      return;
    }
    try {
      const response = await fetch(`/api/proxy/skills/products/export?${queryIds(selectedIds)}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(apiErrorMessage(body, `Export failed (${response.status})`));
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] ??
        "product-comparison.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not export");
    }
  }

  async function remove(entry: ProductListing) {
    if (!window.confirm(`Remove ${entry.name}?`)) return;
    setError(null);
    try {
      await proxyJson(`/skills/products/${entry.id}`, { method: "DELETE" });
      setEntries((current) => current.filter((row) => row.id !== entry.id));
      setSelectedIds((current) => current.filter((id) => id !== entry.id));
      setComparison(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  const lowest = new Set(comparison?.lowestPriceIds ?? []);

  return (
    <div className="flex flex-col gap-lg">
      {error ? <p className="text-sm text-error">{error}</p> : null}

      <div className="flex flex-wrap gap-sm">
        <button
          type="button"
          className="loom-btn"
          disabled={pending}
          onClick={() => void buildComparison()}
        >
          Compare selected
        </button>
        <button
          type="button"
          className="loom-btn loom-btn-secondary"
          onClick={() => void downloadCsv()}
        >
          Spreadsheet (CSV)
        </button>
      </div>

      {entries.length === 0 ? (
        <EmptyState>
          No product listings yet. Open a shopping page with the extension capturing, then
          sync.
        </EmptyState>
      ) : (
        <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
          {entries.map((entry) => (
            <li key={entry.id} className="flex items-start justify-between gap-md py-md">
              <label className="flex min-w-0 items-start gap-sm text-sm">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={selectedIds.includes(entry.id)}
                  onChange={() => toggle(entry.id)}
                />
                <span>
                  <span className="font-medium">{entry.name}</span>
                  <span className="mt-1 block text-xs text-text-secondary">
                    {entry.price ?? "No price"}
                    {" · "}
                    {hostnameOf(entry.sourceUrl)}
                    {" · "}
                    <RelativeTime iso={entry.lastSeenAt} />
                  </span>
                </span>
              </label>
              <button type="button" className="text-xs underline" onClick={() => void remove(entry)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-text-secondary">
        {selected.length} selected. Same-currency prices are ranked; mixed currencies stay
        unranked.
      </p>

      {comparison && comparison.columns.length > 0 ? (
        <div className="loom-glass loom-sheen-mid overflow-x-auto">
          {comparison.priceNote ? (
            <p className="border-b border-border px-md py-sm text-xs text-warning">
              {comparison.priceNote}
            </p>
          ) : null}
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border bg-background-secondary text-left">
                <th className="px-md py-sm font-mono text-xs font-medium text-text-secondary">
                  Spec
                </th>
                {comparison.columns.map((column) => (
                  <th key={column.id} className="px-md py-sm text-xs font-medium">
                    {column.name}
                    {lowest.has(column.id) ? (
                      <span className="ml-2 text-xs font-normal text-success">Lowest</span>
                    ) : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border align-top">
                <td className="px-md py-sm text-text-secondary">Price</td>
                {comparison.columns.map((column) => (
                  <td key={column.id} className="px-md py-sm">
                    <span className="loom-mono text-xs">{column.price.raw ?? "—"}</span>
                    {column.price.comparable ? (
                      <span className="mt-1 block text-xs text-text-secondary">
                        {column.price.amount} {column.price.currency}
                      </span>
                    ) : null}
                  </td>
                ))}
              </tr>
              {comparison.specKeys.map((key) => (
                <tr key={key} className="border-b border-border align-top last:border-b-0">
                  <td className="px-md py-sm text-text-secondary">
                    {key.charAt(0).toUpperCase() + key.slice(1)}
                  </td>
                  {comparison.columns.map((column) => (
                    <td key={column.id} className="px-md py-sm">
                      {column.specs[key] ?? <span className="text-border">—</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState>
          Select listings and click Compare selected to line up specs and prices.
        </EmptyState>
      )}
    </div>
  );
}
