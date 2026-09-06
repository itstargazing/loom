/**
 * Backend connection settings.
 *
 * Read from chrome.storage.sync so a deployed backend can be pointed at without
 * a rebuild; the defaults cover local development. Phase 15 replaces the stub
 * token with a real session token managed by the auth provider.
 */
export const DEFAULT_SYNC_CONFIG = {
    apiBaseUrl: "http://localhost:8000",
    authToken: "loom-dev-token",
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
