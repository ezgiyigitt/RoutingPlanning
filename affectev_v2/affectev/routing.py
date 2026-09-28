"""Temel rota algoritmaları: Dijkstra (mesafe maliyetli) [12] ve A* (süre maliyetli) [13]."""
from __future__ import annotations

import heapq
from typing import List, Optional

import numpy as np
from scipy.sparse.csgraph import dijkstra as _sp_dijkstra

from .models import TrafficState
from .network import RoadNetwork


def _reconstruct(pred: np.ndarray, s: int, t: int) -> Optional[List[int]]:
    if s == t:
        return [s]
    if pred[t] < 0:
        return None
    path = [t]
    while path[-1] != s:
        path.append(int(pred[path[-1]]))
    return path[::-1]


def shortest_path(net: RoadNetwork, weights: np.ndarray, s: int, t: int) -> Optional[List[int]]:
    """Verilen kenar ağırlıklarıyla Dijkstra (scipy, C uygulaması)."""
    _, pred = _sp_dijkstra(net.csr(weights), directed=True, indices=s, return_predecessors=True)
    return _reconstruct(pred, s, t)


def dijkstra_distance(net: RoadNetwork, s: int, t: int) -> Optional[List[int]]:
    """Dijkstra — mesafe maliyetli."""
    return shortest_path(net, net.length_m, s, t)


def astar_time(net: RoadNetwork, tr: TrafficState, s: int, t: int) -> Optional[List[int]]:
    """A* — süre maliyetli. Sezgisel: kuş uçuşu mesafe / ağdaki en yüksek serbest akış hızı
    (kabul edilebilir/admissible olduğundan en hızlı rotayı garanti eder)."""
    goal = net.node_xy(t)
    vmax = net.vmax_ms
    xy = net._xy

    def h(n: int) -> float:
        return float(np.hypot(*(xy[n] - goal))) / vmax

    g = {s: 0.0}
    prev = {s: -1}
    openh = [(h(s), s)]
    closed = set()
    while openh:
        _, u = heapq.heappop(openh)
        if u in closed:
            continue
        if u == t:
            break
        closed.add(u)
        gu = g[u]
        for e in net.out_edges[u]:
            v = int(net.dst[e])
            ng = gu + float(tr.time_s[e])
            if ng < g.get(v, np.inf):
                g[v] = ng
                prev[v] = u
                heapq.heappush(openh, (ng + h(v), v))
    if t not in prev:
        return None
    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return path[::-1]
