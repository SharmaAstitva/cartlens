// Pure helpers for the zoomable time-series chart. A range is { start, end }: inclusive row indexes.
export const MIN_SPAN = 5;

export const full = (len) => ({ start: 0, end: Math.max(0, len - 1) });

const span = (range) => range.end - range.start + 1;

export const isFull = (range, len) => range.start === 0 && range.end === len - 1;

export const canZoomIn = (range, len) => span(range) > Math.min(MIN_SPAN, len);

/** Scale the window around its centre: factor < 1 zooms in, factor > 1 zooms out. */
export function zoom(range, len, factor) {
  const next = Math.min(len, Math.max(Math.min(MIN_SPAN, len), Math.round(span(range) * factor)));
  const mid = (range.start + range.end) / 2;
  const start = Math.max(0, Math.min(Math.round(mid - (next - 1) / 2), len - next));
  return { start, end: start + next - 1 };
}

/** Slide the window by `steps` rows without changing its width. */
export function pan(range, len, steps) {
  const width = span(range);
  const start = Math.max(0, Math.min(range.start + steps, len - width));
  return { start, end: start + width - 1 };
}
