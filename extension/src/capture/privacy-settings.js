/**
 * Local-only sensitive-domain settings.
 *
 * Mirrored from the backend privacy API so the popup can show mode for the
 * current tab without waiting on classification.
 */
import { loadSyncConfig } from "../background/sync-config";
const STORAGE_KEY = "loom:privacy-settings";
const EMPTY = {
    localOnlyDomains: [],
    defaultDomains: [],
    effectiveDomains: [],
    tradeoffNote: "Local mode uses heuristics only — no cloud AI. It may be less accurate.",
};
function normalizeHost(value) {
    let host = value.trim().toLowerCase();
    host = host.replace(/^https?:\/\//, "");
    host = host.split("/")[0] ?? host;
    if (host.startsWith("*."))
        host = host.slice(2);
    return host.replace(/^\.+|\.+$/g, "");
}
export function hostnameOf(url) {
    try {
        return new URL(url).hostname.toLowerCase().replace(/\.$/, "");
    }
    catch {
        return "";
    }
}
export function matchesLocalDomain(url, patterns) {
    const host = hostnameOf(url);
    if (!host)
        return false;
    for (const raw of patterns) {
        const pattern = normalizeHost(raw);
        if (!pattern)
            continue;
        if (host === pattern || host.endsWith(`.${pattern}`))
            return true;
    }
    return false;
}
export async function loadPrivacySettings() {
    try {
        const stored = await chrome.storage.sync.get(STORAGE_KEY);
        const partial = stored[STORAGE_KEY];
        if (!partial)
            return { ...EMPTY };
        return {
            localOnlyDomains: partial.localOnlyDomains ?? [],
            defaultDomains: partial.defaultDomains ?? [],
            effectiveDomains: partial.effectiveDomains ?? [],
            tradeoffNote: partial.tradeoffNote ?? EMPTY.tradeoffNote,
        };
    }
    catch {
        return { ...EMPTY };
    }
}
async function savePrivacySettings(settings) {
    await chrome.storage.sync.set({ [STORAGE_KEY]: settings });
}
export async function refreshPrivacySettingsFromApi() {
    const config = await loadSyncConfig();
    try {
        const response = await fetch(`${config.apiBaseUrl}/api/privacy/settings`, {
            headers: { Authorization: `Bearer ${config.authToken}` },
        });
        if (!response.ok)
            return loadPrivacySettings();
        const body = (await response.json());
        const settings = {
            localOnlyDomains: body.localOnlyDomains ?? [],
            defaultDomains: body.defaultDomains ?? [],
            effectiveDomains: body.effectiveDomains ?? [],
            tradeoffNote: body.tradeoffNote ?? EMPTY.tradeoffNote,
        };
        await savePrivacySettings(settings);
        return settings;
    }
    catch {
        return loadPrivacySettings();
    }
}
export async function saveLocalOnlyDomains(domains) {
    const config = await loadSyncConfig();
    const response = await fetch(`${config.apiBaseUrl}/api/privacy/settings`, {
        method: "PUT",
        headers: {
            Authorization: `Bearer ${config.authToken}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ localOnlyDomains: domains }),
    });
    if (!response.ok) {
        throw new Error(`Save failed (${response.status})`);
    }
    const body = (await response.json());
    const settings = {
        localOnlyDomains: body.localOnlyDomains ?? domains,
        defaultDomains: body.defaultDomains ?? [],
        effectiveDomains: body.effectiveDomains ?? domains,
        tradeoffNote: body.tradeoffNote ?? EMPTY.tradeoffNote,
    };
    await savePrivacySettings(settings);
    return settings;
}
