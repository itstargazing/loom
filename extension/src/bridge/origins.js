/**
 * Origins allowed to use the dashboard bridge.
 *
 * Read from chrome.storage.sync alongside the backend settings, so a deployed
 * dashboard can be authorised without a rebuild. Any localhost / 127.0.0.1
 * origin is allowed automatically (any port) so `next dev` on 3000/3001/… works.
 *
 * Store builds can bake `VITE_LOOM_DASHBOARD_ORIGIN` (e.g. https://app.example.com).
 */
function bakedDashboardOrigin() {
    try {
        const value = import.meta.env
            ?.VITE_LOOM_DASHBOARD_ORIGIN;
        if (typeof value !== "string" || !value.trim())
            return null;
        return new URL(value.trim()).origin;
    }
    catch {
        return null;
    }
}
const baked = bakedDashboardOrigin();
const DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    ...(baked ? [baked] : []),
];
const STORAGE_KEY = "loom:bridge-origins";
function normalize(value) {
    try {
        return new URL(value).origin;
    }
    catch {
        return null;
    }
}
function isLocalDevOrigin(origin) {
    try {
        const host = new URL(origin).hostname;
        return host === "localhost" || host === "127.0.0.1" || host === "[::1]" || host === "::1";
    }
    catch {
        return false;
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
export async function saveBridgeOrigins(raw) {
    const origins = raw
        .map(normalize)
        .filter((origin) => origin !== null);
    const unique = [...new Set(origins)];
    await chrome.storage.sync.set({ [STORAGE_KEY]: unique });
    return unique;
}
/** True when this page may install the dashboard ↔ extension bridge. */
export async function isBridgeOriginAllowed(origin) {
    if (isLocalDevOrigin(origin))
        return true;
    const allowed = await loadBridgeOrigins();
    return allowed.includes(origin);
}
