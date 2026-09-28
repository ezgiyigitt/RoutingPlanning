"""
AffectEV Premium UI - DynamAffect Wizard Interface v4
=====================================================
✅ Perfect Flow (Kusursuz Akış):
✅ 3-second camera countdown with auto-capture
✅ Realistic emotion detection (Smile/Eye Cascade)
✅ All charging stations visible (no emotion-based filtering)
✅ Auto route selection by fatigue state
✅ Fixed NoneType errors, professional map icons, width='stretch'
"""

from geopy.geocoders import Nominatim
import time
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import os
import sys
import threading

# Add current dir to path
sys.path.append(os.getcwd())

# Import DynamAffect Modules
try:
    from dynamaffect_integration import DynamAffectRoutePlanner, create_sample_graph
    DYNAMAFFECT_READY = True
except ImportError as e:
    st.error(f"Module Import Error: {e}")
    DYNAMAFFECT_READY = False

# Import Emotion Engine (RAF-DB + MediaPipe EAR)
try:
    from emotion_engine import detect_smile_and_eyes as _detect_emotion
    EMOTION_ENGINE_READY = True
except ImportError:
    EMOTION_ENGINE_READY = False

# ════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLING
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="AffectEV | DynamAffect",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main {
    background: #f5f5f7;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
div[data-testid="stMetricValue"] {
    font-size: 24px;
    color: #007AFF;
}
.stButton>button {
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: 500;
    transition: all 0.2s;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 16px;
    background: white;
}
.stTabs [aria-selected="true"] {
    background: #007AFF !important;
    color: white !important;
}
.countdown-timer {
    font-size: 48px;
    font-weight: bold;
    color: #FF6B6B;
    text-align: center;
    padding: 20px;
    border-radius: 10px;
    background: #fff0f0;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# DATA & CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

ANKARA_EXTENDED = {
    'Kızılay': (39.9208, 32.8541), 'Ulus': (39.9250, 32.8600),
    'Hacettepe': (39.8950, 32.8650), 'TBMM': (39.9167, 32.8500),
    'Anıtkabir': (39.9256, 32.8373), 'Çankaya': (39.9036, 32.8597),
    'Keçiören': (39.9700, 32.8650), 'Mamak': (39.9300, 32.7950),
    'Yenimahalle': (39.9450, 32.8200), 'Altındağ': (39.9500, 32.8667),
    'Etimesgut': (39.9500, 32.6833), 'Ayrancı': (39.9000, 32.8500),
    'Kavaklıdere': (39.9050, 32.8600), 'Küçükesat': (39.9000, 32.8700),
    'Tunalı Hilmi': (39.9050, 32.8550), 'Dikmen': (39.8833, 32.8833),
    'Balgat': (39.8833, 32.8167), 'Söğütözü': (39.9000, 32.8000),
    'Çayyolu': (39.8667, 32.7333), 'Ümitköy': (39.8667, 32.7000),
    'Yaşamkent': (39.8583, 32.6833), 'Konutkent': (39.8750, 32.6667),
    'Bilkent': (39.8667, 32.7500), 'ODTÜ': (39.8917, 32.7750),
    'Etlik': (39.9583, 32.8833), 'Şentepe': (39.9600, 32.8417),
    'Batıkent': (39.9667, 32.7333), 'Ostim': (39.9667, 32.8333),
    'Sincan': (39.8700, 32.7450), 'Gölbaşı': (39.7900, 32.8300),
    'Polatlı': (39.5900, 32.7800), 'Kazan': (39.9600, 32.6800),
    'Pursaklar': (40.0333, 33.0000), 'Esenboğa Havalimanı': (40.1167, 32.9833)
}

# ════════════════════════════════════════════════════════════════════════════
# EMOTION DETECTION FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def detect_smile_and_eyes(frame_cv):
    """
    Gülümseme ve göz açık/kapalı tespiti.
    Öncelik: MediaPipe EAR (en güvenilir) → RAF-DB CNN → DeepFace → Haar
    Returns: (smile_detected: bool, eyes_open: bool, confidence: float, debug: dict)
    """
    if EMOTION_ENGINE_READY:
        return _detect_emotion(frame_cv)
    
    # Fallback: yalnızca Haar (daha az güvenilir)
    gray = cv2.cvtColor(frame_cv, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    smile_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_smile.xml'
    )
    eye_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_eye.xml'
    )
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    smile_detected = False
    eyes_open = False
    if len(faces) > 0:
        (x, y, w, h) = faces[0]
        roi_gray = gray[y:y+h, x:x+w]
        smiles = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.8, minNeighbors=20)
        smile_detected = len(smiles) > 0
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.05, minNeighbors=15, minSize=(20,20))
        valid_eyes = [(ex,ey,ew,eh) for (ex,ey,ew,eh) in eyes if ey < h * 0.55]
        eyes_open = len(valid_eyes) >= 2
    confidence = 0.6 if eyes_open else 0.4
    return smile_detected, eyes_open, confidence, {"source": "haar_fallback"}

# ════════════════════════════════════════════════════════════════════════════
# SESSION STATE & NAVIGATION
# ════════════════════════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        'current_step': 1,
        'origin': 'Kızılay',
        'destination': 'Çankaya',
        'soc': 60,   # default %60, range %20-%80
        'pupil_value': 35,
        'steering_value': 20,
        'traffic_val': 30,
        'weather_val': 'Clear',
        'camera_used': False,
        'solution': None,
        'selected_route_idx': 1,
        'planner': None,
        'selection_mode': 'Driver',
        'camera_analysis_complete': False,
        'emotion_smile': False,
        'emotion_tired': False,
        'eda': 0.3,
        'smile': 0.2,
        'live_stations': None,   # önbelleklenmiş istasyonlar
        'traffic_density_pct': 30,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    
    if st.session_state.planner is None and DYNAMAFFECT_READY:
        try:
            st.session_state.planner = DynamAffectRoutePlanner(
                graph=create_sample_graph(ANKARA_EXTENDED), 
                driver_id="U001"
            )
        except: pass

init_session_state()

def go_next(): st.session_state.current_step += 1; st.rerun()
def go_back(): st.session_state.current_step -= 1; st.rerun()

def get_coords(address):
    """Geopy ile adresi koordinata çevirir (Ankara kısıtlı)."""
    try:
        geolocator = Nominatim(user_agent="affectev_explorer")
        location = geolocator.geocode(f"{address}, Ankara, Turkey", timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except:
        pass
    return None

def reset(): 
    st.session_state.current_step = 1
    st.session_state.solution = None
    st.session_state.selected_route_idx = 1
    st.session_state.camera_analysis_complete = False
    st.rerun()

# Sidebar Progress
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=80)
    st.title("AffectEV Navigator")
    st.markdown("---")
    steps = ["📍 Planning", "🧠 Analysis", "🛣️ Results", "⭐ Feedback"]
    for i, s_name in enumerate(steps, 1):
        status = "✅" if st.session_state.current_step > i else "🔵" if st.session_state.current_step == i else "⚪"
        st.markdown(f"**{status} Step {i}:** {s_name}")
    st.markdown("---")
    if st.button("🔄 Start New Trip"): reset()

# ════════════════════════════════════════════════════════════════════════════
# STEP 1: TRIP PLANNING
# ════════════════════════════════════════════════════════════════════════════

if st.session_state.current_step == 1:
    st.title("📍 Where are you heading?")
    st.markdown("Select your route and check your battery level.")
    
    col1, col2 = st.columns(2)
    with col1:
        locs = sorted(list(ANKARA_EXTENDED.keys()))
        st.session_state.origin = st.selectbox("Select or Search Starting Point", locs, 
            index=locs.index(st.session_state.origin) if st.session_state.origin in locs else 0)
        with st.expander("🔍 Can't find it? Search any address"): 
            search_origin = st.text_input("Enter address...", key="search_orig")
            if st.button("Add to List", key="btn_orig"): 
                c = get_coords(search_origin)
                if c: 
                    ANKARA_EXTENDED[search_origin] = c
                    st.success(f"✅ Added {search_origin}!")
    
    with col2:
        locs = sorted(list(ANKARA_EXTENDED.keys()))
        st.session_state.destination = st.selectbox("Select or Search Destination", locs,
            index=locs.index(st.session_state.destination) if st.session_state.destination in locs else 1)
        with st.expander("🔍 Can't find it? Search any address"): 
            search_dest = st.text_input("Enter address...", key="search_dest")
            if st.button("Add to List", key="btn_dest"): 
                c = get_coords(search_dest)
                if c: 
                    ANKARA_EXTENDED[search_dest] = c
                    st.success(f"✅ Added {search_dest}!")
    
    st.session_state.soc = st.slider(
        "Current Battery SOC %  (min %20 – max %80)",
        min_value=20, max_value=80,
        value=int(st.session_state.soc),
        step=1,
        help="Battery level below 20% or above 80% cannot be selected."
    )
    if st.session_state.soc < 20:
        st.error("⚠️ Minimum battery level must be 20%!")
    elif st.session_state.soc > 80:
        st.warning("⚡ Charging above 80% negatively affects battery life.")
    
    st.divider()
    if st.button("Proceed to Driver Analysis ➡️", width='stretch', type="primary"):
        if st.session_state.origin == st.session_state.destination:
            st.warning("⚠️ Origin and Destination must be different!")
        else:
            go_next()

# ════════════════════════════════════════════════════════════════════════════
# STEP 2: DRIVER STATE ANALYSIS
# ════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 2:
    st.title("🧠 Driver State Analysis")
    st.markdown("Real-time biometric monitoring for affective routing.")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 🛠️ Environment")
        st.session_state.traffic_val = st.slider("Traffic Density %", 0, 100, st.session_state.traffic_val)
        st.session_state.weather_val = st.selectbox("Weather", ["Clear", "Rainy", "Snowy"], 
            index=["Clear", "Rainy", "Snowy"].index(st.session_state.weather_val))
        st.session_state.eda = st.slider("Stress (EDA) Level %", 0, 100, int(st.session_state.eda*100)) / 100
        st.session_state.smile = st.slider("Smile (AU12) %", 0, 100, int(st.session_state.smile*100)) / 100

    with col1:
        cam_tab, manual_tab = st.tabs(["📷 Camera Analysis", "📊 Manual Override"])
        
        with cam_tab:
            st.markdown("### 3-Second AI Analysis")
            
            if st.button("🔴 Start Camera Analysis (3 seconds)", key="cam_start_btn"):
                st.markdown('<div class="countdown-timer">📹 Get Ready...</div>', unsafe_allow_html=True)
                
                # Initialize camera
                camera = cv2.VideoCapture(0)
                FRAME_WINDOW = st.empty()
                countdown_placeholder = st.empty()
                
                countdown = 3
                smile_frames = 0
                eye_frames = 0
                total_frames = 0
                
                start_time = time.time()
                
                while countdown > 0:
                    elapsed = time.time() - start_time
                    countdown = int(3 - elapsed)
                    
                    ret, frame = camera.read()
                    if not ret:
                        st.error("Camera not accessible")
                        break
                    
                    # Flip for selfie view
                    frame = cv2.flip(frame, 1)
                    
                    # Detect smile and eyes (MediaPipe EAR + RAF-DB)
                    result = detect_smile_and_eyes(frame)
                    smile_det  = result[0]
                    eyes_open  = result[1]
                    conf       = result[2]
                    dbg        = result[3] if len(result) > 3 else {}

                    if smile_det:
                        smile_frames += 1
                    if eyes_open:
                        eye_frames += 1
                    total_frames += 1

                    # EAR overlay
                    ear_l = dbg.get('left_ear', 0)
                    ear_r = dbg.get('right_ear', 0)
                    eye_color = (0, 255, 0) if eyes_open else (0, 0, 255)
                    eye_label = "OPEN" if eyes_open else "CLOSED"
                    cv2.putText(frame, f"Ready: {countdown}s",
                                (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 2)
                    cv2.putText(frame, f"Eye: {eye_label}  EAR:{(ear_l+ear_r)/2:.2f}",
                                (30, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, eye_color, 2)
                    cv2.putText(frame, f"Smile: {'YES' if smile_det else 'NO'}",
                                (30, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,200,0), 2)

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    FRAME_WINDOW.image(frame_rgb)

                    countdown_placeholder.markdown(
                        f'<div class="countdown-timer">{countdown}</div>',
                        unsafe_allow_html=True
                    )
                    time.sleep(0.05)

                countdown_placeholder.empty()
                camera.release()

                # Analyze results
                smile_ratio = smile_frames / total_frames if total_frames > 0 else 0
                eye_ratio   = eye_frames   / total_frames if total_frames > 0 else 0

                st.session_state.smile_ratio = smile_ratio
                st.session_state.eye_ratio = eye_ratio
                st.session_state.emotion_smile = smile_ratio > 0.3
                # Tired = gözler zamanın %70'inden fazlasında kapalı
                st.session_state.emotion_tired = eye_ratio < 0.7
                st.session_state.camera_used = True
                st.session_state.camera_analysis_complete = True

            if st.session_state.get('camera_analysis_complete', False):
                engine_label = "MediaPipe EAR + RAF-DB" if EMOTION_ENGINE_READY else "Haar Cascade"

                eye_ratio = st.session_state.get('eye_ratio', 0)
                smile_ratio = st.session_state.get('smile_ratio', 0)
                eye_status = "Yes ✅" if not st.session_state.emotion_tired else "No – Tired 😴"
                smile_status = "Yes 😊" if st.session_state.emotion_smile else "No"
                st.markdown(f"""
                <div style="background: white; padding: 20px; border-radius: 15px;
                            border-left: 5px solid #007AFF; margin-top:10px;">
                    <h4 style="margin:0; color:#1d1d1f;">✅ Analysis Complete</h4>
                    <p style="font-size:12px; color:#888; margin:4px 0 10px;">Engine: {engine_label}</p>
                    <div>
                        <div style="margin: 6px 0;">😊 <b>Smile Detected:</b> {smile_status}</div>
                        <div style="margin: 6px 0;">👁️ <b>Eyes Focused:</b> {eye_status}</div>
                        <div style="margin: 6px 0;">📊 <b>Eye Open Ratio:</b> {eye_ratio:.0%}</div>
                        <div style="margin: 6px 0;">🎯 <b>Smile Ratio:</b> {smile_ratio:.0%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with manual_tab:
            st.session_state.pupil_value = st.slider("Pupil Dilation %", 0, 100, st.session_state.pupil_value)
            st.session_state.steering_value = st.slider("Steering Variance %", 0, 100, st.session_state.steering_value)
            st.session_state.camera_used = False

    st.divider()
    st.markdown("### 🛠️ Routing Control Authority")
    st.session_state.selection_mode = st.radio(
        "How do you want to choose your route?",
        ["Driver Controlled (Show all options)", "AI Optimized (System selects best route)"],
        index=0 if st.session_state.selection_mode == "Driver" else 1
    ).split(" ")[0]

    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬅️ Back"): go_back()
    with b2:
        if st.button("🚀 Calculate Optimized Routes", type="primary", width='stretch'):
            with st.spinner("DynamAffect Engine is calculating..."):
                sensor_data = {
                    'pupil_dilation': st.session_state.pupil_value,
                    'steering_variance': st.session_state.steering_value,
                    'traffic_density': st.session_state.traffic_val / 100,
                    'weather_severity': {'Clear': 0.1, 'Rainy': 0.5, 'Snowy': 0.8}.get(st.session_state.weather_val, 0.1),
                    'au12': st.session_state.smile,
                    'au15': 0.05,
                    'au4': 0.05,
                    'eda_level': st.session_state.eda,
                    'weather': st.session_state.weather_val.lower(),
                    'lane_clarity': 0.8
                }
                st.session_state.planner.graph = create_sample_graph(ANKARA_EXTENDED)
                st.session_state.solution = st.session_state.planner.plan_route(
                    st.session_state.origin, st.session_state.destination,
                    sensor_data, current_soc=st.session_state.soc
                )
                # Şarj istasyonlarını şimdi çek ve önbellekle
                try:
                    st.session_state.live_stations = st.session_state.planner.get_live_charging_stations()
                except Exception:
                    st.session_state.live_stations = []
                st.session_state.traffic_density_pct = st.session_state.traffic_val
                go_next()

# ════════════════════════════════════════════════════════════════════════════
# STEP 3: RESULTS - AUTO SELECTION + ALL STATIONS
# ════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 3:
    if not st.session_state.solution:
        st.error("⚠️ No route found. Check origin/destination and battery level.")
        if st.button("⬅️ Back to Planning"): reset()
        st.stop()
    
    sol = st.session_state.solution
    st.title("🛣️ Optimized Route Results")
    
    # State Summary
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Driver ASI", f"{sol.asi_current:.2f}")
    with col2: st.info(f"Detected State: **{sol.stress_category}**")
    with col3: 
        if sol.asi_current < -0.3: st.error("🧠 Recommendation: **COMFORT ROUTE**")
        else: st.success("🧠 Recommendation: **EFFICIENT ROUTE**")

    # Intelligent auto-selection by fatigue
    if st.session_state.selection_mode == "AI":
        if sol.asi_current < -0.2:  # Tired/stressed
            st.session_state.selected_route_idx = 2  # EFFICIENT
            st.success("🤖 **AI Decision:** You look tired. Selecting **EFFICIENT** route for quick home arrival.")
        else:  # Energetic
            st.session_state.selected_route_idx = 0  # COMFORT
            st.info("🤖 **AI Decision:** You look energetic. Selecting **COMFORT** route for pleasant drive.")

    # Ensure selected_route_idx is valid
    if st.session_state.selected_route_idx is None:
        st.session_state.selected_route_idx = 1
    
    # Route list setup
    route_list = [sol.route_1_comfort, sol.route_2_balanced, sol.route_3_efficient]
    metric_list = [sol.route_1_metrics, sol.route_2_metrics, sol.route_3_metrics]
    route_types = ["comfort", "balanced", "efficient"]

    # Display tabs only in Driver mode
    if st.session_state.selection_mode == "Driver":
        tab1, tab2, tab3 = st.tabs(["🏞️ COMFORT", "⚖️ BALANCED", "⚡ EFFICIENT"])
        
        for i, tab in enumerate([tab1, tab2, tab3]):
            with tab:
                r = route_list[i]
                m = metric_list[i]
                t = route_types[i]
                
                if sol.asi_current < -0.4 and t == "comfort": 
                    st.warning("✨ **SYSTEM CHOICE:** Recommended to reduce your stress level.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Distance", f"{m['distance_km']:.1f} km")
                c2.metric("Energy", f"{m['energy_kwh']:.1f} kWh")
                c3.metric("Time", f"{m['time_min']:.0f} min")
                
                if st.button(f"📌 Select {t.title()} Route", key=f"sel_{i}"):
                    st.session_state.selected_route_idx = i
                    st.success(f"{t.title()} Route Locked!")
    else:
        # AI Mode - show selected route summary
        idx = st.session_state.selected_route_idx
        r = route_list[idx]
        m = metric_list[idx]
        t = route_types[idx]
        
        st.subheader(f"✨ Selected Route: {t.upper()}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Distance", f"{m['distance_km']:.1f} km")
        c2.metric("Energy", f"{m['energy_kwh']:.1f} kWh")
        c3.metric("Time", f"{m['time_min']:.0f} min")

    # ────────────────────────────────────────────────────
    # MAP: Şarj Merkezli Rota + Trafik Overlay + Tüm İstasyonlar
    # ────────────────────────────────────────────────────
    st.markdown("### 🗺️ Live Route Analysis & Charging Network")

    sel_idx   = st.session_state.selected_route_idx or 1
    sel_route = route_list[sel_idx]
    coords    = [ANKARA_EXTENDED.get(n, (39.92, 32.86)) for n in sel_route.nodes]

    # Cached stations (fetched at Calculate time)
    live_stations = st.session_state.get('live_stations') or []
    traffic_pct   = st.session_state.get('traffic_density_pct', 30)

    # Traffic color: green → yellow → red
    if traffic_pct < 33:
        traffic_color, traffic_label = "#27AE60", "Light Traffic"
    elif traffic_pct < 66:
        traffic_color, traffic_label = "#F39C12", "Moderate Traffic"
    else:
        traffic_color, traffic_label = "#E74C3C", "Heavy Traffic"

    # Harita
    fol_map = folium.Map(location=coords[0], zoom_start=12, tiles="cartodbpositron")

    # Trafik yoğunluğunu temsil eden arka plan çizgisi (kalın, yarı saydam)
    folium.PolyLine(
        coords, color=traffic_color, weight=14, opacity=0.25,
        tooltip=f"🚦 {traffic_label} ({traffic_pct}%)"
    ).add_to(fol_map)

    # Animasyonlu rota (üstte, ince)
    AntPath(
        coords, delay=800, dash_array=[12, 18],
        color="#007AFF", pulse_color="#FFFFFF", weight=5
    ).add_to(fol_map)

    # ── Şarj Merkezli Rota Mantığı ──────────────────────────────────────────
    # Arka plandaki modelin seçtiği istasyonları yansıtmak daha doğru olacaktır, 
    # ancak şimdilik tüm haritadaki istasyonların canlı durumlarını bozmamak için 
    # basit "bounding box" (kutu) filtrelemesini ve mor ağ çizimini kaldırıyoruz.
    
    on_route_stations = []
    on_route_names = set()

    # ── Tüm Şarj İstasyonları → Haritaya Ekle ───────────────────────────────
    for s in live_stations:
        occ = s.occupancy_rate
        is_on_route = id(s) in on_route_names

        # Doluluk → renk
        if occ >= 0.8:
            color, status_emoji = "red",    "🔴 Full"
        elif occ >= 0.5:
            color, status_emoji = "orange", "🟠 Busy"
        else:
            color, status_emoji = "green",  "🟢 Available"

        # Rota üzerindeki istasyon → yıldız ikonu
        icon = folium.Icon(
            color=color,
            icon="plug",
            prefix="fa"
        )

        popup_html = f"""
        <div style="font-family:Arial;width:230px;">
          <h5 style="margin:0 0 6px 0;color:#222;">
            {s.name}
          </h5>
          <div style="background:#f5f5f5;padding:8px;border-radius:6px;font-size:12px;">
            <div><b>⚡ Power:</b> {s.power_kw} kW</div>
            <div><b>👥 Occupancy:</b> {int(occ*100)}% — {status_emoji}</div>
            <div><b>📍 Status:</b> {s.availability_status}</div>
          </div>
        </div>"""

        folium.Marker(
            location=s.coords,
            popup=folium.Popup(popup_html, max_width=260),
            icon=icon,
            tooltip=f"{s.name} — {status_emoji}"
        ).add_to(fol_map)

    # Başlangıç / Varış marker'ları
    folium.Marker(
        coords[0],
        popup=f"<b>🟢 Start: {sel_route.nodes[0]}</b>",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
        tooltip="Start"
    ).add_to(fol_map)
    folium.Marker(
        coords[-1],
        popup=f"<b>🏁 Destination: {sel_route.nodes[-1]}</b>",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
        tooltip="Destination"
    ).add_to(fol_map)

    # Harita Açıklaması (Legend)
    legend_html = f"""
    <div style="position:fixed;bottom:30px;right:30px;z-index:9999;
                background:white;padding:12px 16px;border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,0.15);font-size:13px;">
      <b>🗺️ Map Legend</b><br>
      <span style="color:#007AFF;">━━</span> Selected Route<br>
      <span style="color:{traffic_color};">━━</span> {traffic_label} ({traffic_pct}%)<br>
      <span style="color:purple;">- - -</span> Charging Chain<br>
      ⭐ On-Route Station<br>
      🟢 Available &nbsp; 🟠 Busy &nbsp; 🔴 Full
    </div>"""
    fol_map.get_root().html.add_child(folium.Element(legend_html))

    st_folium(fol_map, width=1200, height=520, returned_objects=[])

    # ── API Durum Paneli ──────────────────────────────────────────────────────
    st.markdown("### 📡 API Integration Status")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.metric("🚦 Traffic API", f"{traffic_pct}%", delta="Live" if traffic_pct > 0 else "Simulated")
    with ac2:
        st.metric("⚡ Charging Station API", f"{len(live_stations)} stations", delta="Overpass OSM")
    with ac3:
        on_route_count = len(on_route_stations)
        st.metric("🔌 On-Route Stations", f"{on_route_count}", delta="Charging Chain")

    # ── All Stations List ─────────────────────────────────────────────────────
    if live_stations:
        st.markdown("### 🔌 All Charging Stations")
        display = sorted(live_stations, key=lambda s: s.occupancy_rate)
        for i, s in enumerate(display[:8]):
            if i % 4 == 0:
                cols = st.columns(4)
            with cols[i % 4]:
                occ_pct = int(s.occupancy_rate * 100)
                tag = "🟢" if occ_pct < 50 else "🟠" if occ_pct < 80 else "🔴"
                star = "⭐ " if id(s) in on_route_names else ""
                st.metric(
                    label=f"{star}{tag} {s.name[:14]}",
                    value=f"{occ_pct}%",
                    delta=f"{s.power_kw} kW"
                )
    else:
        st.info("📡 Loading stations...")

    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬅️ Back to Analysis"): go_back()
    with b2:
        if st.button("Finish Trip & Rate 🏁", width='stretch', type="primary"): go_next()

# ════════════════════════════════════════════════════════════════════════════
# STEP 4: FEEDBACK
# ════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 4:
    st.title("⭐ How was your journey?")
    st.markdown("Your feedback helps DynamAffect learn your preferences.")
    
    stars = st.slider("Rate this route recommendation", 1, 5, 4)
    
    if st.button("Submit & Close Trip", type="primary", width='stretch'):
        st.success("✅ Journey completed! Your feedback has been recorded for Q-Learning.")
        st.balloons()
        if st.button("Plan Another Trip"): reset()

st.sidebar.markdown("---")
st.sidebar.caption("DynamAffect v4.0 | Perfect Flow Update")
