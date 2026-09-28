"""
AffectEV yerel API sunucusu (FastAPI).

Başlatma:  python run.py         (arayüzü de sunar: http://127.0.0.1:8000)
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from affectev.config import (CLS_WEIGHT_TABLE, COMFORT, CLSP, LOCATIONS, NSGA, QL, TRAFFIC,  # noqa: E402
                             VEHICLE, VEHICLE_NOTES, VEHICLES, WEATHER)
from affectev.models import (cls_state_name, cls_weights, cognitive_load_score, make_traffic)  # noqa: E402
from affectev.network import load_network  # noqa: E402
from affectev.nsga2 import CATEGORIES  # noqa: E402
from affectev.options import display_options  # noqa: E402
from affectev.planner import PlannedRoute, apply_soc, plan  # noqa: E402
from affectev.qlearning import ACTIONS, QAgent, encode_state, reward  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
DIST = os.path.join(ROOT, "frontend", "dist")
Q_PATH = os.path.join(ROOT, "data", "q_table.npy")          # eski tek tablo (geriye uyum)
Q_DIR = os.path.join(ROOT, "data", "q_tables")               # sürücü başına Q-tablosu
DRIVERS_PATH = os.path.join(ROOT, "data", "drivers.json")          # arayüzden eklenen yeni sürücüler
STATS_PATH = os.path.join(ROOT, "data", "driver_stats.json")        # sürücü başına geri bildirim sayısı
# Projede daha önce kayıtlı sürücüler (eski sürüm). Salt okunur kullanılır, dosya değiştirilmez.
LEGACY_DRIVERS_PATHS = [os.path.join(ROOT, "data", "surucucler.json"),
                        os.path.join(os.path.dirname(ROOT), "surucucler.json")]
APP_VERSION = "3.0"

app = FastAPI(title="AffectEV API", version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

_lock = threading.Lock()
_traffic_cache: Dict[tuple, object] = {}
_agents: Dict[str, QAgent] = {}


def agent(driver_id: str) -> QAgent:
    """Her sürücünün kendi Q-tablosu vardır (kişiselleştirme)."""
    if driver_id not in _agents:
        a = QAgent(np.random.default_rng(0))
        a.load(os.path.join(Q_DIR, f"{driver_id}.npy"))
        _agents[driver_id] = a
    return _agents[driver_id]


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _legacy_drivers() -> List[dict]:
    for p in LEGACY_DRIVERS_PATHS:
        raw = _read_json(p, None)
        if isinstance(raw, list) and raw:
            out = []
            for d in raw:
                if not isinstance(d, dict) or "uid" not in d:
                    continue
                out.append({"id": str(d["uid"]), "name": d.get("isim") or str(d["uid"]),
                            "age": d.get("yas"), "job": d.get("meslek"),
                            "uses": d.get("kullanim_sayisi"), "last_cls": d.get("son_cls"),
                            "legacy": True})
            return out
    return []


def _new_drivers() -> List[dict]:
    raw = _read_json(DRIVERS_PATH, [])
    return raw if isinstance(raw, list) else []


def _load_drivers() -> List[dict]:
    stats = _read_json(STATS_PATH, {})
    seen, out = set(), []
    for d in _legacy_drivers() + _new_drivers():
        if d["id"] in seen:
            continue
        seen.add(d["id"])
        out.append({**d, "feedbacks": int(stats.get(d["id"], 0))})
    return out


def _save_json(path, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def net():
    return load_network()


def traffic(seed: int, vehicle: str = "tesla_m3", weather: str = "acik"):
    key = (seed, vehicle, weather)
    if key not in _traffic_cache:
        if len(_traffic_cache) > 12:
            _traffic_cache.clear()
        _traffic_cache[key] = make_traffic(net(), seed, VEHICLES[vehicle], WEATHER[weather])
    return _traffic_cache[key]


class PlanRequest(BaseModel):
    origin: str
    destination: str
    cls: Optional[float] = Field(None, ge=0, le=100)
    fatigue: Optional[float] = Field(None, ge=0, le=100)
    cognitive: Optional[float] = Field(None, ge=0, le=100)
    valence: Optional[float] = Field(None, ge=0, le=100)
    soc: float = Field(75.0, ge=1, le=100)
    traffic_seed: int = Field(0, ge=0, le=9)
    vehicle: str = "tesla_m3"
    weather: str = "acik"
    driver_id: str = "U01"


class FeedbackRequest(BaseModel):
    driver_id: str = "U01"
    cls: float
    soc: float
    traffic_density: float
    prev_action: Optional[str] = None
    action: str
    stars: int = Field(..., ge=1, le=5)
    comfort: float
    time_min: float
    min_time_min: float


class FaceRequest(BaseModel):
    frames: List[str] = Field(..., min_length=1, max_length=60)
    cognitive: float = Field(50.0, ge=0, le=100)


class CLSRequest(BaseModel):
    fatigue: float = Field(..., ge=0, le=100)
    cognitive: float = Field(..., ge=0, le=100)
    valence: float = Field(..., ge=0, le=100)


def _resolve(name: str) -> int:
    if name in LOCATIONS:
        return net().nearest_node(*LOCATIONS[name])
    try:
        lat, lon = (float(x) for x in name.split(","))
        return net().nearest_node(lat, lon)
    except Exception:
        raise HTTPException(400, f"Bilinmeyen konum: {name}")


def _simplify(pts, tol_m: float = 15.0):
    """Douglas–Peucker sadeleştirme (yalnızca çizim için; metrikler tam geometriden hesaplanır)."""
    if len(pts) < 3:
        return pts
    a = np.asarray(pts, dtype=float)
    xy = np.column_stack([np.radians(a[:, 1]) * 6371000 * np.cos(np.radians(39.93)), np.radians(a[:, 0]) * 6371000])
    keep = np.zeros(len(a), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(a) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, q = xy[i], xy[j]
        d = q - p
        seg = xy[i + 1:j] - p
        L = np.hypot(*d)
        dist = np.abs(d[0] * seg[:, 1] - d[1] * seg[:, 0]) / L if L > 0 else np.hypot(seg[:, 0], seg[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol_m:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return [tuple(x) for x in a[keep]]


def _route_json(pr: PlannedRoute) -> dict:
    n = net()
    return {
        "method": pr.method,
        "category": pr.category,
        "metrics": {k: (round(v, 1) if k == "n_stop" else round(v, 3)) if isinstance(v, float) else v
                    for k, v in pr.metrics.as_dict().items()},
        "soc_initial": round(pr.soc_initial, 1),
        "soc_final": round(pr.soc_final, 1),
        "charging": None if pr.charging is None else {
            "station": pr.charging.station, "soc_arrival": round(pr.charging.soc_arrival, 1),
            "delta_soc": round(pr.charging.delta_soc, 1), "charge_min": round(pr.charging.charge_min, 1)},
        "geometry": [[round(a, 5), round(b, 5)] for a, b in _simplify(n.path_geometry(pr.path))],
    }


@app.get("/api/health")
def health():
    n = net()
    return {"status": "ok", "version": APP_VERSION, "nodes": n.n_nodes, "edges": n.n_edges,
            "osm_timestamp": n.osm_timestamp}


@app.post("/api/shutdown")
def shutdown(request: Request):
    """Yeni sürüm başlatılırken eski sunucunun portu bırakması için (yalnızca yerel istek)."""
    if request.client is None or request.client.host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(403, "Yalnızca yerel istek")
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return {"ok": True}


class DriverRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)


@app.get("/api/drivers")
def get_drivers():
    return _load_drivers()


@app.post("/api/drivers")
def add_driver(req: DriverRequest):
    import re
    all_ids = {d["id"] for d in _load_drivers()}
    base = re.sub(r"[^a-z0-9]+", "", req.name.lower().translate(str.maketrans("çğıöşü", "cgiosu"))) or "surucu"
    did, k = base, 2
    while did in all_ids:
        did, k = f"{base}{k}", k + 1
    d = {"id": did, "name": req.name.strip()}
    _save_json(DRIVERS_PATH, _new_drivers() + [d])
    return {**d, "feedbacks": 0}


@app.get("/api/vehicles")
def vehicles():
    return [{"id": k, "name": v.name, "battery_kwh": v.C_batt_kwh, "Cd": v.Cd, "mass_kg": v.m, "A": v.A,
             "note": VEHICLE_NOTES.get(k, "")} for k, v in VEHICLES.items()]


@app.get("/api/weather")
def weather():
    return [{"id": k, "name": w.name, "speed": w.speed, "cr": w.cr, "aux_kw": w.aux_kw} for k, w in WEATHER.items()]


@app.get("/api/locations")
def locations():
    return [{"name": k, "lat": v[0], "lon": v[1]} for k, v in LOCATIONS.items()]


@app.get("/api/config")
def config():
    return {
        "vehicle": VEHICLE.__dict__, "nsga": NSGA.__dict__, "qlearning": QL.__dict__,
        "cls_lambdas": CLSP.__dict__, "comfort_weights": COMFORT.__dict__,
        "cls_weight_table": [{"upper": u, "weights": w, "name": nm} for u, w, nm in CLS_WEIGHT_TABLE],
        "traffic": {k: v for k, v in TRAFFIC.__dict__.items()},
    }


@app.post("/api/cls")
def compute_cls(req: CLSRequest):
    c = cognitive_load_score(req.fatigue, req.cognitive, req.valence)
    return {"cls": round(c, 1), "state": cls_state_name(c), "weights": cls_weights(c)}


@app.get("/api/face/status")
def face_status():
    from affectev import face
    return face.status()


@app.post("/api/face/analyze")
def face_analyze(req: FaceRequest):
    """Deneysel yüz okuma: kamera karelerinden Dn. (1)'in F ve V girdilerini önerir.
    C (bilişsel yük) kameradan ölçülmez; istekte gelen değer kullanılır."""
    from affectev import face
    if not face.CV2_AVAILABLE:
        raise HTTPException(503, face.CV2_PROBLEM or "OpenCV kullanılamıyor. OpenCV_Onar.bat dosyasını çalıştırın.")
    try:
        res = face.analyze_batch(req.frames)
    except Exception as e:
        import traceback
        os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
        with open(os.path.join(ROOT, "data", "hata_kaydi.log"), "a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} /api/face/analyze\n{traceback.format_exc()}\n")
        raise HTTPException(500, f"Yüz analizi hatası: {type(e).__name__}: {e}")
    if res.get("ok"):
        c = cognitive_load_score(res["fatigue"], req.cognitive, res["valence_negative"])
        res["cls"] = round(c, 1)
        res["state"] = cls_state_name(c)
    return res


@app.get("/api/charging-stations")
def charging_stations():
    return net().charging


@app.post("/api/plan")
def plan_route(req: PlanRequest):
    if req.cls is not None:
        c = req.cls
    elif None not in (req.fatigue, req.cognitive, req.valence):
        c = cognitive_load_score(req.fatigue, req.cognitive, req.valence)
    else:
        raise HTTPException(400, "cls veya (fatigue, cognitive, valence) gerekli")
    s, t = _resolve(req.origin), _resolve(req.destination)
    if s == t:
        raise HTTPException(400, "Başlangıç ve varış aynı düğüme düşüyor.")
    if req.vehicle not in VEHICLES or req.weather not in WEATHER:
        raise HTTPException(400, "Bilinmeyen araç veya hava durumu")
    tr = traffic(req.traffic_seed, req.vehicle, req.weather)
    with _lock:
        res = plan(net(), s, t, c, req.soc, req.traffic_seed, tr=tr)
    front = res.nsga.front
    front_pts = [{"energy": round(p.obj[0], 3), "time": round(p.obj[1], 2), "comfort": round(100 - p.obj[2], 2),
                  "distance": round(p.metrics.distance_km, 2)} for p in front]
    dom = [{"energy": round(p.obj[0], 3), "time": round(p.obj[1], 2)} for p in res.nsga.population if p.rank > 0]
    ref_route = res.routes["Dengeli"]
    state = encode_state(c, req.soc, ref_route.metrics.traffic_density, None)
    q = agent(req.driver_id).Q[state]
    q_best = ACTIONS[int(np.argmax(q))] if np.any(q != 0) else None
    opts = display_options(net(), front, res.weights)
    opt_routes = {}
    for cat, ind in opts["individuals"].items():
        pr = apply_soc(net(), tr, res._opt, cat, list(ind.path), req.soc, res.weights, cat)
        opt_routes[cat] = {**_route_json(pr), "score": round(opts["scores"][cat], 4)}
    return {
        "options": opt_routes, "recommended": opts["recommended"], "overlap": opts["overlap"],
        "cls": round(c, 1), "state": cls_state_name(c), "weights": res.weights,
        "traffic_seed": req.traffic_seed,
        "front": front_pts, "dominated": dom, "evaluations": res.nsga.evaluations,
        "categories": {k: int(v) for k, v in res.categories.items()},
        "selected_index": res.selected_index,
        "routes": {k: _route_json(v) for k, v in res.routes.items()},
        "qlearning": {"state": {"cls_level": state[0], "soc_level": state[1], "traffic_level": state[2]},
                      "q_values": {a: round(float(v), 3) for a, v in zip(ACTIONS, q)},
                      "recommendation": q_best},
    }


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    if req.action not in ACTIONS:
        raise HTTPException(400, f"Eylem şunlardan biri olmalı: {ACTIONS}")
    prev = ACTIONS.index(req.prev_action) if req.prev_action in ACTIONS else None
    s = encode_state(req.cls, req.soc, req.traffic_density, prev)
    a = ACTIONS.index(req.action)
    fb = (req.stars - 3) / 2.0                        # 1..5 yıldız → [−1, 1]
    delay = (req.time_min - req.min_time_min) / req.min_time_min if req.min_time_min > 0 else 0.0
    r = reward(fb, req.comfort, delay)                # Dn. (8)
    s_next = encode_state(req.cls, req.soc, req.traffic_density, a)
    with _lock:
        ag = agent(req.driver_id)
        ag.update(s, a, r, s_next)                    # Dn. (7)
        ag.save(os.path.join(Q_DIR, f"{req.driver_id}.npy"))
        stats = _read_json(STATS_PATH, {})
        stats[req.driver_id] = int(stats.get(req.driver_id, 0)) + 1
        _save_json(STATS_PATH, stats)
    return {"reward": round(r, 3), "feedback": fb, "delay": round(delay, 4),
            "q_values": {k: round(float(v), 3) for k, v in zip(ACTIONS, ag.Q[s])}}


@app.post("/api/qtable/reset")
def reset_q():
    with _lock:
        for did, ag in _agents.items():
            ag.Q[:] = 0
            ag.save(os.path.join(Q_DIR, f"{did}.npy"))
    return {"ok": True}


@app.get("/api/experiments")
def experiments():
    out = {"available": os.path.exists(os.path.join(RESULTS, "summary.json"))}
    for name in ("summary.json", "case_study.json", "qlearning_summary.json"):
        p = os.path.join(RESULTS, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                out[name.replace(".json", "")] = json.load(f)
    out["figures"] = [f for f in ("sekil1_pareto.png", "sekil2_qlearning.png", "sekil3_harita.png")
                      if os.path.exists(os.path.join(RESULTS, f))]
    return out


if os.path.isdir(RESULTS):
    app.mount("/results", StaticFiles(directory=RESULTS), name="results")

if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        p = os.path.join(DIST, full_path)
        if full_path and os.path.isfile(p):
            return FileResponse(p)
        return FileResponse(os.path.join(DIST, "index.html"))
else:
    @app.get("/")
    def no_ui():
        return JSONResponse({"message": "Arayüz derlenmemiş. frontend klasöründe 'npm install && npm run build' çalıştırın."})
