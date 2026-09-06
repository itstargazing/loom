/**
 * Origins allowed to use the dashboard bridge.
 *
 * Read from chrome.storage.sync alongside the backend settings, so a deployed
 * dashboard can be authorised without a rebuild. Defaults cover `next dev`.
 */
const DEFAULT_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"];
const STORAGE_KEY = "loom:bridge-origins";
function normalize(value) {
    try {
        return new URL(value).origin;
    }
    catch {
        return null;
    }
}
export async function loadBridgeOrigins() {
    let extra = [];
    try {
        const stored = await chrome.storage.sync.get(STORAGE_KEY);
        const value = stored[STORAGE_KEY];
        if (Array.isArray(value)) {
            extra = value.filter((item) => typeof item === "string");
        }
    }
    catch {
        // Storage unavailable; the defaults are enough for local development.
    }
    const origins = [...DEFAULT_ORIGINS, ...extra]
        .map(normalize)
        .filter((origin) => origin !== null);
    return [...new Set(origins)];
}
