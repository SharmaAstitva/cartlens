import { describe, expect, it } from "vitest";
import { canZoomIn, full, isFull, MIN_SPAN, pan, zoom } from "../../zoom";

describe("zoom helpers", () => {
  it("starts with the whole series in view", () => {
    expect(full(30)).toEqual({ start: 0, end: 29 });
    expect(full(0)).toEqual({ start: 0, end: 0 });
    expect(isFull(full(30), 30)).toBe(true);
    expect(isFull({ start: 1, end: 29 }, 30)).toBe(false);
  });

  it("zooms in around the centre and out again", () => {
    const inner = zoom(full(30), 30, 0.5);
    expect(inner).toEqual({ start: 8, end: 22 });
    expect(zoom(inner, 30, 2)).toEqual(full(30));
  });

  it("never zooms narrower than the minimum span or wider than the data", () => {
    let r = full(30);
    for (let i = 0; i < 10; i++) r = zoom(r, 30, 0.5);
    expect(r.end - r.start + 1).toBe(MIN_SPAN);
    expect(canZoomIn(r, 30)).toBe(false);
    expect(zoom(r, 30, 100)).toEqual(full(30));
    expect(canZoomIn(full(3), 3)).toBe(false);
  });

  it("keeps a zoomed window inside the data near the edges", () => {
    expect(zoom({ start: 0, end: 5 }, 30, 2)).toEqual({ start: 0, end: 11 });
    expect(zoom({ start: 24, end: 29 }, 30, 2)).toEqual({ start: 18, end: 29 });
  });

  it("pans without changing the width and stops at either end", () => {
    expect(pan({ start: 5, end: 14 }, 30, 3)).toEqual({ start: 8, end: 17 });
    expect(pan({ start: 5, end: 14 }, 30, -20)).toEqual({ start: 0, end: 9 });
    expect(pan({ start: 5, end: 14 }, 30, 99)).toEqual({ start: 20, end: 29 });
  });
});
