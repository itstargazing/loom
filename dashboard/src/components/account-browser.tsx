"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import type { Account } from "@/lib/types";

async function proxyJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export function AccountBrowser({ initial }: { initial: Account }) {
  const router = useRouter();
  const [account, setAccount] = useState(initial);
  const [displayName, setDisplayName] = useState(initial.displayName);
  const [email, setEmail] = useState(initial.email ?? "");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [purged, setPurged] = useState(false);

  async function save() {
    setError(null);
    setStatus(null);
    try {
      const next = await proxyJson<Account>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ displayName, email }),
      });
      setAccount(next);
      setDisplayName(next.displayName);
      setEmail(next.email ?? "");
      setStatus("Saved.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save");
    }
  }

  async function logout() {
    setError(null);
    setStatus(null);
    try {
      const result = await proxyJson<{ ok: boolean; detail: string }>(
        "/auth/logout",
        { method: "POST" },
      );
      setStatus(result.detail);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Logout failed");
    }
  }

  async function deleteAccount() {
    setError(null);
    setStatus(null);
    try {
      await proxyJson<void>("/auth/me", {
        method: "DELETE",
        body: JSON.stringify({ confirm }),
      });
      setStatus("Account and all LOOM data for this user were deleted.");
      setConfirm("");
      setPurged(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Delete failed");
    }
  }

  if (purged) {
    return (
      <div className="flex flex-col gap-lg">
        <p className="text-sm text-text-secondary">
          All LOOM data for this stub user is gone. The shared development bearer
          is still valid, so the next page load will recreate an empty profile
          rather than signing you out.
        </p>
        <button
          type="button"
          className="loom-btn self-start"
          onClick={() => router.refresh()}
        >
          Reload empty profile
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      {error ? <p className="text-sm text-error">{error}</p> : null}
      {status ? <p className="text-sm text-text-secondary">{status}</p> : null}

      <div className="loom-glass loom-sheen-mid px-md py-sm text-sm text-text-secondary">
        {account.sessionNote}
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-lg gap-y-xs text-sm">
        <dt className="text-text-secondary">User id</dt>
        <dd className="loom-mono">{account.userId}</dd>
        <dt className="text-text-secondary">Auth mode</dt>
        <dd className="loom-mono">{account.authMode}</dd>
      </dl>

      <div className="flex flex-col gap-sm">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Profile
        </h2>
        <label className="flex flex-col gap-xs text-sm">
          Display name
          <input
            className="loom-input"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          Email
          <input
            className="loom-input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="optional"
          />
        </label>
        <button type="button" className="loom-btn self-start" onClick={() => void save()}>
          Save profile
        </button>
      </div>

      <div className="loom-glass loom-sheen-tr flex flex-col gap-sm p-md">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Session
        </h2>
        <p className="text-sm text-text-secondary">
          Stub auth has no server-side session. The dashboard token lives in{" "}
          <span className="loom-mono">LOOM_API_TOKEN</span>. Signing out here
          only tells the client to drop its copy; it does not revoke the shared
          development bearer.
        </p>
        <button
          type="button"
          className="loom-btn loom-btn-secondary self-start"
          onClick={() => void logout()}
        >
          Sign out (client hint)
        </button>
      </div>

      <div className="loom-glass loom-sheen-bl flex flex-col gap-sm p-md">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Delete account
        </h2>
        <p className="text-sm text-text-secondary">
          Permanently erases captures, skill stores, form profiles, watched
          documents, and privacy settings for this user. Type{" "}
          <span className="loom-mono">DELETE</span> to confirm.
        </p>
        <input
          className="loom-input loom-mono"
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          placeholder="DELETE"
        />
        <button
          type="button"
          className="loom-btn loom-btn-secondary self-start text-error"
          disabled={confirm !== "DELETE"}
          onClick={() => void deleteAccount()}
        >
          Delete all data
        </button>
      </div>
    </div>
  );
}
