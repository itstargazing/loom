import Link from "next/link";

import { formatConfidence, hostnameOf } from "@/lib/format";
import type { CellValue, SkillView, Tone } from "@/lib/skills";
import type { SkillEntryBase } from "@/lib/types";

import { DeleteSkillEntry } from "./delete-skill-entry";
import { RelativeTime } from "./relative-time";

const BADGE_CLASSES: Record<Tone, string> = {
  neutral: "loom-badge bg-background-secondary text-text-secondary",
  success: "loom-badge loom-badge-success",
  warning: "loom-badge loom-badge-warning",
  error: "loom-badge loom-badge-error",
};

export function Badge({ tone, children }: { tone: Tone; children: string }) {
  return <span className={BADGE_CLASSES[tone]}>{children}</span>;
}

function Dash() {
  return <span className="text-border">—</span>;
}

function Cell({ value }: { value: CellValue }) {
  switch (value.kind) {
    case "text":
      return value.value ? <span>{value.value}</span> : <Dash />;

    case "mono":
      return value.value ? (
        <span className="loom-mono text-xs">{value.value}</span>
      ) : (
        <Dash />
      );

    case "list":
      return value.values.length ? (
        <ul className="flex flex-col gap-0.5">
          {value.values.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      ) : (
        <Dash />
      );

    case "pairs":
      return value.entries.length ? (
        <dl className="flex flex-col gap-0.5">
          {value.entries.map(([key, detail]) => (
            <div key={key} className="flex gap-sm">
              <dt className="text-text-secondary">{key}</dt>
              <dd className="loom-mono text-xs">{detail}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <Dash />
      );

    case "badge":
      return <Badge tone={value.tone}>{value.value}</Badge>;
  }
}

/**
 * Renders any skill store from its registry entry.
 *
 * The skill-specific columns come first, followed by the envelope columns
 * (source, confidence, times seen, last seen) that every store shares.
 */
export function SkillTable({
  view,
  entries,
  canDelete = false,
}: {
  view: SkillView<SkillEntryBase>;
  entries: SkillEntryBase[];
  canDelete?: boolean;
}) {
  return (
    <div className="loom-glass loom-sheen-mid overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border-soft bg-bg-1 text-left">
            {view.columns.map((column) => (
              <th
                key={column.header}
                scope="col"
                className={`px-md py-sm font-mono text-xs font-medium text-text-secondary ${column.width ?? ""}`}
              >
                {column.header}
              </th>
            ))}
            <th
              scope="col"
              className="w-40 px-md py-sm font-mono text-xs font-medium text-text-secondary"
            >
              Source
            </th>
            <th
              scope="col"
              className="w-24 px-md py-sm text-right font-mono text-xs font-medium text-text-secondary"
            >
              Seen
            </th>
            <th
              scope="col"
              className="w-36 px-md py-sm font-mono text-xs font-medium text-text-secondary"
            >
              Last seen
            </th>
            {canDelete ? (
              <th
                scope="col"
                className="w-20 px-md py-sm font-mono text-xs font-medium text-text-secondary"
              >
                Actions
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr
              key={entry.id}
              className="border-b border-border align-top last:border-b-0 hover:bg-glass"
            >
              {view.columns.map((column) => (
                <td key={column.header} className="px-md py-sm">
                  <Cell value={column.cell(entry)} />
                </td>
              ))}
              <td className="px-md py-sm">
                <Link
                  href={entry.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  title={entry.pageTitle || entry.sourceUrl}
                  className="text-text-secondary underline decoration-border underline-offset-2 transition-colors duration-fast hover:text-text-primary"
                >
                  {hostnameOf(entry.sourceUrl)}
                </Link>
              </td>
              <td className="loom-mono px-md py-sm text-right text-xs">
                {entry.timesSeen}
                <span className="ml-1 text-text-secondary">
                  {formatConfidence(entry.confidence)}
                </span>
              </td>
              <td className="px-md py-sm text-xs text-text-secondary">
                <RelativeTime iso={entry.lastSeenAt} />
              </td>
              {canDelete ? (
                <td className="px-md py-sm text-right">
                  <DeleteSkillEntry
                    slug={view.slug}
                    id={entry.id}
                    label={view.label.toLowerCase()}
                  />
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
