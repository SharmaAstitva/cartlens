// Shared Recharts styling so every chart reads as one system.
export const axisTick = { fill: "var(--muted)", fontSize: 11, fontFamily: "var(--mono)" };

export const tooltipProps = {
  cursor: { stroke: "var(--cyan)", strokeWidth: 1, strokeDasharray: "3 3" },
  contentStyle: {
    background: "var(--panel-2)",
    border: "1px solid var(--line-strong)",
    borderRadius: 8,
    boxShadow: "0 12px 32px rgb(0 0 0 / 0.45)",
    fontFamily: "var(--mono)",
    fontSize: 12,
  },
  labelStyle: { color: "var(--muted)", marginBottom: 4 },
  itemStyle: { color: "var(--text)" },
};

export const compact = (v) => (Math.abs(v) >= 1000 ? `${Math.round(v / 1000).toLocaleString("en-IN")}k` : String(v));
