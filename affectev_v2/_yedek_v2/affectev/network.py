"""
OpenStreetMap tabanlı Ankara yol ağı (Bölüm 4).

Veri: data/ankara_osm.json.gz — Overpass API'den alınmış, Ankara metropol alanı
(39.75–40.14 K, 32.55–33.05 D) için motorlu taşıt yolları (motorway…unclassified
ve bağlantı yolları), sinyalize kavşak düğümleri (highway=traffic_signals),
otobüs durakları (highway=bus_stop) ve şarj istasyonları (amenity=charging_station).

Graf, kavşak düğümleri arasında sadeleştirilmiş yönlü bir graftır. Her kenar için:
uzunluk, serbest akış hızı, yol sınıfı, kenar üzerindeki sinyalize kavşak sayısı
(N_intersection) ve durak sayısı (N_stop) tutulur.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import pickle
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
RAW_PATH = os.path.join(DATA_DIR, "ankara_osm.json.gz")
CACHE_PATH = os.path.join(DATA_DIR, "ankara_graph.pkl")

ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified")
DEFAULT_SPEED = {  # km/h (Türkiye şehir içi hız sınırları; etiket yoksa)
    "motorway": 100.0, "trunk": 82.0, "primary": 70.0, "secondary": 50.0,
    "tertiary": 50.0, "unclassified": 40.0,
}
LINK_SPEED = 40.0
FREE_FLOW_FACTOR = 0.90   # serbest akış hızı = 0.9 x hız sınırı
BUS_STOP_SNAP_M = 25.0

R_EARTH = 6371000.0


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(a))


def _project(lat, lon, lat0=39.93):
    """Yerel eşdikdörtgen projeksiyon (metre)."""
    x = np.radians(lon) * R_EARTH * math.cos(math.radians(lat0))
    y = np.radians(lat) * R_EARTH
    return np.column_stack([x, y])


def _parse_speed(v: Optional[str]) -> Optional[float]:
    if not v:
        return None
    try:
        return float(str(v).split()[0].split(";")[0])
    except ValueError:
        return None


@dataclass
class RoadNetwork:
    node_osm: np.ndarray          # (N,) OSM node id
    node_lat: np.ndarray
    node_lon: np.ndarray
    src: np.ndarray               # (E,)
    dst: np.ndarray
    length_m: np.ndarray
    vfree_kmh: np.ndarray
    road_class: np.ndarray        # (E,) int index in ROAD_CLASSES
    is_link: np.ndarray
    n_signal: np.ndarray          # sinyalize kavşak sayısı (kenar üzerinde, bitiş düğümü dahil)
    n_stop: np.ndarray            # otobüs durağı sayısı
    geom: List[np.ndarray]        # her kenar için [(lat, lon), ...]
    charging: List[dict]          # şarj istasyonları
    osm_timestamp: str

    # ---- türetilmiş yapılar ----
    def __post_init__(self):
        self.n_nodes = len(self.node_lat)
        self.n_edges = len(self.src)
        self.edge_index: Dict[Tuple[int, int], int] = {
            (int(u), int(v)): i for i, (u, v) in enumerate(zip(self.src, self.dst))
        }
        self.out_edges: List[List[int]] = [[] for _ in range(self.n_nodes)]
        for i, u in enumerate(self.src):
            self.out_edges[int(u)].append(i)
        self._xy = _project(self.node_lat, self.node_lon)
        self._tree = cKDTree(self._xy)
        mid_lat = np.array([g[len(g) // 2][0] for g in self.geom])
        mid_lon = np.array([g[len(g) // 2][1] for g in self.geom])
        self.edge_mid_xy = _project(mid_lat, mid_lon)
        self.vmax_ms = float(self.vfree_kmh.max()) / 3.6

    def nearest_node(self, lat: float, lon: float) -> int:
        _, i = self._tree.query(_project(np.array([lat]), np.array([lon]))[0])
        return int(i)

    def node_xy(self, i: int) -> np.ndarray:
        return self._xy[i]

    def csr(self, weights: np.ndarray) -> csr_matrix:
        return csr_matrix((weights, (self.src, self.dst)), shape=(self.n_nodes, self.n_nodes))

    def path_edges(self, path: List[int]) -> np.ndarray:
        return np.array([self.edge_index[(path[i], path[i + 1])] for i in range(len(path) - 1)], dtype=np.int64)

    def path_geometry(self, path: List[int]) -> List[Tuple[float, float]]:
        pts: List[Tuple[float, float]] = []
        for e in self.path_edges(path):
            g = self.geom[int(e)]
            pts.extend([tuple(p) for p in (g if not pts else g[1:])])
        return pts


def _build_from_raw(raw_path: str = RAW_PATH) -> RoadNetwork:
    with gzip.open(raw_path, "rt", encoding="utf-8") as f:
        d = json.load(f)
    nodes = {int(k): v for k, v in d["nodes"].items()}

    # 1) Kavşak düğümlerini bul (2+ yolda geçen veya yol ucu)
    use = {}
    for _, nds, _ in d["ways"]:
        for n in nds:
            use[n] = use.get(n, 0) + 1
        use[nds[0]] = use.get(nds[0], 0) + 1
        use[nds[-1]] = use.get(nds[-1], 0) + 1
    junction = {n for n, c in use.items() if c >= 2}

    # 2) Sinyal ve durak işaretleri
    signal = {n for n, v in nodes.items() if v[2] and "traffic_signals" in str(v[2].get("highway", ""))}
    stop_on = {n for n, v in nodes.items() if v[2] and v[2].get("highway") == "bus_stop"}

    all_ids = np.array(sorted(nodes.keys()))
    lat_all = np.array([nodes[i][0] for i in all_ids])
    lon_all = np.array([nodes[i][1] for i in all_ids])
    tree_all = cKDTree(_project(lat_all, lon_all))
    stop_count: Dict[int, int] = {n: 1 for n in stop_on}
    bs = d.get("bus_stops", [])
    if bs:
        bxy = _project(np.array([b[1] for b in bs]), np.array([b[2] for b in bs]))
        dist, idx = tree_all.query(bxy)
        for dd, ii in zip(dist, idx):
            if dd <= BUS_STOP_SNAP_M:
                nid = int(all_ids[ii])
                stop_count[nid] = stop_count.get(nid, 0) + 1

    # 3) Yolları kavşaklarda böl
    seg_rows = []  # (u_osm, v_osm, length, vfree, cls, is_link, nsig, nstop, geom, oneway)
    for _, nds, tags in d["ways"]:
        hw = tags.get("highway", "unclassified")
        is_link = hw.endswith("_link")
        base = hw.replace("_link", "")
        if base not in ROAD_CLASSES:
            continue
        cls_i = ROAD_CLASSES.index(base)
        lim = _parse_speed(tags.get("maxspeed"))
        if lim is None:
            lim = LINK_SPEED if is_link else DEFAULT_SPEED[base]
        vfree = max(15.0, lim * FREE_FLOW_FACTOR)
        ow = str(tags.get("oneway", "")).lower()
        if ow in ("yes", "true", "1"):
            direction = 1
        elif ow == "-1":
            direction = -1
        elif base == "motorway" or tags.get("junction") in ("roundabout", "circular"):
            direction = 1
        else:
            direction = 0
        start = 0
        for k in range(1, len(nds)):
            if nds[k] in junction or k == len(nds) - 1:
                seg = nds[start:k + 1]
                if len(seg) >= 2 and seg[0] != seg[-1]:
                    la = np.array([nodes[n][0] for n in seg])
                    lo = np.array([nodes[n][1] for n in seg])
                    L = float(haversine_m(la[:-1], lo[:-1], la[1:], lo[1:]).sum())
                    geom = np.column_stack([la, lo])
                    inner_end = seg[1:]
                    inner_start = seg[:-1]
                    seg_rows.append((seg[0], seg[-1], L, vfree, cls_i, is_link,
                                     sum(n in signal for n in inner_end),
                                     sum(stop_count.get(n, 0) for n in inner_end),
                                     sum(n in signal for n in inner_start),
                                     sum(stop_count.get(n, 0) for n in inner_start),
                                     geom, direction))
                start = k

    # 4) Yönlü kenarlar (paralel kenarlarda en kısa olanı tut)
    best: Dict[Tuple[int, int], tuple] = {}
    for (u, v, L, vf, c, lk, sig_f, st_f, sig_b, st_b, geom, dirn) in seg_rows:
        cand = []
        if dirn in (0, 1):
            cand.append((u, v, L, vf, c, lk, sig_f, st_f, geom))
        if dirn in (0, -1):
            cand.append((v, u, L, vf, c, lk, sig_b, st_b, geom[::-1]))
        for row in cand:
            key = (row[0], row[1])
            if key not in best or row[2] < best[key][2]:
                best[key] = row

    used = sorted({k[0] for k in best} | {k[1] for k in best})
    idx = {n: i for i, n in enumerate(used)}
    rows = list(best.values())
    src = np.array([idx[r[0]] for r in rows])
    dst = np.array([idx[r[1]] for r in rows])
    N = len(used)

    # 5) En büyük güçlü bağlı bileşen
    A = csr_matrix((np.ones(len(rows)), (src, dst)), shape=(N, N))
    _, labels = connected_components(A, directed=True, connection="strong")
    big = np.bincount(labels).argmax()
    keep_node = labels == big
    keep_edge = keep_node[src] & keep_node[dst]
    new_idx = -np.ones(N, dtype=np.int64)
    new_idx[keep_node] = np.arange(keep_node.sum())
    rows = [r for r, k in zip(rows, keep_edge) if k]
    used_arr = np.array(used)[keep_node]

    charging = [{"id": c[0], "lat": c[1], "lon": c[2], "operator": c[3].get("operator", ""),
                 "capacity": c[3].get("capacity", "")} for c in d.get("charging", [])]
    # Aynı noktadaki yinelenen istasyon kayıtlarını birleştir
    uniq, seen = [], set()
    for c in charging:
        key = (round(c["lat"], 4), round(c["lon"], 4))
        if key not in seen:
            seen.add(key)
            uniq.append(c)

    return RoadNetwork(
        node_osm=used_arr,
        node_lat=np.array([nodes[n][0] for n in used_arr]),
        node_lon=np.array([nodes[n][1] for n in used_arr]),
        src=new_idx[np.array([idx[r[0]] for r in rows])],
        dst=new_idx[np.array([idx[r[1]] for r in rows])],
        length_m=np.array([r[2] for r in rows]),
        vfree_kmh=np.array([r[3] for r in rows]),
        road_class=np.array([r[4] for r in rows]),
        is_link=np.array([r[5] for r in rows]),
        n_signal=np.array([r[6] for r in rows]),
        n_stop=np.array([r[7] for r in rows]),
        geom=[r[8] for r in rows],
        charging=uniq,
        osm_timestamp=d.get("ts", ""),
    )


_NET: Optional[RoadNetwork] = None


def load_network(rebuild: bool = False) -> RoadNetwork:
    """Ağı yükler; ilk çalıştırmada ham OSM verisinden oluşturup önbelleğe yazar."""
    global _NET
    if _NET is not None and not rebuild:
        return _NET
    if os.path.exists(CACHE_PATH) and not rebuild and os.path.getmtime(CACHE_PATH) >= os.path.getmtime(RAW_PATH):
        with open(CACHE_PATH, "rb") as f:
            state = pickle.load(f)
        _NET = RoadNetwork(**state)
    else:
        _NET = _build_from_raw()
        state = {k: getattr(_NET, k) for k in RoadNetwork.__dataclass_fields__}
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
    return _NET
