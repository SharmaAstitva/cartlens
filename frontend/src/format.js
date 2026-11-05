const DASH = "–";
const missing = (v) => v === null || v === undefined;

const rupees = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const rupeesCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 1,
});
const grouped = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

export const inr = (v) => (missing(v) ? DASH : rupees.format(v));
export const inrCompact = (v) => (missing(v) ? DASH : rupeesCompact.format(v));
export const num = (v) => (missing(v) ? DASH : grouped.format(v));
export const pct = (v, digits = 1) => (missing(v) ? DASH : `${(v * 100).toFixed(digits)}%`);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// Dates arrive as "YYYY-MM-DD"; split instead of new Date() so time zones can't shift the day.
const parts = (iso) => iso.slice(0, 10).split("-").map(Number);

export const monthLabel = (iso) => {
  if (!iso) return DASH;
  const [y, m] = parts(iso);
  return `${MONTHS[m - 1]} ${y}`;
};

export const dayLabel = (iso) => {
  const [, m, d] = parts(iso);
  return `${d} ${MONTHS[m - 1]}`;
};

export const longDate = (iso) => `${dayLabel(iso)} ${parts(iso)[0]}`;

export function delta(current, previous) {
  if (missing(current) || !previous) return null;
  const change = (current - previous) / previous;
  const text = `${(Math.abs(change) * 100).toFixed(1)}%`;
  if (change > 0.0005) return { text: `+${text}`, dir: "up" };
  if (change < -0.0005) return { text: `−${text}`, dir: "down" };
  return { text: "0.0%", dir: "flat" };
}

export const humanize = (column) => {
  const words = column.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
};

export function formatCell(value, column) {
  if (missing(value)) return DASH;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value !== "number") return String(value);
  if (/revenue|value|monetary|price|spend/.test(column)) return inr(value);
  if (/rate|share|pct|percent/.test(column)) return pct(value);
  return num(value);
}
