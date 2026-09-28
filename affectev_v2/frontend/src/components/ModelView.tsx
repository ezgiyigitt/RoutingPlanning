import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function ModelView() {
  const [cfg, setCfg] = useState<any>(null);
  const [net, setNet] = useState<any>(null);
  useEffect(() => { api.config().then(setCfg); api.health().then(setNet).catch(() => {}); }, []);
  const v = cfg?.vehicle, n = cfg?.nsga, q = cfg?.qlearning, l = cfg?.cls_lambdas, c = cfg?.comfort_weights;
  return (
    <div className="page">
      <h1>Model</h1>
      <p className="lead">Kodda uygulanan denklemler ve Tablo 1 parametreleri. Değerler doğrudan <code>affectev/config.py</code> dosyasından okunur.</p>
      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Bilişsel yük ve konfor</h3>
          <div className="eq">CLS = λf·F + λc·C + λv·V   (1)</div>
          <div className="eq">Comfort = 100 − (w_int·N_int + w_stop·N_stop + w_traffic·D_traffic)   (2)</div>
          <h3>Enerji ve SoC</h3>
          <div className="eq">E_route = Σ (E_drag + E_roll + E_accel + E_aux)   (3)</div>
          <div className="eq">E_drag = ½ρC_dAv²d · E_roll = C_r·m·g·cos(α)·d<br />E_accel = m·a·d · E_aux = P_aux·d/v   (3a–3d)</div>
          <div className="eq">SoC_final = SoC_initial − ΣE_j / C_batt + ΣΔSoC_c   (4)</div>
          <div className="eq">Δt_charge = (SoC_target − SoC_current)·C_batt / P_charge   (5)</div>
          <h3>D-NSGA-II ve Q-Learning</h3>
          <div className="eq">s = (CLS, SoC_level, Traffic_level, Route_type)   (6)</div>
          <div className="eq">Q(s,a) ← Q(s,a) + α[r + γ·max Q(s′,a′) − Q(s,a)]   (7)</div>
          <div className="eq">r = θ1·feedback + θ2·comfort − θ3·delay   (8)</div>
          <div className="eq">a = argmax Q(s,a′) (1−ε) · rastgele (ε)   (9)</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Tablo 1 · Parametreler</h3>
          {cfg && (
            <table className="tbl">
              <tbody>
                <tr><td>Araç</td><td className="num">{v.name}</td></tr>
                <tr><td>C<sub>d</sub> · m · A · C<sub>r</sub></td><td className="num">{v.Cd} · {v.m} kg · {v.A} m² · {v.Cr}</td></tr>
                <tr><td>SoC<sub>min</sub></td><td className="num">%{v.soc_min}</td></tr>
                <tr><td>NSGA-II popülasyon / nesil</td><td className="num">{n.population} / {n.generations}</td></tr>
                <tr><td>Çaprazlama / mutasyon</td><td className="num">{n.crossover_rate} / {n.mutation_rate}</td></tr>
                <tr><td>Q-Learning α · γ · ε</td><td className="num">{q.alpha} · {q.gamma} · {q.epsilon}</td></tr>
                <tr><td>λf · λc · λv</td><td className="num">{l.lambda_f} · {l.lambda_c} · {l.lambda_v}</td></tr>
                <tr><td>w_int · w_stop · w_traffic</td><td className="num">{c.w_intersection} · {c.w_stop} · {c.w_traffic}</td></tr>
                <tr><td>θ1 · θ2 · θ3</td><td className="num">{q.theta1} · {q.theta2} · {q.theta3}</td></tr>
              </tbody>
            </table>
          )}
          <h3>Tablo 1 dışı (bildiriye eklenmeli)</h3>
          {cfg && (
            <table className="tbl"><tbody>
              <tr><td>ρ · g</td><td className="num">{v.rho} kg/m³ · {v.g} m/s²</td></tr>
              <tr><td>P<sub>aux</sub></td><td className="num">{v.P_aux_kw} kW</td></tr>
              <tr><td>C<sub>batt</sub> · P<sub>charge</sub> · SoC<sub>target</sub></td><td className="num">{v.C_batt_kwh} kWh · {v.P_charge_kw} kW · %{v.soc_target}</td></tr>
            </tbody></table>
          )}
          {net && <p className="muted" style={{ fontSize: 12.5 }}>Yol ağı: OpenStreetMap ({net.osm_timestamp.slice(0, 10)}), {net.nodes.toLocaleString("tr-TR")} düğüm · {net.edges.toLocaleString("tr-TR")} yönlü kenar.</p>}
        </div>
      </div>
    </div>
  );
}
