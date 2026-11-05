import { useEffect, useRef, useState } from "react";

/** True when the browser supports media queries and the user has not asked for reduced motion. */
export const prefersMotion = () =>
  typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: no-preference)").matches;

/**
 * Animate a number from its previous value to `target` (from 0 on first render).
 * Returns the target straight away when motion is off or the value is missing.
 */
export function useCountUp(target, duration = 900) {
  const animate = typeof target === "number" && prefersMotion();
  const [shown, setShown] = useState(0);
  const last = useRef(0);

  useEffect(() => {
    if (!animate) return undefined;
    const from = last.current;
    const started = performance.now();
    let frame;
    const tick = (now) => {
      const t = Math.min(1, (now - started) / duration);
      const value = from + (target - from) * (1 - (1 - t) ** 3);
      last.current = value;
      setShown(Number.isInteger(target) ? Math.round(value) : value);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, animate, duration]);

  return animate ? shown : target;
}
