import { loadCaptureSettings, setSignalEnabled } from "../capture/settings";
import { CAPTURE_EVENT_DESCRIPTIONS, CAPTURE_EVENT_LABELS, CAPTURE_EVENT_TYPES, } from "../capture/types";
import { requestPdfForm, requestPdfSnapshot } from "../pdf/messages";
import { loadSyncConfig } from "../background/sync-config";
import { loadPrivacySettings, matchesLocalDomain, refreshPrivacySettingsFromApi, saveLocalOnlyDomains, } from "../capture/privacy-settings";
const FEED_POLL_MS = 1000;
const SYNC_POLL_MS = 2000;
const FEED_VISIBLE_LIMIT = 25;
function setText(id, value) {
    const el = document.getElementById(id);
    if (el)
        el.textContent = value;
}
/** Renders a badge as a text node, since some labels come from server responses. */
function setBadge(id, variant, text) {
    const host = document.getElementById(id);
    if (!host)
        return;
    const badge = document.createElement("span");
    badge.className = `loom-badge loom-badge-${variant}`;
    badge.textContent = text;
    host.replaceChildren(badge);
}
/* ---------------------------------------------------------------- settings */
function renderSignalToggles(enabled) {
    const container = document.getElementById("signal-toggles");
    if (!container)
        return;
    container.replaceChildren();
    for (const type of CAPTURE_EVENT_TYPES) {
        const row = document.createElement("div");
        row.className = "flex items-center justify-between gap-3";
        const text = document.createElement("span");
        text.className = "min-w-0 flex-1";
        const name = document.createElement("span");
        name.className = "block font-mono text-xs";
        name.textContent = CAPTURE_EVENT_LABELS[type];
        const description = document.createElement("span");
        description.className = "block mt-0.5 text-xs text-text-secondary";
        description.textContent = CAPTURE_EVENT_DESCRIPTIONS[type];
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.role = "switch";
        toggle.className = "loom-switch";
        toggle.setAttribute("aria-checked", String(enabled[type]));
        toggle.setAttribute("aria-label", CAPTURE_EVENT_LABELS[type]);
        toggle.addEventListener("click", () => {
            const next = toggle.getAttribute("aria-checked") !== "true";
            toggle.setAttribute("aria-checked", String(next));
            void setSignalEnabled(type, next);
        });
        text.append(name, description);
        row.append(text, toggle);
        container.append(row);
    }
}
/* -------------------------------------------------------------------- sync */
function renderSyncStatus(status) {
    setText("sync-queued", String(status.queued));
    setText("sync-sent", status.totalSynced.toLocaleString());
    setText("sync-last", status.lastSyncedAtMs ? new Date(status.lastSyncedAtMs).toLocaleTimeString() : "never");
    if (status.lastError) {
        setBadge("sync-badge", "error", status.lastError);
    }
    else if (status.queued > 0) {
        setBadge("sync-badge", "warning", "Pending upload");
    }
    else {
        setBadge("sync-badge", "success", "Up to date");
    }
}
async function pollSyncStatus() {
    const response = await chrome.runtime.sendMessage({ type: "sync:get-status" });
    if (response?.ok)
        renderSyncStatus(response.status);
}
function initSyncSection() {
    document.getElementById("sync-now")?.addEventListener("click", () => {
        void chrome.runtime.sendMessage({ type: "sync:now" }).then(pollSyncStatus);
    });
    void pollSyncStatus();
    setInterval(() => void pollSyncStatus(), SYNC_POLL_MS);
}
/* ---------------------------------------------------------- local-only mode */
async function renderLocalModeSection() {
    const settings = await refreshPrivacySettingsFromApi().catch(loadPrivacySettings);
    const textarea = document.getElementById("local-mode-domains");
    if (textarea) {
        textarea.value = settings.localOnlyDomains.join("\n");
    }
    setText("local-mode-defaults", settings.defaultDomains.length
        ? `Always on: ${settings.defaultDomains.join(", ")}`
        : "");
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = activeTab?.url ?? "";
    if (url && matchesLocalDomain(url, settings.effectiveDomains)) {
        setBadge("local-mode-badge", "warning", "This tab → local heuristics (no cloud AI)");
    }
    else if (url.startsWith("http")) {
        setBadge("local-mode-badge", "success", "This tab → cloud / configured AI");
    }
    else {
        setBadge("local-mode-badge", "warning", "Open an http(s) page to see mode");
    }
}
function initLocalModeSection() {
    document.getElementById("local-mode-save")?.addEventListener("click", () => {
        void (async () => {
            const status = document.getElementById("local-mode-status");
            const textarea = document.getElementById("local-mode-domains");
            const domains = (textarea?.value ?? "")
                .split(/\n|,/)
                .map((part) => part.trim())
                .filter(Boolean);
            try {
                await saveLocalOnlyDomains(domains);
                if (status)
                    status.textContent = "Saved.";
                await renderLocalModeSection();
            }
            catch (error) {
                if (status) {
                    status.textContent =
                        error instanceof Error ? error.message : "Could not save domains.";
                }
            }
        })();
    });
    void renderLocalModeSection();
}
/* ----------------------------------------------------------- live doc diff */
async function watchCurrentTab() {
    const status = document.getElementById("watch-status");
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = activeTab?.url?.trim();
    if (!url || (!url.startsWith("http://") && !url.startsWith("https://"))) {
        if (status)
            status.textContent = "Open an http(s) page first.";
        return;
    }
    const config = await loadSyncConfig();
    const label = activeTab.title?.trim() || url;
    try {
        const setsResponse = await fetch(`${config.apiBaseUrl}/api/skills/live-doc-diff/sets`, {
            headers: { Authorization: `Bearer ${config.authToken}` },
        });
        if (!setsResponse.ok) {
            throw new Error(`List failed (${setsResponse.status})`);
        }
        const sets = (await setsResponse.json());
        let setId = sets[0]?.id;
        if (!setId) {
            const created = await fetch(`${config.apiBaseUrl}/api/skills/live-doc-diff/sets`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${config.authToken}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name: "From extension" }),
            });
            if (!created.ok)
                throw new Error(`Create set failed (${created.status})`);
            const body = (await created.json());
            setId = body.id;
        }
        const added = await fetch(`${config.apiBaseUrl}/api/skills/live-doc-diff/sets/${setId}/documents`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${config.authToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ sourceUrl: url, label }),
        });
        if (!added.ok)
            throw new Error(`Add failed (${added.status})`);
        if (status) {
            status.textContent = `Added to watched set. Open the dashboard Live Doc Diff page and Scan.`;
        }
    }
    catch (error) {
        if (status) {
            status.textContent =
                error instanceof Error ? error.message : "Could not register this tab.";
        }
    }
}
function initWatchSection() {
    document.getElementById("watch-current-tab")?.addEventListener("click", () => {
        void watchCurrentTab();
    });
}
/* --------------------------------------------------------------------- pdf */
async function renderPdfStatus() {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const snapshot = await requestPdfSnapshot({ tabId: activeTab?.id });
    if (!snapshot)
        return;
    document.getElementById("pdf-section")?.classList.remove("hidden");
    setText("pdf-title", snapshot.title);
    setText("pdf-pages", String(snapshot.numPages));
    const charCount = snapshot.pages.reduce((sum, page) => sum + page.text.length, 0);
    setText("pdf-chars", charCount.toLocaleString());
    const form = await requestPdfForm({ url: snapshot.url });
    setText("pdf-fields", form?.hasFormFields ? String(form.fields.length) : "none");
    if (snapshot.usingFallback) {
        setBadge("pdf-badge", "warning", "Fallback — capture unavailable");
    }
    else {
        setBadge("pdf-badge", "success", "Text extracted");
    }
}
/* -------------------------------------------------------------- debug feed */
/** One-line description of an event, so the feed stays scannable. */
function summarize(event) {
    switch (event.type) {
        case "highlight_selected":
        case "text_copied":
            return event.payload.text;
        case "page_opened":
            return `${event.payload.contentType.toUpperCase()} · ${event.payload.wordCount} words`;
        case "scroll_dwell":
            return `${event.payload.sections.length} of ${event.payload.trackedSectionCount} sections read`;
        case "upload_field_detected":
            return event.payload.labelText || event.payload.fieldName || "unlabelled field";
    }
}
function renderFeed(feed) {
    const counts = CAPTURE_EVENT_TYPES.filter((type) => feed.counts[type] > 0)
        .map((type) => `${type}=${feed.counts[type]}`)
        .join("  ");
    setText("debug-counts", counts || "no events yet");
    const list = document.getElementById("debug-feed");
    if (!list)
        return;
    list.replaceChildren();
    for (const event of feed.events.slice(0, FEED_VISIBLE_LIMIT)) {
        const item = document.createElement("li");
        item.className = "border-l border-border pl-3 animate-fade-in";
        const header = document.createElement("p");
        header.className = "text-xs font-mono";
        header.textContent = event.type;
        const time = document.createElement("span");
        time.className = "ml-2 text-text-secondary";
        time.textContent = new Date(event.timestamp).toLocaleTimeString();
        header.append(time);
        const body = document.createElement("p");
        body.className = "mt-0.5 text-xs text-text-secondary line-clamp-2";
        body.textContent = summarize(event);
        item.append(header, body);
        list.append(item);
    }
}
async function pollFeed() {
    const response = await chrome.runtime.sendMessage({ type: "capture:get-feed" });
    if (response?.ok)
        renderFeed(response.feed);
}
function initDebugPanel() {
    document.getElementById("debug-section")?.classList.remove("hidden");
    document.getElementById("debug-clear")?.addEventListener("click", () => {
        void chrome.runtime.sendMessage({ type: "capture:clear-feed" }).then(pollFeed);
    });
    void pollFeed();
    setInterval(() => void pollFeed(), FEED_POLL_MS);
}
/* -------------------------------------------------------------------- init */
async function init() {
    const settings = await loadCaptureSettings();
    renderSignalToggles(settings.signals);
    initSyncSection();
    initLocalModeSection();
    initWatchSection();
    void renderPdfStatus();
    if (import.meta.env.DEV && settings.debugPanel) {
        initDebugPanel();
    }
}
document.addEventListener("DOMContentLoaded", () => {
    void init();
});
