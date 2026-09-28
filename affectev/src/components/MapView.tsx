import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { ChargingStation, RouteData } from "@/lib/api";

// Fix leaflet default icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

const createCustomIcon = (status?: string) => {
  let color = '#3b82f6';
  const s = status ? status.toLowerCase() : '';
  if (s === 'available') color = '#22c55e';
  if (s === 'busy' || s === 'moderate') color = '#f97316';
  if (s === 'full') color = '#ef4444';

  return L.divIcon({
    className: "custom-marker-station",
    html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.4);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
};

const createStartEndIcon = (type: 'start' | 'end') => {
  return L.divIcon({
    className: "custom-marker-se",
    html: `<div style="background-color: ${type === 'start' ? '#3b82f6' : '#ef4444'}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 6px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px; font-family: sans-serif;">${type === 'start' ? 'A' : 'B'}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
};

function MapUpdater({ allCoords }: { allCoords: [number, number][][] }) {
  const map = useMap();

  useEffect(() => {
    const flat = allCoords.flat();
    if (flat.length > 0) {
      const bounds = L.latLngBounds(flat);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [allCoords, map]);

  return null;
}

const createSpecialChargingIcon = () => {
  return L.divIcon({
    className: "custom-marker-cp",
    html: `<div style="background-color: #8b5cf6; width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(139, 92, 246, 0.8); display: flex; align-items: center; justify-content: center; color: white; font-size: 14px;">⚡</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

interface MapViewProps {
  routes: RouteData[];
  selectedRouteId: number;
  stations: ChargingStation[];
  chargingPoints?: ChargingStation[];
  onSelectRoute?: (id: number) => void;
}

export default function MapView({ routes, selectedRouteId, stations, chargingPoints, onSelectRoute }: MapViewProps) {
  const center: [number, number] = [39.9334, 32.8597];

  // Tüm rotaların koordinatlarını [lat, lng][] formatına dönüştür
  const allPolylines = routes.map((r) => ({
    id: r.id,
    color: r.color ?? "#3b82f6",
    name: r.name,
    coords: (r.coords ?? []).map((c) => [c.lat, c.lng] as [number, number]),
  }));

  // Seçili rotanın start/end noktaları
  const selectedRoute = routes.find((r) => r.id === selectedRouteId);
  const selectedCoords = selectedRoute
    ? (selectedRoute.coords ?? []).map((c) => [c.lat, c.lng] as [number, number])
    : [];

  const allCoords = allPolylines.map((p) => p.coords);

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: "100%", width: "100%", zIndex: 0 }}
      zoomControl={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      {/* Canlı trafik katmanı */}
      <TileLayer
        url="https://mt0.google.com/vt/lyrs=m,traffic&x={x}&y={y}&z={z}"
        attribution='&copy; Google Maps Traffic'
        opacity={0.4}
      />

      {/* ── Tüm rotalar aynı haritada ─────────────────────────────── */}
      {[...allPolylines].sort((a, b) => {
        if (a.id === selectedRouteId) return 1;
        if (b.id === selectedRouteId) return -1;
        return 0;
      }).map((route) => {
        const isSelected = route.id === selectedRouteId;
        if (route.coords.length === 0) return null;
        return (
          <Polyline
            key={`route-${route.id}-${isSelected}`}
            positions={route.coords}
            color={route.color}
            weight={isSelected ? 8 : 3}
            opacity={isSelected ? 1.0 : 0.4}
            dashArray={isSelected ? "" : "8, 12"}
            eventHandlers={{
              click: () => onSelectRoute?.(route.id),
            }}
          >
            <Popup>
              <div className="text-sm font-medium" style={{ color: route.color }}>
                {route.name}
              </div>
              <div className="text-xs text-gray-500 mt-1">Seçmek için tıklayın</div>
            </Popup>
          </Polyline>
        );
      })}

      {/* ── Başlangıç / Bitiş Marker'ları (seçili rotaya göre) ───── */}
      {selectedCoords.length > 0 && (
        <>
          <Marker position={selectedCoords[0]} icon={createStartEndIcon('start')}>
            <Popup>
              <div className="font-medium">Başlangıç: {selectedRoute?.coords?.[0]?.name}</div>
            </Popup>
          </Marker>
          <Marker position={selectedCoords[selectedCoords.length - 1]} icon={createStartEndIcon('end')}>
            <Popup>
              <div className="font-medium">Varış: {selectedRoute?.coords?.[selectedCoords.length - 1]?.name}</div>
            </Popup>
          </Marker>
        </>
      )}

      {/* ── Özel Şarj Molası ──────────────────────────────────────── */}
      {chargingPoints && chargingPoints.length > 0 && chargingPoints.map((cp, i) => (
        <Marker key={`cp-${i}`} position={[cp.lat, cp.lng]} icon={createSpecialChargingIcon()}>
          <Popup>
            <div className="text-sm font-medium text-purple-700">
              <strong className="block mb-1">⚡ Şarj Molası: {cp.name}</strong>
              Seçili rota bu istasyona uğramaktadır.
            </div>
          </Popup>
        </Marker>
      ))}

      {/* ── Tüm Şarj İstasyonları (Arka Plan) ─────────────────────── */}
      {stations && stations.length > 0 && stations.map((st, i) => {
        // Eğer bu istasyon özel şarj noktamızsa arka planda tekrar çizme
        if (chargingPoints?.some(cp => cp.name === st.name)) return null;
        return (
          <Marker key={`st-${i}`} position={[st.lat, st.lng]} icon={createCustomIcon(st.status)}>
            <Popup>
              <div className="text-sm font-medium">
                <strong className="block mb-1">{st.name || "EV Station"}</strong>
                Power: {st.power_kw} kW
              </div>
            </Popup>
          </Marker>
        );
      })}

      <MapUpdater allCoords={allCoords} />
    </MapContainer>
  );
}
