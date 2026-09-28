"""
Örnek vaka: Keçiören → Bilkent, başlangıç SoC %75 (Tablo 4, Şekil 3) ve Şekil 1 (Pareto cephesi).

Tablo 4: trafik tohumu 0, D-NSGA-II tek çalıştırma; düşük CLS = 15, yüksek CLS = 85. AffectEV
rotası, cepheden CLS'ye göre etkinleşen seçenektir (nsga2.activate). Sağlamlık için aynı vaka
10 trafik tohumunda da koşulur ve ortalaması case_study.json'a yazılır.

Şekil 1: bildiride senaryo adı verilmemiştir. Eski kodda (gorseller_hoca_stili.py) Şekil 1
Sincan → Ulus için çizildiğinden aynı senaryo kullanılır (tohum 0). Keçiören–Bilkent cephesi
case_study.json'da ayrıca raporlanır.

Çıktılar: results/tablo4.md, results/case_study.json,
          results/sekil1_pareto.png, results/sekil3_harita.png
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from affectev.config import CLS_LEVELS, EXP, LOCATIONS  # noqa: E402
from affectev.models import cls_weights, make_traffic  # noqa: E402
from affectev.network import load_network  # noqa: E402
from affectev.nsga2 import DNSGA2, activate, categorize, fast_non_dominated_sort  # noqa: E402
from affectev.planner import apply_soc  # noqa: E402
from affectev.routing import astar_time  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
ORIGIN, DEST, SOC0, SEED = "Keçiören", "Bilkent", 75.0, 0
FIG1_ORIGIN, FIG1_DEST = "Sincan", "Ulus"
CLS_LOW, CLS_HIGH = 15.0, 85.0
LOW, HIGH, ASTAR = f"AffectEV / Düşük CLS ({CLS_LOW:.0f})", f"AffectEV / Yüksek CLS ({CLS_HIGH:.0f})", "Geleneksel (A*)"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "savefig.dpi": 300})


def run_case(net, s, t, seed):
    tr = make_traffic(net, seed)
    opt = DNSGA2(net, tr, np.random.default_rng([EXP.master_seed, 0, seed]))
    res = opt.run(s, t, record_history=True)
    cats = categorize(res.front)
    c_lo, i_lo = activate(res.front, cls_weights(CLS_LOW), cats)
    c_hi, i_hi = activate(res.front, cls_weights(CLS_HIGH), cats)
    routes = {
        ASTAR: apply_soc(net, tr, opt, "A*", astar_time(net, tr, s, t), SOC0, (0, 1, 0)),
        LOW: apply_soc(net, tr, opt, "AffectEV", list(res.front[i_lo].path), SOC0, cls_weights(CLS_LOW), c_lo),
        HIGH: apply_soc(net, tr, opt, "AffectEV", list(res.front[i_hi].path), SOC0, cls_weights(CLS_HIGH), c_hi),
    }
    return tr, opt, res, cats, routes


def main():
    os.makedirs(RESULTS, exist_ok=True)
    net = load_network()
    s = net.nearest_node(*LOCATIONS[ORIGIN])
    t = net.nearest_node(*LOCATIONS[DEST])
    tr, opt, res, cats, routes = run_case(net, s, t, SEED)
    front = res.front
    same_lo_astar = routes[LOW].path == routes[ASTAR].path

    # ---------------- Tablo 4 ----------------
    L = [f"Tablo 4: Keçiören–Bilkent Senaryosu Rota Üretimi Karşılaştırması (başlangıç SoC %75, tohum {SEED})", "",
         "| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor (0-100) | Kavşak | Duruş | Seçenek |",
         "|---|---|---|---|---|---|---|---|---|"]
    out = {"origin": ORIGIN, "destination": DEST, "soc_initial": SOC0, "seed": SEED,
           "front_size": len(front), "evaluations": res.evaluations, "routes": {},
           "low_cls_equals_astar": same_lo_astar,
           "front": [{"energy": float(p.obj[0]), "time": float(p.obj[1]), "comfort": float(100 - p.obj[2]),
                      "distance": float(p.metrics.distance_km)} for p in front],
           "categories": {k: int(v) for k, v in cats.items()}}
    for name, pr in routes.items():
        m = pr.metrics
        L.append(f"| {name} | {m.distance_km:.1f} | {m.time_min:.1f} | {m.energy_kwh:.2f} | "
                 f"{pr.soc_final:.1f} | {m.comfort:.1f} | {m.n_intersection} | {m.n_stop:.1f} | {pr.category or '—'} |")
        out["routes"][name] = {**m.as_dict(), "soc_final": pr.soc_final, "category": pr.category,
                               "charging": pr.charging is not None}
    a, h = routes[ASTAR].metrics, routes[HIGH].metrics
    rel = {"comfort_pct": 100 * (h.comfort - a.comfort) / a.comfort,
           "energy_pct": 100 * (h.energy_kwh - a.energy_kwh) / a.energy_kwh,
           "distance_pct": 100 * (h.distance_km - a.distance_km) / a.distance_km,
           "time_pct": 100 * (h.time_min - a.time_min) / a.time_min}
    out["high_vs_astar_pct"] = rel
    L += ["", f"Yüksek CLS rotasının A*'a göre değişimi: konfor {rel['comfort_pct']:+.1f}%, "
              f"enerji {rel['energy_pct']:+.1f}%, mesafe {rel['distance_pct']:+.1f}%, süre {rel['time_pct']:+.1f}%.",
          f"Düşük CLS rotası A* ile aynı mı: {'evet' if same_lo_astar else 'hayır'}.",
          f"Cephe büyüklüğü: {len(front)} çözüm; etkinleşen seçenekler — düşük CLS: {routes[LOW].category}, "
          f"yüksek CLS: {routes[HIGH].category}."]

    # 10 tohum sağlamlık kontrolü
    agg = {k: [] for k in routes}
    for sd in range(10):
        _, _, _, _, r10 = run_case(net, s, t, sd)
        for k, pr in r10.items():
            agg[k].append([pr.metrics.distance_km, pr.metrics.time_min, pr.metrics.energy_kwh, pr.soc_final,
                           pr.metrics.comfort])
    out["mean_10_seeds"] = {k: dict(zip(("distance_km", "time_min", "energy_kwh", "soc_final", "comfort"),
                                        np.mean(v, axis=0).tolist())) for k, v in agg.items()}
    L += ["", "10 trafik tohumu ortalaması:", "",
          "| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor |", "|---|---|---|---|---|---|"]
    for k, v in out["mean_10_seeds"].items():
        L.append(f"| {k} | {v['distance_km']:.1f} | {v['time_min']:.1f} | {v['energy_kwh']:.2f} | "
                 f"{v['soc_final']:.1f} | {v['comfort']:.1f} |")
    with open(os.path.join(RESULTS, "tablo4.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(RESULTS, "case_study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n".join(L))

    # ---------------- Şekil 1: Pareto cephesi (Sincan → Ulus) ----------------
    s1 = net.nearest_node(*LOCATIONS[FIG1_ORIGIN])
    t1 = net.nearest_node(*LOCATIONS[FIG1_DEST])
    opt1 = DNSGA2(net, tr, np.random.default_rng([EXP.master_seed, 1, SEED]))
    res1 = opt1.run(s1, t1)
    fr1 = res1.front
    cats1 = categorize(fr1)
    act = {}
    for cls, _ in CLS_LEVELS:
        c, _i = activate(fr1, cls_weights(cls), cats1)
        act.setdefault(c, []).append(int(cls))
    allind = list(opt1._cache.values())
    F = np.array([p.obj for p in allind])
    fr0 = set(fast_non_dominated_sort(F)[0])
    dom = [i for i in range(len(allind)) if i not in fr0]
    FF = np.array([p.obj for p in fr1])
    fig, ax = plt.subplots(figsize=(8.5 / 2.54, 7.2 / 2.54))
    ax.scatter(F[dom, 0], F[dom, 1], marker="x", s=10, lw=0.5, c="0.65", label="Baskılanan çözümler", zorder=1)
    f2 = sorted(fast_non_dominated_sort(FF[:, :2])[0], key=lambda i: FF[i, 0])
    ax.plot(FF[f2, 0], FF[f2, 1], c="k", lw=0.9, zorder=2, label="Pareto cephesi")
    sc = ax.scatter(FF[:, 0], FF[:, 1], c=100 - FF[:, 2], cmap="Greys", s=14, edgecolors="k",
                    linewidths=0.4, zorder=3)
    labels = {"Verimlilik": "Verimlilik odaklı", "Dengeli": "Dengeli çözüm", "Konfor": "Konfor odaklı"}
    placed = {}
    for k, i in cats1.items():
        txt = labels[k] + (f"\n(CLS {', '.join(map(str, act[k]))})" if k in act else "")
        placed.setdefault(i, []).append(txt)
    slots = [(0.03, 0.55), (0.45, 0.10), (0.50, 0.45), (0.70, 0.66)]
    items = sorted(placed.items(), key=lambda kv: (FF[kv[0], 0], FF[kv[0], 1]))
    for n, (i, txts) in enumerate(items):
        ax.scatter(FF[i, 0], FF[i, 1], s=70, facecolors="none", edgecolors="k", linewidths=1.2, zorder=4)
        ax.annotate("\n".join(txts), xy=(FF[i, 0], FF[i, 1]), xycoords="data",
                    xytext=slots[n % len(slots)], textcoords="axes fraction", fontsize=6.3, ha="left", va="bottom",
                    arrowprops=dict(arrowstyle="-", lw=0.5, shrinkA=0, shrinkB=4),
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.3", lw=0.5), zorder=6)
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("Konfor skoru", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    # Eksenler: cephe + baskılanan çözümlerin %90'ı (uç aykırı değerler kırpılır)
    xq, yq = np.quantile(F[:, 0], 0.90), np.quantile(F[:, 1], 0.90)
    x0, y0 = F[:, 0].min(), F[:, 1].min()
    ax.set_xlim(x0 - 0.08 * (xq - x0), xq + 0.05 * (xq - x0))
    ax.set_ylim(y0 - 0.08 * (yq - y0), yq + 0.05 * (yq - y0))
    ax.set_xlabel("Enerji tüketimi (kWh)")
    ax.set_ylabel("Seyahat süresi (dk)")
    ax.legend(fontsize=6, loc="upper right", frameon=True)
    ax.grid(alpha=0.25, lw=0.4)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "sekil1_pareto.png"), bbox_inches="tight")
    plt.close(fig)
    out["figure1"] = {"origin": FIG1_ORIGIN, "destination": FIG1_DEST, "seed": SEED, "front_size": len(fr1),
                      "evaluated": len(allind), "activation": act,
                      "categories": {k: {"energy": float(fr1[i].obj[0]), "time": float(fr1[i].obj[1]),
                                         "comfort": float(100 - fr1[i].obj[2])} for k, i in cats1.items()}}
    with open(os.path.join(RESULTS, "case_study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # ---------------- Şekil 3: Harita ----------------
    fig, ax = plt.subplots(figsize=(8.5 / 2.54, 8.0 / 2.54))
    segs = [np.column_stack([g[:, 1], g[:, 0]]) for g in net.geom]
    major = np.isin(net.road_class, [0, 1, 2])
    ax.add_collection(LineCollection([s_ for s_, mj in zip(segs, major) if not mj], colors="0.85", linewidths=0.25))
    ax.add_collection(LineCollection([s_ for s_, mj in zip(segs, major) if mj], colors="0.65", linewidths=0.45))
    styles = [(ASTAR, "-", "k", 1.6), (LOW, (0, (1, 1)), "0.35", 1.6), (HIGH, (0, (4, 2)), "k", 1.6)]
    for name, ls, col, lw in styles:
        pr = routes[name]
        pts = np.array(net.path_geometry(pr.path))
        ax.plot(pts[:, 1], pts[:, 0], ls=ls, c=col, lw=lw, label=f"{name} – {pr.metrics.distance_km:.1f} km", zorder=5)
    for nm, node, mk in ((ORIGIN, s, "o"), (DEST, t, "s")):
        ax.scatter(net.node_lon[node], net.node_lat[node], marker=mk, s=28, c="k", zorder=6)
        ax.annotate(nm, (net.node_lon[node], net.node_lat[node]), xytext=(5, 4), textcoords="offset points",
                    fontsize=7, weight="bold", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    allpts = np.vstack([np.array(net.path_geometry(r.path)) for r in routes.values()])
    pad = 0.02
    ax.set_xlim(allpts[:, 1].min() - pad, allpts[:, 1].max() + pad)
    ax.set_ylim(allpts[:, 0].min() - pad, allpts[:, 0].max() + pad)
    ax.set_aspect(1 / np.cos(np.radians(39.93)))
    ax.set_xticks([]), ax.set_yticks([])
    ax.legend(fontsize=5.5, loc="upper left", framealpha=0.95)
    ax.text(0.99, 0.01, "Harita verisi: © OpenStreetMap katkıcıları (ODbL)", transform=ax.transAxes,
            fontsize=5, ha="right", va="bottom", color="0.3")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "sekil3_harita.png"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
