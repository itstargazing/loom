"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { MarkdownDoc } from "@/components/markdown-doc";
import { SourceLink } from "@/components/source-link";
import { apiErrorMessage } from "@/lib/api-error";
import { hostnameOf } from "@/lib/format";
import type { AskAnswer, Brief } from "@/lib/types";

function fileStem(topic: string): string {
  const cleaned = topic.replace(/[<>:"/\\|?*]+/g, " ").trim().slice(0, 40);
  return cleaned || "brief";
}

const PANEL =
  "loom-glass loom-sheen-mid flex w-full flex-col gap-sm px-xl py-xl";

export function AskChat() {
  const searchParams = useSearchParams();
  const preset = searchParams.get("q") ?? "";
  const mode = searchParams.get("mode");
  const deadlineId = searchParams.get("deadlineId");
  const [question, setQuestion] = useState(preset);
  const [answer, setAnswer] = useState<AskAnswer | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [briefing, setBriefing] = useState(false);
  const autoRan = useRef<string | null>(null);

  async function ask(event?: FormEvent, raw?: string) {
    event?.preventDefault();
    const q = (raw ?? question).trim();
    if (!q) return;
    setQuestion(q);
    setAsking(true);
    setError(null);
    try {
      const response = await fetch("/api/proxy/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(apiErrorMessage(body, "Ask failed"));
      }
      setAnswer(body as AskAnswer);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Ask failed");
    } finally {
      setAsking(false);
    }
  }

  async function generateBrief(raw?: string, id?: string | null) {
    const topic = (raw ?? question.trim() ?? answer?.question ?? "").trim();
    if (!topic && !id) return;
    setQuestion(topic || question);
    setBriefing(true);
    setError(null);
    try {
      const response = await fetch("/api/proxy/briefs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic || undefined,
          deadlineId: id || undefined,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(apiErrorMessage(body, "Could not generate a brief"));
      }
      setBrief(body as Brief);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not generate a brief");
    } finally {
      setBriefing(false);
    }
  }

  useEffect(() => {
    const key = `${mode ?? "ask"}:${deadlineId ?? ""}:${preset}`;
    if (autoRan.current === key) return;
    if (mode === "brief") {
      if (!preset && !deadlineId) return;
      autoRan.current = key;
      void generateBrief(preset, deadlineId);
      return;
    }
    if (!preset) return;
    autoRan.current = key;
    void ask(undefined, preset);
  }, [preset, mode, deadlineId]);

  function downloadBrief() {
    if (!brief) return;
    const blob = new Blob([brief.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${fileStem(brief.topic)}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const busy = asking || briefing;

  return (
    <div className="flex w-full flex-col gap-lg">
      <section className={PANEL}>
        <form onSubmit={(event) => void ask(event)} className="flex w-full flex-col gap-md">
          <label className="flex w-full flex-col gap-1">
            <span className="font-mono text-xs text-text-secondary">Question</span>
            <textarea
              className="min-h-24 w-full resize-y bg-transparent p-0 font-mono text-[13px] leading-relaxed text-text-primary placeholder:text-text-faint focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--text)]"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What did I save about…?"
              data-gramm="false"
              data-gramm_editor="false"
              data-enable-grammarly="false"
            />
          </label>
          <hr className="loom-divider" />
          <div className="flex flex-wrap gap-sm">
            <button type="submit" className="loom-btn" disabled={busy}>
              {asking ? "Thinking…" : "Ask"}
            </button>
            <button
              type="button"
              className="loom-btn loom-btn-secondary"
              disabled={busy || (!question.trim() && !deadlineId)}
              onClick={() => void generateBrief(question, deadlineId)}
            >
              {briefing ? "Writing brief…" : "Generate brief"}
            </button>
          </div>
          <p className="text-xs text-text-secondary">
            Ask looks up a passage. Generate brief writes a one-page note from those
            captures — it will say when the file is thin instead of guessing.
          </p>
        </form>
      </section>

      {error ? <p className="text-sm text-error">{error}</p> : null}

      {briefing && !brief ? (
        <div className={`${PANEL} text-sm text-text-secondary`}>
          Writing a one-page brief from captured pages…
        </div>
      ) : null}

      {brief ? (
        <article className="loom-glass loom-glass-bright loom-sheen-tl flex w-full flex-col gap-sm px-xl py-xl">
          <div className="flex flex-wrap items-start justify-between gap-md">
            <div className="flex flex-col gap-xs">
              <span className="loom-badge w-fit">Brief</span>
              <h2 className="loom-display font-display text-lg font-semibold tracking-tight">
                {brief.topic}
              </h2>
            </div>
            <button type="button" className="loom-btn loom-btn-secondary" onClick={downloadBrief}>
              Export markdown
            </button>
          </div>
          <hr className="loom-divider" />
          <MarkdownDoc markdown={brief.markdown} />
        </article>
      ) : null}

      {!answer && !brief && !briefing ? (
        <div className={`${PANEL} text-sm text-text-secondary`}>
          Ask a question about pages, highlights, and copies LOOM has captured.
        </div>
      ) : null}

      {answer ? (
        <article className={PANEL}>
          <span className="loom-badge w-fit">Answer</span>
          <p className="text-sm text-text-primary">{answer.answer}</p>
          {answer.empty ? (
            <p className="text-xs text-text-secondary">
              No matching captures yet — nothing was invented.
            </p>
          ) : (
            <ul className="flex w-full flex-col gap-sm">
              {answer.citations.map((citation, index) => (
                <li key={`${citation.captureEventId}-${index}`} className="flex flex-col gap-xs">
                  <p className="font-mono text-xs text-text-faint">[{index + 1}]</p>
                  <SourceLink href={citation.sourceUrl}>
                    {citation.pageTitle || hostnameOf(citation.sourceUrl)}
                  </SourceLink>
                  <span className="text-xs text-text-faint">
                    {citation.snippet.slice(0, 220)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </article>
      ) : null}
    </div>
  );
}
