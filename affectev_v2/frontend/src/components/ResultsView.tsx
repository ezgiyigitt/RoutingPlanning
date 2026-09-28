import { useEffect, useState } from "react";
import { api, fmt } from "../lib/api";

const LABEL: Record<string, string> = {
  Dijkstra: "Dijkstra (mesafe)", "A*": "A* (süre)", "NSGA-II": "NSGA-II (CLS yok)", AffectEV: "AffectEV (CLS uyarlamalı)",
};
const STATE: Record<string, string> = { "15": "Çok Enerjik", "30": "Enerjik", "50": "Nötr", "65": "Yorgun", "85": "Stresli" };
const W: Record<string, string> = { "15": "0,50 / 0,40 / 0,10", "30": "0,40 / 0,35 / 0,25", "50": "0,28 / 0,22 / 0,50", "65": "0,13 / 0,10 / 0,77", "85": "0,08 / 0,07 / 0,85" };

export default function ResultsView() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.experiments().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="page"><p className="muted">Sonuçlar yüklenemedi: {err}</p></div>;
  if (!d) return <div className="page"><p className="muted">Yükleniyor…</p></div>;
  if (!d.available) return (
    <div className="page">
      <h1>Deney Sonuçları</h1>
      <p className="lead">Henüz deney sonucu yok. Proje klasöründe <code>python experiments/run_all.py</code> komutunu çalıştırın.</p>
    </div>
  );
  const s = d.summary, cs = d.case_study, q = d.qlearning_summary;
  const t2 = s.table2;
  const a = t2["A*"], ae = t2["AffectEV"];
  const hi = s.table3["85"];
  return (
    <div className="page">
      <h1>Deney Sonuçları</h1>
      <p className="lead">{s.n_scenarios} rastgele şehir içi senaryo × {s.n_seeds} tohum. Tüm değerler <code>experiments/</code> altındaki
        scriptlerin ürettiği <code>results/</code> dosyalarından okunur.</p>

      <div className="grid-3">
        <div className="card kpi"><b>{fmt(hi.comfort)}</b><span>Konfor · AffectEV, CLS=85 (A*: {fmt(a.comfort_mean)})</span></div>
        <div className="card kpi"><b>{fmt(ae.comfort_mean)}</b><span>Ortalama konfor · AffectEV (tüm CLS)</span></div>
        {q && <div className="card kpi"><b>{fmt(q.q_last200_mean, 2)}</b><span>Q-Learning son 200 bölüm ödülü (rastgele: {fmt(q.random_mean, 2)})</span></div>}
      </div>

      <h2>Tablo 2 · Performans karşılaştırması (ablasyon)</h2>
      <div className="card">
        <table className="tbl">
          <thead><tr><th>Yöntem</th><th className="num">Süre (dk)</th><th className="num">Enerji (kWh)</th><th className="num">Konfor (0–100)</th><th className="num">Ort. kavşak</th><th className="num">Mesafe (km)</th></tr></thead>
          <tbody>
            {Object.keys(LABEL).map((k) => {
              const r = t2[k];
              return (
                <tr key={k}>
                  <td>{LABEL[k]}</td>
                  <td className="num">{fmt(r.time_mean)} ± {fmt(r.time_sd)}</td>
                  <td className="num">{fmt(r.energy_mean, 2)} ± {fmt(r.energy_sd, 2)}</td>
                  <td className="num">{fmt(r.comfort_mean)} ± {fmt(r.comfort_sd)}</td>
                  <td className="num">{fmt(r.intersection_mean)}</td>
                  <td className="num">{fmt(r.distance_mean)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h2>Tablo 3 · CLS düzeyine göre adaptasyon</h2>
      <div className="card">
        <table className="tbl">
          <thead><tr><th>Sürücü durumu</th><th className="num">CLS</th><th>w<sub>e</sub> / w<sub>t</sub> / w<sub>c</sub></th><th className="num">Konfor</th><th className="num">Enerji (kWh)</th><th className="num">Süre (dk)</th><th className="num">Mesafe (km)</th><th>Rejim</th></tr></thead>
          <tbody>
            {Object.entries(s.table3).map(([k, r]: any) => (
              <tr key={k}>
                <td>{STATE[k]}</td><td className="num">{k}</td><td>{W[k]}</td>
                <td className="num">{fmt(r.comfort)}</td><td className="num">{fmt(r.energy, 2)}</td><td className="num">{fmt(r.time)}</td>
                <td className="num">{fmt(r.distance)}</td>
                <td><b>{r.regime}</b> <span className="muted">(%{fmt(100 * r.regime_share, 0)})</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {cs && (<>
        <h2>Tablo 4 · Keçiören → Bilkent (SoC %{cs.soc_initial})</h2>
        <div className="card">
          <table className="tbl">
            <thead><tr><th>Algoritma / Durum</th><th className="num">Mesafe (km)</th><th className="num">Süre (dk)</th><th className="num">Enerji (kWh)</th><th className="num">Nihai SoC (%)</th><th className="num">Konfor</th></tr></thead>
            <tbody>
              {Object.entries(cs.routes).map(([k, r]: any) => (
                <tr key={k}><td>{k}</td><td className="num">{fmt(r.distance_km)}</td><td className="num">{fmt(r.time_min)}</td>
                  <td className="num">{fmt(r.energy_kwh, 2)}</td><td className="num">{fmt(r.soc_final)}</td><td className="num">{fmt(r.comfort)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </>)}

      <h2>Şekiller</h2>
      <div className="grid-3">
        {[["sekil1_pareto.png", "Şekil 1: Enerji–süre düzleminde Pareto-optimal çözüm cephesi (Keçiören → Bilkent)"],
          ["sekil2_qlearning.png", "Şekil 2: Q-Learning bölüm başına ödül eğrisi (1000 bölüm, 10 tohum, ±1 std)"],
          ["sekil3_harita.png", "Şekil 3: Düşük ve yüksek CLS rotalarının karşılaştırması (OSM)"]]
          .filter(([f]) => d.figures.includes(f)).map(([f, cap]) => (
            <div className="card" key={f}>
              <a href={`/results/${f}`} target="_blank" rel="noreferrer"><img className="fig" src={`/results/${f}`} alt={cap} /></a>
              <div className="fig-cap">{cap}</div>
            </div>
          ))}
      </div>
    </div>
  );
}
