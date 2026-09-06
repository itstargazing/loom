/** Shared DOM helpers for the capture signals. */

const BLOCK_TAGS = new Set([
  "P",
  "LI",
  "BLOCKQUOTE",
  "PRE",
  "TD",
  "TH",
  "DD",
  "DT",
  "FIGCAPTION",
  "H1",
  "H2",
  "H3",
  "H4",
  "H5",
  "H6",
  "SECTION",
  "ARTICLE",
  "DIV",
]);

const HEADING_TAGS = new Set(["H1", "H2", "H3", "H4", "H5", "H6"]);

export function collapseWhitespace(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

export function truncate(text: string, limit: number): string {
  return text.length <= limit ? text : `${text.slice(0, limit).trimEnd()}…`;
}

/** Nearest block-level ancestor of a node, used to scope context extraction. */
export function findBlockAncestor(node: Node | null): Element | null {
  let current: Node | null = node;

  while (current) {
    if (current instanceof Element && BLOCK_TAGS.has(current.tagName)) {
      return current;
    }
    current = current.parentNode;
  }

  return null;
}

/**
 * Paragraph-level context around a selection, so a classifier can tell an
 * unfamiliar term from an ordinary sentence.
 */
export function extractContext(range: Range | null, limit = 600): string {
  if (!range) return "";

  const block = findBlockAncestor(range.commonAncestorContainer);
  const raw = collapseWhitespace(block?.textContent ?? range.toString());
  if (raw.length <= limit) return raw;

  const selected = collapseWhitespace(range.toString());
  const at = raw.indexOf(selected);
  if (at === -1) return truncate(raw, limit);

  // Centre the window on the selection so context exists on both sides.
  const padding = Math.max(0, Math.floor((limit - selected.length) / 2));
  const start = Math.max(0, at - padding);
  const slice = raw.slice(start, start + limit).trim();

  return `${start > 0 ? "…" : ""}${slice}${start + limit < raw.length ? "…" : ""}`;
}

/** Closest preceding heading, used to label a dwell section. */
export function nearestHeading(element: Element): string | null {
  let current: Element | null = element;

  while (current) {
    let sibling: Element | null = current.previousElementSibling;
    while (sibling) {
      if (HEADING_TAGS.has(sibling.tagName)) {
        const text = collapseWhitespace(sibling.textContent ?? "");
        if (text) return truncate(text, 120);
      }
      sibling = sibling.previousElementSibling;
    }
    current = current.parentElement;
  }

  return null;
}

/** Visible label text for a form control, falling back to nearby text. */
export function labelTextFor(input: HTMLInputElement): string {
  if (input.labels && input.labels.length > 0) {
    const text = collapseWhitespace(
      [...input.labels].map((label) => label.textContent ?? "").join(" "),
    );
    if (text) return truncate(text, 200);
  }

  const aria = input.getAttribute("aria-label");
  if (aria) return truncate(collapseWhitespace(aria), 200);

  const labelledBy = input.getAttribute("aria-labelledby");
  if (labelledBy) {
    const referenced = labelledBy
      .split(/\s+/)
      .map((id) => document.getElementById(id)?.textContent ?? "")
      .join(" ");
    const text = collapseWhitespace(referenced);
    if (text) return truncate(text, 200);
  }

  const fieldset = input.closest("fieldset");
  const legend = collapseWhitespace(fieldset?.querySelector("legend")?.textContent ?? "");
  if (legend) return truncate(legend, 200);

  return "";
}

/** Broader text near an element, for matching against recently seen documents. */
export function surroundingTextFor(element: Element, limit = 400): string {
  const container =
    element.closest("form, fieldset, section, article, li, td") ??
    element.parentElement ??
    element;
  return truncate(collapseWhitespace(container.textContent ?? ""), limit);
}
