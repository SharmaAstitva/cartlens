import DataTable from "../components/DataTable";
import { Async } from "../components/Status";
import { longDate, num } from "../format";
import { useApi } from "../useApi";

const COUNTS = [
  ["raw_events", "Raw events"],
  ["quarantined", "Quarantined"],
  ["orders", "Orders"],
  ["customers", "Customers"],
];

const when = (iso) => (iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "–");

function Health({ data }) {
  return (
    <dl className="kpis">
      {COUNTS.map(([key, label]) => (
        <div key={key} role="group" aria-label={label} className="kpi">
          <dt>{label}</dt>
          <dd className="kpi-value">{num(data.counts?.[key])}</dd>
        </div>
      ))}
      <div role="group" aria-label="AI model" className="kpi">
        <dt>AI model</dt>
        <dd className="kpi-small">{data.llm.mode === "groq" ? data.llm.model : "Demo mode (no API key)"}</dd>
      </div>
      <div role="group" aria-label="Data through" className="kpi">
        <dt>Data through</dt>
        <dd className="kpi-small">{data.data_through ? longDate(data.data_through) : "Data not loaded yet"}</dd>
      </div>
    </dl>
  );
}

export default function Pipeline() {
  const health = useApi("/api/health");
  const runs = useApi("/api/v1/pipeline/runs?limit=20");
  return (
    <section>
      <h1>Pipeline</h1>
      <p className="lede">
        Every morning a GitHub Actions job runs the Prefect flow in Docker: load new events, quarantine
        bad ones, then <code>dbt build</code> rebuilds and tests every model.
      </p>
      <Async result={health}>{(data) => <Health data={data} />}</Async>
      <h2>Recent runs</h2>
      <Async result={runs}>
        {(rows) => (
          <DataTable
            columns={["finished_at", "status", "window_end", "events_inserted", "events_duplicate",
              "events_quarantined", "dbt_tests_passed", "error"]}
            labels={{ finished_at: "Finished", window_end: "Loaded through", events_inserted: "New events",
              events_duplicate: "Duplicates", events_quarantined: "Quarantined", dbt_tests_passed: "dbt tests" }}
            render={{
              finished_at: when,
              status: (s) => (
                <span className={`badge ${s}`}>
                  <i aria-hidden="true" />
                  {s}
                </span>
              ),
              window_end: (d) => (d ? longDate(d) : "–"),
              dbt_tests_passed: (n) => (n === null ? "–" : `${n} passed`),
              error: (e) => e ?? "",
            }}
            rows={rows.map((r) => [r.finished_at, r.status, r.window_end, r.events_inserted,
              r.events_duplicate, r.events_quarantined, r.dbt_tests_passed, r.error])}
          />
        )}
      </Async>
    </section>
  );
}
