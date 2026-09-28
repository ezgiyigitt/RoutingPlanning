"""
Örnek vaka: Keçiören → Bilkent, başlangıç SoC %75 (Tablo 4, Şekil 1, Şekil 3).
Trafik gerçekleşmesi: tohum 0. D-NSGA-II tek çalıştırma; düşük CLS = 15, yüksek CLS = 85.

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
from affectev.config import EXP, LOCATIONS  # noqa: E402
from affectev.models import cls_weights, make_traffic  # noqa: E402
from affectev.network import load_network  # noqa: E402
from affectev.nsga2 import DNSGA2, categorize, fast_non_dominated_sort, weighted_choice  # noqa: E402
from affectev.planner import apply_soc  # noqa: E402
from affectev.routing import astar_time  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
ORIGIN, DEST, SOC0, SEED = "Keçiören", "Bilkent", 75.0, 0
CLS_LOW, CLS_HIGH = 15.0, 85.0

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "savefig.dpi": 300})


def main():
    os.makedirs(RESULTS, exist_ok=True)
    net = load_network()
    tr = make_traffic(net, SEED)
    s = net.nearest_node(*LOCATIONS[ORIGIN])
    t = net.nearest_node(*LOCATIONS[DEST])
    opt = DNSGA2(net, tr, np.random.default_rng([EXP.master_seed, 0, SEED]))
    res = opt.run(s, t, record_history=True)
    front = res.front
    cats = categorize(front)
    i_lo = weighted_choice(front, cls_weights(CLS_LOW))
    i_hi = weighted_choice(front, cls_weights(CLS_HIGH))

    routes = {
        "Geleneksel (A*)": apply_soc(net, tr, opt, "A*", astar_time(net, tr, s, t), SOC0, (0, 1, 0)),
        f"AffectEV / Düşük CLS ({CLS_LOW:.0f})": apply_soc(net, tr, opt, "AffectEV", list(front[i_lo].path), SOC0, cls_weights(CLS_LOW)),
        f"AffectEV / Yüksek CLS ({CLS_HIGH:.0f})": apply_soc(net, tr, opt, "AffectEV", list(front[i_hi].path), SOC0, cls_weights(CLS_HIGH)),
    }
    same_lo_astar = routes[f"AffectEV / Düşük CLS ({CLS_LOW:.0f})"].path == routes["Geleneksel (A*)"].path

    # ---------------- Tablo 4 ----------------
    L = ["Tablo 4: Keçiören–Bilkent Senaryosu Rota Üretimi Karşılaştırması (başlangıç SoC %75, tohum 0)", "",
         "| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor (0-100) | Kavşak | Durak |",
         "|---|---|---|---|---|---|---|---|"]
    out = {"origin": ORIGIN, "destination": DEST, "soc_initial": SOC0, "seed": SEED,
           "front_size": len(front), "evaluations": res.evaluations, "routes": {},
           "low_cls_equals_astar": same_lo_astar}
    for name, pr in routes.items():
        m = pr.metrics
        L.append(f"| {name} | {m.distance_km:.1f} | {m.time_min:.1f} | {m.energy_kwh:.2f} | "
                 f"{pr.soc_final:.1f} | {m.comfort:.1f} | {m.n_intersection} | {m.n_stop} |")
        out["routes"][name] = {**m.as_dict(), "soc_final": pr.soc_final,
                               "charging": pr.charging is not None}
    a = routes["Geleneksel (A*)"].metrics
    h = routes[f"AffectEV / Yüksek CLS ({CLS_HIGH:.0f})"].metrics
    rel = {"comfort_pct": 100 * (h.comfort - a.comfort) / a.comfort,
           "energy_pct": 100 * (h.energy_kwh - a.energy_kwh) / a.energy_kwh,
           "distance_pct": 100 * (h.distance_km - a.distance_km) / a.distance_km,
           "time_pct": 100 * (h.time_min - a.time_min) / a.time_min}
    out["high_vs_astar_pct"] = rel
    L += ["", f"Yüksek CLS rotasının A*'a göre değişimi: konfor {rel['comfort_pct']:+.1f}%, "
              f"enerji {rel['energy_pct']:+.1f}%, mesafe {rel['distance_pct']:+.1f}%, süre {rel['time_pct']:+.1f}%.",
          f"Düşük CLS rotası A* ile aynı mı: {'evet' if same_lo_astar else 'hayır'}."]
    with open(os.path.join(RESULTS, "tablo4.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(RESULTS, "case_study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n".join(L))

    # ---------------- Şekil 1: Pareto cephesi ----------------
    allind = list(opt._cache.values())
    F = np.array([p.obj for p in allind])
    fr0 = set(fast_non_dominated_sort(F)[0])
    dom = [i for i in range(len(allind)) if i not in fr0]
    FF = np.array([p.obj for p in front])
    fig, ax = plt.subplots(figsize=(8.5 / 2.54, 7.2 / 2.54))
    ax.scatter(F[dom, 0], F[dom, 1], marker="x", s=10, lw=0.5, c="0.65", label="Baskılanan çözümler", zorder=1)
    # enerji–süre düzleminde baskılanmayan alt küme (2B izdüşüm çizgisi)
    f2 = fast_non_dominated_sort(FF[:, :2])[0]
    f2 = sorted(f2, key=lambda i: FF[i, 0])
    ax.plot(FF[f2, 0], FF[f2, 1], c="k", lw=0.9, zorder=2, label="Pareto cephesi (enerji–süre)")
    sc = ax.scatter(FF[:, 0], FF[:, 1], c=100 - FF[:, 2], cmap="Greys", s=14, edgecolors="k",
                    linewidths=0.4, zorder=3)
    labels = {"Verimlilik": "Verimlilik odaklı", "Dengeli": "Dengeli", "Konfor": "Konfor odaklı"}
    sel = {i_lo: f"CLS={CLS_LOW:.0f}", i_hi: f"CLS={CLS_HIGH:.0f}"}
    placed = {}
    for k, i in cats.items():
        txt = labels[k] + (f"\n({sel[i]})" if i in sel else "")
        placed.setdefault(i, []).append(txt)
    for extra_i, lab in sel.items():
        if extra_i not in placed:
            placed[extra_i] = [f"AffectEV seçimi\n({lab})"]
    # Etiket kutuları eksen kesirlerinde sabit konumlara yerleştirilir (çakışmayı önlemek için)
    slots = [(0.04, 0.34), (0.40, 0.05), (0.40, 0.40), (0.70, 0.62)]
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
    ax.set_xlabel("Enerji tüketimi (kWh)")
    ax.set_ylabel("Seyahat süresi (dk)")
    ax.legend(fontsize=6, loc="upper left", frameon=True)
    ax.grid(alpha=0.25, lw=0.4)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "sekil1_pareto.png"), bbox_inches="tight")
    plt.close(fig)

    # ---------------- Şekil 3: Harita ----------------
    fig, ax = plt.subplots(figsize=(8.5 / 2.54, 8.0 / 2.54))
    segs = [np.column_stack([g[:, 1], g[:, 0]]) for g in net.geom]
    major = np.isin(net.road_class, [0, 1, 2])
    ax.add_collection(LineCollection([s_ for s_, mj in zip(segs, major) if not mj], colors="0.85", linewidths=0.25))
    ax.add_collection(LineCollection([s_ for s_, mj in zip(segs, major) if mj], colors="0.65", linewidths=0.45))
    styles = [("Geleneksel (A*)", "-", "k", 1.6), (f"AffectEV / Düşük CLS ({CLS_LOW:.0f})", (0, (1, 1)), "0.35", 1.6),
              (f"AffectEV / Yüksek CLS ({CLS_HIGH:.0f})", (0, (4, 2)), "k", 1.6)]
    for name, ls, col, lw in styles:
        pr = routes[name]
        pts = np.array(net.path_geometry(pr.path))
        lab = f"{name} – {pr.metrics.distance_km:.1f} km"
        ax.plot(pts[:, 1], pts[:, 0], ls=ls, c=col, lw=lw, label=lab, zorder=5)
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
