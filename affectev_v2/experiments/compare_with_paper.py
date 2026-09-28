"""
Kodun ürettiği sonuçları bildirideki (187.pdf) sayıların yanına koyar.

Girdi : results/summary.json, results/case_study.json, results/qlearning_summary.json
        experiments/paper_values.py (bildiri sayıları; yalnızca karşılaştırma için)
Çıktı : results/bildiri_karsilastirma.md
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paper_values as P  # noqa: E402

RESULTS = os.path.join(ROOT, "results")


def _load(name):
    p = os.path.join(RESULTS, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def pct(code, paper):
    return f"{100 * (code - paper) / abs(paper):+.0f}%" if paper else "—"


def main():
    S, C, Q = _load("summary.json"), _load("case_study.json"), _load("qlearning_summary.json")
    L = ["# Kod sonuçları ↔ bildiri (187.pdf)", "",
         "Her satırda solda bildirideki değer, sağda bu kodun ürettiği değer ve göreli fark vardır.",
         "Kod değerleri `python experiments/run_all.py` ile üretilir; bu dosya da otomatik yazılır.", ""]
    if S:
        L += ["## Tablo 2 — 50 senaryo × 10 tohum", "",
              "| Yöntem | Süre bildiri | Süre kod | Enerji bildiri | Enerji kod | Konfor bildiri | Konfor kod | Kavşak bildiri | Kavşak kod |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k, (t, ts, e, es, c, cs, j) in P.TABLE2.items():
            r = S["table2"][k]
            L.append(f"| {k} | {t} ± {ts} | {r['time_mean']:.1f} ± {r['time_sd']:.1f} ({pct(r['time_mean'], t)}) | "
                     f"{e} ± {es} | {r['energy_mean']:.1f} ± {r['energy_sd']:.1f} ({pct(r['energy_mean'], e)}) | "
                     f"{c} ± {cs} | {r['comfort_mean']:.1f} ± {r['comfort_sd']:.1f} ({pct(r['comfort_mean'], c)}) | "
                     f"{j} | {r['intersection_mean']:.1f} ({pct(r['intersection_mean'], j)}) |")
        L += ["", "## Tablo 3 — CLS düzeyleri", "",
              "| CLS | Konfor bildiri | Konfor kod | Enerji bildiri | Enerji kod | Süre bildiri | Süre kod | Rejim bildiri | Rejim kod |",
              "|---|---|---|---|---|---|---|---|---|"]
        for cls, (c, e, t, rj) in P.TABLE3.items():
            r = S["table3"][str(cls)]
            L.append(f"| {cls} | {c} | {r['comfort']:.1f} | {e} | {r['energy']:.2f} | {t} | {r['time']:.1f} | {rj} | "
                     f"{r['regime']} (%{100 * r['regime_share']:.0f}) |")
        c15, c85 = S["table3"]["15"], S["table3"]["85"]
        pc = P.TABLE3
        L += ["", "Göreli değişim CLS 15 → 85:", "",
              "| | Bildiri | Kod |", "|---|---|---|",
              f"| Konfor | {pct(pc[85][0], pc[15][0])} | {pct(c85['comfort'], c15['comfort'])} |",
              f"| Enerji | {pct(pc[85][1], pc[15][1])} | {pct(c85['energy'], c15['energy'])} |",
              f"| Süre | {pct(pc[85][2], pc[15][2])} | {pct(c85['time'], c15['time'])} |"]
    if C:
        L += ["", "## Tablo 4 — Keçiören → Bilkent (SoC %75, tohum 0)", "",
              "| Satır | Bildiri (km / dk / kWh / SoC / konfor) | Kod (km / dk / kWh / SoC / konfor) |", "|---|---|---|"]
        names = {"A*": "Geleneksel (A*)", "Düşük CLS": None, "Yüksek CLS": None}
        for k in C["routes"]:
            if "Düşük" in k:
                names["Düşük CLS"] = k
            if "Yüksek" in k:
                names["Yüksek CLS"] = k
        for k, vals in P.TABLE4.items():
            r = C["routes"][names[k]]
            L.append(f"| {k} | {' / '.join(str(v) for v in vals)} | {r['distance_km']:.1f} / {r['time_min']:.1f} / "
                     f"{r['energy_kwh']:.2f} / {r['soc_final']:.1f} / {r['comfort']:.1f} |")
        rel = C["high_vs_astar_pct"]
        L += ["", f"Yüksek CLS / A*: bildiri konfor +41%, enerji +84%, mesafe +91% — kod konfor "
                  f"{rel['comfort_pct']:+.1f}%, enerji {rel['energy_pct']:+.1f}%, mesafe {rel['distance_pct']:+.1f}%.",
              f"Düşük CLS = A* rotası: bildiri evet — kod {'evet' if C['low_cls_equals_astar'] else 'hayır'}."]
    if Q:
        L += ["", "## Şekil 2 — Q-Learning", "",
              "| | Bildiri | Kod |", "|---|---|---|",
              f"| Son 200 bölüm ortalama ödül | ≈{P.FIGURE2['plateau']} | {Q['q_last200_mean']:.2f} |",
              f"| Rastgele politika | ≈{P.FIGURE2['random']} | {Q['random_mean']:.2f} |",
              f"| Q-Learning − rastgele (son 200) | ≈{P.FIGURE2['plateau'] - P.FIGURE2['random']:.1f} | "
              f"{Q['improvement_over_random_last200']:.2f} |",
              f"| İlk 100 bölüm ortalaması | negatif | {Q['q_first100_mean']:.2f} |"]
    with open(os.path.join(RESULTS, "bildiri_karsilastirma.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
