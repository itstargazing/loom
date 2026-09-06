/**
 * Unobtrusive confirmation shown when a capture is filed into a skill.
 *
 * Lives in a shadow root so page CSS cannot restyle it, and auto-dismisses so
 * it never interrupts reading.
 */
const DISMISS_MS = 2500;
const HOST_ID = "loom-skill-toast";
function tokenStyles() {
    return `
    :host { all: initial; }
    .toast {
      font-family: Inter, system-ui, sans-serif;
      font-size: 12px;
      line-height: 1.4;
      color: #111111;
      background: #ffffff;
      border: 1px solid #e5e5e5;
      border-radius: 2px;
      box-shadow: 0 1px 3px rgba(17, 17, 17, 0.06);
      padding: 8px 12px;
      max-width: 280px;
      animation: loom-slide-up 200ms ease-out forwards;
    }
    .label { color: #666666; }
    .detail {
      font-family: "JetBrains Mono", ui-monospace, monospace;
      font-weight: 500;
    }
    :host(.loom-out) .toast {
      animation: loom-fade-out 150ms ease-in forwards;
    }
    @keyframes loom-slide-up {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes loom-fade-out {
      from { opacity: 1; }
      to { opacity: 0; }
    }
  `;
}
export function showConfirmation(label, detail, anchor) {
    document.getElementById(HOST_ID)?.remove();
    const host = document.createElement("div");
    host.id = HOST_ID;
    host.style.position = "fixed";
    host.style.zIndex = "2147483646";
    host.style.pointerEvents = "none";
    const top = anchor ? Math.min(anchor.bottom + 8, window.innerHeight - 64) : 16;
    const left = anchor ? Math.min(Math.max(8, anchor.left), window.innerWidth - 300) : 16;
    host.style.top = `${Math.max(8, top)}px`;
    host.style.left = `${left}px`;
    const shadow = host.attachShadow({ mode: "open" });
    const wrap = document.createElement("div");
    wrap.className = "toast";
    wrap.setAttribute("role", "status");
    const labelEl = document.createElement("span");
    labelEl.className = "label";
    labelEl.textContent = `${label} · `;
    const detailEl = document.createElement("span");
    detailEl.className = "detail";
    detailEl.textContent = detail;
    wrap.append(labelEl, detailEl);
    const style = document.createElement("style");
    style.textContent = tokenStyles();
    shadow.append(style, wrap);
    document.documentElement.append(host);
    window.setTimeout(() => {
        host.classList.add("loom-out");
        window.setTimeout(() => host.remove(), 180);
    }, DISMISS_MS);
}
export function selectionRect() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0)
        return null;
    const rect = selection.getRangeAt(0).getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0)
        return null;
    return rect;
}
export function clipDetail(text, max = 72) {
    const collapsed = text.replace(/\s+/g, " ").trim();
    if (collapsed.length <= max)
        return collapsed;
    return `${collapsed.slice(0, max - 1)}…`;
}
