import { useEffect, useRef } from "react";

/**
 * Calls `fn` when the browser tab regains focus / becomes visible again,
 * so data stays fresh without a manual reload. Throttled so rapid
 * focus/visibility toggles don't hammer the backend.
 *
 * @param {Function} fn - async or sync refetch callback
 * @param {Object} opts
 * @param {boolean} opts.enabled - when false, listeners are not attached
 * @param {number} opts.throttleMs - minimum gap between refetches (default 8s)
 */
export function useVisibilityRefetch(fn, { enabled = true, throttleMs = 8000 } = {}) {
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const lastRun = useRef(0);

  useEffect(() => {
    if (!enabled) return undefined;

    const maybeRun = () => {
      if (document.visibilityState === "hidden") return;
      const now = Date.now();
      if (now - lastRun.current < throttleMs) return;
      lastRun.current = now;
      try {
        fnRef.current?.();
      } catch (e) {
        /* swallow — refetch is best-effort */
      }
    };

    const onVisibility = () => maybeRun();
    const onFocus = () => maybeRun();

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("focus", onFocus);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("focus", onFocus);
    };
  }, [enabled, throttleMs]);
}

export default useVisibilityRefetch;
