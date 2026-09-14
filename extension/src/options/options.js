import { loadSyncConfig, saveSyncConfig } from "../background/sync-config";
import { loadBridgeOrigins, saveBridgeOrigins } from "../bridge/origins";
function setStatus(message) {
    const el = document.getElementById("save-status");
    if (el)
        el.textContent = message;
}
function setHint(configToken) {
    const el = document.getElementById("token-hint");
    if (!el)
        return;
    if (!configToken) {
        el.textContent =
            "No token saved — use dashboard Sync now while signed in, or paste a JWT for background sync.";
        return;
    }
    const preview = configToken.length <= 12
        ? "(short token set)"
        : `${configToken.slice(0, 4)}…${configToken.slice(-4)}`;
    el.textContent = `Token on disk: ${preview}`;
}
function setUrlHint(apiBaseUrl) {
    const el = document.getElementById("url-hint");
    if (!el)
        return;
    try {
        const parsed = new URL(apiBaseUrl);
        el.textContent = `Will call ${parsed.origin}/api/capture/events`;
        el.classList.remove("text-error");
    }
    catch {
        el.textContent = "Enter a valid http(s) URL.";
        el.classList.add("text-error");
    }
}
async function hydrate() {
    const config = await loadSyncConfig();
    const origins = await loadBridgeOrigins();
    const url = document.getElementById("api-base-url");
    const token = document.getElementById("auth-token");
    const bridge = document.getElementById("bridge-origins");
    const privacy = document.getElementById("privacy-link");
    if (url)
        url.value = config.apiBaseUrl;
    if (token)
        token.value = config.authToken;
    if (bridge) {
        bridge.value = origins
            .filter((origin) => origin !== "http://localhost:3000" &&
            origin !== "http://127.0.0.1:3000")
            .join("\n");
    }
    if (privacy) {
        try {
            const baked = import.meta.env?.VITE_LOOM_DASHBOARD_ORIGIN;
            const base = (baked?.trim() || "http://localhost:3000").replace(/\/$/, "");
            privacy.href = `${base}/legal/privacy`;
        }
        catch {
            privacy.href = "http://localhost:3000/legal/privacy";
        }
    }
    setHint(config.authToken);
    setUrlHint(config.apiBaseUrl);
}
document.getElementById("api-base-url")?.addEventListener("input", (event) => {
    const value = event.target.value;
    setUrlHint(value);
});
document.getElementById("sync-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    void (async () => {
        const url = document.getElementById("api-base-url");
        const token = document.getElementById("auth-token");
        const bridge = document.getElementById("bridge-origins");
        try {
            new URL(url?.value ?? "");
            const saved = await saveSyncConfig({
                apiBaseUrl: url?.value ?? "",
                authToken: token?.value ?? "",
            });
            const originLines = (bridge?.value ?? "")
                .split(/\n|,/)
                .map((part) => part.trim())
                .filter(Boolean);
            await saveBridgeOrigins(originLines);
            setHint(saved.authToken);
            setUrlHint(saved.apiBaseUrl);
            setStatus("Saved to chrome.storage.sync. Reload dashboard tabs.");
        }
        catch (error) {
            setStatus(error instanceof Error ? error.message : "Could not save.");
        }
    })();
});
document.getElementById("test-api")?.addEventListener("click", () => {
    void (async () => {
        const config = await loadSyncConfig();
        try {
            const response = await fetch(`${config.apiBaseUrl.replace(/\/$/, "")}/health`);
            if (!response.ok) {
                setStatus(`API health failed: HTTP ${response.status}`);
                return;
            }
            const ready = await fetch(`${config.apiBaseUrl.replace(/\/$/, "")}/ready`);
            if (ready.status === 401 || ready.status === 403) {
                setStatus(`API reachable but auth rejected health/ready (${ready.status}).`);
                return;
            }
            if (!ready.ok) {
                setStatus(`API up but not ready (HTTP ${ready.status}). Check Postgres/Redis.`);
                return;
            }
            setStatus("API /health and /ready look good.");
        }
        catch (error) {
            setStatus(error instanceof Error
                ? `Could not reach API: ${error.message}`
                : "Could not reach API.");
        }
    })();
});
document.getElementById("clear-token")?.addEventListener("click", () => {
    void (async () => {
        const token = document.getElementById("auth-token");
        if (token)
            token.value = "";
        const saved = await saveSyncConfig({ authToken: "" });
        setHint(saved.authToken);
        setStatus("Token cleared.");
    })();
});
document.addEventListener("DOMContentLoaded", () => {
    void hydrate();
});
