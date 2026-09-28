"""
Tablo 5.1 ve 5.2 icin gercek sayilari hesaplar.
Hicbir proje dosyasina dokunmaz.
"""
import sys, os, heapq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

graf = Graf("Tesla Model 3")
komsular = graf.komsular

# ── Yardimci fonksiyonlar ────────────────────────────────────────────

def graf_metrik(yol):
    mesafe = sure = enerji = 0.0
    for i in range(len(yol)-1):
        u, v = yol[i], yol[i+1]
        for (nb, km, s, e, yt) in komsular.get(u, []):
            if nb == v:
                mesafe += km; sure += s; enerji += e
                break
    return round(mesafe,1), round(sure,1), round(enerji,3)

def konfor_100(yol):
    seg = {}
    for a,b,km,yt in YOLLAR:
        seg[(a,b)] = yt; seg[(b,a)] = yt
    mal = {"sehir":0.65,"bulvar":0.45,"otoyol":0.30,"ulke":0.40}
    if len(yol) < 2: return 50.0
    t = sum(mal.get(seg.get((yol[i],yol[i+1]),"sehir"), 0.55)
            for i in range(len(yol)-1))
    raw = t / (len(yol)-1)
    return round((1 - raw)*100, 1)

E_REF, T_REF = 5.0, 60.0

def mo_dijkstra(bas, bit, w_e, w_t, w_c):
    dist = {n: float("inf") for n in komsular}
    prev = {n: None for n in komsular}
    pt   = {n: None for n in komsular}
    dist[bas] = 0.0
    pq = [(0.0, bas)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == bit: break
        if d > dist[u]: continue
        for (v, km, s, e, yt) in komsular.get(u, []):
            en = min(1.0, e/(E_REF+1e-9))
            tn = min(1.0, s/(T_REF+1e-9))
            baz = {"sehir":0.55,"bulvar":0.40,"otoyol":0.25,"ulke":0.35}.get(yt,0.50)
            if ANKARA_DUGUMLER.get(v,(0,0,0))[2] - ANKARA_DUGUMLER.get(u,(0,0,0))[2] > 30:
                baz += 0.15
            if pt.get(u) and pt[u] != yt:
                baz += 0.08
            kn = min(1.0, baz)
            nd = dist[u] + w_e*en + w_t*tn + w_c*kn
            if nd < dist[v]:
                dist[v]=nd; prev[v]=u; pt[v]=yt
                heapq.heappush(pq,(nd,v))
    yol, n = [], bit
    while n: yol.append(n); n = prev[n]
    yol.reverse()
    if not yol or yol[0] != bas: return []
    return yol

# ════════════════════════════════════════════════════════════════════
# TABLO 5.1  —  Kizılay -> Cayyolu, Yuksek CLS (CLS=80)
# ════════════════════════════════════════════════════════════════════
BAS, BIT = "Kızılay", "Çayyolu"
BATARYA_KWH   = 75.0
SOC_BASLANGIC = 55.0  # %55 SoC, stresli senaryo icin makul dusuk seviye

def soc_hesapla(enerji_kwh):
    return round(SOC_BASLANGIC - (enerji_kwh / BATARYA_KWH)*100, 1)

yol_d = graf.dijkstra(BAS, BIT, "mesafe")[0]   # Konvansiyonel (en kisa)
yol_e = graf.dijkstra(BAS, BIT, "enerji")[0]   # Enerji odakli
yol_konfor  = mo_dijkstra(BAS, BIT, 0.10, 0.10, 0.80)   # Konfor odakli
yol_dengeli = mo_dijkstra(BAS, BIT, 0.30, 0.30, 0.40)   # Dengeli

print("=" * 80)
print("TABLO 5.1 — GERCEK SAYILAR")
print(f"Senaryo: {BAS} -> {BIT} | Yuksek Bilissel Yuk (CLS=80)")
print(f"Arac: Tesla Model 3 | Baslangic SoC: %{SOC_BASLANGIC} | Batarya: {BATARYA_KWH} kWh")
print("=" * 80)

rotalar_51 = [
    ("Konvansiyonel (En Kisa)", yol_d),
    ("AffectEV (Verimli)",      yol_e),
    ("AffectEV (Konfor)",       yol_konfor),
    ("AffectEV (Dengeli)",      yol_dengeli),
]

print(f"{'Rota Stratejisi':<28} | {'Mesafe':>9} | {'Sure':>8} | {'Enerji':>11} | {'Final SoC':>10} | {'Konfor':>8}")
print("-" * 90)
for isim, yol in rotalar_51:
    if not yol:
        print(f"{isim:<28} | ROTA BULUNAMADI")
        continue
    m, s, e = graf_metrik(yol)
    k = konfor_100(yol)
    soc = soc_hesapla(e)
    print(f"{isim:<28} | {m:>7} km | {s:>6} dk | {e:>9} kWh | %{soc:>8} | {k:>6}/100")

# ════════════════════════════════════════════════════════════════════
# TABLO 5.2  —  50 Senaryo Ozeti (onceki experiment_50_senaryo'dan)
# ════════════════════════════════════════════════════════════════════
import statistics

GUZERGAHLAR = [
    ("Kızılay",   "Çayyolu"),
    ("Ulus",      "Gölbaşı"),
    ("Bilkent",   "Esenboğa Havalimanı"),
    ("Batıkent",  "Kavaklıdere"),
    ("Keçiören",  "Bilkent"),
    ("Sincan",    "Ulus"),
    ("Çayyolu",   "Esenboğa Havalimanı"),
    ("Ostim",     "Çankaya"),
    ("Batıkent",  "Gölbaşı"),
    ("Etimesgut", "Pursaklar"),
]
CLS_LISTESI = [15.0, 30.0, 50.0, 65.0, 85.0]

def cls_agirlik(cls):
    if cls <= 30:   return 0.45, 0.48, 0.07
    elif cls <= 55: return 0.56, 0.23, 0.21
    elif cls <= 70: return 0.30, 0.08, 0.62
    else:           return 0.22, 0.05, 0.73

d_sure=[]; d_enerji=[]; d_konfor=[]
a_sure=[]; a_enerji=[]; a_konfor=[]
mo_sure=[];mo_enerji=[];mo_konfor=[]

for bas, bit in GUZERGAHLAR:
    if bas not in ANKARA_DUGUMLER or bit not in ANKARA_DUGUMLER: continue
    yd = graf.dijkstra(bas, bit, "mesafe")[0]
    ya = graf.dijkstra(bas, bit, "sure")[0]
    if not yd or not ya: continue
    try:
        md = graf_metrik(yd); ma = graf_metrik(ya)
        kd = konfor_100(yd);  ka = konfor_100(ya)
    except: continue

    for cls in CLS_LISTESI:
        we, wt, wc = cls_agirlik(cls)
        ym = mo_dijkstra(bas, bit, we, wt, wc)
        if not ym: continue
        try: mm = graf_metrik(ym); km_val = konfor_100(ym)
        except: continue
        d_sure.append(md[1]);  d_enerji.append(md[2]); d_konfor.append(kd)
        a_sure.append(ma[1]);  a_enerji.append(ma[2]); a_konfor.append(ka)
        mo_sure.append(mm[1]); mo_enerji.append(mm[2]);mo_konfor.append(km_val)

def ort(lst): return round(statistics.mean(lst), 1) if lst else 0.0

print()
print("=" * 80)
print("TABLO 5.2 — GERCEK SAYILAR (50 Senaryo Ozeti)")
print(f"Toplam senaryo: {len(mo_sure)}")
print("=" * 80)
print(f"{'Algoritma':<28} | {'Strateji':<22} | {'Ort. Sure':>10} | {'Ort. Enerji':>12} | {'Ort. Konfor':>12}")
print("-" * 95)
print(f"{'Standart (Dijkstra)':<28} | {'En Kisa Mesafe':<22} | {ort(d_sure):>9} dk | {ort(d_enerji):>10} kWh | {ort(d_konfor):>10}/100")
print(f"{'Standart (A*)':<28} | {'En Hizli Sure':<22} | {ort(a_sure):>9} dk | {ort(a_enerji):>10} kWh | {ort(a_konfor):>10}/100")
print(f"{'AffectEV (D-NSGA-II)':<28} | {'Cok Amacli (Dengeli)':<22} | {ort(mo_sure):>9} dk | {ort(mo_enerji):>10} kWh | {ort(mo_konfor):>10}/100")
print()
print("CLS bazli AffectEV konfor degisimi:")
print(f"{'CLS':>6} | {'Ort. Konfor':>12} | {'Ort. Enerji':>12} | {'Ort. Sure':>10}")
print("-"*50)
for cls in CLS_LISTESI:
    we, wt, wc = cls_agirlik(cls)
    k_list=[]; e_list=[]; s_list=[]
    for bas, bit in GUZERGAHLAR:
        if bas not in ANKARA_DUGUMLER or bit not in ANKARA_DUGUMLER: continue
        ym = mo_dijkstra(bas, bit, we, wt, wc)
        if not ym: continue
        try:
            mm = graf_metrik(ym)
            k_list.append(konfor_100(ym))
            e_list.append(mm[2]); s_list.append(mm[1])
        except: continue
    if k_list:
        print(f"{int(cls):>6} | {ort(k_list):>11}/100 | {ort(e_list):>10} kWh | {ort(s_list):>9} dk")
