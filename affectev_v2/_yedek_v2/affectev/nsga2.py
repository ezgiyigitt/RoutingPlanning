"""
D-NSGA-II (Bölüm 3) — Deb vd. [7] NSGA-II'nin rota planlama uyarlaması ve CLS'ye
bağlı dinamik karar aşaması.

Amaçlar (hepsi minimize edilir):
    f1 = E_route (kWh, Dn. 3)
    f2 = seyahat süresi (dk)
    f3 = 100 − Comfort_route (Dn. 2)

Kromozom: başlangıçtan varışa döngüsüz düğüm dizisi (rota).
Çaprazlama (p_c = 0,8): ortak düğüm üzerinden tek noktalı çaprazlama.
Mutasyon  (p_m = 0,1): rastgele bir alt rotanın gürültülü ağırlıklarla yeniden yönlendirilmesi.
Seçim: ikili turnuva (rank, crowding distance); çevresel seçim (μ+λ) elitist.

Dinamik karar (D-NSGA-II): Optimizasyon Pareto cephesini üretir; hangi Pareto
çözümünün etkinleşeceği CLS'ye bağlı (w_e, w_t, w_c) ağırlıklarıyla belirlenir:
    F(r) = w_e·ê(r) + w_t·t̂(r) + w_c·ĉ(r)      (cephe içinde min-max normalize)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import NSGA, NSGA2Params
from .models import RouteMetrics, TrafficState, route_metrics
from .network import RoadNetwork
from .routing import shortest_path

CATEGORIES = ("Verimlilik", "Dengeli", "Konfor")


@dataclass
class Individual:
    path: Tuple[int, ...]
    metrics: RouteMetrics
    obj: np.ndarray                  # (f1, f2, f3)
    rank: int = 0
    crowding: float = 0.0


@dataclass
class NSGAResult:
    population: List[Individual]
    front: List[Individual]
    evaluations: int
    history: List[Dict[str, float]] = field(default_factory=list)


def remove_loops(path: Sequence[int]) -> List[int]:
    out: List[int] = []
    pos: Dict[int, int] = {}
    for n in path:
        if n in pos:
            k = pos[n]
            for m in out[k + 1:]:
                pos.pop(m, None)
            out = out[:k + 1]
        else:
            pos[n] = len(out)
            out.append(n)
    return out


def fast_non_dominated_sort(F: np.ndarray) -> List[List[int]]:
    n = len(F)
    le = (F[:, None, :] <= F[None, :, :]).all(axis=2)
    lt = (F[:, None, :] < F[None, :, :]).any(axis=2)
    dom = le & lt                     # dom[i, j]: i, j'yi baskılar
    n_dom = dom.sum(axis=0)           # i'yi baskılayan sayısı
    fronts: List[List[int]] = []
    current = [i for i in range(n) if n_dom[i] == 0]
    while current:
        fronts.append(current)
        nxt = []
        for i in current:
            for j in np.nonzero(dom[i])[0]:
                n_dom[j] -= 1
                if n_dom[j] == 0:
                    nxt.append(int(j))
        current = nxt
    return fronts


def crowding_distance(F: np.ndarray) -> np.ndarray:
    n, m = F.shape
    cd = np.zeros(n)
    if n <= 2:
        return np.full(n, np.inf)
    for k in range(m):
        order = np.argsort(F[:, k], kind="stable")
        rng = F[order[-1], k] - F[order[0], k]
        cd[order[0]] = cd[order[-1]] = np.inf
        if rng > 0:
            cd[order[1:-1]] += (F[order[2:], k] - F[order[:-2], k]) / rng
    return cd


def weighted_choice(front: Sequence[Individual], weights: Tuple[float, float, float]) -> int:
    """Dinamik karar: F = w_e·ê + w_t·t̂ + w_c·ĉ (cephede min-max normalize); argmin indeksi."""
    F = np.array([ind.obj for ind in front])
    lo, hi = F.min(axis=0), F.max(axis=0)
    span = np.where(hi - lo > 1e-12, hi - lo, 1.0)
    Fn = (F - lo) / span
    score = Fn @ np.asarray(weights)
    # Eşitlikte sırasıyla enerji, süre, konfor küçük olan seçilir (deterministik)
    order = np.lexsort((F[:, 2], F[:, 1], F[:, 0], np.round(score, 12)))
    return int(order[0])


def categorize(front: Sequence[Individual]) -> Dict[str, int]:
    """Pareto cephesinden üç kategori: Verimlilik (min enerji), Dengeli (eşit ağırlık),
    Konfor (max konfor)."""
    F = np.array([ind.obj for ind in front])
    eff = int(np.lexsort((F[:, 2], F[:, 1], F[:, 0]))[0])
    com = int(np.lexsort((F[:, 1], F[:, 0], F[:, 2]))[0])
    bal = weighted_choice(front, (1 / 3, 1 / 3, 1 / 3))
    return {"Verimlilik": eff, "Dengeli": bal, "Konfor": com}


class DNSGA2:
    def __init__(self, net: RoadNetwork, traffic: TrafficState, rng: np.random.Generator,
                 params: NSGA2Params = NSGA):
        self.net = net
        self.tr = traffic
        self.rng = rng
        self.p = params
        self._cache: Dict[Tuple[int, ...], Individual] = {}
        self.evaluations = 0
        # Rastgele yol üretimi için normalize edilmiş kenar maliyet bileşenleri
        L = net.length_m
        disc = 0.5 * net.n_signal + 0.3 * net.n_stop + 0.2 * 100.0 * traffic.density * L / 5000.0
        self._components = np.vstack([
            traffic.energy_kwh / traffic.energy_kwh.mean(),
            traffic.time_s / traffic.time_s.mean(),
            (disc + 1e-3) / (disc.mean() + 1e-3),
        ])

    # ---------------------------------------------------------------- değerlendirme
    def evaluate(self, path: Sequence[int]) -> Individual:
        key = tuple(path)
        ind = self._cache.get(key)
        if ind is None:
            m = route_metrics(self.net, self.tr, self.net.path_edges(list(key)))
            ind = Individual(key, m, np.array([m.energy_kwh, m.time_min, 100.0 - m.comfort]))
            self._cache[key] = ind
            self.evaluations += 1
        return Individual(ind.path, ind.metrics, ind.obj)

    # ---------------------------------------------------------------- operatörler
    def _noisy_weights(self, lam: Optional[np.ndarray] = None, sigma: float = 0.35) -> np.ndarray:
        if lam is None:
            lam = self.rng.dirichlet(np.ones(3))
        w = lam @ self._components
        return w * self.rng.lognormal(0.0, sigma, size=w.shape) + 1e-9

    def random_path(self, s: int, t: int, lam: Optional[np.ndarray] = None, sigma: float = 0.35):
        return shortest_path(self.net, self._noisy_weights(lam, sigma), s, t)

    def crossover(self, a: Tuple[int, ...], b: Tuple[int, ...]):
        common = set(a[1:-1]) & set(b[1:-1])
        if not common:
            return list(a), list(b)
        c = self.rng.choice(sorted(common))
        i, j = a.index(c), b.index(c)
        return remove_loops(a[:i] + b[j:]), remove_loops(b[:j] + a[i:])

    def mutate(self, path: List[int]) -> List[int]:
        if len(path) < 3:
            return path
        i, j = sorted(self.rng.choice(len(path), size=2, replace=False))
        if j - i < 2:
            j = min(len(path) - 1, i + 2)
        sub = self.random_path(path[i], path[j], sigma=0.6)
        if sub is None:
            return path
        return remove_loops(path[:i] + sub + path[j + 1:])

    def _tournament(self, pop: List[Individual]) -> Individual:
        a, b = self.rng.choice(len(pop), size=2, replace=False)
        A, B = pop[a], pop[b]
        if A.rank != B.rank:
            return A if A.rank < B.rank else B
        return A if A.crowding >= B.crowding else B

    # ---------------------------------------------------------------- seçim
    def _rank(self, pop: List[Individual]) -> List[List[int]]:
        F = np.array([p.obj for p in pop])
        fronts = fast_non_dominated_sort(F)
        for r, fr in enumerate(fronts):
            cd = crowding_distance(F[fr])
            for k, i in enumerate(fr):
                pop[i].rank = r
                pop[i].crowding = float(cd[k])
        return fronts

    def _environmental_selection(self, pop: List[Individual]) -> List[Individual]:
        fronts = self._rank(pop)
        out: List[Individual] = []
        for fr in fronts:
            if len(out) + len(fr) <= self.p.population:
                out.extend(pop[i] for i in fr)
            else:
                rest = sorted(fr, key=lambda i: -pop[i].crowding)
                out.extend(pop[i] for i in rest[: self.p.population - len(out)])
                break
        return out

    @staticmethod
    def _unique(pop: List[Individual]) -> List[Individual]:
        seen, out = set(), []
        for p in pop:
            if p.path not in seen:
                seen.add(p.path)
                out.append(p)
        return out

    # ---------------------------------------------------------------- ana döngü
    def run(self, s: int, t: int, generations: Optional[int] = None,
            record_history: bool = False) -> NSGAResult:
        G = self.p.generations if generations is None else generations
        N = self.p.population
        pop: List[Individual] = []
        # Başlangıç popülasyonu: üç tek-amaç uç noktası + gürültülü rastgele ağırlıklı yollar
        for lam in np.eye(3):
            pth = self.random_path(s, t, lam=lam, sigma=0.0)
            if pth:
                pop.append(self.evaluate(pth))
        tries = 0
        while len(self._unique(pop)) < N and tries < 5 * N:
            pth = self.random_path(s, t)
            tries += 1
            if pth:
                pop.append(self.evaluate(pth))
        pop = self._unique(pop)[:N]
        self._rank(pop)
        history = []
        for gen in range(G):
            offspring: List[Individual] = []
            while len(offspring) < N:
                pa, pb = self._tournament(pop), self._tournament(pop)
                if self.rng.random() < self.p.crossover_rate:
                    ca, cb = self.crossover(pa.path, pb.path)
                else:
                    ca, cb = list(pa.path), list(pb.path)
                for c in (ca, cb):
                    if self.rng.random() < self.p.mutation_rate:
                        c = self.mutate(c)
                    offspring.append(self.evaluate(c))
            pop = self._environmental_selection(self._unique(pop + offspring))
            if record_history:
                F = np.array([p.obj for p in pop if p.rank == 0])
                history.append({"gen": gen + 1, "front_size": len(F),
                                "min_energy": float(F[:, 0].min()), "min_time": float(F[:, 1].min()),
                                "max_comfort": float(100 - F[:, 2].min())})
        self._rank(pop)
        front = [p for p in pop if p.rank == 0]
        # Aynı amaç değerine sahip farklı yolları tekilleştir
        seen, uniq = set(), []
        for p in sorted(front, key=lambda x: tuple(x.obj)):
            k = tuple(np.round(p.obj, 6))
            if k not in seen:
                seen.add(k)
                uniq.append(p)
        return NSGAResult(pop, uniq, self.evaluations, history)
