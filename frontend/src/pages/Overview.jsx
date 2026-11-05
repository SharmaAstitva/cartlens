import { useState } from "react";
import DataTable from "../components/DataTable";
import { Async } from "../components/Status";
import ZoomChart from "../components/ZoomChart";
import { dayLabel, delta, inr, inrCompact, num, pct } from "../format";
import { useCountUp } from "../motion";
import { useApi } from "../useApi";

const PERIODS = [7, 30, 90];
// Each metric keeps one colour everywhere: money is amber, people are cyan, activity is violet.
const METRICS = [
  { key: "net_revenue", label: "Net revenue", fmt: inrCompact, tone: "amber" },
  { key: "orders", label: "Orders", fmt: num, tone: "violet" },
  { key: "avg_order_value", label: "Avg order value", fmt: inr, tone: "amber" },
  { key: "customers", label: "Customers", fmt: num, tone: "cyan" },
  { key: "repeat_rate", label: "Repeat rate", fmt: pct, tone: "cyan" },
  { key: "conversion_rate", label: "Conversion", fmt: (v) => pct(v, 2), tone: "violet" },
];

function KpiValue({ value, fmt }) {
  return <dd className="kpi-value">{fmt(useCountUp(value))}</dd>;
}

function Kpis({ data }) {
  return (
    <dl className="kpis">
      {METRICS.map((m) => {
        const change = delta(data.current[m.key], data.previous[m.key]);
        return (
          <div key={m.key} role="group" aria-label={m.label} className={`kpi tone-${m.tone}`}>
            <dt>{m.label}</dt>
            <KpiValue value={data.current[m.key]} fmt={m.fmt} />
            {change && (
              <dd className="kpi-delta">
                <span className={`pill ${change.dir}`}>{change.text}</span>{" "}
                <span className="muted">vs previous {data.days} days</span>
              </dd>
            )}
          </div>
        );
      })}
    </dl>
  );
}

export default function Overview() {
  const [days, setDays] = useState(30);
  const kpis = useApi(`/api/v1/kpis?days=${days}`);
  const cities = useApi("/api/v1/cities?limit=8");

  return (
    <section>
      <div className="page-head">
        <h1>Overview</h1>
        <div className="segmented" aria-label="Period">
          {PERIODS.map((d) => (
            <button key={d} type="button" aria-pressed={d === days} onClick={() => setDays(d)}>
              {d} days
            </button>
          ))}
        </div>
      </div>
      <Async result={kpis}>
        {(data) => (
          <>
            <Kpis data={data} />
            <h2>Net revenue per day</h2>
            {data.series.length === 0 ? (
              <p className="muted">No orders in this period yet.</p>
            ) : (
              <ZoomChart
                key={`${data.days}-${data.through}`}
                data={data.series.map((d) => ({ day: dayLabel(d.date), net_revenue: d.net_revenue }))}
                x="day"
                y="net_revenue"
                label="Net revenue"
                format={inr}
              />
            )}
          </>
        )}
      </Async>
      <h2>Top cities</h2>
      <Async result={cities}>
        {(rows) => (
          <DataTable
            columns={["city", "customers", "repeat_rate", "orders", "net_revenue"]}
            bars={["net_revenue"]}
            rows={rows.map((r) => [r.city, r.customers, r.repeat_rate, r.orders, r.net_revenue])}
          />
        )}
      </Async>
    </section>
  );
}
