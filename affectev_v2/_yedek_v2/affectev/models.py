"""
Bildiri Bölüm 2: Bilişsel yük (Dn. 1), konfor (Dn. 2), kinetik enerji (Dn. 3, 3a–3d),
SoC ve şarj dinamikleri (Dn. 4, 5) ile sentetik trafik modeli.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

import dataclasses

from .config import CLSP, CLS_WEIGHT_TABLE, COMFORT, TRAFFIC, VEHICLE, WEATHER, VehicleParams, WeatherParams
from .network import RoadNetwork, _project


# ─────────────────────────────────────────────────────────────────────────────
# Denklem (1): CLS = λf·F + λc·C + λv·V
# ─────────────────────────────────────────────────────────────────────────────
def cognitive_load_score(F: float, C: float, V: float) -> float:
    """F: yorgunluk, C: bilişsel yük, V: olumsuz duygusal değerlik (hepsi 0–100)."""
    cls = CLSP.lambda_f * F + CLSP.lambda_c * C + CLSP.lambda_v * V
    return float(np.clip(cls, 0.0, 100.0))


def cls_weights(cls: float) -> Tuple[float, float, float]:
    """Tablo 3: CLS düzeyine göre (w_e, w_t, w_c)."""
    for upper, w, _ in CLS_WEIGHT_TABLE:
        if cls <= upper:
            return w
    return CLS_WEIGHT_TABLE[-1][1]


def cls_state_name(cls: float) -> str:
    for upper, _, name in CLS_WEIGHT_TABLE:
        if cls <= upper:
            return name
    return CLS_WEIGHT_TABLE[-1][2]


# ─────────────────────────────────────────────────────────────────────────────
# Sentetik trafik (her tohum için farklı bir gerçekleşme)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TrafficState:
    seed: int
    density: np.ndarray       # D_e ∈ [0, 1]
    speed_kmh: np.ndarray     # v_e
    time_s: np.ndarray        # kenar seyahat süresi (s), sinyal beklemesi dahil
    energy_kwh: np.ndarray    # Dn. 3 kenar enerjisi
    n_accel: np.ndarray       # kenar üzerindeki ivmelenme (kalkış) olay sayısı
    veh: VehicleParams = VEHICLE          # hava etkileri uygulanmış araç parametreleri


def effective_vehicle(veh: VehicleParams, weather: Optional[WeatherParams]) -> VehicleParams:
    if weather is None:
        return veh
    return dataclasses.replace(veh, Cr=veh.Cr * weather.cr, P_aux_kw=veh.P_aux_kw + weather.aux_kw, rho=weather.rho)


def make_traffic(net: RoadNetwork, seed: int, veh: VehicleParams = VEHICLE,
                 weather: Optional[WeatherParams] = None) -> TrafficState:
    rng = np.random.default_rng(seed)
    T = TRAFFIC
    xy = net.edge_mid_xy
    from .network import ROAD_CLASSES
    base = np.array([T.base_density[ROAD_CLASSES[c]] for c in net.road_class])
    cxy = _project(np.array([T.center_latlon[0]]), np.array([T.center_latlon[1]]))[0]
    dc = np.linalg.norm(xy - cxy, axis=1) / 1000.0
    D = base + T.center_amp * np.exp(-(dc ** 2) / (2 * T.center_sigma_km ** 2))
    # Tohuma bağlı trafik sıcak noktaları
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    for _ in range(T.hotspots):
        p = rng.uniform(lo, hi)
        s = rng.uniform(*T.hotspot_sigma_km)
        amp = rng.uniform(-0.5, 1.0) * T.hotspot_amp
        dk = np.linalg.norm(xy - p, axis=1) / 1000.0
        D = D + amp * np.exp(-(dk ** 2) / (2 * s ** 2))
    D = D + rng.normal(0.0, T.noise_sd, size=D.shape)
    D = np.clip(D, 0.02, 0.95)

    wf = weather.speed if weather is not None else 1.0
    v = np.maximum(T.min_speed_kmh, wf * net.vfree_kmh * (1.0 - T.speed_drop * D))
    v_ms = v / 3.6
    wait = net.n_signal * (T.signal_wait_s[0] + T.signal_wait_s[1] * D)
    t = net.length_m / v_ms + wait
    p_stop = T.stop_prob[0] + T.stop_prob[1] * D
    n_acc = net.n_signal * p_stop + (net.length_m / 1000.0) * T.stop_go_per_km * D ** 2
    veh_eff = effective_vehicle(veh, weather)
    E = segment_energy_kwh(net.length_m, v_ms, n_acc, veh_eff)
    return TrafficState(seed, D, v, t, E, n_acc, veh_eff)


# ─────────────────────────────────────────────────────────────────────────────
# Denklem (3): E_route = Σ (E_drag + E_roll + E_accel + E_aux)
# ─────────────────────────────────────────────────────────────────────────────
def energy_components_j(d_m, v_ms, n_accel, alpha_rad=0.0, veh: VehicleParams = VEHICLE):
    """Segment başına enerji bileşenleri (Joule).

    (3a) E_drag  = ½·ρ·Cd·A·v²·d
    (3b) E_roll  = Cr·m·g·cos(α)·d
    (3c) E_accel = m·a·d ; a·d = Σ ½·v² (segmentteki her kalkış için 0→v ivmelenmesi)
    (3d) E_aux   = P_aux·d / v
    α: OSM verisinde yükseklik bulunmadığından 0 alınır (cos α = 1).
    """
    d_m = np.asarray(d_m, dtype=float)
    v_ms = np.asarray(v_ms, dtype=float)
    e_drag = 0.5 * veh.rho * veh.Cd * veh.A * v_ms ** 2 * d_m
    e_roll = veh.Cr * veh.m * veh.g * np.cos(alpha_rad) * d_m
    a_times_d = np.asarray(n_accel, dtype=float) * 0.5 * v_ms ** 2
    e_accel = veh.m * a_times_d
    e_aux = veh.P_aux_kw * 1000.0 * d_m / v_ms
    return e_drag, e_roll, e_accel, e_aux


def segment_energy_kwh(d_m, v_ms, n_accel, veh: VehicleParams = VEHICLE) -> np.ndarray:
    return sum(energy_components_j(d_m, v_ms, n_accel, veh=veh)) / 3.6e6


# ─────────────────────────────────────────────────────────────────────────────
# Rota metrikleri ve Denklem (2): konfor
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RouteMetrics:
    distance_km: float
    time_min: float
    energy_kwh: float
    comfort: float
    n_intersection: int
    n_stop: int
    traffic_density: float    # D_traffic (0–100)

    def as_dict(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def comfort_score(n_intersection: float, n_stop: float, d_traffic_100: float) -> float:
    """Dn. (2): Comfort = 100 − (w_int·N_int + w_stop·N_stop + w_traffic·D_traffic).
    D_traffic: rota boyunca uzunluk ağırlıklı ortalama trafik yoğunluğu, 0–100'e normalize."""
    c = 100.0 - (COMFORT.w_intersection * n_intersection
                 + COMFORT.w_stop * n_stop
                 + COMFORT.w_traffic * d_traffic_100)
    return float(np.clip(c, 0.0, 100.0))


def route_metrics(net: RoadNetwork, tr: TrafficState, edges: np.ndarray) -> RouteMetrics:
    L = net.length_m[edges]
    n_int = int(net.n_signal[edges].sum())
    n_st = int(net.n_stop[edges].sum())
    d100 = float(100.0 * (tr.density[edges] * L).sum() / max(L.sum(), 1.0))
    return RouteMetrics(
        distance_km=float(L.sum() / 1000.0),
        time_min=float(tr.time_s[edges].sum() / 60.0),
        energy_kwh=float(tr.energy_kwh[edges].sum()),
        comfort=comfort_score(n_int, n_st, d100),
        n_intersection=n_int,
        n_stop=n_st,
        traffic_density=d100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Denklem (4) ve (5): SoC ve şarj
# ─────────────────────────────────────────────────────────────────────────────
def soc_final(soc_initial: float, energies_kwh: List[float], delta_soc_stops: List[float] = (),
              veh: VehicleParams = VEHICLE) -> float:
    """Dn. (4): SoC_final = SoC_initial − ΣE_j / C_batt + Σ ΔSoC_c   (yüzde)."""
    return soc_initial - 100.0 * sum(energies_kwh) / veh.C_batt_kwh + sum(delta_soc_stops)


def charge_time_min(soc_current: float, soc_target: float = VEHICLE.soc_target,
                    veh: VehicleParams = VEHICLE) -> float:
    """Dn. (5): Δt_charge = (SoC_target − SoC_current)·C_batt / P_charge."""
    return max(0.0, (soc_target - soc_current) / 100.0) * veh.C_batt_kwh / veh.P_charge_kw * 60.0
