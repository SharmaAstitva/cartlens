import { monthLabel, pct } from "../format";

/** Classic retention triangle: one row per cohort, one column per month since first order. */
export default function CohortGrid({ rows }) {
  const cohorts = [...new Set(rows.map((r) => r.cohort_month))];
  const maxMonth = Math.max(...rows.map((r) => r.month_number));
  const months = Array.from({ length: maxMonth + 1 }, (_, i) => i);
  const cell = new Map(rows.map((r) => [`${r.cohort_month}|${r.month_number}`, r]));

  return (
    <div className="table-wrap">
      <table className="cohorts">
        <thead>
          <tr>
            <th scope="col">First order</th>
            <th scope="col" className="num">
              Customers
            </th>
            {months.map((m) => (
              <th key={m} scope="col" className="num">
                M{m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cohorts.map((c) => {
            const size = cell.get(`${c}|0`)?.cohort_size;
            return (
              <tr key={c}>
                <th scope="row">{monthLabel(c)}</th>
                <td className="num">{size}</td>
                {months.map((m) => {
                  const r = cell.get(`${c}|${m}`);
                  if (!r) return <td key={m} />;
                  return (
                    <td
                      key={m}
                      className="num heat"
                      style={{ "--heat": Math.min(1, r.retention_rate * 2.5) }}
                      title={`${monthLabel(c)} cohort, month ${m}: ${r.active_customers} of ${r.cohort_size} customers`}
                    >
                      {pct(r.retention_rate, 0)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
