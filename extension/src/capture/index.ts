import { captureEmitter } from "./emitter";
import { loadCaptureSettings, onCaptureSettingsChanged, type CaptureSettings } from "./settings";
import { installCopySignal } from "./signals/copy";
import { installHighlightSignal } from "./signals/highlight";
import { installPageOpenedSignal } from "./signals/page-opened";
import { installScrollDwellSignal } from "./signals/scroll-dwell";
import { installUploadFieldSignal } from "./signals/upload-field";
import type { CaptureEventType } from "./types";

type Teardown = () => void;

/**
 * Installs the passive capture signals the user has enabled.
 *
 * Disabled signals attach no listeners and no observers at all, so a page pays
 * nothing for a signal that is switched off.
 */
export async function initCapture(options?: {
  onHighlight?: (eventId: string, rect: DOMRect | null) => void;
  onCopy?: (eventId: string, rect: DOMRect | null) => void;
}): Promise<Teardown> {
  const installed = new Map<CaptureEventType, Teardown>();
  const stopLifecycleFlush = captureEmitter.installLifecycleFlush();

  const install = (type: CaptureEventType, settings: CaptureSettings): void => {
    if (installed.has(type)) return;

    switch (type) {
      case "highlight_selected":
        installed.set(type, installHighlightSignal(options?.onHighlight));
        break;
      case "text_copied":
        installed.set(type, installCopySignal(options?.onCopy));
        break;
      case "page_opened":
        installed.set(type, installPageOpenedSignal());
        break;
      case "scroll_dwell":
        installed.set(type, installScrollDwellSignal(settings.dwellThresholdMs));
        break;
      case "upload_field_detected":
        installed.set(type, installUploadFieldSignal());
        break;
    }
  };

  const uninstall = (type: CaptureEventType): void => {
    const teardown = installed.get(type);
    if (!teardown) return;
    teardown();
    installed.delete(type);
  };

  const apply = (settings: CaptureSettings): void => {
    for (const [type, enabled] of Object.entries(settings.signals) as [
      CaptureEventType,
      boolean,
    ][]) {
      if (enabled) {
        install(type, settings);
      } else {
        uninstall(type);
      }
    }
  };

  apply(await loadCaptureSettings());

  // Toggling a signal takes effect on open tabs without a reload.
  const stopWatchingSettings = onCaptureSettingsChanged(apply);

  return () => {
    for (const type of [...installed.keys()]) uninstall(type);
    stopWatchingSettings();
    stopLifecycleFlush();
    void captureEmitter.flush();
  };
}
