"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { apiErrorMessage } from "@/lib/api-error";
import { hostnameOf } from "@/lib/format";
import type { AutoAttachMatch, RecentDocument } from "@/lib/types";

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

export function AutoAttachBrowser({
  initialDocuments,
}: {
  initialDocuments: RecentDocument[];
}) {
  const router = useRouter();
  const [documents, setDocuments] = useState(initialDocuments);
  const [labelText, setLabelText] = useState("Upload your resume (PDF)");
  const [surroundingText, setSurroundingText] = useState(
    "Application materials. Attach a recent CV or resume.",
  );
  const [accept, setAccept] = useState("application/pdf");
  const [match, setMatch] = useState<AutoAttachMatch | null>(null);
  const [candidates, setCandidates] = useState<AutoAttachMatch[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function runMatch() {
    setError(null);
    try {
      const body = await proxyJson<{
        match: AutoAttachMatch | null;
        candidates: AutoAttachMatch[];
      }>("/skills/auto-attach/match", {
        method: "POST",
        body: JSON.stringify({ labelText, surroundingText, accept }),
      });
      setMatch(body.match);
      setCandidates(body.candidates);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Match failed");
    }
  }

  async function remove(doc: RecentDocument) {
    if (!window.confirm(`Remove ${doc.filename} from the index?`)) return;
    setError(null);
    try {
      await proxyJson(`/skills/auto-attach/documents/${doc.id}`, { method: "DELETE" });
      setDocuments((current) => current.filter((row) => row.id !== doc.id));
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      {error ? <p className="text-sm text-error">{error}</p> : null}

      <p className="text-sm text-text-secondary">
        LOOM indexes PDFs you open or upload (Form Filler), then suggests a match when an
        upload field appears. Suggestions never attach without a click. Enable{" "}
        <span className="loom-mono text-xs">Upload fields</span> in the extension popup.
      </p>

      <div className="loom-glass loom-sheen-mid flex flex-col gap-sm p-md">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Try a match
        </h2>
        <input
          className="loom-input"
          value={labelText}
          onChange={(event) => setLabelText(event.target.value)}
          placeholder="Field label"
        />
        <textarea
          className="loom-input min-h-[4rem]"
          value={surroundingText}
          onChange={(event) => setSurroundingText(event.target.value)}
          placeholder="Surrounding text"
        />
        <input
          className="loom-input"
          value={accept}
          onChange={(event) => setAccept(event.target.value)}
          placeholder="accept attribute"
        />
        <button type="button" className="loom-btn self-start" onClick={() => void runMatch()}>
          Match against index
        </button>
        {match ? (
          <div className="loom-glass loom-sheen-tr px-md py-sm text-sm">
            <p className="font-medium">{match.filename}</p>
            <p className="mt-1 text-xs text-text-secondary">
              {match.reason} · {Math.round(match.confidence * 100)}% ·{" "}
              {match.hasFile ? "file cached" : "metadata only"}
            </p>
          </div>
        ) : candidates.length === 0 && match === null ? null : (
          <p className="text-xs text-text-secondary">No confident match.</p>
        )}
      </div>

      <div className="flex flex-col gap-sm">
        <h2 className="font-mono text-xs font-medium text-text-secondary">
          Recent documents
        </h2>
        {documents.length === 0 ? (
          <EmptyState>
            No documents indexed yet. Open a PDF with LOOM&apos;s viewer, upload one in Form
            Filler, or wait for seed data.
          </EmptyState>
        ) : (
          <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-start justify-between gap-md py-md">
                <div className="min-w-0 text-sm">
                  <p className="font-medium">{doc.filename}</p>
                  <p className="mt-1 text-xs text-text-secondary">
                    {doc.docType.replace("_", " ")}
                    {doc.sourceUrl ? ` · ${hostnameOf(doc.sourceUrl)}` : ""}
                    {" · "}
                    {doc.hasFile ? "cached" : "no file"}
                    {" · "}
                    <RelativeTime iso={doc.lastSeenAt} />
                  </p>
                  {doc.summary ? (
                    <p className="mt-1 line-clamp-2 text-xs text-text-secondary">
                      {doc.summary}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="text-xs underline"
                  onClick={() => void remove(doc)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
