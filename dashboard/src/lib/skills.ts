/**
 * Dashboard-side mirror of the backend's `SKILL_RESOURCES` registry.
 *
 * Each entry describes both the route and how to lay the store out, so a new
 * skill needs one addition here rather than a new page component. Columns
 * describe *what* a cell contains, not how it looks; `SkillTable` owns the
 * styling.
 */

import type {
  Citation,
  ContractFlag,
  ContradictionClaim,
  Deadline,
  GlossaryTerm,
  JobListing,
  ProductListing,
  ReadingCompilerEntry,
  SkillEntryBase,
} from "./types";

export type Tone = "neutral" | "success" | "warning" | "error";

export type CellValue =
  | { kind: "text"; value: string | null }
  | { kind: "mono"; value: string | null }
  | { kind: "list"; values: string[] }
  | { kind: "pairs"; entries: Array<[string, string]> }
  | { kind: "badge"; value: string; tone: Tone };

export interface SkillColumn<T> {
  header: string;
  cell: (entry: T) => CellValue;
  /** Tailwind width class; omit to let the column flex. */
  width?: string;
}

export interface SkillView<T> {
  slug: string;
  label: string;
  /** Shown under the page heading to explain what lands in this store. */
  description: string;
  columns: Array<SkillColumn<T>>;
}

const text = (value: string | null | undefined): CellValue => ({
  kind: "text",
  value: value ?? null,
});

const mono = (value: string | null | undefined): CellValue => ({
  kind: "mono",
  value: value ?? null,
});

const pairs = (record: Record<string, string> | undefined): CellValue => ({
  kind: "pairs",
  entries: Object.entries(record ?? {}),
});

const RISK_TONES: Record<string, Tone> = {
  low: "success",
  medium: "warning",
  high: "error",
};

/**
 * Widens a typed view so views for different skills can share one array.
 *
 * The cast is safe because a view is only ever used with entries fetched from
 * its own `slug`, and `getSkillView` is the single way to reach one.
 */
function defineSkill<T extends SkillEntryBase>(
  view: SkillView<T>,
): SkillView<SkillEntryBase> {
  return view as SkillView<SkillEntryBase>;
}

export const SKILL_VIEWS: Array<SkillView<SkillEntryBase>> = [
  defineSkill<GlossaryTerm>({
    slug: "glossary",
    label: "Glossary",
    description:
      "Terms highlighted while reading, with the definition and the sentence they appeared in.",
    columns: [
      { header: "Term", cell: (entry) => mono(entry.term), width: "w-48" },
      { header: "Definition", cell: (entry) => text(entry.definition) },
      { header: "Context", cell: (entry) => text(entry.contextSnippet) },
    ],
  }),
  defineSkill<Citation>({
    slug: "citations",
    label: "Citations",
    description:
      "Quoted passages with APA and MLA citations, grouped into collections you can export.",
    columns: [
      { header: "Quote", cell: (entry) => text(entry.quote) },
      { header: "Author", cell: (entry) => text(entry.author), width: "w-40" },
      { header: "Work", cell: (entry) => text(entry.workTitle), width: "w-48" },
      { header: "Formatted", cell: (entry) => pairs(entry.formatted), width: "w-64" },
    ],
  }),
  defineSkill<Deadline>({
    slug: "deadlines",
    label: "Deadlines",
    description:
      "Dated obligations from syllabi, contracts, and event pages, on one calendar.",
    columns: [
      { header: "Deadline", cell: (entry) => text(entry.title) },
      { header: "Due", cell: (entry) => mono(entry.dueText), width: "w-40" },
      {
        header: "Resolved",
        cell: (entry) => mono(entry.dueDate?.slice(0, 10)),
        width: "w-32",
      },
      {
        header: "Kind",
        cell: (entry) =>
          entry.kind
            ? { kind: "badge", value: entry.kind, tone: "neutral" }
            : text(null),
        width: "w-32",
      },
    ],
  }),
  defineSkill<ContradictionClaim>({
    slug: "contradictions",
    label: "Contradictions",
    description:
      "Conflicting claims from different sources, flagged by the background watcher with a plain-language explanation.",
    columns: [
      { header: "Claim", cell: (entry) => text(entry.claim) },
      { header: "Topic", cell: (entry) => mono(entry.topic), width: "w-48" },
    ],
  }),
  defineSkill<ReadingCompilerEntry>({
    slug: "reading",
    label: "Reading Compiler",
    description:
      "Passages you lingered on, merged into one clean document and exportable as Markdown or PDF.",
    columns: [
      { header: "Passage", cell: (entry) => text(entry.passage) },
      { header: "Heading", cell: (entry) => text(entry.heading), width: "w-48" },
      {
        header: "Dwell",
        cell: (entry) => mono(`${Math.round(entry.dwellMs / 1000)}s`),
        width: "w-24",
      },
    ],
  }),
  defineSkill<ProductListing>({
    slug: "products",
    label: "Product Comparisons",
    description:
      "Products seen across shopping pages. Compare specs, rank same-currency prices, and export a spreadsheet.",
    columns: [
      { header: "Product", cell: (entry) => text(entry.name) },
      { header: "Price", cell: (entry) => mono(entry.price), width: "w-28" },
      { header: "Specs", cell: (entry) => pairs(entry.specs) },
    ],
  }),
  defineSkill<JobListing>({
    slug: "jobs",
    label: "Job Listings",
    description: "Roles seen on job boards and company pages.",
    columns: [
      { header: "Role", cell: (entry) => text(entry.title) },
      { header: "Company", cell: (entry) => text(entry.company), width: "w-40" },
      { header: "Salary", cell: (entry) => mono(entry.salary), width: "w-36" },
      {
        header: "Requirements",
        cell: (entry) => ({ kind: "list", values: entry.requirements ?? [] }),
      },
      {
        header: "Apply by",
        cell: (entry) => mono(entry.applicationDeadline),
        width: "w-32",
      },
    ],
  }),
  defineSkill<ContractFlag>({
    slug: "contract-flags",
    label: "Contract Flags",
    description:
      "Clauses in terms, policies, and agreements that are worth a second look.",
    columns: [
      { header: "Clause", cell: (entry) => text(entry.clauseText) },
      { header: "Why flagged", cell: (entry) => text(entry.flagReason) },
      {
        header: "Risk",
        cell: (entry) => ({
          kind: "badge",
          value: entry.riskLevel,
          tone: RISK_TONES[entry.riskLevel] ?? "neutral",
        }),
        width: "w-24",
      },
    ],
  }),
];

/** Skills that have a dedicated page but are not SkillEntry stores. */
export const EXTRA_SKILL_LINKS: Array<{ slug: string; label: string }> = [
  { slug: "form-filler", label: "Form Filler" },
  { slug: "live-doc-diff", label: "Live Doc Diff" },
  { slug: "auto-attach", label: "Auto-Attach" },
];

const BY_SLUG = new Map(SKILL_VIEWS.map((view) => [view.slug, view]));

export function getSkillView(slug: string): SkillView<SkillEntryBase> | undefined {
  return BY_SLUG.get(slug);
}

export function skillPageExists(slug: string): boolean {
  return BY_SLUG.has(slug) || EXTRA_SKILL_LINKS.some((link) => link.slug === slug);
}
