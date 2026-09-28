"""
Tablo 2 (ablasyon, 50 senaryo × 10 tohum) ve Tablo 3 (CLS düzeyine göre adaptasyon)
results/raw_runs.csv dosyasından üretilir. Hiçbir sayı elle girilmez.

Çıktılar: results/tablo2.md, results/tablo3.md, results/summary.json
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from affectev.config import CLS_LEVELS  # noqa: E402
from affectev.models import cls_weights  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
REGIME_ABBR = {"Verimlilik": "V", "Dengeli": "D", "Konfor": "K"}


def load_rows():
    with open(os.path.join(RESULTS, "raw_runs.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("distance_km", "time_min", "energy_kwh", "comfort", "n_intersection", "n_stop",
                  "traffic_density", "soc_initial", "soc_final", "charge_min"):
            r[k] = float(r[k])
        r["charging_stop"] = int(r["charging_stop"])
        r["cls"] = float(r["cls"]) if r["cls"] else None
    return rows


def ms(vals, nd=1):
    a = np.asarray(vals, dtype=float)
    return f"{a.mean():.{nd}f} ± {a.std(ddof=1):.{nd}f}"


def main():
    rows = load_rows()
    n_sc = len({r["scenario"] for r in rows})
    n_seed = len({r["seed"] for r in rows})
    by = defaultdict(list)
    for r in rows:
        by[r["method"]].append(r)

    summary = {"n_scenarios": n_sc, "n_seeds": n_seed, "table2": {}, "table3": {}}
    order = [("Dijkstra", "Dijkstra (mesafe)"), ("A*", "A* (süre)"),
             ("NSGA-II", "NSGA-II (CLS yok)"), ("AffectEV", "AffectEV (CLS uyarlamalı)")]
    lines = [f"Tablo 2: {n_sc} Şehir İçi Senaryosunda Performans Karşılaştırması (Ablasyon)", "",
             "| Yöntem | Seyahat Süresi (dk) | Enerji Tüketimi (kWh) | Konfor Skoru (0-100) | Ortalama Kavşak | Mesafe (km) | Şarj durağı |",
             "|---|---|---|---|---|---|---|"]
    for key, label in order:
        R = by[key]
        t = [r["time_min"] for r in R]
        e = [r["energy_kwh"] for r in R]
        c = [r["comfort"] for r in R]
        k = [r["n_intersection"] for r in R]
        d = [r["distance_km"] for r in R]
        ch = sum(r["charging_stop"] for r in R)
        lines.append(f"| {label} | {ms(t)} | {ms(e, 2)} | {ms(c)} | {np.mean(k):.1f} | {ms(d)} | {ch}/{len(R)} |")
        summary["table2"][key] = {"time_mean": float(np.mean(t)), "time_sd": float(np.std(t, ddof=1)),
                                  "energy_mean": float(np.mean(e)), "energy_sd": float(np.std(e, ddof=1)),
                                  "comfort_mean": float(np.mean(c)), "comfort_sd": float(np.std(c, ddof=1)),
                                  "intersection_mean": float(np.mean(k)), "distance_mean": float(np.mean(d)),
                                  "n": len(R), "charging_stops": ch}
    lines += ["",
              f"Not: Değerler {n_sc} senaryo × {n_seed} tohum üzerinden ortalama ± standart sapmadır. "
              f"AffectEV satırı beş CLS düzeyinin (15, 30, 50, 65, 85) tamamını kapsar "
              f"({len(by['AffectEV'])} çalıştırma). Ortalama Kavşak: rotadaki kavşak kümesi sayısı (N_intersection; tanım için affectev/network.py)."]
    with open(os.path.join(RESULTS, "tablo2.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---- Tablo 3 ----
    ref = {r_key: np.mean([r["comfort"] for r in by[r_key]]) for r_key in ("NSGA-II",)}
    l3 = ["Tablo 3: CLS Düzeyine Göre AffectEV Adaptasyon Performansı ve Rejimler", "",
          "| Sürücü Durumu | CLS | Ağırlıklar (w_e / w_t / w_c) | Konfor | Enerji (kWh) | Süre (dk) | Mesafe (km) | Kavşak | Rejim (dağılım) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for cls, name in CLS_LEVELS:
        R = [r for r in by["AffectEV"] if r["cls"] == cls]
        cats = Counter(r["category"] for r in R)          # etkinleşen seçenek (nsga2.activate)
        top, cnt = cats.most_common(1)[0]
        dist = ", ".join(f"{REGIME_ABBR[c]} %{100 * n / len(R):.0f}" for c, n in
                         sorted(cats.items(), key=lambda x: "VDK".index(REGIME_ABBR[x[0]])))
        w = cls_weights(cls)
        l3.append(f"| {name} | {cls:.0f} | {w[0]:.2f} / {w[1]:.2f} / {w[2]:.2f} | "
                  f"{np.mean([r['comfort'] for r in R]):.1f} | {np.mean([r['energy_kwh'] for r in R]):.2f} | "
                  f"{np.mean([r['time_min'] for r in R]):.1f} | {np.mean([r['distance_km'] for r in R]):.1f} | "
                  f"{np.mean([r['n_intersection'] for r in R]):.1f} | **{REGIME_ABBR[top]}** ({dist}) |")
        summary["table3"][str(int(cls))] = {
            "comfort": float(np.mean([r["comfort"] for r in R])),
            "energy": float(np.mean([r["energy_kwh"] for r in R])),
            "time": float(np.mean([r["time_min"] for r in R])),
            "distance": float(np.mean([r["distance_km"] for r in R])),
            "regime": REGIME_ABBR[top], "regime_share": cnt / len(R),
            "regime_dist": {REGIME_ABBR[c]: n / len(R) for c, n in cats.items()}}
    l3 += ["", "(V: Verimlilik, D: Dengeli, K: Konfor rejimi. Rejim, D-NSGA-II cephesindeki üç seçenekten "
           "CLS ağırlıklarıyla etkinleşendir (en sık görülen); parantez içi tüm çalıştırmalardaki dağılımdır.)"]
    with open(os.path.join(RESULTS, "tablo3.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(l3) + "\n")

    # Eşleştirilmiş karşılaştırma: yüksek CLS AffectEV vs A* (aynı senaryo, aynı tohum)
    key = lambda r: (r["scenario"], r["seed"])  # noqa: E731
    astar = {key(r): r for r in by["A*"]}
    hi = [r for r in by["AffectEV"] if r["cls"] == 85.0]
    dc = np.array([r["comfort"] - astar[key(r)]["comfort"] for r in hi])
    de = np.array([r["energy_kwh"] - astar[key(r)]["energy_kwh"] for r in hi])
    try:
        from scipy.stats import wilcoxon
        p = float(wilcoxon(dc).pvalue) if np.any(dc != 0) else 1.0
    except Exception:
        p = float("nan")
    summary["paired_cls85_vs_astar"] = {"comfort_diff_mean": float(dc.mean()), "energy_diff_mean": float(de.mean()),
                                        "wilcoxon_p_comfort": p, "n": len(dc)}
    with open(os.path.join(RESULTS, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n".join(lines))
    print()
    print("\n".join(l3))
    print(json.dumps(summary["paired_cls85_vs_astar"], indent=1))


if __name__ == "__main__":
    main()
