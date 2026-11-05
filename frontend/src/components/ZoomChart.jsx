import { useEffect, useId, useRef, useState } from "react";
import { Area, AreaChart, Brush, CartesianGrid, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { canZoomIn, full, isFull, pan, zoom } from "../zoom";
import { axisTick, compact, tooltipProps } from "./chartTheme";
import DataTable from "./DataTable";

/**
 * A time series you can explore: zoom buttons, Ctrl/⌘ + scroll, keyboard (← → + − 0),
 * and a draggable navigator under the plot. Remount it (key) when the data set changes.
 */
export default function ZoomChart({ data, x, y, label, format, height = 280 }) {
  const len = data.length;
  const [range, setRange] = useState(() => full(len));
  const plot = useRef(null);
  const gradient = useId();

  useEffect(() => {
    const el = plot.current;
    const onWheel = (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      setRange((r) => zoom(r, len, e.deltaY < 0 ? 0.8 : 1.25));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [len]);

  const width = range.end - range.start + 1;
  const keys = {
    ArrowLeft: (r) => pan(r, len, -Math.max(1, Math.round(width / 4))),
    ArrowRight: (r) => pan(r, len, Math.max(1, Math.round(width / 4))),
    "+": (r) => zoom(r, len, 0.5),
    "=": (r) => zoom(r, len, 0.5),
    "-": (r) => zoom(r, len, 2),
    0: () => full(len),
  };
  const onKeyDown = (e) => {
    const move = keys[e.key];
    if (!move) return;
    e.preventDefault();
    setRange(move);
  };

  const visible = data.slice(range.start, range.end + 1);
  const total = visible.reduce((sum, d) => sum + d[y], 0);
  const best = visible.reduce((a, b) => (b[y] > a[y] ? b : a));

  return (
    <figure className="zoom">
      <div className="zoom-bar">
        <p className="zoom-window">
          {data[range.start][x]} to {data[range.end][x]}
          <span className="muted"> ({width} of {len} days)</span>
        </p>
        <div className="zoom-controls" role="group" aria-label="Chart zoom">
          <button type="button" aria-label="Zoom in" disabled={!canZoomIn(range, len)} onClick={() => setRange((r) => zoom(r, len, 0.5))}>
            +
          </button>
          <button type="button" aria-label="Zoom out" disabled={isFull(range, len)} onClick={() => setRange((r) => zoom(r, len, 2))}>
            −
          </button>
          <button type="button" disabled={isFull(range, len)} onClick={() => setRange(full(len))}>
            Reset
          </button>
        </div>
      </div>

      <div
        ref={plot}
        className="chart chart-live"
        tabIndex={0}
        role="group"
        aria-label={`${label} chart. Left and right arrows pan, plus and minus zoom, 0 resets.`}
        onKeyDown={onKeyDown}
      >
        <ResponsiveContainer width="100%" height={height} initialDimension={{ width: 640, height }}>
          <AreaChart data={data} margin={{ top: 12, right: 18, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--amber)" stopOpacity={0.45} />
                <stop offset="100%" stopColor="var(--amber)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey={x} tick={axisTick} tickLine={false} axisLine={false} minTickGap={24} />
            <YAxis tick={axisTick} tickFormatter={compact} tickLine={false} axisLine={false} width={52} />
            <Tooltip {...tooltipProps} formatter={(v) => [format(v), label]} />
            <Area
              type="monotone"
              dataKey={y}
              stroke="var(--amber)"
              strokeWidth={2.25}
              fill={`url(#${gradient})`}
              activeDot={{ r: 5, fill: "var(--amber)", stroke: "var(--bg)", strokeWidth: 2 }}
              animationDuration={900}
            />
            <ReferenceDot x={best[x]} y={best[y]} r={6} fill="var(--bg)" stroke="var(--cyan)" strokeWidth={2.5} />
            <Brush
              dataKey={x}
              height={34}
              startIndex={range.start}
              endIndex={range.end}
              onChange={({ startIndex, endIndex }) => setRange({ start: startIndex, end: endIndex })}
              stroke="var(--cyan)"
              fill="var(--panel)"
              travellerWidth={10}
              tickFormatter={() => ""}
            >
              <AreaChart data={data}>
                <Area type="monotone" dataKey={y} stroke="var(--cyan)" strokeWidth={1} fill="var(--cyan)" fillOpacity={0.12} isAnimationActive={false} />
              </AreaChart>
            </Brush>
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <dl className="readout">
        <div>
          <dt>Total in view</dt>
          <dd>{format(total)}</dd>
        </div>
        <div>
          <dt>Daily average</dt>
          <dd>{format(total / width)}</dd>
        </div>
        <div>
          <dt>Best day</dt>
          <dd>
            {best[x]} <span className="muted">{format(best[y])}</span>
          </dd>
        </div>
      </dl>

      <DataTable columns={[x, y]} rows={visible.map((d) => [d[x], d[y]])} labels={{ [x]: "Day", [y]: label }} />
    </figure>
  );
}
