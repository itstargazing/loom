import { loadSyncConfig, saveSyncConfig } from "../background/sync-config";
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
            "No token saved — capture sync will fail until you paste one.";
        return;
    }
    const preview = configToken.length <= 12
        ? "(short token set)"
        : `${configToken.slice(0, 4)}…${configToken.slice(-4)}`;
    el.textContent = `Token on disk: ${preview}`;
}
async function hydrate() {
    const config = await loadSyncConfig();
    const url = document.getElementById("api-base-url");
    const token = document.getElementById("auth-token");
    if (url)
        url.value = config.apiBaseUrl;
    if (token)
        token.value = config.authToken;
    setHint(config.authToken);
}
document.getElementById("sync-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    void (async () => {
        const url = document.getElementById("api-base-url");
        const token = document.getElementById("auth-token");
        try {
            const saved = await saveSyncConfig({
                apiBaseUrl: url?.value ?? "",
                authToken: token?.value ?? "",
            });
            setHint(saved.authToken);
            setStatus("Saved to chrome.storage.sync.");
        }
        catch (error) {
            setStatus(error instanceof Error ? error.message : "Could not save.");
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
