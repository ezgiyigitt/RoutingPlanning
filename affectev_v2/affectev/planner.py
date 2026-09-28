"""
AffectEV uçtan uca planlayıcı: CLS → ağırlıklar → D-NSGA-II Pareto cephesi →
CLS'ye göre rota seçimi → SoC kontrolü (Dn. 4) → gerekirse şarj durağı ekleme (Dn. 5).
Aynı SoC/şarj işlemi karşılaştırma yöntemlerine (Dijkstra, A*, NSGA-II sabit) de uygulanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import FIXED_WEIGHTS, VEHICLE
from .models import (RouteMetrics, TrafficState, charge_time_min, cls_weights, make_traffic,
                     route_metrics, soc_final)
from .network import RoadNetwork, load_network
from .nsga2 import CATEGORIES, DNSGA2, NSGAResult, activate, categorize, weighted_choice
from .routing import astar_time, dijkstra_distance, shortest_path


@dataclass
class ChargingPlan:
    station: dict
    soc_arrival: float
    delta_soc: float
    charge_min: float
    legs: Tuple[List[int], List[int]]


@dataclass
class PlannedRoute:
    method: str
    path: List[int]
    metrics: RouteMetrics
    soc_initial: float
    soc_final: float
    charging: Optional[ChargingPlan] = None
    category: Optional[str] = None

    @property
    def total_time_min(self) -> float:
        return self.metrics.time_min + (self.charging.charge_min if self.charging else 0.0)


def _scalar_weights(opt: DNSGA2, w: Tuple[float, float, float]) -> np.ndarray:
    return np.asarray(w) @ opt._components + 1e-9


def apply_soc(net: RoadNetwork, tr: TrafficState, opt: DNSGA2, method: str, path: List[int],
              soc0: float, weights: Tuple[float, float, float], category: Optional[str] = None
              ) -> PlannedRoute:
    """Dn. (4): SoC_final < SoC_min ise en uygun şarj istasyonunu rotaya ekler."""
    veh = tr.veh
    m = route_metrics(net, tr, net.path_edges(path))
    sf = soc_final(soc0, [m.energy_kwh], veh=veh)
    if sf >= veh.soc_min or not net.charging:
        return PlannedRoute(method, path, m, soc0, sf, None, category)
    s, t = path[0], path[-1]
    W = _scalar_weights(opt, weights)
    best = None
    for st in net.charging:
        c = net.nearest_node(st["lat"], st["lon"])
        p1 = shortest_path(net, W, s, c)
        p2 = shortest_path(net, W, c, t)
        if p1 is None or p2 is None:
            continue
        m1 = route_metrics(net, tr, net.path_edges(p1)) if len(p1) > 1 else None
        m2 = route_metrics(net, tr, net.path_edges(p2)) if len(p2) > 1 else None
        e1 = m1.energy_kwh if m1 else 0.0
        soc_arr = soc_final(soc0, [e1], veh=veh)
        if soc_arr <= 0:
            continue
        dsoc = max(0.0, veh.soc_target - soc_arr)
        tch = charge_time_min(soc_arr, veh.soc_target, veh)
        total = (m1.time_min if m1 else 0) + (m2.time_min if m2 else 0) + tch
        feasible = soc_arr >= veh.soc_min
        key = (not feasible, total)
        if best is None or key < best[0]:
            best = (key, st, p1, p2, soc_arr, dsoc, tch)
    if best is None:
        return PlannedRoute(method, path, m, soc0, sf, None, category)
    _, st, p1, p2, soc_arr, dsoc, tch = best
    full = p1 + p2[1:]
    mf = route_metrics(net, tr, net.path_edges(full))
    sf2 = soc_final(soc0, [mf.energy_kwh], [dsoc], veh=veh)
    return PlannedRoute(method, full, mf, soc0, sf2, ChargingPlan(st, soc_arr, dsoc, tch, (p1, p2)), category)


@dataclass
class PlanResult:
    origin: int
    destination: int
    cls: float
    weights: Tuple[float, float, float]
    traffic_seed: int
    nsga: NSGAResult
    categories: Dict[str, int]
    selected_index: int
    routes: Dict[str, PlannedRoute] = field(default_factory=dict)


def plan(net: RoadNetwork, s: int, t: int, cls: float, soc0: float, seed: int,
         tr: Optional[TrafficState] = None, nsga_result: Optional[NSGAResult] = None,
         opt: Optional[DNSGA2] = None) -> PlanResult:
    tr = tr or make_traffic(net, seed)
    if nsga_result is None or opt is None:
        opt = DNSGA2(net, tr, np.random.default_rng(seed))
        nsga_result = opt.run(s, t)
    w = cls_weights(cls)
    front = nsga_result.front
    cats = categorize(front)
    cat_of_sel, sel = activate(front, w, cats)          # Bölüm 3: CLS'ye göre etkinleşen seçenek
    routes: Dict[str, PlannedRoute] = {}
    routes["Dijkstra"] = apply_soc(net, tr, opt, "Dijkstra (mesafe)", dijkstra_distance(net, s, t), soc0, (1, 0, 0))
    routes["A*"] = apply_soc(net, tr, opt, "A* (süre)", astar_time(net, tr, s, t), soc0, (0, 1, 0))
    _, fixed = activate(front, FIXED_WEIGHTS, cats)     # ablasyon: sabit eşit ağırlık
    routes["NSGA-II"] = apply_soc(net, tr, opt, "NSGA-II (CLS yok)", list(front[fixed].path), soc0, FIXED_WEIGHTS)
    routes["AffectEV"] = apply_soc(net, tr, opt, "AffectEV (CLS uyarlamalı)", list(front[sel].path), soc0, w,
                                   cat_of_sel)
    for k in CATEGORIES:
        routes[k] = apply_soc(net, tr, opt, k, list(front[cats[k]].path), soc0, w, k)
    out = PlanResult(s, t, cls, w, seed, nsga_result, cats, sel, routes)
    out._opt = opt
    return out
