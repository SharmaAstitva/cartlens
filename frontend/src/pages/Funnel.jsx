import DataTable from "../components/DataTable";
import { Async } from "../components/Status";
import { monthLabel, num, pct } from "../format";
import { useApi } from "../useApi";

const STEPS = [
  ["sessions_viewed", "Viewed a product"],
  ["sessions_added_to_cart", "Added to cart"],
  ["sessions_checked_out", "Started checkout"],
  ["sessions_ordered", "Placed an order"],
];

function Steps({ month }) {
  const top = month[STEPS[0][0]];
  return (
    <ol className="funnel" aria-label={`Funnel for ${monthLabel(month.month)}`}>
      {STEPS.map(([key, label], i) => (
        <li key={key} style={{ "--share": month[key] / top, "--i": i }}>
          <span className="funnel-label">{label}</span>
          <span className="funnel-count">{num(month[key])}</span>
          {i > 0 && (
            <span className="muted">{pct(month[key] / month[STEPS[i - 1][0]])} of previous step</span>
          )}
        </li>
      ))}
    </ol>
  );
}

export default function Funnel() {
  const funnel = useApi("/api/v1/funnel?months=6");
  return (
    <section>
      <h1>Funnel</h1>
      <Async result={funnel}>
        {(rows) =>
          rows.length === 0 ? (
            <p className="muted">No sessions yet. Run the pipeline to load data.</p>
          ) : (
            <>
              <h2>{monthLabel(rows.at(-1).month)} so far</h2>
              <Steps month={rows.at(-1)} />
              <h2>By month</h2>
              <DataTable
                columns={["month", ...STEPS.map(([k]) => k), "conversion"]}
                labels={Object.fromEntries(STEPS)}
                render={{ month: monthLabel, conversion: (v) => pct(v, 2) }}
                rows={rows.map((r) => [
                  r.month,
                  ...STEPS.map(([k]) => r[k]),
                  r.sessions_ordered / r.sessions_viewed,
                ])}
              />
            </>
          )
        }
      </Async>
    </section>
  );
}
