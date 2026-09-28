import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-polylineoffset";
import { CATEGORIES, COLORS, fmt, type Category, type Location, type RouteResult } from "../lib/api";

type Options = Record<Category, RouteResult>;

function Fit({ options, bottomPad }: { options: Options | null; bottomPad: number }) {
  const map = useMap();
  useEffect(() => {
    if (!options) return;
    const pts = CATEGORIES.flatMap((c) => options[c].geometry);
    map.invalidateSize();
    if (pts.length) map.fitBounds(L.latLngBounds(pts as any), { paddingTopLeft: [50, 70], paddingBottomRight: [60, bottomPad] });
  }, [options, map, bottomPad]);
  return null;
}

/** Her rota için, diğer rotalardan en uzak noktayı (rotanın %25–%75'i arasında) bulur: süre balonu oraya konur. */
function labelPoints(options: Options): Record<Category, [number, number]> {
  const out = {} as Record<Category, [number, number]>;
  const placed: [number, number][] = [];
  const d2 = (a: number[], b: number[]) => { const dy = a[0] - b[0], dx = (a[1] - b[1]) * 0.77; return dy * dy + dx * dx; };
  for (const c of CATEGORIES) {
    const g = options[c].geometry;
    const others = CATEGORIES.filter((o) => o !== c).flatMap((o) => options[o].geometry);
    let best = g[Math.floor(g.length / 2)], bestS = -1;
    for (let i = Math.floor(g.length * 0.2); i < Math.ceil(g.length * 0.8); i++) {
      let dmin = Infinity;
      for (const o of others) dmin = Math.min(dmin, d2(g[i], o));
      let lmin = Infinity;
      for (const p of placed) lmin = Math.min(lmin, d2(g[i], p));
      const MIN_SEP = 0.03 * 0.03;   // ~3 km: balonlar birbirinin üstüne binmesin
      const score = lmin < MIN_SEP ? lmin * 1e-3 : dmin + 1e-9;
      if (score > bestS) { bestS = score; best = g[i]; }
    }
    out[c] = best as [number, number];
    placed.push(out[c]);
  }
  return out;
}

/** Üç rota; ortak yol parçalarında üst üste binmesinler diye yan yana (piksel kaydırmalı) çizilir. */
const OFFSET: Record<Category, number> = { Verimlilik: -6, Dengeli: 0, Konfor: 6 };

function RouteLines({ options, active, onSelect }: { options: Options; active: Category | null; onSelect: (c: Category) => void }) {
  const map = useMap();
  useEffect(() => {
    const layers: L.Layer[] = [];
    const order = CATEGORIES.filter((c) => c !== active).concat(active ? [active] : []);
    for (const c of order) {
      const on = c === active;
      const g = options[c].geometry as L.LatLngExpression[];
      const common = { lineCap: "round", lineJoin: "round", offset: OFFSET[c], interactive: true } as any;
      const casing = L.polyline(g, { ...common, color: "#ffffff", weight: on ? 12 : 7, opacity: on ? 1 : 0.7 });
      const line = L.polyline(g, { ...common, color: COLORS[c], weight: on ? 7.5 : 4, opacity: on ? 1 : 0.5 });
      for (const l of [casing, line]) { l.on("click", () => onSelect(c)); l.addTo(map); layers.push(l); }
    }
    return () => { layers.forEach((l) => map.removeLayer(l)); };
  }, [options, active, map, onSelect]);
  return null;
}

function bubble(c: Category, minutes: number, active: boolean, recommended: boolean) {
  return L.divIcon({
    className: "",
    html: `<div class="route-bubble ${active ? "on" : ""}" style="--c:${COLORS[c]}">
             ${recommended ? '<span class="star">★</span>' : ""}<b>${fmt(minutes, 0)} dk</b><span>${c}</span></div>`,
    iconSize: [0, 0],
  });
}

export default function RouteMap({ options, active, recommended, onSelect, dark, origin, destination, bottomPad }: {
  options: Options | null; active: Category | null; recommended: Category | null; onSelect: (c: Category) => void;
  dark: boolean; origin?: Location; destination?: Location; bottomPad: number;
}) {
  const labels = useMemo(() => (options ? labelPoints(options) : null), [options]);
  return (
    <MapContainer className={`map ${dark ? "dark" : ""}`} center={[39.93, 32.82]} zoom={11} zoomSnap={0.25} zoomControl={false} attributionControl>
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıcıları' />
      <ZoomControl position="topright" />
      <Fit options={options} bottomPad={bottomPad} />
      {options && <RouteLines options={options} active={active} onSelect={onSelect} />}
      {options && labels && CATEGORIES.map((c) => (
        <Marker key={`b-${c}-${active === c}-${recommended === c}`} position={labels[c]}
          icon={bubble(c, options[c].metrics.time_min, active === c, recommended === c)}
          eventHandlers={{ click: () => onSelect(c) }} zIndexOffset={active === c ? 1000 : 0} />
      ))}
      {options && CATEGORIES.map((c) => options[c].charging && (
        <CircleMarker key={`ch-${c}`} center={[options[c].charging!.station.lat, options[c].charging!.station.lon]} radius={8}
          pathOptions={{ color: "#fff", weight: 2, fillColor: "#30d158", fillOpacity: 1 }}>
          <Tooltip>Şarj durağı · {fmt(options[c].charging!.charge_min, 0)} dk</Tooltip>
        </CircleMarker>
      ))}
      {origin && <CircleMarker center={[origin.lat, origin.lon]} radius={8} pathOptions={{ color: "#fff", weight: 3, fillColor: "#1d1d1f", fillOpacity: 1 }}>
        <Tooltip permanent direction="top" offset={[0, -8]} className="place-tip">{origin.name}</Tooltip></CircleMarker>}
      {destination && <CircleMarker center={[destination.lat, destination.lon]} radius={8} pathOptions={{ color: "#fff", weight: 3, fillColor: "#ff3b30", fillOpacity: 1 }}>
        <Tooltip permanent direction="top" offset={[0, -8]} className="place-tip">{destination.name}</Tooltip></CircleMarker>}
    </MapContainer>
  );
}
