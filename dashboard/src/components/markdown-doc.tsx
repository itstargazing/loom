import type { ReactNode } from "react";

type Block =
  | { kind: "h1" | "h2" | "h3"; text: string }
  | { kind: "p"; text: string }
  | { kind: "ul"; items: string[] };

function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-medium text-text-primary">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

function parse(markdown: string): Block[] {
  const blocks: Block[] = [];
  let list: string[] = [];

  function flushList() {
    if (list.length) {
      blocks.push({ kind: "ul", items: list });
      list = [];
    }
  }

  for (const raw of markdown.replace(/\r\n/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushList();
      continue;
    }
    if (line.startsWith("### ")) {
      flushList();
      blocks.push({ kind: "h3", text: line.slice(4) });
      continue;
    }
    if (line.startsWith("## ")) {
      flushList();
      blocks.push({ kind: "h2", text: line.slice(3) });
      continue;
    }
    if (line.startsWith("# ")) {
      flushList();
      blocks.push({ kind: "h1", text: line.slice(2) });
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      list.push(line.slice(2));
      continue;
    }
    flushList();
    const previous = blocks[blocks.length - 1];
    if (previous?.kind === "p") {
      previous.text = `${previous.text} ${line.trim()}`;
    } else {
      blocks.push({ kind: "p", text: line.trim() });
    }
  }
  flushList();
  return blocks;
}

/** Renders the brief as typed sections, matching dashboard headings. */
export function MarkdownDoc({ markdown }: { markdown: string }) {
  const blocks = parse(markdown);
  return (
    <div className="flex flex-col gap-md">
      {blocks.map((block, index) => {
        if (block.kind === "h1") {
          return (
            <h2 key={index} className="loom-display font-display text-lg font-semibold tracking-tight">
              {block.text}
            </h2>
          );
        }
        if (block.kind === "h2") {
          return (
            <h3
              key={index}
              className="font-mono text-xs tracking-wide text-text-secondary"
            >
              {block.text}
            </h3>
          );
        }
        if (block.kind === "h3") {
          return (
            <h4 key={index} className="text-sm font-medium text-text-primary">
              {block.text}
            </h4>
          );
        }
        if (block.kind === "ul") {
          return (
            <ul key={index} className="flex flex-col gap-xs text-sm text-text-primary">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex} className="flex gap-sm">
                  <span className="text-text-faint">·</span>
                  <span>{inline(item)}</span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index} className="text-sm text-text-primary">
            {inline(block.text)}
          </p>
        );
      })}
    </div>
  );
}
