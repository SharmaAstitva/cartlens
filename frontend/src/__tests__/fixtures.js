import { vi } from "vitest";

class Reply {
  constructor(status, body) {
    this.status = status;
    this.body = body;
  }
}

/** An HTTP response with a non-200 status, for use in mockFetch routes. */
export const reply = (status, body) => new Reply(status, body);

/** Stub global fetch. `routes` maps a path prefix to a JSON body, a reply(), or a function returning one. */
export function mockFetch(routes) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    const path = url.replace(/^https?:\/\/[^/]+/, "");
    const key = Object.keys(routes)
      .filter((prefix) => path.startsWith(prefix))
      .sort((a, b) => b.length - a.length)[0];
    if (key === undefined) throw new TypeError("Failed to fetch");
    let route = routes[key];
    if (typeof route === "function") route = route(path, options);
    const { status, body } = route instanceof Reply ? route : { status: 200, body: route };
    return { ok: status < 400, status, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export const health = {
  status: "ok",
  database: "ok",
  llm: { mode: "demo", model: null },
  counts: { raw_events: 271000, quarantined: 740, orders: 15359, customers: 7867 },
  last_run: { run_id: 3, status: "success", finished_at: "2026-11-04T01:42:10Z", window_end: "2026-11-03" },
  data_through: "2026-11-03",
};

const day = (d, rev, orders) => ({ date: d, net_revenue: rev, orders, sessions: orders * 20 });

export const kpis = {
  through: "2026-11-03",
  days: 30,
  current: {
    net_revenue: 1250000, orders: 820, sessions: 16400, customers: 700, returning_customers: 290,
    avg_order_value: 1524.39, conversion_rate: 0.05, repeat_rate: 0.4143,
  },
  previous: {
    net_revenue: 1000000, orders: 820, sessions: 15000, customers: 650, returning_customers: 300,
    avg_order_value: 1219.51, conversion_rate: 0.0547, repeat_rate: 0.4615,
  },
  series: [day("2026-11-02", 40000, 26), day("2026-11-03", 45000, 30)],
};

export const cities = [
  { city: "Mumbai", state: "Maharashtra", customers: 1100, repeat_customers: 450, repeat_rate: 0.409, orders: 2200, net_revenue: 3300000, avg_order_value: 1500 },
  { city: "Pune", state: "Maharashtra", customers: 600, repeat_customers: 260, repeat_rate: 0.433, orders: 1200, net_revenue: 1800000, avg_order_value: 1500 },
];

export const funnel = [
  { month: "2026-10-01", sessions_viewed: 6000, sessions_added_to_cart: 2280, sessions_checked_out: 1410, sessions_ordered: 1130 },
  { month: "2026-11-01", sessions_viewed: 600, sessions_added_to_cart: 230, sessions_checked_out: 140, sessions_ordered: 110 },
];

export const cohorts = [
  { cohort_month: "2026-09-01", month_number: 0, cohort_size: 500, active_customers: 500, retention_rate: 1 },
  { cohort_month: "2026-09-01", month_number: 1, cohort_size: 500, active_customers: 120, retention_rate: 0.24 },
  { cohort_month: "2026-10-01", month_number: 0, cohort_size: 650, active_customers: 650, retention_rate: 1 },
];

export const segments = [
  { segment: "Champions", customers: 400, net_revenue: 2500000, avg_recency_days: 12.5, avg_orders: 6.8 },
  { segment: "Hibernating", customers: 3000, net_revenue: 1900000, avg_recency_days: 210, avg_orders: 1.1 },
];

export const runs = [
  { run_id: 3, status: "success", as_of: "2026-11-04", started_at: "2026-11-04T01:40:00Z", finished_at: "2026-11-04T01:42:10Z",
    window_start: "2026-11-03", window_end: "2026-11-03", events_received: 1210, events_inserted: 1195, events_duplicate: 12,
    events_quarantined: 3, dbt_models_ok: 11, dbt_tests_passed: 34, dbt_tests_failed: 0, error: null },
  { run_id: 2, status: "failed", as_of: "2026-11-03", started_at: "2026-11-03T01:40:00Z", finished_at: "2026-11-03T01:40:30Z",
    window_start: null, window_end: null, events_received: null, events_inserted: null, events_duplicate: null,
    events_quarantined: null, dbt_models_ok: null, dbt_tests_passed: null, dbt_tests_failed: null, error: "connection refused" },
];

export const examples = {
  mode: "demo",
  questions: ["Which city had the most repeat buyers last month?", "How many customers are in each RFM segment?"],
};

export const answer = {
  question: "Which city had the most repeat buyers last month?",
  mode: "demo",
  sql: "SELECT\n  city,\n  COUNT(DISTINCT customer_id) AS repeat_buyers\nFROM fct_orders",
  chart: { type: "bar", x: "city", y: "repeat_buyers" },
  explanation: "Counts customers who ordered last month and had ordered before.",
  columns: ["city", "repeat_buyers"],
  rows: [["Mumbai", 52], ["Bengaluru", 47]],
  truncated: false,
};
