"""
AffectEV FastAPI Backend - Affect-Aware True Route Diversity
============================================================
FIX v3: Each route type uses different Ankara waypoints -> OSRM draws genuinely different roads.
ASI (emotional state) determines which districts to pass through.
Short distance (<3 km): Single route + warning. Long distance: 3 different physical paths.
"""

import os, sys, base64, random, math
from datetime import datetime
import numpy as np
import cv2
import requests
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dynamaffect_integration import DynamAffectRoutePlanner, create_sample_graph
    from dynamaffect_core import AffectAwareEnergyModel
    DYNAMAFFECT_READY = True
except Exception as e:
    print(f"[WARN] DynamAffect could not be loaded: {e}")
    DYNAMAFFECT_READY = False

try:
    from emotion_engine import detect_smile_and_eyes
    EMOTION_READY = True
except Exception as e:
    print(f"[WARN] Emotion engine could not be loaded: {e}")
    EMOTION_READY = False

try:
    from dynamaffect_qlearning import (
        DynamAffectPersonalization,
        QAction,
        QState,
        RewardSignal,
    )
    QLEARNING_READY = True
except Exception as e:
    print(f"[WARN] Q-learning could not be loaded: {e}")
    QLEARNING_READY = False

# ── Ankara Coordinates ───────────────────────────────────────────────────────
ANKARA = {
    'Kizilay':      (39.9208, 32.8541), 'Ulus':         (39.9250, 32.8600),
    'Hacettepe':    (39.8950, 32.8650), 'TBMM':         (39.9167, 32.8500),
    'Anitkabir':    (39.9256, 32.8373), 'Cankaya':      (39.9036, 32.8597),
    'Kecioren':     (39.9700, 32.8650), 'Mamak':        (39.9300, 32.7950),
    'Yenimahalle':  (39.9450, 32.8200), 'Altindag':     (39.9500, 32.8667),
    'Etimesgut':    (39.9500, 32.6833), 'Ayranci':       (39.9000, 32.8500),
    'Kavaklidere':  (39.9050, 32.8600), 'Kucukesat':    (39.9000, 32.8700),
    'Tunali Hilmi': (39.9050, 32.8550), 'Dikmen':       (39.8833, 32.8833),
    'Balgat':       (39.8833, 32.8167), 'Soguttozu':    (39.9000, 32.8000),
    'Cayyolu':      (39.8667, 32.7333), 'Umitkoy':      (39.8667, 32.7000),
    'Yasamkent':    (39.8583, 32.6833), 'Konutkent':    (39.8750, 32.6667),
    'Bilkent':      (39.8667, 32.7500), 'ODTU':         (39.8917, 32.7750),
    'Etlik':        (39.9583, 32.8833), 'Sentepe':      (39.9600, 32.8417),
    'Batikent':     (39.9667, 32.7333), 'Ostim':        (39.9667, 32.8333),
    'Sincan':       (39.8700, 32.7450), 'Golbasi':      (39.7900, 32.8300),
    'Polatli':      (39.5900, 32.7800), 'Kazan':        (39.9600, 32.6800),
    'Pursaklar':    (40.0333, 33.0000), 'Esenboga':     (40.1167, 32.9833),
    # Original keys (for backward compat)
    'Kızılay':      (39.9208, 32.8541), 'Çankaya':      (39.9036, 32.8597),
    'Keçiören':     (39.9700, 32.8650), 'Altındağ':     (39.9500, 32.8667),
    'Ayrancı':      (39.9000, 32.8500), 'Kavaklıdere':  (39.9050, 32.8600),
    'Küçükesat':    (39.9000, 32.8700), 'Tunalı Hilmi': (39.9050, 32.8550),
    'Söğütözü':     (39.9000, 32.8000), 'Çayyolu':      (39.8667, 32.7333),
    'Ümitköy':      (39.8667, 32.7000), 'Yaşamkent':    (39.8583, 32.6833),
    'Gölbaşı':      (39.7900, 32.8300), 'Polatlı':      (39.5900, 32.7800),
    'Şentepe':      (39.9600, 32.8417), 'Batıkent':     (39.9667, 32.7333),
    'Esenboğa':     (40.1167, 32.9833),
}

app = FastAPI(title="AffectEV API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

_planner: Optional[DynamAffectRoutePlanner] = None
_personalization: Optional[DynamAffectPersonalization] = None

def get_planner(driver_id="U001"):
    global _planner
    if _planner is None and DYNAMAFFECT_READY:
        _planner = DynamAffectRoutePlanner(graph=create_sample_graph(ANKARA), driver_id=driver_id)
    elif _planner:
        _planner.driver_id = driver_id
    return _planner


def get_personalization():
    global _personalization
    if _personalization is None and QLEARNING_READY:
        storage = os.path.join(os.path.dirname(os.path.abspath(__file__)), "driver_q_networks")
        _personalization = DynamAffectPersonalization(storage_dir=storage)
    return _personalization


# ── Pydantic Schemas ──────────────────────────────────────────────────────────
class PlanRouteRequest(BaseModel):
    origin: str
    destination: str
    battery: float
    weather: str
    traffic: str
    pupil_dilation: float = 35.0
    steering_variance: float = 20.0
    eda_level: float = 0.3
    smile_ratio: float = 0.2
    eyes_tired: bool = False
    driver_id: str = "U001"
    affect_state: str = ""   # Camera detection: Stressed / Fatigued / Alert / Relaxed
    emotion: str = ""        # Raw emotion: fear / sadness / happiness / neutral etc.

class AnalyzeEmotionRequest(BaseModel):
    frame_b64: str

class FeedbackRequest(BaseModel):
    origin: str
    destination: str
    selected_route: int
    rating: int
    feedback: str = ""
    asi: float = 0.0
    driver_id: str = "U001"

class DriverProfileRequest(BaseModel):
    isim: str
    yas: int
    stres_egilimi: float
    yorgunluk_esigi: int


# ── Core Helpers ──────────────────────────────────────────────────────────────
def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_live_traffic(lat: float, lng: float) -> str:
    """
    Real-time traffic status fetched from TomTom API.
    If API_KEY is empty, returns a random or time-based simulation.
    """
    TOMTOM_API_KEY = "UtBPOqj1pisKuElRKGV203Rs4xwiDXJP"  # Enter TomTom Traffic API Key here
    
    if TOMTOM_API_KEY:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={lat},{lng}&key={TOMTOM_API_KEY}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("flowSegmentData", {})
                current = data.get("currentSpeed", 50)
                free = data.get("freeFlowSpeed", 50)
                ratio = current / free if free > 0 else 1.0
                if ratio > 0.8: return "Light"
                elif ratio > 0.4: return "Moderate"
                else: return "Heavy"
        except:
            pass
            
    # No API key: realistic simulation (e.g., time-based or random)
    import random
    return random.choices(["Light", "Moderate", "Heavy"], weights=[0.3, 0.5, 0.2])[0]



# Different "bridge" districts per route type
# OSRM uses these points as waypoints on the real road network → draws different roads
_HUB_SETS = {
    "COMFORT":  ["Ayrancı","Tunalı Hilmi","Küçükesat","Balgat","Söğütözü","Bilkent","ODTÜ",
                 "Ayrani","Tunali Hilmi","Kucukesat","Balgat","Soguttozu","Bilkent","ODTU"],
    "BALANCED": ["Kızılay","Çankaya","Ulus","Yenimahalle","Ostim","Keçiören",
                 "Kizilay","Cankaya","Ulus","Yenimahalle","Ostim","Kecioren"],
    "EFFICIENT":["Ulus","Altındağ","Etlik","Ostim","Batıkent","Sincan","Etimesgut",
                 "Ulus","Altindag","Etlik","Ostim","Batikent","Sincan","Etimesgut"],
}


def _pick_hub(origin: str, destination: str, route_type: str, dist_km: float) -> Optional[str]:
    """
    Select a district waypoint between origin and destination appropriate for the route type.
    Returns None if distance is less than 3 km (single route is sufficient).
    """
    if dist_km < 3.0:
        return None

    candidates = [h for h in _HUB_SETS.get(route_type, [])
                  if h != origin and h != destination and h in ANKARA]
    if not candidates:
        return None

    o = ANKARA[origin]
    d = ANKARA[destination]

    def score(hub: str) -> float:
        hc = ANKARA[hub]
        return _haversine_km(o[0], o[1], hc[0], hc[1]) + _haversine_km(hc[0], hc[1], d[0], d[1])

    ranked = sorted(candidates, key=score)

    if route_type == "EFFICIENT":
        # Efficient: Most direct path (waypoint with least deviation)
        idx = 0
    elif route_type == "BALANCED":
        # Balanced: Slight deviation
        idx = max(0, len(ranked) // 4)
    else:  # COMFORT
        # Comfort: Quieter urban districts, slightly more deviation
        idx = max(0, len(ranked) // 2)

    return ranked[idx]


def _osrm_route(names: list) -> Optional[dict]:
    """Fetch real road geometry from OSRM."""
    pts = []
    for n in names:
        if isinstance(n, dict):
            pts.append(f"{n['lng']},{n['lat']}")
        else:
            c = ANKARA.get(n)
            if c:
                pts.append(f"{c[1]},{c[0]}")
    if len(pts) < 2:
        return None
    url = "http://router.project-osrm.org/route/v1/driving/" + ";".join(pts)
    url += "?geometries=geojson&overview=full&steps=false"
    try:
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                r = data["routes"][0]
                coords = [{"lat": c[1], "lng": c[0], "name": ""}
                          for c in r["geometry"]["coordinates"]]
                return {
                    "coords": coords,
                    "distance_m": r["distance"],
                    "duration_s": r["duration"],
                }
    except Exception as e:
        print(f"[OSRM] {e}")
    return None


def _convergent(routes: list) -> bool:
    """Returns True if route midpoints are very close to each other."""
    def mid(coords):
        if not coords: return None
        return (sum(c["lat"] for c in coords)/len(coords),
                sum(c["lng"] for c in coords)/len(coords))
    mps = [mid(r.get("coords", [])) for r in routes[:3]]
    mps = [m for m in mps if m]
    if len(mps) < 2: return False
    for i in range(len(mps)):
        for j in range(i+1, len(mps)):
            if _haversine_km(mps[i][0],mps[i][1],mps[j][0],mps[j][1]) * 1000 > 200:
                return False
    return True


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status":"ok","dynamaffect":DYNAMAFFECT_READY,"emotion_engine":EMOTION_READY,"version":"3.0"}

import json
@app.get("/api/drivers")
def get_drivers():
    try:
        with open("surucucler.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "ok", "drivers": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/drivers")
def add_driver(req: DriverProfileRequest):
    try:
        with open("surucucler.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        new_uid = f"U{len(data)+1:02d}"
        new_driver = {
            "uid": new_uid,
            "isim": req.isim,
            "yas": req.yas,
            "stres_egilimi": req.stres_egilimi,
            "yorgunluk_esigi": req.yorgunluk_esigi,
            "meslek": "New Driver",
            "gun_ici_tip": "morning",
            "tercih_hizi": 70,
            "sarj_konfor": 30,
            "km_yil": 15000,
            "dominant_duygu": "neutral",
            "biyometrik": {
                "kalp_hizi_baz": 75,
                "goz_acikligi_baz": 0.30,
                "blink_baz_dk": 15,
                "au4_baz": 0.1,
                "au12_baz": 0.2
            },
            "suruc_gecmis": []
        }
        data.append(new_driver)
        with open("surucucler.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "driver": new_driver}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/plan-route")
def plan_route(req: PlanRouteRequest):
    """
    Main route planning endpoint.
    On error, returns simulation data instead of 400 to avoid breaking the UI flow.
    """
    # Lokasyon kontrolü
    if req.origin not in ANKARA or req.destination not in ANKARA:
        print(f"[WARN] Invalid location: {req.origin} -> {req.destination}. Switching to simulation.")
        return _simulate_route(req)
    
    if req.origin == req.destination:
        return _simulate_route(req)

    # ── Live Traffic and ASI Calculation ───────────────────────────────────────────
    # Fetch real/simulated live traffic instead of the traffic from the UI
    o_c = ANKARA[req.origin]
    live_traffic_status = get_live_traffic(o_c[0], o_c[1])
    
    weather_sev   = {"Sunny":0.1,"Cloudy":0.2,"Rainy":0.5,"Snowy":0.8}.get(req.weather, 0.1)
    traffic_dens  = {"Light":0.2,"Moderate":0.5,"Heavy":0.8}.get(live_traffic_status, 0.5)

    asi = 0.0
    battery_constraints = {
        "soc_min_percent": 20, "soc_max_percent": 80,
        "current_soc_percent": req.battery,
        "usable_energy_kwh": round(75 * max(0, req.battery - 20) / 100, 1),
    }
    recommended_breaks = []

    planner = get_planner(req.driver_id)
    if planner:
        try:
            planner.graph = create_sample_graph(ANKARA)
            sensor_data = {
                "pupil_dilation": req.pupil_dilation,
                "steering_variance": req.steering_variance,
                "traffic_density": traffic_dens,
                "weather_severity": weather_sev,
                "au12": req.smile_ratio, "au15": 0.05, "au4": 0.05,
                "eda_level": req.eda_level, "lane_clarity": 0.8,
                "weather": req.weather.lower(),
            }
            sol = planner.plan_route(req.origin, req.destination, sensor_data, current_soc=req.battery)
            if sol and hasattr(sol, "asi_current"):
                asi = float(sol.asi_current)
                battery_constraints = {
                    k: float(v) if isinstance(v, (int, float, np.number)) else v
                    for k, v in sol.battery_constraints.items()
                }
                recommended_breaks = [
                    {k: float(v) if isinstance(v, np.number) else v for k, v in b.items()}
                    for b in (sol.recommended_breaks or [])
                ]
        except Exception as e:
            print(f"[WARN] D-NSGA-II: {e}")
            asi = round(random.uniform(-0.4, 0.4), 3)
    else:
        asi = round(random.uniform(-0.4, 0.4), 3)

    # ── Route recommendation: affect_state is primary source, ASI is fallback ────
    # Thesis logic: Stressed/Fatigued → Comfort, Happy/Alert → Efficient, Normal → Balanced
    # ASI formula and D-NSGA-II remain unchanged; only rec_id is corrected here.
    affect = req.affect_state.strip() if req.affect_state else ""
    emotion_raw = req.emotion.strip().lower() if req.emotion else ""

    if affect in ("Stressed", "Fatigued") or emotion_raw in ("fear", "anger", "sadness", "disgust"):
        rec_id = 0          # Comfort Route
        stress_category = "Stressed/Fatigued"
    elif affect == "Alert" or emotion_raw in ("happiness", "surprise"):
        rec_id = 2          # Efficient Route
        stress_category = "Alert/Safe"
    else:
        # Fallback: ASI-based (original thesis logic)
        rec_id = 0 if asi < -0.1 else (2 if asi > 0.1 else 1)
        stress_category = ("Stressed/Fatigued" if asi < -0.1
                           else "Alert/Safe" if asi > 0.1
                           else "Relaxed/Normal")

    # ── Mesafe ────────────────────────────────────────────────────
    o_c = ANKARA[req.origin]
    d_c = ANKARA[req.destination]
    dist_km = _haversine_km(o_c[0], o_c[1], d_c[0], d_c[1])
    is_short = dist_km < 3.0

    # ── If battery is low, find nearest charging station (shared for all routes) ─
    # Thesis SoC constraint logic: SoC_initial - E_segment <= SoC_threshold
    CHARGE_THRESHOLD = 30  # Charging required below 30%
    best_charge_station = None
    if req.battery < CHARGE_THRESHOLD:
        fallback_stations = [
            {"name": "ZES - Armada AVM",  "lat": 39.912, "lng": 32.812, "status": "AVAILABLE"},
            {"name": "Esarj - Kizilay",   "lat": 39.920, "lng": 32.854, "status": "FULL"},
            {"name": "ZES - Bilkent",     "lat": 39.867, "lng": 32.750, "status": "BUSY"},
            {"name": "Voltrun - Cankaya", "lat": 39.903, "lng": 32.860, "status": "AVAILABLE"},
            {"name": "PO - Batikent",     "lat": 39.967, "lng": 32.733, "status": "AVAILABLE"},
            {"name": "ZES - Kecioren",    "lat": 39.970, "lng": 32.865, "status": "AVAILABLE"},
            {"name": "Esarj - Ostim",     "lat": 39.967, "lng": 32.833, "status": "AVAILABLE"},
            {"name": "ZES - ODTU",        "lat": 39.892, "lng": 32.775, "status": "AVAILABLE"},
        ]
        best_score = float("inf")
        for st in fallback_stations:
            # Nearest station on route: start->station + station->destination
            seq = (_haversine_km(o_c[0], o_c[1], st["lat"], st["lng"]) +
                   _haversine_km(st["lat"], st["lng"], d_c[0], d_c[1]))
            if seq < best_score:
                best_score = seq
                best_charge_station = st
    # (type, name, desc, color, dist_factor, kwh_per_km, base_complexity)
    DEFS = [
        ("COMFORT",  "Comfort Route",  "Calm and relaxed route — stress-free drive",  "#22c55e", 1.15, 0.15, 25),
        ("BALANCED", "Balanced Route", "Balanced speed and efficiency",                "#3b82f6", 1.00, 0.18, 50),
        ("EFFICIENT","Efficient Route","Fastest route — direct arterials",            "#f97316", 0.88, 0.21, 72),
    ]

    routes = []
    for idx, (rtype, rname, rdesc, rcolor, dfactor, kwh_km, base_cx) in enumerate(DEFS):
        hub = _pick_hub(req.origin, req.destination, rtype, dist_km)
        charge_stops = 0

        # If battery is low: add the nearest pre-calculated charging station to the route
        if best_charge_station:
            waypoints = [req.origin, best_charge_station, req.destination]
            charge_stops = 1
        else:
            waypoints = [req.origin] + ([hub] if hub else []) + [req.destination]


        osrm = _osrm_route(waypoints)

        if osrm:
            real_dist  = round(osrm["distance_m"] / 1000, 1)
            real_time  = max(1, round(osrm["duration_s"] / 60))
            
            # Advanced Energy Model (AffectAwareEnergyModel) Usage
            # If charging stop exists, all 3 routes follow the same path.
            # The scientific explanation for different kWh is 'Driving Dynamics' (Speed, Acceleration).
            
            # Speed simulation: Comfort (slow), Balanced (medium), Efficient (fast/aggressive)
            speed_multiplier = [0.9, 1.0, 1.15][idx] 
            avg_speed = ((real_dist / (real_time / 60)) if real_time > 0 else 50) * speed_multiplier
            
            # Elevation simulation (same elevation for same road, must not be random)
            elevation_diff = (real_dist * 0.5) + (base_cx * 0.2) 
            
            if DYNAMAFFECT_READY:
                energy_model = AffectAwareEnergyModel()
                real_kwh = round(energy_model.calculate_energy(real_dist, elevation_diff, avg_speed, asi), 1)
            else:
                real_kwh = round(real_dist * kwh_km, 1)
                
            # ── COORDINATE OFFSET (prevents route lines from overlapping) ──
            # Shift each route type by 0.0001 degrees (~10m) left or right
            offset_lat = (idx - 1) * 0.00015
            offset_lng = (idx - 1) * 0.00015
            coords = [{"lat": c["lat"] + offset_lat, "lng": c["lng"] + offset_lng, "name": ""}
                      for c in osrm["coords"]]
        else:
            # No OSRM access: interpolation diverging in different directions
            real_dist  = round(dist_km * dfactor, 1)
            speeds = [45, 60, 75]
            real_time  = max(1, round(real_dist / speeds[idx] * 60))
            
            # Advanced Energy Model (AffectAwareEnergyModel) Usage
            avg_speed = speeds[idx]
            elevation_diff = random.uniform(-50, 50) + (base_cx / 2)
            if DYNAMAFFECT_READY:
                energy_model = AffectAwareEnergyModel()
                real_kwh = round(energy_model.calculate_energy(real_dist, elevation_diff, avg_speed, asi), 1)
            else:
                real_kwh = round(real_dist * kwh_km, 1)
                
            offsets    = [(0.010, -0.008), (0.0, 0.0), (-0.009, 0.009)]
            on, oe     = offsets[idx]
            mid_lat    = (o_c[0] + d_c[0]) / 2 + on
            mid_lng    = (o_c[1] + d_c[1]) / 2 + oe
            hub_name   = hub or "Midpoint"
            coords     = [
                {"lat": o_c[0], "lng": o_c[1], "name": req.origin},
                {"lat": round(mid_lat, 6), "lng": round(mid_lng, 6), "name": hub_name},
                {"lat": d_c[0], "lng": d_c[1], "name": req.destination},
            ]

        # If charging stop exists, add it explicitly to description for UI display
        final_desc = rdesc
        if charge_stops > 0 and best_charge_station:
            final_desc += f" (Stop: {best_charge_station['name']})"

        entry = {
            "id": idx,
            "type": rtype,
            "name": rname,
            "description": final_desc,
            "distance_km": real_dist,
            "time_min": real_time,
            "energy_kwh": real_kwh,
            "complexity_score": round(base_cx + random.uniform(-4, 4), 1),
            "charge_stops": charge_stops,
            "coords": coords,
            "color": rcolor,
        }
        if idx == rec_id:
            entry["recommended"] = True

        routes.append(entry)

    # Comfort her zaman en uzun, Efficient en kisa olmali
    if len(routes) == 3:
        max_dist = max(r["distance_km"] for r in routes)
        routes[0]["distance_km"] = round(max(routes[0]["distance_km"], max_dist), 1)  # COMFORT en uzun
        routes[2]["distance_km"] = round(min(routes[2]["distance_km"], routes[1]["distance_km"]), 1)  # EFFICIENT en kisa
        # Sureleri de buna gore guncelle (kaba tahmim: km / ort_hiz * 60)
        speeds = [45, 60, 75]
        for i, r in enumerate(routes):
            r["time_min"] = max(1, round(r["distance_km"] / speeds[i] * 60))

    # For short distances return only 1 route
    if is_short:
        routes = routes[:1]

    is_conv = _convergent(routes)

    if is_short:
        note = (f"For this short {round(dist_km,1)} km distance, all 3 routes use the same physical path. "
                f"Only one route available.")
    elif is_conv:
        note = ("All 3 routes share the same path; metric differences are D-NSGA-II analysis results.")
    else:
        note = "Each route offers a different physical path through different districts."

    return {
        "asi": round(asi, 3),
        "stress_category": stress_category,
        "battery_constraints": battery_constraints,
        "routes": routes,
        "recommended_breaks": recommended_breaks,
        "charging_points": [best_charge_station] if best_charge_station else [],
        "route_diversity_info": {
            "physically_identical": is_conv or is_short,
            "distance_km": round(dist_km, 1),
            "single_alternative_warning": is_short,
            "note": note,
        },
    }


@app.post("/api/analyze-emotion")
def analyze_emotion(req: AnalyzeEmotionRequest):
    try:
        img_bytes = base64.b64decode(req.frame_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Frame could not be decoded")
    except Exception as e:
        raise HTTPException(400, f"Invalid frame: {e}")

    if EMOTION_READY:
        try:
            smile, eyes_open, confidence, debug = detect_smile_and_eyes(frame)
            return {
                "smile_detected": bool(smile), "eyes_open": bool(eyes_open),
                "confidence": float(round(confidence, 3)),
                "emotion": str(debug.get("emotion","unknown")),
                "avg_ear": float(debug.get("avg_ear", 0.0)),
                "source": str(debug.get("source","unknown")),
            }
        except Exception as e:
            print(f"[ERROR] emotion: {e}")

    return {
        "smile_detected": random.random() > 0.5,
        "eyes_open": random.random() > 0.3,
        "confidence": round(random.uniform(0.5, 0.9), 3),
        "emotion": random.choice(["happiness","neutral","sadness"]),
        "avg_ear": round(random.uniform(0.18, 0.35), 3),
        "source": "simulation",
    }


@app.get("/api/charging-stations")
def charging_stations():
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        q = '[out:json];node["amenity"="charging_station"](39.75,32.55,40.15,33.05);out body;'
        headers = {"User-Agent": "AffectEV-App/3.0"}
        resp = requests.get(overpass_url, params={"data": q}, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for el in data.get("elements", []):
                tags = el.get("tags", {})
                name = tags.get("name", tags.get("operator","EV Station"))
                lat = float(el["lat"])
                lng = float(el["lon"])
                
                status = "Available"
                
                result.append({
                    "name": name,
                    "lat": lat, "lng": lng,
                    "power_kw": int(tags.get("capacity", 50)) if str(tags.get("capacity")).isdigit() else 50,
                    "status": status,
                })
            if result:
                return {"stations": result, "count": len(result)}
    except Exception as e:
        print(f"[OVERPASS] {e}")

    fallback = [
        {"name":"ZES - Armada AVM",     "lat":39.912,"lng":32.812,"power_kw":120,"status":"Available"},
        {"name":"Esarj - Kizilay",      "lat":39.920,"lng":32.854,"power_kw":50, "status":"Available"},
        {"name":"ZES - Bilkent",        "lat":39.867,"lng":32.750,"power_kw":150,"status":"Available"},
        {"name":"Voltrun - Cankaya",    "lat":39.903,"lng":32.860,"power_kw":22, "status":"Available"},
        {"name":"PO - Batikent",        "lat":39.967,"lng":32.733,"power_kw":50, "status":"Available"},
        {"name":"ZES - Kecioren",       "lat":39.970,"lng":32.865,"power_kw":120,"status":"Available"},
        {"name":"Esarj - Ostim",        "lat":39.967,"lng":32.833,"power_kw":50, "status":"Available"},
        {"name":"ZES - ODTU",           "lat":39.892,"lng":32.775,"power_kw":150,"status":"Available"},
    ]
    return {"stations": fallback, "count": len(fallback)}


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        types = ["COMFORT","BALANCED","EFFICIENT"]
        route_type = types[req.selected_route] if 0 <= req.selected_route < len(types) else "BALANCED"
        action_map = {
            "COMFORT": QAction.SCENIC if QLEARNING_READY else "scenic_route",
            "BALANCED": QAction.BALANCED if QLEARNING_READY else "balanced_route",
            "EFFICIENT": QAction.FAST if QLEARNING_READY else "fast_route",
        }
        action = action_map[route_type]

        q_learning = {
            "updated": False,
            "reward": 0.0,
            "q_value": None,
            "states_explored": 0,
            "episodes": 0,
        }

        personalization = get_personalization()
        if personalization:
            state = QState(
                origin=req.origin,
                destination=req.destination,
                asi=float(req.asi),
                time_of_day=datetime.now().hour,
                weather="unknown",
                route_type="route_choice",
            )
            reward_signal = RewardSignal(
                completed=True,
                early_exit=False,
                driver_feedback=float(req.rating),
                harsh_accel=False,
                traffic_incident=False,
                time_efficiency=1.0,
            )
            personalization.learn_from_episode(
                driver_id=req.driver_id,
                state=state,
                action=action,
                reward_signal=reward_signal,
            )
            personalization.save_all()

            network = personalization.get_or_create_network(req.driver_id)
            state_key = state.to_key()
            stats = network.get_statistics()
            q_learning = {
                "updated": True,
                "reward": reward_signal.calculate_reward(),
                "q_value": network.Q[state_key][action],
                "states_explored": stats["states_explored"],
                "episodes": stats["episodes"],
            }

        print(
            f"[Q-LEARNING] Driver {req.driver_id}: Route {route_type}, "
            f"Rating {req.rating}, Updated {q_learning['updated']}"
        )
        return {
            "status": "ok",
            "message": f"Thank you! Feedback saved to {req.driver_id} Q-learning profile.",
            "selected_route_type": route_type,
            "rating": req.rating,
            "driver_id": req.driver_id,
            "q_learning": q_learning,
        }
    except Exception as e:
        print(f"[Q-LEARNING ERROR] {e}")
        return {"status": "ok", "message": "Feedback received.", "q_learning": {"updated": False}}


@app.get("/api/locations")
def locations():
    # Return original Turkish-character location names
    orig = [
        'Kızılay','Ulus','Hacettepe','TBMM','Anıtkabir','Çankaya','Keçiören','Mamak',
        'Yenimahalle','Altındağ','Etimesgut','Ayrancı','Kavaklıdere','Küçükesat',
        'Tunalı Hilmi','Dikmen','Balgat','Söğütözü','Çayyolu','Ümitköy','Yaşamkent',
        'Konutkent','Bilkent','ODTÜ','Etlik','Şentepe','Batıkent','Ostim','Sincan',
        'Gölbaşı','Polatlı','Kazan','Pursaklar','Esenboğa',
    ]
    return {"locations": sorted(orig)}


def _simulate_route(req: PlanRouteRequest):
    """
    Generates realistic routes on error.
    """
    o = ANKARA.get(req.origin, (39.9208, 32.8541))
    d = ANKARA.get(req.destination, (39.9036, 32.8597))
    dist = _haversine_km(o[0], o[1], d[0], d[1])
    
    routes = []
    types = [
        ("COMFORT",  "Comfort Route",  "Calm and relaxed route", "#22c55e", 1.15, 0.15),
        ("BALANCED", "Balanced Route", "Balanced speed and efficiency", "#3b82f6", 1.00, 0.18),
        ("EFFICIENT","Efficient Route","Fastest, direct route", "#f97316", 0.92, 0.21),
    ]
    
    for i, (rt, rn, rd, rc, df, kwh) in enumerate(types):
        rdist = round(dist * df, 1)
        rtime = max(1, round(rdist / 50 * 60))
        routes.append({
            "id": i, "type": rt, "name": rn, "description": rd,
            "distance_km": rdist, "time_min": rtime, "energy_kwh": round(rdist * kwh, 1),
            "complexity_score": 50, "charge_stops": 0, "color": rc,
            "coords": [{"lat": o[0], "lng": o[1]}, {"lat": d[0], "lng": d[1]}]
        })
    
    return {
        "asi": 0.0, "stress_category": "Relaxed", "routes": routes,
        "battery_constraints": {"soc_min_percent": 20, "current_soc_percent": req.battery},
        "route_diversity_info": {"note": "Simulation mode active."}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
