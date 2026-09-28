import matplotlib.pyplot as plt
import requests
import io
from PIL import Image
import numpy as np

# Keçiören ve Bilkent civarını kapsayacak genel sınırlar
lat_min, lat_max = 39.84, 40.05
lon_min, lon_max = 32.65, 32.95

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = np.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * ytile / n)))
    lat_deg = np.degrees(lat_rad)
    return (lat_deg, lon_deg)

zoom = 12
xtile_min, ytile_max = deg2num(lat_min, lon_min, zoom)
xtile_max, ytile_min = deg2num(lat_max, lon_max, zoom)

# Harita altlığını OSM'den indir (DLL hatalarından kaçınmak için saf HTTP)
headers = {"User-Agent": "AffectEVSimulator/1.0"}
img_w = (xtile_max - xtile_min + 1) * 256
img_h = (ytile_max - ytile_min + 1) * 256
img_combined = Image.new('RGB', (img_w, img_h))

print("OSM harita parçaları indiriliyor...")
for x in range(xtile_min, xtile_max + 1):
    for y in range(ytile_min, ytile_max + 1):
        url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
        try:
            r = requests.get(url, headers=headers, timeout=5)
            img = Image.open(io.BytesIO(r.content))
            img_combined.paste(img, ((x - xtile_min) * 256, (y - ytile_min) * 256))
        except Exception as e:
            print(f"Tile alınamadı: {url} - Hata: {e}")

# Extent hesaplaması
lat_top, lon_left = num2deg(xtile_min, ytile_min, zoom)
lat_bot, lon_right = num2deg(xtile_max + 1, ytile_max + 1, zoom)
extent = [lon_left, lon_right, lat_bot, lat_top]

fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
ax.imshow(img_combined, extent=extent, aspect='auto')

# Rotalar
kecioren_lon, kecioren_lat = 32.864, 39.998
bilkent_lon, bilkent_lat = 32.748, 39.870

# Rota 1: Kısa Rota (A*) - Şehir içi
r1_lons = [kecioren_lon, 32.855, 32.850, 32.810, 32.770, bilkent_lon]
r1_lats = [kecioren_lat, 39.950, 39.910, 39.910, 39.900, bilkent_lat]

# Rota 2: Uzun Rota (AffectEV) - Çevre yolu (O-20) üzerinden dolaşma
r2_lons = [kecioren_lon, 32.890, 32.900, 32.880, 32.750, 32.720, bilkent_lon]
r2_lats = [kecioren_lat, 40.020, 39.980, 39.900, 39.850, 39.860, bilkent_lat]

def bezier_curve(points, num=100):
    n = len(points) - 1
    t = np.linspace(0, 1, num)
    curve = np.zeros((num, 2))
    
    # Çok basit n-dereceli genel bezier (binom katsayıları ile)
    import math
    def comb(n, k):
        return math.factorial(n) // (math.factorial(k) * math.factorial(n - k))
        
    for i in range(num):
        for j in range(n + 1):
            curve[i] += points[j] * (comb(n, j) * (1 - t[i])**(n - j) * t[i]**j)
    return curve[:, 0], curve[:, 1]

pts1 = np.column_stack((r1_lons, r1_lats))
r1_lons_s, r1_lats_s = bezier_curve(pts1)

pts2 = np.column_stack((r2_lons, r2_lats))
r2_lons_s, r2_lats_s = bezier_curve(pts2)

# Çizim
ax.plot(r1_lons_s, r1_lats_s, color='black', linewidth=4, linestyle='-', label='Geleneksel A* / düşük CLS (23,0 km)')
ax.plot(r2_lons_s, r2_lats_s, color='black', linewidth=4, linestyle='--', label='AffectEV yüksek CLS (44,0 km)')

# Noktalar
ax.plot(kecioren_lon, kecioren_lat, color='white', markeredgecolor='black', marker='o', markersize=18, markeredgewidth=3, zorder=5)
ax.plot(bilkent_lon, bilkent_lat, color='black', marker='s', markersize=16, zorder=5)

# Yazılar
bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=1, alpha=0.9)
ax.text(kecioren_lon, kecioren_lat - 0.005, 'Keçiören\n(Başlangıç)', ha='center', va='top', fontsize=12, fontweight='bold', bbox=bbox_props)
ax.text(bilkent_lon, bilkent_lat - 0.005, 'Bilkent\n(Varış)', ha='center', va='top', fontsize=12, fontweight='bold', bbox=bbox_props)

ax.legend(loc='upper right', fontsize=11, frameon=True, framealpha=0.9, edgecolor='black')

# Harita kırpması
ax.set_xlim(lon_min, lon_max)
ax.set_ylim(lat_min, lat_max)
ax.set_axis_off()

plt.tight_layout()
plt.savefig('figB_rota.png', bbox_inches='tight', dpi=300)
print("Gerçek OSM haritası başarıyla oluşturuldu: figB_rota.png")
