// API client - connects to FastAPI backend (localhost:8000)
const BASE = "http://localhost:8000/api";

export interface RouteData {
  id: number;
  type: string;
  name: string;
  description: string;
  distance_km: number;
  time_min: number;
  energy_kwh: number;
  charge_stops: number;
  coords: { lat: number; lng: number; name: string }[];
  color: string;
  recommended?: boolean;
}

export interface RouteDiversityInfo {
  physically_identical: boolean;
  distance_km: number;
  single_alternative_warning: boolean;
  note: string;
}

export interface PlanRouteResponse {
  asi: number;
  stress_category: string;
  unique_route_count?: number;
  battery_constraints: {
    soc_min_percent: number;
    soc_max_percent: number;
    current_soc_percent: number;
    usable_energy_kwh: number;
  };
  routes: RouteData[];
  recommended_breaks: { location: string; duration_min: number }[];
  route_diversity_info?: RouteDiversityInfo;
  charging_points?: ChargingStation[];
}

export interface EmotionResponse {
  smile_detected: boolean;
  eyes_open: boolean;
  confidence: number;
  emotion: string;
  avg_ear: number;
  source: string;
}

export interface ChargingStation {
  name: string;
  lat: number;
  lng: number;
  power_kw: number;
  status: string;
}

// ── Plan Route ────────────────────────────────────────────────────────────────
export async function planRoute(params: {
  origin: string;
  destination: string;
  battery: number;
  weather: string;
  traffic: string;
  pupil_dilation?: number;
  steering_variance?: number;
  eda_level?: number;
  smile_ratio?: number;
  eyes_tired?: boolean;
  driver_id?: string;
  affect_state?: string;  // Camera detection: Stressed / Fatigued / Alert / Relaxed
  emotion?: string;       // Raw emotion: fear / sadness / happiness / neutral etc.
}): Promise<PlanRouteResponse> {
  const res = await fetch(`${BASE}/plan-route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Route planning failed");
  }
  return res.json();
}

// ── Analyze Emotion ───────────────────────────────────────────────────────────
export async function analyzeEmotion(frameB64: string): Promise<EmotionResponse> {
  const res = await fetch(`${BASE}/analyze-emotion`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frame_b64: frameB64 }),
  });
  if (!res.ok) throw new Error("Emotion analysis failed");
  return res.json();
}

// ── Charging Stations ─────────────────────────────────────────────────────────
export async function getChargingStations(): Promise<{ stations: ChargingStation[]; count: number }> {
  const res = await fetch(`${BASE}/charging-stations`);
  if (!res.ok) throw new Error("Could not load charging stations");
  return res.json();
}

// ── Feedback ──────────────────────────────────────────────────────────────────
export async function submitFeedback(params: {
  origin: string;
  destination: string;
  selected_route: number;
  rating: number;
  asi: number;
  driver_id?: string;
}): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error("Failed to submit feedback");
  return res.json();
}

// ── Locations ─────────────────────────────────────────────────────────────────
export async function getLocations(): Promise<string[]> {
  const res = await fetch(`${BASE}/locations`);
  if (!res.ok) throw new Error("Could not load locations");
  const data = await res.json();
  return data.locations as string[];
}

// ── Health Check ──────────────────────────────────────────────────────────────
export async function healthCheck(): Promise<{ status: string; dynamaffect: boolean; emotion_engine: boolean }> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("API not reachable");
  return res.json();
}
