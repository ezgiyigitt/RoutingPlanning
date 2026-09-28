export type Category = "Konfor" | "Dengeli" | "Verimlilik";
export const CATEGORIES: Category[] = ["Verimlilik", "Dengeli", "Konfor"];

export interface Location { name: string; lat: number; lon: number }

export interface Metrics {
  distance_km: number; time_min: number; energy_kwh: number; comfort: number;
  n_intersection: number; n_stop: number; traffic_density: number;
}

export interface Charging {
  station: { lat: number; lon: number; operator?: string };
  soc_arrival: number; delta_soc: number; charge_min: number;
}

export interface RouteResult {
  method: string; category: Category | null; metrics: Metrics;
  soc_initial: number; soc_final: number; charging: Charging | null;
  geometry: [number, number][];
}

export interface FrontPoint { energy: number; time: number; comfort: number; distance: number }

export interface PlanResponse {
  options: Record<Category, RouteResult & { score: number }>;
  recommended: Category;
  overlap: Record<string, number>;
  cls: number; state: string; weights: [number, number, number]; traffic_seed: number;
  front: FrontPoint[]; dominated: { energy: number; time: number }[]; evaluations: number;
  categories: Record<Category, number>; selected_index: number;
  routes: Record<string, RouteResult>;
  qlearning: { state: { cls_level: number; soc_level: number; traffic_level: number };
               q_values: Record<Category, number>; recommendation: Category | null };
}

export interface FaceResult {
  ok: boolean; message?: string; frames: number; face_frames: number; method?: string;
  eyes_closed_ratio?: number; smile_ratio?: number; emotion?: string | null; emotion_tr?: string | null;
  fatigue?: number; valence_negative?: number; cls?: number; state?: string;
}

export interface Driver { id: string; name: string; feedbacks?: number; age?: number; job?: string; legacy?: boolean }
export interface Vehicle { id: string; name: string; battery_kwh: number; Cd: number; mass_kg: number; A: number; note: string }
export interface Weather { id: string; name: string; speed: number; cr: number; aux_kw: number }

export interface PlanRequest {
  origin: string; destination: string; soc: number; traffic_seed: number;
  vehicle?: string; weather?: string; driver_id?: string;
  cls?: number; fatigue?: number; cognitive?: number; valence?: number;
}

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `${r.status}`;
    try { const b = await r.json(); msg = b.detail || JSON.stringify(b); } catch { /* */ }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

const post = (url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  health: () => fetch("/api/health").then(j<{ nodes: number; edges: number; osm_timestamp: string }>),
  drivers: () => fetch("/api/drivers").then(j<Driver[]>),
  addDriver: (name: string) => post("/api/drivers", { name }).then(j<Driver>),
  vehicles: () => fetch("/api/vehicles").then(j<Vehicle[]>),
  weather: () => fetch("/api/weather").then(j<Weather[]>),
  locations: () => fetch("/api/locations").then(j<Location[]>),
  config: () => fetch("/api/config").then(j<any>),
  cls: (fatigue: number, cognitive: number, valence: number) =>
    post("/api/cls", { fatigue, cognitive, valence }).then(j<{ cls: number; state: string; weights: number[] }>),
  plan: (req: PlanRequest) => post("/api/plan", req).then(j<PlanResponse>),
  feedback: (body: unknown) => post("/api/feedback", body).then(j<{ reward: number; q_values: Record<Category, number> }>),
  resetQ: () => post("/api/qtable/reset", {}).then(j<{ ok: boolean }>),
  chargers: () => fetch("/api/charging-stations").then(j<{ lat: number; lon: number; operator: string }[]>),
  faceStatus: () => fetch("/api/face/status").then(j<{ opencv: boolean; emotion_model: boolean }>),
  faceAnalyze: (frames: string[], cognitive: number) => post("/api/face/analyze", { frames, cognitive }).then(j<FaceResult>),
  experiments: () => fetch("/api/experiments").then(j<any>),
};

export const COLORS: Record<string, string> = {
  Verimlilik: "#34c759",
  Dengeli: "#007aff",
  Konfor: "#af52de",
  "A*": "#8e8e93",
  Dijkstra: "#636366",
  "NSGA-II": "#ff9f0a",
};

export const CLS_BANDS = [
  { upper: 25, name: "Çok Enerjik", w: [0.5, 0.4, 0.1] },
  { upper: 45, name: "Enerjik", w: [0.4, 0.35, 0.25] },
  { upper: 60, name: "Nötr", w: [0.28, 0.22, 0.5] },
  { upper: 75, name: "Yorgun", w: [0.13, 0.1, 0.77] },
  { upper: 100, name: "Stresli", w: [0.08, 0.07, 0.85] },
];

export const bandOf = (cls: number) => CLS_BANDS.find((b) => cls <= b.upper) ?? CLS_BANDS[4];
export const fmt = (x: number, d = 1) => x.toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
