import { captureEmitter } from "../emitter";
import { collapseWhitespace, nearestHeading, truncate } from "../dom-utils";
import { watchDom } from "../dom-watcher";
const SECTION_SELECTOR = "p, li, blockquote, pre, h1, h2, h3, h4";
/** Ignore fragments too short to be a meaningful passage. */
const MIN_SECTION_LENGTH = 80;
/** Bound on tracked elements, so very long pages stay cheap. */
const MAX_SECTIONS = 400;
/** A section counts as on-screen once this share of it is visible. */
const VISIBLE_RATIO = 0.5;
function qualifies(element) {
    const length = (element.textContent ?? "").trim().length;
    // Headings are short by nature but still worth tracking as section markers.
    if (/^H[1-4]$/.test(element.tagName))
        return length >= 3;
    return length >= MIN_SECTION_LENGTH;
}
/**
 * Emits scroll_dwell when the user leaves the page.
 *
 * Attention is measured per section with an IntersectionObserver rather than a
 * scroll listener, so scrolling stays smooth. Time only accrues while the tab is
 * actually visible, which keeps a backgrounded tab from inflating dwell.
 */
export function installScrollDwellSignal(dwellThresholdMs) {
    const sections = [];
    const byElement = new WeakMap();
    let paused = document.visibilityState === "hidden";
    let emitted = false;
    const startAccruing = (section, now) => {
        if (section.since === null)
            section.since = now;
    };
    const stopAccruing = (section, now) => {
        if (section.since === null)
            return;
        section.dwellMs += now - section.since;
        section.since = null;
    };
    const observer = new IntersectionObserver((entries) => {
        const now = performance.now();
        for (const entry of entries) {
            const section = byElement.get(entry.target);
            if (!section)
                continue;
            // Compare against the smaller of the element and the viewport so a
            // section taller than the screen can still register as "on screen".
            const reference = Math.min(entry.boundingClientRect.height || 1, entry.rootBounds?.height ?? window.innerHeight);
            section.onScreen =
                entry.isIntersecting && entry.intersectionRect.height >= reference * VISIBLE_RATIO;
            if (section.onScreen && !paused) {
                startAccruing(section, now);
            }
            else {
                stopAccruing(section, now);
            }
        }
    }, { threshold: [0, 0.25, 0.5, 0.75, 1] });
    const track = (elements) => {
        for (const element of elements) {
            if (sections.length >= MAX_SECTIONS)
                return;
            if (byElement.has(element) || !qualifies(element))
                continue;
            // Deliberately does not hold the element — only the WeakMap keys on it, so
            // nodes removed by infinite scroll can still be collected.
            const section = {
                index: sections.length,
                heading: nearestHeading(element),
                excerpt: truncate(collapseWhitespace(element.textContent ?? ""), 500),
                dwellMs: 0,
                onScreen: false,
                since: null,
            };
            sections.push(section);
            byElement.set(element, section);
            observer.observe(element);
        }
    };
    track(document.querySelectorAll(SECTION_SELECTOR));
    // Pick up late-loading and infinite-scroll content.
    const unwatchDom = watchDom((added) => {
        for (const element of added) {
            if (element.matches(SECTION_SELECTOR))
                track([element]);
            track(element.querySelectorAll(SECTION_SELECTOR));
        }
    });
    const onVisibilityChange = () => {
        const now = performance.now();
        paused = document.visibilityState === "hidden";
        for (const section of sections) {
            if (paused) {
                stopAccruing(section, now);
            }
            else if (section.onScreen) {
                startAccruing(section, now);
            }
        }
    };
    const emitSummary = () => {
        if (emitted)
            return;
        emitted = true;
        const now = performance.now();
        for (const section of sections)
            stopAccruing(section, now);
        const read = sections
            .filter((section) => section.dwellMs >= dwellThresholdMs)
            .map((section) => ({
            index: section.index,
            heading: section.heading,
            excerpt: section.excerpt,
            dwellMs: Math.round(section.dwellMs),
        }));
        if (read.length === 0)
            return;
        captureEmitter.emit("scroll_dwell", {
            totalVisibleMs: Math.round(sections.reduce((total, section) => total + section.dwellMs, 0)),
            sections: read,
            trackedSectionCount: sections.length,
            dwellThresholdMs,
        });
        // This runs during page teardown, so flush explicitly rather than relying on
        // the emitter's own pagehide listener, which may already have fired.
        void captureEmitter.flush();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pagehide", emitSummary);
    return () => {
        emitSummary();
        observer.disconnect();
        unwatchDom();
        document.removeEventListener("visibilitychange", onVisibilityChange);
        window.removeEventListener("pagehide", emitSummary);
    };
}
