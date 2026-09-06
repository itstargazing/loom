/**
 * A single debounced MutationObserver shared by every signal that needs to know
 * about newly added DOM nodes.
 *
 * One observer for the whole extension keeps the per-page cost flat as more
 * signals are added, and the work runs in an idle callback so mutation-heavy
 * pages do not jank.
 */
const DEBOUNCE_MS = 750;
const listeners = new Set();
let observer = null;
let debounceTimer = null;
let pending = [];
function runWhenIdle(callback) {
    if (typeof requestIdleCallback === "function") {
        requestIdleCallback(callback, { timeout: 1000 });
    }
    else {
        setTimeout(callback, 0);
    }
}
function drain() {
    const added = pending;
    pending = [];
    if (added.length === 0)
        return;
    runWhenIdle(() => {
        for (const listener of listeners) {
            try {
                listener(added);
            }
            catch (error) {
                console.warn("[LOOM] DOM listener failed:", error);
            }
        }
    });
}
function handleMutations(mutations) {
    for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
            if (node instanceof Element) {
                pending.push(node);
            }
        }
    }
    if (pending.length === 0)
        return;
    if (debounceTimer !== null)
        clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        debounceTimer = null;
        drain();
    }, DEBOUNCE_MS);
}
function start() {
    if (observer || !document.body)
        return;
    observer = new MutationObserver(handleMutations);
    observer.observe(document.body, { childList: true, subtree: true });
}
function stop() {
    observer?.disconnect();
    observer = null;
    if (debounceTimer !== null) {
        clearTimeout(debounceTimer);
        debounceTimer = null;
    }
    pending = [];
}
/** Subscribe to added-element batches. Returns a teardown function. */
export function watchDom(listener) {
    listeners.add(listener);
    start();
    return () => {
        listeners.delete(listener);
        if (listeners.size === 0)
            stop();
    };
}
