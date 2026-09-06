import { CAPTURE_EVENT_TYPES } from "./types";
/** Only highlight and copy capture are on by default. */
export const DEFAULT_CAPTURE_SETTINGS = {
    signals: {
        highlight_selected: true,
        text_copied: true,
        page_opened: false,
        scroll_dwell: false,
        upload_field_detected: false,
    },
    dwellThresholdMs: 3000,
    debugPanel: true,
};
const STORAGE_KEY = "loom:capture-settings";
function normalize(stored) {
    const partial = (stored ?? {});
    const signals = { ...DEFAULT_CAPTURE_SETTINGS.signals };
    for (const type of CAPTURE_EVENT_TYPES) {
        const value = partial.signals?.[type];
        if (typeof value === "boolean") {
            signals[type] = value;
        }
    }
    return {
        signals,
        dwellThresholdMs: typeof partial.dwellThresholdMs === "number" && partial.dwellThresholdMs > 0
            ? partial.dwellThresholdMs
            : DEFAULT_CAPTURE_SETTINGS.dwellThresholdMs,
        debugPanel: typeof partial.debugPanel === "boolean"
            ? partial.debugPanel
            : DEFAULT_CAPTURE_SETTINGS.debugPanel,
    };
}
export async function loadCaptureSettings() {
    try {
        const stored = await chrome.storage.sync.get(STORAGE_KEY);
        return normalize(stored[STORAGE_KEY]);
    }
    catch {
        return { ...DEFAULT_CAPTURE_SETTINGS };
    }
}
export async function saveCaptureSettings(settings) {
    await chrome.storage.sync.set({ [STORAGE_KEY]: settings });
}
export async function setSignalEnabled(type, enabled) {
    const current = await loadCaptureSettings();
    const next = {
        ...current,
        signals: { ...current.signals, [type]: enabled },
    };
    await saveCaptureSettings(next);
    return next;
}
/** Subscribe to settings changes. Returns a teardown function. */
export function onCaptureSettingsChanged(listener) {
    const handler = (changes, areaName) => {
        if (areaName !== "sync" || !(STORAGE_KEY in changes))
            return;
        listener(normalize(changes[STORAGE_KEY].newValue));
    };
    chrome.storage.onChanged.addListener(handler);
    return () => chrome.storage.onChanged.removeListener(handler);
}
