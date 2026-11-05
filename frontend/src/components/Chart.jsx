import { useId } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCell, humanize } from "../format";
import { axisTick, compact, tooltipProps } from "./chartTheme";
import DataTable from "./DataTable";

/** Draw an answer from the API's chart spec: bar, line, number or table. */
export default function Chart({ spec, columns, rows, height = 300 }) {
  const { type, x, y } = spec;
  const gradient = useId();
  if (type === "number" && rows.length === 1) {
    const col = y && columns.includes(y) ? y : columns[columns.length - 1];
    return <p className="big-number">{formatCell(rows[0][columns.indexOf(col)], col)}</p>;
  }
  if (type !== "bar" && type !== "line") return <DataTable columns={columns} rows={rows} />;

  const data = rows.map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));
  const tooltip = <Tooltip {...tooltipProps} formatter={(v) => [formatCell(v, y), humanize(y)]} />;
  const axes = (
    <>
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--cyan)" stopOpacity={type === "bar" ? 0.95 : 0.4} />
          <stop offset="100%" stopColor="var(--violet)" stopOpacity={type === "bar" ? 0.55 : 0} />
        </linearGradient>
      </defs>
      <CartesianGrid stroke="var(--grid)" vertical={false} />
      <XAxis dataKey={x} tick={axisTick} tickLine={false} axisLine={false} />
      <YAxis tick={axisTick} tickFormatter={compact} tickLine={false} axisLine={false} width={52} />
    </>
  );
  return (
    <>
      <div className="chart" aria-hidden="true">
        <ResponsiveContainer width="100%" height={height} initialDimension={{ width: 640, height }}>
          {type === "bar" ? (
            <BarChart data={data}>
              {axes}
              {tooltip}
              <Bar dataKey={y} fill={`url(#${gradient})`} radius={[4, 4, 0, 0]} animationDuration={800} />
            </BarChart>
          ) : (
            <AreaChart data={data}>
              {axes}
              {tooltip}
              <Area type="monotone" dataKey={y} stroke="var(--cyan)" strokeWidth={2.25} fill={`url(#${gradient})`} />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>
      <DataTable columns={columns} rows={rows} />
    </>
  );
}
