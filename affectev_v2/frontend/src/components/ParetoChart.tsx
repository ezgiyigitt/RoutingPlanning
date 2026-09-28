import { useState } from "react";
import { CATEGORIES, COLORS, fmt, type Category, type PlanResponse } from "../lib/api";

export default function ParetoChart({ plan, height = 190 }: { plan: PlanResponse; height?: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 420, H = height, m = { l: 40, r: 12, t: 10, b: 30 };
  const pts = plan.front;
  const all = [...pts, ...plan.dominated];
  const ex = [Math.min(...all.map((p) => p.energy)), Math.max(...all.map((p) => p.energy))];
  const ey = [Math.min(...all.map((p) => p.time)), Math.max(...all.map((p) => p.time))];
  const padx = (ex[1] - ex[0]) * 0.08 || 0.1, pady = (ey[1] - ey[0]) * 0.08 || 0.5;
  const sx = (v: number) => m.l + ((v - (ex[0] - padx)) / (ex[1] - ex[0] + 2 * padx)) * (W - m.l - m.r);
  const sy = (v: number) => H - m.b - ((v - (ey[0] - pady)) / (ey[1] - ey[0] + 2 * pady)) * (H - m.t - m.b);
  const cmin = Math.min(...pts.map((p) => p.comfort)), cmax = Math.max(...pts.map((p) => p.comfort));
  const op = (c: number) => 0.25 + 0.75 * ((c - cmin) / (cmax - cmin || 1));
  const catOf = (i: number) => (CATEGORIES.find((c) => plan.categories[c] === i) as Category | undefined);
  const ticks = (a: number, b: number, n = 4) => Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);
  const h = hover != null ? pts[hover] : null;
  return (
    <div style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block" }}>
        {ticks(ey[0], ey[1]).map((v, i) => (
          <g key={`y${i}`}>
            <line x1={m.l} x2={W - m.r} y1={sy(v)} y2={sy(v)} stroke="var(--separator)" strokeWidth={0.5} />
            <text x={m.l - 6} y={sy(v) + 3} fontSize={9} textAnchor="end" fill="var(--text-3)">{fmt(v, 0)}</text>
          </g>
        ))}
        {ticks(ex[0], ex[1]).map((v, i) => (
          <text key={`x${i}`} x={sx(v)} y={H - m.b + 13} fontSize={9} textAnchor="middle" fill="var(--text-3)">{fmt(v, 2)}</text>
        ))}
        <text x={(W + m.l) / 2} y={H - 3} fontSize={9.5} textAnchor="middle" fill="var(--text-2)">Enerji (kWh)</text>
        <text x={10} y={(H - m.b) / 2} fontSize={9.5} textAnchor="middle" fill="var(--text-2)" transform={`rotate(-90 10 ${(H - m.b) / 2})`}>Süre (dk)</text>
        {plan.dominated.map((p, i) => (
          <g key={`d${i}`} stroke="var(--text-3)" strokeWidth={0.8} opacity={0.45}>
            <line x1={sx(p.energy) - 2.5} x2={sx(p.energy) + 2.5} y1={sy(p.time) - 2.5} y2={sy(p.time) + 2.5} />
            <line x1={sx(p.energy) - 2.5} x2={sx(p.energy) + 2.5} y1={sy(p.time) + 2.5} y2={sy(p.time) - 2.5} />
          </g>
        ))}
        {pts.map((p, i) => {
          const c = catOf(i);
          const sel = i === plan.selected_index;
          return (
            <g key={i} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}>
              {sel && <circle cx={sx(p.energy)} cy={sy(p.time)} r={9} fill="none" stroke="var(--text)" strokeWidth={1.4} />}
              <circle cx={sx(p.energy)} cy={sy(p.time)} r={c ? 5.5 : 3.6}
                fill={c ? COLORS[c] : "var(--accent)"} fillOpacity={c ? 1 : op(p.comfort)}
                stroke="var(--bg-elev)" strokeWidth={c ? 1.5 : 0.6} />
            </g>
          );
        })}
      </svg>
      {h && (
        <div style={{ position: "absolute", left: `${(sx(h.energy) / W) * 100}%`, top: sy(h.time) - 58, transform: "translateX(-50%)",
          background: "var(--bg-elev)", boxShadow: "var(--shadow)", borderRadius: 10, padding: "6px 9px", fontSize: 11.5, pointerEvents: "none", whiteSpace: "nowrap" }}>
          <b>{fmt(h.energy, 2)} kWh · {fmt(h.time)} dk</b><br />Konfor {fmt(h.comfort)} · {fmt(h.distance)} km
        </div>
      )}
    </div>
  );
}
