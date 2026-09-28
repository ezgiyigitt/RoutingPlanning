import { useEffect, useState } from "react";
import { AppContextType } from "../App";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Zap, Clock, Route, Battery, Leaf, Loader2, AlertCircle, Info } from "lucide-react";
import MapView from "../components/MapView";
import { getChargingStations, type ChargingStation, type RouteData } from "@/lib/api";

// Route colors
const ROUTE_STYLES: Record<number, { border: string; badge: string }> = {
  0: { border: "border-green-500 ring-green-500", badge: "bg-green-50 text-green-700" },
  1: { border: "border-blue-500 ring-blue-500", badge: "bg-blue-50 text-blue-700" },
  2: { border: "border-orange-500 ring-orange-500", badge: "bg-orange-50 text-orange-700" },
};

const STYLE_ORDER = [
  { border: "border-green-500 ring-green-500", badge: "bg-green-50 text-green-700" },
  { border: "border-blue-500 ring-blue-500", badge: "bg-blue-50 text-blue-700" },
  { border: "border-orange-500 ring-orange-500", badge: "bg-orange-50 text-orange-700" },
];

const FALLBACK_ROUTES: RouteData[] = [
  {
    id: 0, type: "COMFORT", name: "Comfort Route",
    description: "Scenic with rest stops",
    distance_km: 32.4, time_min: 45, energy_kwh: 5.2, charge_stops: 1,
    coords: [], color: "#22c55e",
  },
  {
    id: 1, type: "BALANCED", name: "Balanced Route",
    description: "Optimal efficiency & time",
    distance_km: 24.3, time_min: 38, energy_kwh: 4.1, charge_stops: 0,
    coords: [], color: "#3b82f6", recommended: true,
  },
  {
    id: 2, type: "EFFICIENT", name: "Efficient Route",
    description: "Fastest, higher density",
    distance_km: 21.8, time_min: 32, energy_kwh: 3.8, charge_stops: 0,
    coords: [], color: "#f97316",
  },
];

export default function StepResults({ state, setState, nextStep }: AppContextType) {
  const [stations, setStations] = useState<ChargingStation[]>([]);
  const [loadingStations, setLoadingStations] = useState(true);

  const routeData = state.routeData;
  const routes: RouteData[] = routeData?.routes ?? FALLBACK_ROUTES;

  // HONEST CHECK: Are routes physically the same?
  const routeDiversityInfo = state.routeData?.route_diversity_info || {
    physically_identical: false,
    distance_km: 25,
    single_alternative_warning: false,
    note: ""
  };

  // Backend already sets recommended=true based on ASI — find that route's id
  const asi = routeData?.asi ?? 0;

  // Camera detection is primary source; backend ASI is used as fallback
  const affectState     = state.analysisResults?.affectState ?? null;
  const detectedEmotion = state.analysisResults?.emotion ?? null;
  const stressCategory  = affectState ?? routeData?.stress_category ?? "Relaxed";

  // Route recommendation: based on affectState (camera detection has priority)
  const recommendedByAffect = affectState === "Stressed" || affectState === "Fatigued" ? 0
    : affectState === "Alert" ? routes.length - 1
    : Math.floor(routes.length / 2);
  const aiRecommendedId = routes.find(r => r.recommended)?.id ?? recommendedByAffect;

  const selectedIndex = state.selectedRoute !== null ? state.selectedRoute : aiRecommendedId;

  useEffect(() => {
    getChargingStations()
      .then((data) => setStations(data.stations))
      .catch(() => setStations([]))
      .finally(() => setLoadingStations(false));
  }, []);

  const handleSelect = (id: number) => {
    setState({ ...state, selectedRoute: id });
  };



  const legendItems = routes.map((r, idx) => ({
    color: r.color ?? STYLE_ORDER[idx % STYLE_ORDER.length].border,
    name: r.name,
    id: r.id,
  }));

  return (
    <div className="bg-card p-6 md:p-8 rounded-2xl shadow-sm border border-border/50">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 space-y-4 md:space-y-0">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Recommended Routes</h2>
          <div className="flex items-center space-x-2 mt-2 flex-wrap gap-y-1">
            <span className="text-sm text-muted-foreground">Tailored for:</span>
            <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
              {stressCategory} State
            </Badge>
            {detectedEmotion && (
              <Badge variant="outline" className="text-xs capitalize">
                😐 {detectedEmotion}
              </Badge>
            )}
            {routeData && (
              <Badge variant="outline" className="text-xs">
                ASI: {asi.toFixed(2)}
              </Badge>
            )}
            {routeData && (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                {routes.length} route{routes.length !== 1 ? "s" : ""}
              </Badge>
            )}
          </div>
        </div>
        {!routeData && (
          <div className="flex items-center space-x-1 text-xs text-orange-500">
            <AlertCircle className="w-3 h-3" />
            <span>Simulation mode (API offline)</span>
          </div>
        )}
      </div>

      {/* ────────────────────────────────────────────────────────────────────────────── */}
      {/* HONEST DISCLOSURE: Route Convergence Warning */}
      {/* ────────────────────────────────────────────────────────────────────────────── */}
      {routeDiversityInfo.physically_identical && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 flex gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold mb-1">
              {routeDiversityInfo.single_alternative_warning
                ? "⚠️ Single Route Available"
                : "Route Diversity Note"}
            </p>
            <p className="text-blue-800">{routeDiversityInfo.note}</p>
          </div>
        </div>
      )}

      {/* Route Cards */}
      <div
        className={`grid gap-4 mb-8 grid-cols-1 ${routes.length === 1
            ? "md:grid-cols-1 max-w-sm"
            : routes.length === 2
              ? "md:grid-cols-2"
              : "md:grid-cols-3"
          }`}
      >
        {routes.map((route, idx) => {
          const style = STYLE_ORDER[idx % STYLE_ORDER.length];
          const isSelected = selectedIndex === route.id;
          const isAiPick = route.id === aiRecommendedId;

          return (
            <Card
              key={route.id}
              id={`route-card-${route.id}`}
              className={`relative p-4 cursor-pointer transition-all duration-300 hover:shadow-md ${isSelected
                  ? `ring-2 ${style.border} shadow-sm`
                  : "border-border/60 opacity-80 hover:opacity-100"
                }`}
              onClick={() => handleSelect(route.id)}
            >
              {/* Color stripe */}
              <div
                className="absolute top-0 left-0 right-0 h-1 rounded-t-xl"
                style={{ backgroundColor: route.color ?? "#3b82f6" }}
              />

              {route.recommended && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-[10px] uppercase tracking-wider font-bold px-3 py-1 rounded-full shadow-sm">
                  AI Recommended
                </div>
              )}
              {isAiPick && !route.recommended && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-violet-600 text-white text-[10px] uppercase tracking-wider font-bold px-3 py-1 rounded-full shadow-sm">
                  Best for You
                </div>
              )}

              <div className="space-y-3 mt-1">
                <div>
                  <h3 className="font-semibold text-foreground">{route.name}</h3>
                  <p className="text-xs text-muted-foreground">{route.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-y-2 text-sm">
                  <div className="flex items-center space-x-1.5">
                    <Route className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="font-medium text-foreground">{route.distance_km} km</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="font-medium text-foreground">{route.time_min} min</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Battery className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="font-medium text-foreground">{route.charge_stops} stops</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Leaf className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="font-medium text-foreground">{route.energy_kwh} kWh</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Map */}
      <div className="h-72 md:h-96 w-full rounded-xl overflow-hidden border border-border mb-3">
        <MapView
          routes={routes}
          selectedRouteId={selectedIndex}
          stations={stations}
          chargingPoints={routeData?.charging_points as any}
          onSelectRoute={handleSelect}
        />
      </div>

      {/* Map Legend */}
      <div className="flex flex-wrap items-center gap-3 mb-4 px-1">
        {legendItems.map((item) => (
          <button
            key={item.id}
            className={`flex items-center space-x-1.5 text-xs rounded-full px-2.5 py-1 border transition-all ${selectedIndex === item.id
                ? "border-current font-semibold shadow-sm"
                : "border-border/40 opacity-70 hover:opacity-100"
              }`}
            style={{ color: item.color, borderColor: selectedIndex === item.id ? item.color : undefined }}
            onClick={() => handleSelect(item.id)}
          >
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span>{item.name}</span>
          </button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground">
          {loadingStations ? (
            <span className="flex items-center space-x-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Loading stations...</span>
            </span>
          ) : (
            <span>⚡ {stations.length} charging stations</span>
          )}
        </span>
      </div>

      <Button
        className="w-full rounded-full h-14 text-lg font-medium transition-all hover:scale-[1.02] active:scale-[0.98]"
        onClick={nextStep}
      >
        Navigate with this Route
      </Button>
    </div>
  );
}