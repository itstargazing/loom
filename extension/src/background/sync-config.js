/**
 * Backend connection settings.
 *
 * Read from chrome.storage.sync so a deployed backend can be pointed at without
 * a rebuild. Paste your own session/JWT token here — do not ship a shared
 * production credential in the default build.
 *
 * Store / production builds can bake defaults via Vite env:
 *   VITE_LOOM_API_BASE_URL
 *   (dashboard origin is handled in bridge/origins.ts)
 */
function bakedApiBaseUrl() {
    try {
        const value = import.meta.env
            ?.VITE_LOOM_API_BASE_URL;
        return typeof value === "string" ? value.trim() : "";
    }
    catch {
        return "";
    }
}
export const DEFAULT_SYNC_CONFIG = {
    apiBaseUrl: bakedApiBaseUrl() || "http://localhost:8000",
    // Empty by default so a shared release build does not impersonate one user.
    // Prefer Sync now from the signed-in dashboard (passes Clerk JWT).
    // Optional: paste a JWT here for background sync when the dashboard is closed.
    authToken: "",
};
const STORAGE_KEY = "loom:sync-config";
export async function loadSyncConfig() {
    try {
        const stored = await chrome.storage.sync.get(STORAGE_KEY);
        const partial = (stored[STORAGE_KEY] ?? {});
        return {
            apiBaseUrl: partial.apiBaseUrl?.trim() || DEFAULT_SYNC_CONFIG.apiBaseUrl,
            authToken: partial.authToken?.trim() || DEFAULT_SYNC_CONFIG.authToken,
        };
    }
    catch {
        return { ...DEFAULT_SYNC_CONFIG };
    }
}
export async function saveSyncConfig(next) {
    const current = await loadSyncConfig();
    const merged = {
        apiBaseUrl: next.apiBaseUrl?.trim() || current.apiBaseUrl,
        authToken: next.authToken !== undefined ? next.authToken.trim() : current.authToken,
    };
    await chrome.storage.sync.set({ [STORAGE_KEY]: merged });
    return merged;
}
