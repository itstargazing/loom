/**
 * Interactive suggestion near a file input. Never attaches without a click.
 */
const HOST_ID = "loom-auto-attach-prompt";
function tokenStyles() {
    return `
    :host { all: initial; }
    .card {
      font-family: Inter, system-ui, sans-serif;
      font-size: 12px;
      line-height: 1.4;
      color: #111111;
      background: #ffffff;
      border: 1px solid #e5e5e5;
      border-radius: 2px;
      box-shadow: 0 1px 3px rgba(17, 17, 17, 0.08);
      padding: 10px 12px;
      max-width: 300px;
      pointer-events: auto;
    }
    .title { color: #666666; margin: 0 0 4px; }
    .name {
      font-family: "JetBrains Mono", ui-monospace, monospace;
      font-weight: 500;
      margin: 0 0 6px;
      word-break: break-word;
    }
    .reason { color: #666666; margin: 0 0 10px; font-size: 11px; }
    .actions { display: flex; gap: 8px; }
    button {
      font: inherit;
      cursor: pointer;
      border: 1px solid #e5e5e5;
      background: #111111;
      color: #ffffff;
      border-radius: 2px;
      padding: 4px 10px;
    }
    button.secondary {
      background: #ffffff;
      color: #111111;
    }
    button:disabled { opacity: 0.5; cursor: default; }
  `;
}
export function dismissAutoAttachPrompt() {
    document.getElementById(HOST_ID)?.remove();
}
export function showAutoAttachPrompt(suggestion, anchor, onUse, onDismiss) {
    dismissAutoAttachPrompt();
    const host = document.createElement("div");
    host.id = HOST_ID;
    host.style.position = "fixed";
    host.style.zIndex = "2147483646";
    host.style.pointerEvents = "auto";
    const top = anchor ? Math.min(anchor.bottom + 8, window.innerHeight - 140) : 16;
    const left = anchor ? Math.min(Math.max(8, anchor.left), window.innerWidth - 320) : 16;
    host.style.top = `${Math.max(8, top)}px`;
    host.style.left = `${left}px`;
    const shadow = host.attachShadow({ mode: "open" });
    const card = document.createElement("div");
    card.className = "card";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-label", "LOOM file suggestion");
    const title = document.createElement("p");
    title.className = "title";
    title.textContent = "Use this file from earlier?";
    const name = document.createElement("p");
    name.className = "name";
    name.textContent = suggestion.filename;
    const reason = document.createElement("p");
    reason.className = "reason";
    reason.textContent = suggestion.hasFile
        ? `${suggestion.reason} · ${Math.round(suggestion.confidence * 100)}%`
        : `${suggestion.reason} · file not cached (open it again to attach)`;
    const actions = document.createElement("div");
    actions.className = "actions";
    const useBtn = document.createElement("button");
    useBtn.type = "button";
    useBtn.textContent = suggestion.hasFile ? "Use file" : "Dismiss";
    useBtn.disabled = !suggestion.hasFile;
    const dismissBtn = document.createElement("button");
    dismissBtn.type = "button";
    dismissBtn.className = "secondary";
    dismissBtn.textContent = "Not now";
    useBtn.addEventListener("click", () => {
        void Promise.resolve(onUse()).finally(() => dismissAutoAttachPrompt());
    });
    dismissBtn.addEventListener("click", () => {
        onDismiss();
        dismissAutoAttachPrompt();
    });
    if (!suggestion.hasFile) {
        useBtn.style.display = "none";
    }
    actions.append(useBtn, dismissBtn);
    card.append(title, name, reason, actions);
    const style = document.createElement("style");
    style.textContent = tokenStyles();
    shadow.append(style, card);
    document.documentElement.append(host);
}
