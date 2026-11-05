import { describe, expect, it } from "vitest";
import { dayLabel, delta, formatCell, humanize, inr, inrCompact, monthLabel, num, pct } from "../../format";

describe("format", () => {
  it("formats rupees with Indian digit grouping", () => {
    expect(inr(1734567)).toBe("₹17,34,567");
    expect(inrCompact(17345678)).toBe("₹1.7Cr");
    expect(num(1234567)).toBe("12,34,567");
  });

  it("formats rates as percentages", () => {
    expect(pct(0.1234)).toBe("12.3%");
    expect(pct(0.05, 0)).toBe("5%");
  });

  it("shows a dash for missing values", () => {
    for (const f of [inr, inrCompact, num, pct]) {
      expect(f(null)).toBe("–");
      expect(f(undefined)).toBe("–");
    }
  });

  it("labels dates", () => {
    expect(monthLabel("2026-03-01")).toBe("Mar 2026");
    expect(dayLabel("2026-03-07")).toBe("7 Mar");
    expect(monthLabel(null)).toBe("–");
  });

  it("computes period-over-period change", () => {
    expect(delta(125, 100)).toEqual({ text: "+25.0%", dir: "up" });
    expect(delta(80, 100)).toEqual({ text: "−20.0%", dir: "down" });
    expect(delta(100, 100)).toEqual({ text: "0.0%", dir: "flat" });
    expect(delta(5, 0)).toBeNull();
    expect(delta(null, 100)).toBeNull();
  });

  it("turns column names into labels", () => {
    expect(humanize("repeat_buyers")).toBe("Repeat buyers");
    expect(humanize("aov")).toBe("Aov");
  });

  it("formats table cells by column meaning", () => {
    expect(formatCell(1500, "net_revenue")).toBe("₹1,500");
    expect(formatCell(1500, "avg_order_value")).toBe("₹1,500");
    expect(formatCell(0.25, "refund_rate")).toBe("25.0%");
    expect(formatCell(0.25, "share")).toBe("25.0%");
    expect(formatCell(12345, "orders")).toBe("12,345");
    expect(formatCell("2026-03-01", "month")).toBe("2026-03-01");
    expect(formatCell(null, "orders")).toBe("–");
    expect(formatCell(true, "is_refunded")).toBe("Yes");
  });
});
