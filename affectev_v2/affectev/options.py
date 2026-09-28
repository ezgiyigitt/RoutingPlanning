"""
Arayüzde sürücüye sunulan üç rota seçeneği (Bölüm 3: "Konfor Odaklı, Dengeli ve Verimlilik
Odaklı ... bir çözüm kümesi sunmaktadır; hangisinin etkinleşeceği CLS düzeyine bağlıdır").

Seçenekler D-NSGA-II Pareto cephesinden seçilir ve haritada ayırt edilebilmeleri için
birbirinden yeterince farklı güzergâhlar olmaları sağlanır:
  * Verimlilik: cephedeki en düşük enerjili çözüm.
  * Konfor:     en yüksek konforlu çözüm; Verimlilik rotasıyla güzergâhının %MAX_OVERLAP'ından
                fazlası ortaksa, bu sınırı sağlayan en konforlu çözüm (daha konforlu olmak şartıyla).
  * Makullük:   yalnızca süresi en hızlı Pareto çözümünün en fazla 1,5 katı olan çözümler sunulur.
  * Dengeli:    eşit ağırlıklı normalize skoru en iyi olan ve diğer iki rotayla örtüşmesi
                sınırın altında kalan çözüm (yoksa örtüşmesi en az olan).
Önerilen seçenek, üç seçenek arasında CLS ağırlıklı normalize skoru (F = w_e·ê + w_t·t̂ + w_c·ĉ,
cephe genelinde min-max) en düşük olandır.

Not: Bildirideki Tablo 2–4 deneyleri, CLS ağırlıklı seçimi tüm Pareto cephesi üzerinden yapar
(nsga2.weighted_choice); bu modül yalnızca arayüz sunumu içindir.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

from .network import RoadNetwork
from .nsga2 import Individual

MAX_OVERLAP = 0.70
MAX_TIME_FACTOR = 1.5   # sunulan seçenekler en hızlı Pareto çözümünün en fazla 1,5 katı sürede olmalı


def _edge_set(net: RoadNetwork, ind: Individual) -> Tuple[set, float]:
    e = net.path_edges(list(ind.path))
    return set(int(x) for x in e), float(net.length_m[e].sum())


def overlap(net: RoadNetwork, a: Individual, b: Individual) -> float:
    """a rotasının uzunluğunun b ile ortak olan oranı (0–1)."""
    ea, la = _edge_set(net, a)
    eb, _ = _edge_set(net, b)
    shared = sum(net.length_m[i] for i in ea & eb)
    return float(shared / la) if la > 0 else 1.0


def _norm_scores(front: Sequence[Individual], w) -> np.ndarray:
    F = np.array([p.obj for p in front])
    lo, hi = F.min(0), F.max(0)
    span = np.where(hi - lo > 1e-12, hi - lo, 1.0)
    return ((F - lo) / span) @ np.asarray(w, dtype=float)


def display_options(net: RoadNetwork, front: Sequence[Individual], weights) -> Dict[str, object]:
    full = list(front)
    tmin = min(p.obj[1] for p in full)
    front = [p for p in full if p.obj[1] <= MAX_TIME_FACTOR * tmin] or full
    n = len(front)
    energy = np.array([p.obj[0] for p in front])
    comfort = np.array([100 - p.obj[2] for p in front])
    eff = int(np.lexsort(([p.obj[1] for p in front], energy))[0])

    com = int(np.argmax(comfort))
    if n > 1 and overlap(net, front[com], front[eff]) > MAX_OVERLAP:
        cands = [i for i in range(n) if i != eff and comfort[i] > comfort[eff]
                 and overlap(net, front[i], front[eff]) <= MAX_OVERLAP]
        if cands:
            com = max(cands, key=lambda i: comfort[i])

    eq = _norm_scores(front, (1 / 3, 1 / 3, 1 / 3))
    others = [i for i in range(n) if i not in (eff, com)]
    bal = eff if not others else None
    if others:
        ok = [i for i in others if overlap(net, front[i], front[eff]) <= MAX_OVERLAP
              and overlap(net, front[i], front[com]) <= MAX_OVERLAP]
        if ok:
            bal = min(ok, key=lambda i: eq[i])
        else:
            bal = min(others, key=lambda i: (max(overlap(net, front[i], front[eff]),
                                                 overlap(net, front[i], front[com])), eq[i]))
    chosen = {"Verimlilik": eff, "Dengeli": bal, "Konfor": com}

    score = _norm_scores(full, weights)
    pos = {id(p): i for i, p in enumerate(full)}
    score = np.array([score[pos[id(p)]] for p in front])
    recommended = min(chosen, key=lambda k: (score[chosen[k]], front[chosen[k]].obj[0]))
    pair_overlap = {
        f"{a}-{b}": round(overlap(net, front[chosen[a]], front[chosen[b]]), 3)
        for a, b in (("Verimlilik", "Dengeli"), ("Verimlilik", "Konfor"), ("Dengeli", "Konfor"))
    }
    return {"indices": chosen, "individuals": {k: front[i] for k, i in chosen.items()}, "recommended": recommended, "overlap": pair_overlap,
            "scores": {k: float(score[i]) for k, i in chosen.items()}}
