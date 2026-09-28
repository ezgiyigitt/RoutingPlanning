import { useEffect, useRef, useState } from "react";
import {
  api, bandOf, CATEGORIES, COLORS, fmt,
  type Category, type Driver, type FaceResult, type Location, type PlanResponse, type Vehicle, type Weather,
} from "../lib/api";
import FaceCapture from "./FaceCapture";
import RouteMap from "./RouteMap";
import { Battery, SliderRow } from "./ui";

const STEPS = ["Sürücü", "Araç", "Hava", "Analiz", "Güzergâh", "Rotalar"];
const LAMBDA = { f: 0.4, c: 0.4, v: 0.2 }; // Tablo 1
const SUBTITLE: Record<Category, string> = {
  Verimlilik: "En az enerji", Dengeli: "Süre, enerji ve konfor dengesi", Konfor: "En sakin sürüş",
};
const STATE_MSG: Record<string, string> = {
  "Çok Enerjik": "Verimlilik ve hız öncelikli rotalar öne çıkarılacak.",
  "Enerjik": "Enerji ve süre ağırlıklı rotalar öne çıkarılacak.",
  "Nötr": "Konfor giderek önem kazanıyor; dengeli rotalar öne çıkarılacak.",
  "Yorgun": "Daha az kavşaklı, sakin rotalar öne çıkarılacak.",
  "Stresli": "Konfor en önemli kriter; en sakin rotalar öne çıkarılacak.",
};

function Stepper({ step, onJump }: { step: number; onJump: (i: number) => void }) {
  return (
    <div className="stepper-bar">
      {STEPS.map((s, i) => (
        <button key={s} className={`st ${i === step ? "cur" : ""} ${i < step ? "done" : ""}`}
          disabled={i > step} onClick={() => i < step && onJump(i)}>
          <span className="num">{i < step ? "✓" : i + 1}</span><span className="lbl">{s}</span>
        </button>
      ))}
    </div>
  );
}

const WeatherIcon = ({ id }: { id: string }) => {
  const p = { width: 34, height: 34, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (id === "acik") return <svg {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>;
  if (id === "yagmurlu") return <svg {...p}><path d="M7 15a4.5 4.5 0 1 1 .9-8.9A6 6 0 0 1 19 9a3.5 3.5 0 0 1-1 6.9H7z" /><path d="M8 19l-1 2M12 19l-1 2M16 19l-1 2" /></svg>;
  if (id === "karli") return <svg {...p}><path d="M12 2v20M4.2 7l15.6 10M4.2 17L19.8 7" /><path d="M9.5 3.5L12 5l2.5-1.5M9.5 20.5L12 19l2.5 1.5" /></svg>;
  return <svg {...p}><path d="M14 14.8V5a2 2 0 1 0-4 0v9.8a4 4 0 1 0 4 0z" /><path d="M12 9v6" /></svg>;
};

export default function Wizard({ dark, onToast }: { dark: boolean; onToast: (m: string, err?: boolean) => void }) {
  const [step, setStep] = useState(0);
  // Seçenekler
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [weathers, setWeathers] = useState<Weather[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  // Seçimler
  const [driver, setDriver] = useState<Driver | null>(null);
  const [newName, setNewName] = useState("");
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [soc, setSoc] = useState(75);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [C, setC] = useState(50);
  const [manual, setManual] = useState(false);
  const [F, setF] = useState(40);
  const [V, setV] = useState(40);
  const [face, setFace] = useState<FaceResult | null>(null);
  const [cls, setCls] = useState<number | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [camKey, setCamKey] = useState(0);
  const [origin, setOrigin] = useState("Keçiören");
  const [dest, setDest] = useState("Bilkent");
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState<Category | null>(null);
  const [rated, setRated] = useState(0);
  const prevAction = useRef<Category | null>(null);

  useEffect(() => {
    const fail = (what: string) => () => onToast(`${what} yüklenemedi. Sunucuyu yeniden başlatın (AffectEV_Baslat.bat).`, true);
    api.drivers().then(setDrivers).catch(fail("Sürücüler"));
    api.vehicles().then(setVehicles).catch(fail("Araçlar"));
    api.weather().then(setWeathers).catch(fail("Hava durumu seçenekleri"));
    api.locations().then(setLocations).catch(fail("Konumlar"));
  }, []);

  // CLS sonucu gösterildikten sonra otomatik olarak güzergâh adımına geç
  useEffect(() => {
    if (countdown === null) return;
    if (countdown <= 0) { setCountdown(null); setStep(4); return; }
    const t = setTimeout(() => setCountdown((c) => (c === null ? null : c - 1)), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  function finishAnalysis(f: number, v: number) {
    const c = Math.round((LAMBDA.f * f + LAMBDA.c * C + LAMBDA.v * v) * 10) / 10;
    setF(f); setV(v); setCls(c); setCountdown(4);
  }

  async function addDriver() {
    if (!newName.trim()) return;
    try {
      const d = await api.addDriver(newName.trim());
      setDrivers((x) => [...x, d]); setDriver(d); setNewName("");
    } catch (e: any) { onToast(e.message, true); }
  }

  async function computeRoutes() {
    if (origin === dest) { onToast("Başlangıç ve varış farklı olmalı", true); return; }
    if (!driver || !vehicle || !weather || cls === null) return;
    setLoading(true); setRated(0);
    try {
      const p = await api.plan({
        origin, destination: dest, fatigue: F, cognitive: C, valence: V, soc, traffic_seed: 0,
        vehicle: vehicle.id, weather: weather.id, driver_id: driver.id,
      });
      setPlan(p); setActive(p.recommended); setStep(5);
    } catch (e: any) { onToast(`Planlama hatası: ${e.message}`, true); }
    finally { setLoading(false); }
  }

  async function rate(n: number) {
    if (!plan || !active || !driver) return;
    const r = plan.options[active];
    const minT = Math.min(...CATEGORIES.map((k) => plan.options[k].metrics.time_min));
    try {
      await api.feedback({
        driver_id: driver.id, cls: plan.cls, soc, traffic_density: plan.options.Dengeli.metrics.traffic_density,
        prev_action: prevAction.current, action: active, stars: n, comfort: r.metrics.comfort,
        time_min: r.metrics.time_min, min_time_min: minT,
      });
      setRated(n); prevAction.current = active;
      onToast(`Teşekkürler ${driver.name}, tercihin öğrenildi`);
    } catch (e: any) { onToast(e.message, true); }
  }

  function newTrip() {
    setPlan(null); setActive(null); setFace(null); setCls(null); setManual(false); setStep(3);
  }

  const band = bandOf(cls ?? 0);
  const loc = (n: string) => locations.find((l) => l.name === n);

  return (
    <div className="wizard">
      <Stepper step={step} onJump={(i) => { setCountdown(null); setStep(i); }} />

      {/* 1 · Sürücü */}
      {step === 0 && (
        <section className="wz-card">
          <h1>Sürücü kim?</h1>
          <p className="wz-lead">Kayıtlı sürücülerden birini seçin ya da yeni sürücü ekleyin. Her sürücünün rota tercihleri ayrı öğrenilir.</p>
          <div className="choice-grid">
            {drivers.map((d) => (
              <button key={d.id} className={`choice ${driver?.id === d.id ? "sel" : ""}`} onClick={() => setDriver(d)}>
                <span className="avatar">{d.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}</span>
                <b>{d.name}</b>
                <small>{[d.age, d.job].filter(Boolean).join(" · ") || (d.legacy ? "Kayıtlı sürücü" : "Yeni profil")}</small>
                {d.feedbacks ? <small className="muted-2">{d.feedbacks} geri bildirim</small> : null}
              </button>
            ))}
            <div className="choice add">
              <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Yeni sürücü adı"
                onKeyDown={(e) => e.key === "Enter" && addDriver()} maxLength={40} />
              <button className="btn-secondary" onClick={addDriver} disabled={!newName.trim()}>Ekle</button>
            </div>
          </div>
          <div className="wz-actions"><span />
            <button className="btn-primary" disabled={!driver} onClick={() => setStep(1)}>Devam</button></div>
        </section>
      )}

      {/* 2 · Araç */}
      {step === 1 && (
        <section className="wz-card">
          <h1>Araç seçimi</h1>
          <p className="wz-lead">Enerji hesabı (Dn. 3) araca özgü parametrelerle yapılır.</p>
          <div className="choice-grid">
            {vehicles.map((v) => (
              <button key={v.id} className={`choice left ${vehicle?.id === v.id ? "sel" : ""}`} onClick={() => setVehicle(v)}>
                <b>{v.name}</b>
                <small>{fmt(v.battery_kwh, 1)} kWh · C<sub>d</sub> {fmt(v.Cd, 3)} · {fmt(v.mass_kg, 0)} kg</small>
                {v.note && <small className="note-inline">{v.note}</small>}
              </button>
            ))}
          </div>
          <div className="group" style={{ marginTop: 16 }}>
            <div className="slider-row">
              <div className="slider-head"><span style={{ display: "flex", gap: 8, alignItems: "center" }}><Battery soc={soc} /> Şarj durumu</span><span>%{soc}</span></div>
              <input type="range" min={5} max={100} value={soc} style={{ ["--p" as any]: `${((soc - 5) / 95) * 100}%` }}
                onChange={(e) => setSoc(Number(e.target.value))} aria-label="Şarj durumu" />
            </div>
          </div>
          <div className="wz-actions">
            <button className="btn-secondary" onClick={() => setStep(0)}>Geri</button>
            <button className="btn-primary" disabled={!vehicle} onClick={() => setStep(2)}>Devam</button></div>
        </section>
      )}

      {/* 3 · Hava durumu */}
      {step === 2 && (
        <section className="wz-card">
          <h1>Hava durumu</h1>
          <p className="wz-lead">Hız, yuvarlanma direnci ve klima/ısıtma tüketimini etkiler.</p>
          <div className="choice-grid four">
            {weathers.map((w) => (
              <button key={w.id} className={`choice ${weather?.id === w.id ? "sel" : ""}`} onClick={() => setWeather(w)}>
                <span className="wicon"><WeatherIcon id={w.id} /></span>
                <b>{w.name}</b>
                <small>{w.id === "acik" ? "Referans koşul" : `Hız ×${fmt(w.speed, 2)} · +${fmt(w.aux_kw, 1)} kW`}</small>
              </button>
            ))}
          </div>
          <div className="wz-actions">
            <button className="btn-secondary" onClick={() => setStep(1)}>Geri</button>
            <button className="btn-primary" disabled={!weather} onClick={() => setStep(3)}>Tamam</button></div>
        </section>
      )}

      {/* 4 · Sürücü analizi (yüz okuma → CLS; sonuç açılır pencerede) */}
      {step === 3 && (
        <section className="wz-card wide">
              <h1>Sürücü analizi</h1>
              <p className="wz-lead">Kameraya önden bakın. 3 saniyelik yüz okumayla yorgunluk (F) ve olumsuz duygu (V) ölçülür.</p>
              <div className="analysis">
                <div>
                  {!manual ? (
                    <FaceCapture key={camKey} cognitive={C} onResult={(r) => { setFace(r); finishAnalysis(Math.round(r.fatigue!), Math.round(r.valence_negative!)); }}
                      onCameraError={() => setManual(true)} />
                  ) : (
                    <div className="group">
                      <SliderRow label="Yorgunluk (F)" value={F} onChange={setF} />
                      <SliderRow label="Olumsuz duygu (V)" value={V} onChange={setV} />
                    </div>
                  )}
                </div>
                <div>
                  <div className="group">
                    <SliderRow label="Zihinsel yük (C)" hint="kameradan ölçülemez" value={C} onChange={setC} />
                  </div>
                  <p className="note" style={{ margin: "10px 4px" }}>CLS = 0,40·F + 0,40·C + 0,20·V (Dn. 1)</p>
                  {manual ? (
                    <button className="btn-primary" onClick={() => finishAnalysis(F, V)}>CLS'yi hesapla</button>
                  ) : (
                    <button className="link-btn" onClick={() => setManual(true)}>Kamerasız devam et (değerleri elle gir)</button>
                  )}
                  <p className="note" style={{ margin: "14px 4px 0" }}>Deneysel modül: bildiride biyometrik kestirim kapsam dışıdır; değerler doğrulanmamıştır. Görüntüler kaydedilmez.</p>
                </div>
              </div>
              <div className="wz-actions"><button className="btn-secondary" onClick={() => setStep(2)}>Geri</button><span /></div>
        </section>
      )}
      {step === 3 && cls !== null && (
        <div className="sheet-backdrop">
          <div className="sheet result-sheet" role="dialog" aria-modal="true" aria-label="Analiz sonucu">
            <div className="cls-result">
              <div className="gauge" style={{ ["--p" as any]: `${cls}%` }}>
                <div><b>{fmt(cls, 0)}</b><span>CLS</span></div>
              </div>
              <h1 style={{ marginTop: 18 }}>{band.name}</h1>
              <p className="wz-lead">{STATE_MSG[band.name]}</p>
              <div className="fcv">
                <div><b>{fmt(F, 0)}</b><span>Yorgunluk</span></div>
                <div><b>{fmt(C, 0)}</b><span>Zihinsel yük</span></div>
                <div><b>{fmt(V, 0)}</b><span>Olumsuz duygu</span></div>
              </div>
              <div className="fcv small">
                <div><b>{band.w[0].toFixed(2)}</b><span>w<sub>e</sub> enerji</span></div>
                <div><b>{band.w[1].toFixed(2)}</b><span>w<sub>t</sub> süre</span></div>
                <div><b>{band.w[2].toFixed(2)}</b><span>w<sub>c</sub> konfor</span></div>
              </div>
              {face?.emotion_tr && <p className="note">Baskın duygu: {face.emotion_tr}</p>}
              <div className="wz-actions center">
                <button className="btn-secondary" onClick={() => { setCountdown(null); setCls(null); setFace(null); setCamKey((k) => k + 1); }}>Tekrar ölç</button>
                <button className="btn-primary" onClick={() => { setCountdown(null); setStep(4); }}>
                  Güzergâh seçimine geç{countdown !== null ? ` (${countdown})` : ""}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5 · Başlangıç / varış */}
      {step === 4 && (
        <section className="wz-card">
          <h1>Nereye gidiyoruz?</h1>
          <div className="summary-chips">
            <span>{driver?.name}</span><span>{vehicle?.name}</span><span>{weather?.name}</span>
            <span>CLS {fmt(cls ?? 0, 0)} · {band.name}</span><span>%{soc} şarj</span>
          </div>
          <div className="group">
            <div className="row">
              <span className="dot" style={{ background: "var(--text)" }} /><span className="label-sm">Başlangıç</span>
              <select value={origin} onChange={(e) => setOrigin(e.target.value)}>{locations.map((l) => <option key={l.name}>{l.name}</option>)}</select>
            </div>
            <div className="row">
              <span className="dot" style={{ background: "#ff3b30" }} /><span className="label-sm">Varış</span>
              <select value={dest} onChange={(e) => setDest(e.target.value)}>{locations.map((l) => <option key={l.name}>{l.name}</option>)}</select>
              <button className="swap-btn" title="Yer değiştir" onClick={() => { setOrigin(dest); setDest(origin); }}>⇅</button>
            </div>
          </div>
          <div className="wz-actions">
            <button className="btn-secondary" onClick={() => setStep(3)}>Geri</button>
            <button className="btn-primary" onClick={computeRoutes} disabled={loading}>
              {loading ? <><span className="spinner" /> Rotalar hesaplanıyor…</> : "Rotaları göster"}</button>
          </div>
        </section>
      )}

      {/* 6 · Üç rota + canlı harita */}
      {step === 5 && plan && (
        <section className="results">
          <div className="results-head">
            <div>
              <h1>{origin} → {dest}</h1>
              <p className="wz-lead">{driver?.name} · {vehicle?.name} · {weather?.name} · CLS {fmt(plan.cls, 0)} ({plan.state})</p>
            </div>
            <button className="btn-secondary" onClick={newTrip}>Yeni yolculuk</button>
          </div>
          <div className="options">
            {CATEGORIES.map((c) => {
              const r = plan.options[c], m = r.metrics, on = active === c;
              return (
                <button key={c} className={`opt ${on ? "sel" : ""}`} style={{ ["--c" as any]: COLORS[c] }} onClick={() => setActive(c)}>
                  <div className="opt-top">
                    <span className="dot" style={{ background: COLORS[c], width: 12, height: 12 }} />
                    <b>{c}</b>
                    {plan.recommended === c && <span className="badge ai">★ Önerilen</span>}
                    {on && <span className="check">✓</span>}
                  </div>
                  <small>{SUBTITLE[c]}</small>
                  <div className="opt-time"><b>{fmt(m.time_min, 0)}</b> dk</div>
                  <div className="opt-stats">
                    <span><b>{fmt(m.distance_km, 1)}</b> km</span>
                    <span><b>{fmt(m.energy_kwh, 2)}</b> kWh</span>
                    <span><b>{fmt(m.comfort, 0)}</b> konfor</span>
                  </div>
                  <div className="opt-foot">{m.n_intersection} kavşak · varışta %{fmt(r.soc_final, 0)} şarj</div>
                  {r.charging && <div className="opt-foot" style={{ color: "var(--green)" }}>⚡︎ Şarj durağı · {fmt(r.charging.charge_min, 0)} dk</div>}
                </button>
              );
            })}
          </div>
          <div className="map-wrap">
            <RouteMap options={plan.options} active={active} recommended={plan.recommended} onSelect={setActive}
              dark={dark} origin={loc(origin)} destination={loc(dest)} bottomPad={40} />
          </div>
          <div className="rate-row">
            <span>{active} rotasını puanla</span>
            <div className="stars">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} className={n <= rated ? "on" : ""} onClick={() => rate(n)} aria-label={`${n} yıldız`}>★</button>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
