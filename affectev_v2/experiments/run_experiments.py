"""
Bölüm 4 deneyleri: 50 rastgele şehir içi başlangıç–varış senaryosu × 10 tohum.

Her (senaryo, tohum) için:
  * tohuma ait sentetik trafik gerçekleşmesi oluşturulur (make_traffic(seed)),
  * Dijkstra (mesafe) ve A* (süre) rotaları hesaplanır,
  * D-NSGA-II bir kez çalıştırılır (100 birey / 50 nesil, p_c=0,8, p_m=0,1),
  * cepheden üç seçenek (Verimlilik, Dengeli, Konfor) çıkarılır; NSGA-II (CLS yok, eşit
    ağırlık) ve AffectEV'in 5 CLS düzeyi (15, 30, 50, 65, 85) için etkinleşen seçenek alınır
    (Bölüm 3, nsga2.activate),
  * tüm rotalara aynı SoC/şarj kontrolü uygulanır (Dn. 4–5).

Çıktılar (results/):
  raw_runs.csv        — her satır bir (senaryo, tohum, yöntem, CLS) sonucu
  scenarios.json      — 50 senaryonun başlangıç/varış düğümleri ve başlangıç SoC'si
  trip_options.json   — Q-Learning deneyi için her (senaryo, tohum) Pareto kategorileri

Kullanım:  python experiments/run_experiments.py [--workers 2] [--scenarios 50] [--seeds 10]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from affectev.config import CLS_LEVELS, EXP, FIXED_WEIGHTS  # noqa: E402
from affectev.models import cls_weights, make_traffic  # noqa: E402
from affectev.network import haversine_m, load_network  # noqa: E402
from affectev.nsga2 import DNSGA2, activate, categorize  # noqa: E402
from affectev.planner import apply_soc  # noqa: E402
from affectev.routing import astar_time, dijkstra_distance  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
FIELDS = ["scenario", "seed", "method", "cls", "category", "distance_km", "time_min", "energy_kwh",
          "comfort", "n_intersection", "n_stop", "traffic_density", "soc_initial", "soc_final",
          "charging_stop", "charge_min", "front_size"]


def make_scenarios(net, n: int, master_seed: int):
    rng = np.random.default_rng(master_seed)
    out = []
    while len(out) < n:
        s, t = rng.integers(net.n_nodes, size=2)
        d = haversine_m(net.node_lat[s], net.node_lon[s], net.node_lat[t], net.node_lon[t]) / 1000
        if EXP.min_od_km <= d <= EXP.max_od_km:
            out.append({"id": len(out) + 1, "origin": int(s), "destination": int(t),
                        "origin_latlon": [float(net.node_lat[s]), float(net.node_lon[s])],
                        "destination_latlon": [float(net.node_lat[t]), float(net.node_lon[t])],
                        "crow_km": round(float(d), 2),
                        "soc_initial": round(float(rng.uniform(*EXP.soc_initial_range)), 1)})
    return out


_NET = None
_TR = {}


def _row(sc, seed, method, cls, cat, pr, front_size):
    m = pr.metrics
    return {"scenario": sc["id"], "seed": seed, "method": method, "cls": cls, "category": cat or "",
            "distance_km": m.distance_km, "time_min": m.time_min, "energy_kwh": m.energy_kwh,
            "comfort": m.comfort, "n_intersection": m.n_intersection, "n_stop": m.n_stop,
            "traffic_density": m.traffic_density, "soc_initial": pr.soc_initial, "soc_final": pr.soc_final,
            "charging_stop": int(pr.charging is not None),
            "charge_min": pr.charging.charge_min if pr.charging else 0.0, "front_size": front_size}


def run_one(args):
    sc, seed = args
    global _NET
    if _NET is None:
        _NET = load_network()
    net = _NET
    if seed not in _TR:
        _TR[seed] = make_traffic(net, seed)
    tr = _TR[seed]
    s, t, soc0 = sc["origin"], sc["destination"], sc["soc_initial"]
    rng = np.random.default_rng([EXP.master_seed, sc["id"], seed])
    opt = DNSGA2(net, tr, rng)
    res = opt.run(s, t)
    front = res.front
    cats = categorize(front)
    rows = []
    rows.append(_row(sc, seed, "Dijkstra", "", "", apply_soc(net, tr, opt, "Dijkstra", dijkstra_distance(net, s, t), soc0, (1, 0, 0)), len(front)))
    rows.append(_row(sc, seed, "A*", "", "", apply_soc(net, tr, opt, "A*", astar_time(net, tr, s, t), soc0, (0, 1, 0)), len(front)))
    fc, fi = activate(front, FIXED_WEIGHTS, cats)
    rows.append(_row(sc, seed, "NSGA-II", "", fc, apply_soc(net, tr, opt, "NSGA-II", list(front[fi].path), soc0, FIXED_WEIGHTS), len(front)))
    for cls, _ in CLS_LEVELS:
        w = cls_weights(cls)
        c, i = activate(front, w, cats)
        rows.append(_row(sc, seed, "AffectEV", cls, c, apply_soc(net, tr, opt, "AffectEV", list(front[i].path), soc0, w), len(front)))
    trip = {"scenario": sc["id"], "seed": seed,
            "traffic_d100": front[cats["Dengeli"]].metrics.traffic_density}
    for key, cat in (("Konfor", "Konfor"), ("Dengeli", "Dengeli"), ("Verimlilik", "Verimlilik")):
        mm = front[cats[cat]].metrics
        trip[key] = {"energy": mm.energy_kwh, "time": mm.time_min, "comfort": mm.comfort}
    return rows, trip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--scenarios", type=int, default=EXP.n_scenarios)
    ap.add_argument("--seeds", type=int, default=EXP.n_seeds)
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)
    net = load_network()
    scenarios = make_scenarios(net, a.scenarios, EXP.master_seed)
    with open(os.path.join(RESULTS, "scenarios.json"), "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=1)
    jobs = [(sc, seed) for seed in range(a.seeds) for sc in scenarios]
    t0 = time.time()
    all_rows, trips = [], []
    with Pool(a.workers) as pool:
        for k, (rows, trip) in enumerate(pool.imap(run_one, jobs, chunksize=2), 1):
            all_rows.extend(rows)
            trips.append(trip)
            if k % 25 == 0 or k == len(jobs):
                el = time.time() - t0
                print(f"  {k}/{len(jobs)} çalıştırma  ({el:.0f} sn, kalan ~{el / k * (len(jobs) - k):.0f} sn)", flush=True)
    with open(os.path.join(RESULTS, "raw_runs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    with open(os.path.join(RESULTS, "trip_options.json"), "w", encoding="utf-8") as f:
        json.dump(trips, f)
    print(f"Tamamlandı: {len(jobs)} çalıştırma, {len(all_rows)} satır, {time.time() - t0:.0f} sn")


if __name__ == "__main__":
    main()
