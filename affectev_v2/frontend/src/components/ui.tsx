import { useLayoutEffect, useRef, useState } from "react";

export function Segmented<T extends string>({ options, value, onChange, full = false }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; full?: boolean;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const [thumb, setThumb] = useState({ left: 2, width: 0 });
  const idx = Math.max(0, options.findIndex((o) => o.value === value));
  useLayoutEffect(() => {
    const el = refs.current[idx];
    if (el) setThumb({ left: el.offsetLeft, width: el.offsetWidth });
  }, [idx, options.length]);
  useLayoutEffect(() => {
    const onResize = () => {
      const el = refs.current[idx];
      if (el) setThumb({ left: el.offsetLeft, width: el.offsetWidth });
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [idx]);
  return (
    <div className={`segmented ${full ? "full" : ""}`} role="tablist">
      <div className="thumb" style={{ left: thumb.left, width: thumb.width }} />
      {options.map((o, i) => (
        <button key={o.value} ref={(el) => (refs.current[i] = el)} role="tab" aria-selected={o.value === value}
          onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

export function SliderRow({ label, value, onChange, min = 0, max = 100, step = 1, suffix = "", hint }: {
  label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number;
  suffix?: string; hint?: string;
}) {
  const p = ((value - min) / (max - min)) * 100;
  return (
    <div className="slider-row">
      <div className="slider-head">
        <span>{label}{hint && <span className="muted" style={{ fontSize: 12 }}> · {hint}</span>}</span>
        <span>{value}{suffix}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        style={{ ["--p" as any]: `${p}%` }} onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  );
}

export function Battery({ soc }: { soc: number }) {
  const color = soc < 20 ? "var(--red)" : soc < 40 ? "var(--orange)" : "var(--green)";
  return (
    <svg width="30" height="14" viewBox="0 0 30 14" aria-hidden>
      <rect x="0.5" y="0.5" width="25" height="13" rx="3.5" fill="none" stroke="currentColor" opacity=".4" />
      <rect x="27" y="4.5" width="2" height="5" rx="1" fill="currentColor" opacity=".4" />
      <rect x="2.5" y="2.5" width={Math.max(1, 21 * soc / 100)} height="9" rx="2" fill={color} />
    </svg>
  );
}
