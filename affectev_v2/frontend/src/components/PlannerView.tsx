import { useEffect, useState } from "react";
import { api, bandOf, CATEGORIES, COLORS, fmt, type Category, type Location, type PlanResponse } from "../lib/api";
import FaceReader from "./FaceReader";
import RouteMap from "./RouteMap";
import { Battery, Segmented, SliderRow } from "./ui";

const LAMBDA = { f: 0.4, c: 0.4, v: 0.2 }; // Tablo 1
const SUBTITLE: Record<Category, string> = {
  Verimlilik: "En az enerji",
  Dengeli: "Süre, enerji ve konfor dengesi",
  Konfor: "En sakin sürüş",
};

export default function PlannerView({ dark, onToast }: { dark: boolean; onToast: (m: string, err?: boolean) => void }) {
  const [locations, setLocations] = useState<Location[]>([]);
  const [origin, setOrigin] = useState("Keçiören");
  const [dest, setDest] = useState("Bilkent");
  const [mode, setMode] = useState<"direct" | "fcv">("direct");
  const [cls, setCls] = useState(85);
  const [F, setF] = useState(70);
  const [C, setC] = useState(80);
  const [V, setV] = useState(60);
  const [soc, setSoc] = useState(75);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState<Category | null>(null);
  const [rated, setRated] = useState<Partial<Record<Category, number>>>({});
  const [prevAction, setPrevAction] = useState<Category | null>(null);
  const [faceOpen, setFaceOpen] = useState(false);

  useEffect(() => { api.locations().then(setLocations).catch(() => onToast("Sunucuya bağlanılamadı", true)); }, []);

  const effCls = mode === "direct" ? cls : Math.round((LAMBDA.f * F + LAMBDA.c * C + LAMBDA.v * V) * 10) / 10;
  const band = bandOf(effCls);

  async function run() {
    if (origin === dest) { onToast("Başlangıç ve varış farklı olmalı", true); return; }
    setLoading(true); setRated({});
    try {
      const body = mode === "direct"
        ? { origin, destination: dest, cls, soc, traffic_seed: 0 }
        : { origin, destination: dest, fatigue: F, cognitive: C, valence: V, soc, traffic_seed: 0 };
      const p = await api.plan(body);
      setPlan(p); setActive(p.recommended);
    } catch (e: any) {
      onToast(`Planlama hatası: ${e.message}`, true);
    } finally { setLoading(false); }
  }

  async function rate(c: Category, n: number) {
    if (!plan) return;
    const r = plan.options[c];
    const minT = Math.min(...CATEGORIES.map((k) => plan.options[k].metrics.time_min));
    try {
      await api.feedback({
        cls: plan.cls, soc, traffic_density: plan.options.Dengeli.metrics.traffic_density,
        prev_action: prevAction, action: c, stars: n, comfort: r.metrics.comfort,
        time_min: r.metrics.time_min, min_time_min: minT,
      });
      setRated((x) => ({ ...x, [c]: n })); setPrevAction(c);
      onToast("Teşekkürler, tercihiniz öğrenildi");
    } catch (e: any) { onToast(e.message, true); }
  }

  const loc = (n: string) => locations.find((l) => l.name === n);
  const opts = plan?.options ?? null;
  const best = opts ? {
    time: Math.min(...CATEGORIES.map((c) => opts[c].metrics.time_min)),
    energy: Math.min(...CATEGORIES.map((c) => opts[c].metrics.energy_kwh)),
    comfort: Math.max(...CATEGORIES.map((c) => opts[c].metrics.comfort)),
  } : null;

  return (
    <div className="stage">
      <RouteMap options={opts} active={active} recommended={plan?.recommended ?? null} onSelect={setActive}
        dark={dark} origin={loc(origin)} destination={loc(dest)} bottomPad={opts ? 260 : 60} />

      <aside className="panel-float">
        <div className="group">
          <div className="row">
            <span className="dot" style={{ background: "var(--text)" }} />
            <select value={origin} onChange={(e) => setOrigin(e.target.value)} aria-label="Başlangıç">
              {locations.map((l) => <option key={l.name}>{l.name}</option>)}
            </select>
          </div>
          <div className="row">
            <span className="dot" style={{ background: "#ff3b30" }} />
            <select value={dest} onChange={(e) => setDest(e.target.value)} aria-label="Varış">
              {locations.map((l) => <option key={l.name}>{l.name}</option>)}
            </select>
            <button className="swap-btn" title="Yer değiştir" onClick={() => { setOrigin(dest); setDest(origin); }}>⇅</button>
          </div>
        </div>

        <div className="section-label">Sürücü durumu</div>
        <div className="group">
          <div className="cls-display">
            <span className="big">{fmt(effCls, 0)}</span>
            <span className="pill">{band.name}</span>
            <span style={{ flex: 1 }} />
            <Segmented value={mode} onChange={setMode}
              options={[{ value: "direct", label: "CLS" }, { value: "fcv", label: "F·C·V" }]} />
          </div>
          {mode === "direct" ? (
            <SliderRow label="Bilişsel yük" value={cls} onChange={setCls} />
          ) : (
            <>
              <SliderRow label="Yorgunluk" value={F} onChange={setF} />
              <SliderRow label="Bilişsel yük" value={C} onChange={setC} />
              <SliderRow label="Olumsuz duygu" value={V} onChange={setV} />
            </>
          )}
          <div style={{ padding: "0 14px 12px" }}>
            <button className="btn-face" onClick={() => setFaceOpen(true)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" /><circle cx="9" cy="10" r=".6" fill="currentColor" /><circle cx="15" cy="10" r=".6" fill="currentColor" /><path d="M9 15c1.5 1.2 4.5 1.2 6 0" /></svg>
              Kamerayla yüz oku
            </button>
          </div>
        </div>

        <div className="section-label">Batarya</div>
        <div className="group">
          <div className="slider-row">
            <div className="slider-head"><span style={{ display: "flex", gap: 8, alignItems: "center" }}><Battery soc={soc} /> Tesla Model 3 SR</span><span>%{soc}</span></div>
            <input type="range" min={5} max={100} value={soc} style={{ ["--p" as any]: `${((soc - 5) / 95) * 100}%` }}
              onChange={(e) => setSoc(Number(e.target.value))} aria-label="Şarj durumu" />
          </div>
        </div>

        <button className="btn-primary" onClick={run} disabled={loading || !locations.length}>
          {loading ? <><span className="spinner" /> Rotalar hesaplanıyor…</> : "Rotaları Göster"}
        </button>
      </aside>

      {opts && best && (
        <div className="route-strip">
          {CATEGORIES.map((c) => {
            const r = opts[c], m = r.metrics, on = active === c;
            const dt = m.time_min - best.time, de = m.energy_kwh - best.energy;
            return (
              <div key={c} className={`card route-card ${on ? "active" : ""}`} style={{ ["--c" as any]: COLORS[c] }}
                onClick={() => setActive(c)} role="button" aria-pressed={on}>
                <div className="rc-head">
                  <span className="dot" style={{ background: COLORS[c], width: 12, height: 12 }} />
                  <div>
                    <div className="rc-title">{c}</div>
                    <div className="rc-sub">{SUBTITLE[c]}</div>
                  </div>
                  {plan!.recommended === c && <span className="badge ai">★ Önerilen</span>}
                </div>
                <div className="rc-time"><b>{fmt(m.time_min, 0)}</b> dk
                  <span className="rc-delta">{dt < 0.5 ? "en hızlı" : `+${fmt(dt, 0)} dk`}</span></div>
                <div className="rc-stats">
                  <span><b>{fmt(m.energy_kwh, 2)}</b> kWh{de < 0.005 ? <em> · en az</em> : null}</span>
                  <span><b>{fmt(m.distance_km, 1)}</b> km</span>
                  <span><b>{fmt(m.comfort, 0)}</b> konfor{m.comfort >= best.comfort - 0.05 ? <em> · en yüksek</em> : null}</span>
                </div>
                <div className="rc-foot">
                  <span>{m.n_intersection} kavşak · {fmt(m.n_stop, 0)} duruş · varışta %{fmt(r.soc_final, 0)}</span>
                </div>
                {r.charging && <div className="rc-foot" style={{ color: "var(--green)" }}>⚡︎ Şarj durağı · {fmt(r.charging.charge_min, 0)} dk</div>}
                {on && (
                  <div className="rc-rate" onClick={(e) => e.stopPropagation()}>
                    <span>Puanla</span>
                    <div className="stars">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <button key={n} className={n <= (rated[c] ?? 0) ? "on" : ""} onClick={() => rate(c, n)} aria-label={`${n} yıldız`}>★</button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!opts && !loading && (
        <div className="hint card">Güzergâhı ve sürücü durumunu seçip <b>Rotaları Göster</b>'e dokunun.</div>
      )}

      {faceOpen && <FaceReader cognitive={C} onClose={() => setFaceOpen(false)}
        onApply={(f, v) => { setF(f); setV(v); setMode("fcv"); onToast(`Yüz okuma uygulandı · F=${f}, V=${v}`); }} />}
    </div>
  );
}
