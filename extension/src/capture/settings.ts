import { CAPTURE_EVENT_TYPES, type CaptureEventType } from "./types";

export interface CaptureSettings {
  /** Per-signal enable flags. Each toggles independently. */
  signals: Record<CaptureEventType, boolean>;
  /**
   * Minimum time a page section must stay visible to count as actually read.
   * Consumed by the scroll_dwell signal.
   */
  dwellThresholdMs: number;
  /** Shows the live event feed in the popup. Dev builds only. */
  debugPanel: boolean;
}

/** Only highlight and copy capture are on by default. */
export const DEFAULT_CAPTURE_SETTINGS: CaptureSettings = {
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

function normalize(stored: unknown): CaptureSettings {
  const partial = (stored ?? {}) as Partial<CaptureSettings>;
  const signals = { ...DEFAULT_CAPTURE_SETTINGS.signals };

  for (const type of CAPTURE_EVENT_TYPES) {
    const value = partial.signals?.[type];
    if (typeof value === "boolean") {
      signals[type] = value;
    }
  }

  return {
    signals,
    dwellThresholdMs:
      typeof partial.dwellThresholdMs === "number" && partial.dwellThresholdMs > 0
        ? partial.dwellThresholdMs
        : DEFAULT_CAPTURE_SETTINGS.dwellThresholdMs,
    debugPanel:
      typeof partial.debugPanel === "boolean"
        ? partial.debugPanel
        : DEFAULT_CAPTURE_SETTINGS.debugPanel,
  };
}

export async function loadCaptureSettings(): Promise<CaptureSettings> {
  try {
    const stored = await chrome.storage.sync.get(STORAGE_KEY);
    return normalize(stored[STORAGE_KEY]);
  } catch {
    return { ...DEFAULT_CAPTURE_SETTINGS };
  }
}

export async function saveCaptureSettings(settings: CaptureSettings): Promise<void> {
  await chrome.storage.sync.set({ [STORAGE_KEY]: settings });
}

export async function setSignalEnabled(
  type: CaptureEventType,
  enabled: boolean,
): Promise<CaptureSettings> {
  const current = await loadCaptureSettings();
  const next: CaptureSettings = {
    ...current,
    signals: { ...current.signals, [type]: enabled },
  };
  await saveCaptureSettings(next);
  return next;
}

/** Subscribe to settings changes. Returns a teardown function. */
export function onCaptureSettingsChanged(
  listener: (settings: CaptureSettings) => void,
): () => void {
  const handler = (
    changes: Record<string, chrome.storage.StorageChange>,
    areaName: string,
  ): void => {
    if (areaName !== "sync" || !(STORAGE_KEY in changes)) return;
    listener(normalize(changes[STORAGE_KEY].newValue));
  };

  chrome.storage.onChanged.addListener(handler);
  return () => chrome.storage.onChanged.removeListener(handler);
}
