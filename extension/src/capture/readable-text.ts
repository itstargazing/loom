import { collapseWhitespace } from "./dom-utils";

/**
 * Reader-mode-style text extraction.
 *
 * Scores candidate containers by paragraph density rather than raw text length,
 * which keeps navigation, sidebars, and comment threads out of the result. A
 * hand-rolled heuristic is used instead of a full Readability dependency so the
 * content script stays small and fast on every page load.
 */

const MAX_TEXT_LENGTH = 50_000;

const STRIPPED_SELECTOR = [
  "script",
  "style",
  "noscript",
  "svg",
  "canvas",
  "iframe",
  "nav",
  "header",
  "footer",
  "aside",
  "form",
  "button",
  "select",
  "[aria-hidden='true']",
  "[hidden]",
  "[role='navigation']",
  "[role='banner']",
  "[role='complementary']",
].join(",");

const UNLIKELY_PATTERN =
  /(^|[\s_-])(nav|menu|sidebar|footer|header|comment|promo|advert|ads?|banner|cookie|newsletter|social|share|related|breadcrumb|pagination|modal|popup)([\s_-]|$)/i;

function isUnlikelyContainer(element: Element): boolean {
  if (typeof element.className !== "string") return false;
  return UNLIKELY_PATTERN.test(`${element.className} ${element.id}`);
}

function scoreCandidate(element: Element): number {
  const paragraphs = element.querySelectorAll("p, li, blockquote, pre");
  let score = 0;

  for (const paragraph of paragraphs) {
    const length = (paragraph.textContent ?? "").trim().length;
    // Short fragments are usually UI chrome, not prose.
    if (length < 40) continue;
    score += Math.min(length, 1000);
  }

  if (isUnlikelyContainer(element)) score *= 0.25;

  return score;
}

function pickContentRoot(root: Element): Element {
  const semantic = root.querySelector("article, main, [role='main']");
  if (semantic && scoreCandidate(semantic) > 0) return semantic;

  const candidates = root.querySelectorAll("article, main, section, div");
  let best = root;
  let bestScore = scoreCandidate(root);

  // Cap the search so pathologically large DOMs cannot stall page load.
  let examined = 0;
  for (const candidate of candidates) {
    if (examined >= 500) break;
    examined += 1;

    const score = scoreCandidate(candidate);
    if (score > bestScore) {
      best = candidate;
      bestScore = score;
    }
  }

  return best;
}

export interface ReadableText {
  text: string;
  wordCount: number;
  truncated: boolean;
}

export function extractReadableText(): ReadableText {
  if (!document.body) {
    return { text: "", wordCount: 0, truncated: false };
  }

  // Work on a detached clone so stripping elements never touches the live page.
  const clone = document.body.cloneNode(true) as HTMLElement;
  for (const node of clone.querySelectorAll(STRIPPED_SELECTOR)) {
    node.remove();
  }

  const root = pickContentRoot(clone);
  const blocks: string[] = [];

  for (const block of root.querySelectorAll("h1, h2, h3, h4, h5, h6, p, li, blockquote, pre")) {
    const text = collapseWhitespace(block.textContent ?? "");
    if (text.length >= 2) blocks.push(text);
  }

  const joined = blocks.length > 0 ? blocks.join("\n\n") : collapseWhitespace(root.textContent ?? "");
  const truncated = joined.length > MAX_TEXT_LENGTH;
  const text = truncated ? joined.slice(0, MAX_TEXT_LENGTH) : joined;

  return {
    text,
    wordCount: text.length === 0 ? 0 : text.split(/\s+/).length,
    truncated,
  };
}
