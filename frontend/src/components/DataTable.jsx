import { formatCell, humanize } from "../format";

/**
 * A plain data table. Numeric columns are right-aligned; columns listed in `bars`
 * get a thin in-cell bar scaled to the column's largest value.
 */
export default function DataTable({ columns, rows, labels = {}, render = {}, bars = [] }) {
  if (!rows.length) return <p className="muted">No rows matched.</p>;
  const numeric = columns.map((_, j) => rows.some((r) => typeof r[j] === "number"));
  const max = Object.fromEntries(
    bars.map((c) => [c, Math.max(...rows.map((r) => r[columns.indexOf(c)] ?? 0))]),
  );
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c, j) => (
              <th key={c} scope="col" className={numeric[j] ? "num" : undefined}>
                {labels[c] ?? humanize(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((value, j) => {
                const c = columns[j];
                const bar = max[c] > 0 && typeof value === "number";
                return (
                  <td
                    key={c}
                    className={[numeric[j] && "num", bar && "bar-cell"].filter(Boolean).join(" ") || undefined}
                    style={bar ? { "--bar": value / max[c] } : undefined}
                    data-money={bar && /revenue|value/.test(c) ? "" : undefined}
                  >
                    {render[c] ? render[c](value) : formatCell(value, c)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
