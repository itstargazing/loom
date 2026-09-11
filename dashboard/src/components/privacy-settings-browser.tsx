"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { apiErrorMessage } from "@/lib/api-error";
import type { PrivacySettings } from "@/lib/types";

async function proxyJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, `Request failed (${response.status})`));
  }
  return body as T;
}

export function PrivacySettingsBrowser({
  initial,
}: {
  initial: PrivacySettings;
}) {
  const router = useRouter();
  const [domainsText, setDomainsText] = useState(
    initial.localOnlyDomains.join("\n"),
  );
  const [checkUrl, setCheckUrl] = useState("https://bank.example.com/login");
  const [checkResult, setCheckResult] = useState<string | null>(null);
  const [settings, setSettings] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function save() {
    setError(null);
    setStatus(null);
    try {
      const domains = domainsText
        .split(/\n|,/)
        .map((part) => part.trim())
        .filter(Boolean);
      const next = await proxyJson<PrivacySettings>("/privacy/settings", {
        method: "PUT",
        body: JSON.stringify({ localOnlyDomains: domains }),
      });
      setSettings(next);
      setDomainsText(next.localOnlyDomains.join("\n"));
      setStatus("Saved.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save");
    }
  }

  async function check() {
    setError(null);
    try {
      const params = new URLSearchParams({ url: checkUrl });
      const result = await proxyJson<{
        localMode: boolean;
        hostname: string;
        matchedPattern: string | null;
      }>(`/privacy/local-mode?${params.toString()}`);
      setCheckResult(
        result.localMode
          ? `${result.hostname} → local heuristics (matched ${result.matchedPattern})`
          : `${result.hostname} → cloud / configured AI`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Check failed");
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      {error ? <p className="text-sm text-error">{error}</p> : null}
      {status ? <p className="text-sm text-text-secondary">{status}</p> : null}

      <div className="loom-glass loom-sheen-mid px-md py-sm text-sm text-text-secondary">
        {settings.tradeoffNote}
      </div>

      <div className="flex flex-col gap-sm">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Always local (built-in)
        </h2>
        <p className="text-sm loom-mono">
          {settings.defaultDomains.length
            ? settings.defaultDomains.join(", ")
            : "None"}
        </p>
      </div>

      <div className="flex flex-col gap-sm">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Your local-only domains
        </h2>
        <textarea
          className="loom-input min-h-[8rem] loom-mono text-xs"
          value={domainsText}
          onChange={(event) => setDomainsText(event.target.value)}
          placeholder={"intranet.company.com\npayroll.example.com"}
        />
        <button type="button" className="loom-btn self-start" onClick={() => void save()}>
          Save domains
        </button>
      </div>

      <div className="loom-glass loom-sheen-tr flex flex-col gap-sm p-md">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Check a URL
        </h2>
        <input
          className="loom-input"
          value={checkUrl}
          onChange={(event) => setCheckUrl(event.target.value)}
        />
        <button
          type="button"
          className="loom-btn loom-btn-secondary self-start"
          onClick={() => void check()}
        >
          Check mode
        </button>
        {checkResult ? (
          <p className="text-sm text-text-secondary">{checkResult}</p>
        ) : null}
      </div>

      <p className="text-xs text-text-secondary">
        Effective list ({settings.effectiveDomains.length}):{" "}
        <span className="loom-mono">{settings.effectiveDomains.join(", ") || "—"}</span>
      </p>
    </div>
  );
}
