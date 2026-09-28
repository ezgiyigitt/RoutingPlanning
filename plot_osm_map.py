import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
from shapely.geometry import Point, LineString
import numpy as np

# Koordinatlar (Enlem, Boylam) -> (Y, X)
kecioren_lon, kecioren_lat = 32.864, 39.998
bilkent_lon, bilkent_lat = 32.748, 39.870

# Rota 1: Kısa Rota (A*) - Şehir içi
# Keçiören'den şehir merkezine, oradan Eskişehir yoluna
route1_lons = [kecioren_lon, 32.855, 32.850, 32.810, 32.770, bilkent_lon]
route1_lats = [kecioren_lat, 39.950, 39.910, 39.910, 39.900, bilkent_lat]

# Rota 2: Uzun Rota (AffectEV) - Çevre yolu üzerinden, daha az trafik
# Keçiören'den O-20 çevre yoluna çıkıp şehri dışarıdan dolaşma
route2_lons = [kecioren_lon, 32.890, 32.900, 32.880, 32.750, 32.720, bilkent_lon]
route2_lats = [kecioren_lat, 40.020, 39.980, 39.900, 39.850, 39.860, bilkent_lat]

# Yumuşatma fonksiyonu (Bezier benzeri)
def smooth_line(lons, lats, num_points=100):
    # Basit bir spline interpolasyonu için lons ve lats'i düzenli aralıklarla örneklendir
    # Daha güzel kavisler çizmek için
    import scipy.interpolate as interp
    t = np.arange(len(lons))
    ti = np.linspace(0, len(lons)-1, num_points)
    
    cs_lon = interp.CubicSpline(t, lons)
    cs_lat = interp.CubicSpline(t, lats)
    return cs_lon(ti), cs_lat(ti)

try:
    r1_lons, r1_lats = smooth_line(route1_lons, route1_lats)
    r2_lons, r2_lats = smooth_line(route2_lons, route2_lats)
    line1 = LineString(zip(r1_lons, r1_lats))
    line2 = LineString(zip(r2_lons, r2_lats))
except Exception:
    # CubicSpline yoksa düz çizgi çiz
    line1 = LineString(zip(route1_lons, route1_lats))
    line2 = LineString(zip(route2_lons, route2_lats))


gdf_routes = gpd.GeoDataFrame({
    'name': ['A* (Kısa Rota)', 'AffectEV (Konfor)'],
    'geometry': [line1, line2]
}, crs="EPSG:4326")

gdf_points = gpd.GeoDataFrame({
    'name': ['Keçiören (Başlangıç)', 'Bilkent (Varış)'],
    'geometry': [Point(kecioren_lon, kecioren_lat), Point(bilkent_lon, bilkent_lat)]
}, crs="EPSG:4326")

# Contextily için Web Mercator (EPSG:3857) dönüşümü
gdf_routes = gdf_routes.to_crs(epsg=3857)
gdf_points = gdf_points.to_crs(epsg=3857)

# Plot
fig, ax = plt.subplots(figsize=(8, 8), dpi=300)

# Rotaları çiz
gdf_routes.iloc[[0]].plot(ax=ax, color='black', linewidth=4, linestyle='-', zorder=2, label='Geleneksel A* / düşük CLS (23,0 km)')
gdf_routes.iloc[[1]].plot(ax=ax, color='red', linewidth=4, linestyle='--', zorder=2, label='AffectEV yüksek CLS (44,0 km)')

# Noktaları çiz
gdf_points.iloc[[0]].plot(ax=ax, color='white', edgecolor='black', markersize=250, marker='o', linewidth=2, zorder=3)
gdf_points.iloc[[1]].plot(ax=ax, color='black', markersize=250, marker='s', zorder=3)

# Harita altlığını ekle
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

# Eksenleri gizle (daha temiz görünüm)
ax.set_axis_off()

# Lejant
ax.legend(loc='upper right', fontsize=11, frameon=True, framealpha=0.9, edgecolor='black')

# Etiketler (Başlangıç ve varış için text ekle)
# Text offset in EPSG:3857 coordinates
for idx, row in gdf_points.iterrows():
    ax.annotate(text=row['name'], xy=(row.geometry.x, row.geometry.y), 
                xytext=(0, -20), textcoords='offset points', 
                ha='center', va='top', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.8))

plt.tight_layout()
plt.savefig('figB_rota.png', bbox_inches='tight', dpi=300)
print("Gerçek OSM haritası başarıyla oluşturuldu: figB_rota.png")
