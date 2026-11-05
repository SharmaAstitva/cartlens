import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { prefersMotion, useCountUp } from "../../motion";

function enableMotion(reduced = false) {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: !reduced })));
  let now = 0;
  const frames = [];
  vi.spyOn(performance, "now").mockImplementation(() => now);
  vi.stubGlobal("requestAnimationFrame", vi.fn((cb) => frames.push(cb)));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  /** Advance the clock and run the frames that were waiting. */
  return (ms) =>
    act(() => {
      now += ms;
      frames.splice(0).forEach((cb) => cb(now));
    });
}

describe("prefersMotion", () => {
  it("is off when the browser cannot tell (jsdom) or the user asked for less motion", () => {
    expect(prefersMotion()).toBe(false);
    enableMotion(true);
    expect(prefersMotion()).toBe(false);
  });

  it("is on when motion is allowed", () => {
    enableMotion();
    expect(prefersMotion()).toBe(true);
  });
});

describe("useCountUp", () => {
  it("returns the target straight away without motion", () => {
    const { result } = renderHook(() => useCountUp(1234));
    expect(result.current).toBe(1234);
  });

  it("returns missing values unchanged", () => {
    enableMotion();
    const { result } = renderHook(() => useCountUp(null));
    expect(result.current).toBeNull();
  });

  it("counts whole numbers up from zero, then on to a new target", () => {
    const tick = enableMotion();
    const { result, rerender } = renderHook(({ v }) => useCountUp(v, 1000), { initialProps: { v: 1000 } });
    expect(result.current).toBe(0);
    tick(500);
    expect(result.current).toBe(875);
    expect(Number.isInteger(result.current)).toBe(true);
    tick(500);
    expect(result.current).toBe(1000);

    rerender({ v: 2000 });
    tick(1000);
    tick(1000);
    expect(result.current).toBe(2000);
  });

  it("keeps decimals for rates and stops the animation on unmount", () => {
    const tick = enableMotion();
    const { result, unmount } = renderHook(() => useCountUp(0.5, 1000));
    tick(500);
    expect(result.current).toBeCloseTo(0.4375);
    unmount();
    expect(cancelAnimationFrame).toHaveBeenCalled();
  });
});
