import sys; sys.path.insert(0,'.')
from api import _osrm_route, ANKARA, _pick_hub, _haversine_km

o, d = 'Ulus', 'Golbasi'
if o not in ANKARA: o = 'Ulus'
if d not in ANKARA: d = 'Gölbaşı'
dist = _haversine_km(*ANKARA[o], *ANKARA[d])
print(f'Mesafe: {dist:.1f} km')

for rt in ['COMFORT','BALANCED','EFFICIENT']:
    hub = _pick_hub(o, d, rt, dist)
    wp = [o] + ([hub] if hub else []) + [d]
    print(f'  {rt} waypoints: {wp}')
    r = _osrm_route(wp)
    if r:
        km = round(r['distance_m']/1000,1)
        dk = round(r['duration_s']/60)
        pts = len(r['coords'])
        print(f'    -> OSRM OK: {km} km, {dk} dk, {pts} koordinat noktasi')
    else:
        print(f'    -> OSRM erisim yok (fallback kullanilacak)')
