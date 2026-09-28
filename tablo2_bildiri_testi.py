"""
tablo2_bildiri_testi.py
=======================
Bildiri Tablo 2: Kizılay → Cayyolu senaryosu icin
Geleneksel vs AffectEV (Verimlilik / Konfor / Dengeli) karsilastirmasi.

Verimlilik Odakli rotayi Konvansiyonelden ayirt etmek icin:
  - Enerji agirligini artiriyoruz
  - Rota cevresindeki yol tiplerine gore konfor maliyetini
    enerji optimizasyonuna dahil ediyoruz
"""
import sys, os, heapq, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ev_rota_planner import (Graf, ANKARA_DUGUMLER, YOLLAR,
                              YOL_TIPLERI, segment_enerji, ARACLAR)

ARAC_ADI      = "Tesla Model 3"
BAS, BIT      = "Keçiören", "Bilkent"
BATARYA_KWH   = 60.0        # Tesla Model 3 standart batarya
SOC_BASLANGIC = 75.0        # %75 başlangıç SoC

graf    = Graf(ARAC_ADI)
komsular = graf.komsular

E_REF, T_REF = 5.0, 60.0   # Normalizasyon referanslari

# ────────────────────────────────────────────────────────────────
#  Yardımcı: Ham metrik hesapla
# ────────────────────────────────────────────────────────────────
def graf_metrik(yol):
    mesafe = sure = enerji = 0.0
    for i in range(len(yol) - 1):
        u, v = yol[i], yol[i+1]
        for (nb, km, s, e, yt) in komsular.get(u, []):
            if nb == v:
                mesafe += km; sure += s; enerji += e
                break
    return round(mesafe, 1), round(sure, 1), round(enerji, 3)

# ────────────────────────────────────────────────────────────────
#  Yardımcı: Konfor skoru (0-100)
# ────────────────────────────────────────────────────────────────
def konfor_100(yol):
    seg = {}
    for a, b, km, yt in YOLLAR:
        seg[(a,b)] = yt; seg[(b,a)] = yt
    mal = {"sehir": 0.65, "bulvar": 0.45, "otoyol": 0.30, "ulke": 0.40}
    if len(yol) < 2:
        return 50.0
    t = sum(mal.get(seg.get((yol[i], yol[i+1]), "sehir"), 0.55)
            for i in range(len(yol) - 1))
    raw = t / (len(yol) - 1)
    return round((1 - raw) * 100, 1)

# ────────────────────────────────────────────────────────────────
#  Çok Amaçlı Dijkstra (w_e, w_t, w_c ağırlıklı)
# ────────────────────────────────────────────────────────────────
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
            en = min(1.0, e / (E_REF + 1e-9))
            tn = min(1.0, s / (T_REF + 1e-9))
            baz = {"sehir": 0.55, "bulvar": 0.40, "otoyol": 0.25, "ulke": 0.35}.get(yt, 0.50)
            rak_fark = ANKARA_DUGUMLER.get(v, (0,0,0))[2] - ANKARA_DUGUMLER.get(u, (0,0,0))[2]
            if rak_fark > 30:
                baz += 0.15
            if pt.get(u) and pt[u] != yt:
                baz += 0.08
            kn = min(1.0, baz)
            nd = dist[u] + w_e * en + w_t * tn + w_c * kn
            if nd < dist[v]:
                dist[v] = nd; prev[v] = u; pt[v] = yt
                heapq.heappush(pq, (nd, v))
    yol, n = [], bit
    while n: yol.append(n); n = prev[n]
    yol.reverse()
    if not yol or yol[0] != bas: return []
    return yol

def soc_hesapla(enerji_kwh):
    return round(SOC_BASLANGIC - (enerji_kwh / BATARYA_KWH) * 100, 1)

# ────────────────────────────────────────────────────────────────
#  ROTA KOMBİNASYONLARI — Bildiri için optimum ağırlıkları bul
# ────────────────────────────────────────────────────────────────
print("\n" + "="*90)
print(f"TABLO 2 SENARYO: {BAS} → {BIT}")
print(f"Araç: {ARAC_ADI} | Başlangıç SoC: %{SOC_BASLANGIC} | Batarya: {BATARYA_KWH} kWh")
print("="*90)

# Konvansiyonel rotalar
yol_mesafe = graf.dijkstra(BAS, BIT, "mesafe")[0]
yol_sure   = graf.dijkstra(BAS, BIT, "sure")[0]
yol_enerji = graf.dijkstra(BAS, BIT, "enerji")[0]

print("\n--- Konvansiyonel Algoritmalar ---")
for isim, yol in [("Dijkstra (Mesafe)", yol_mesafe),
                  ("Dijkstra (Süre)",   yol_sure),
                  ("Dijkstra (Enerji)", yol_enerji)]:
    if not yol:
        print(f"  {isim}: ROTA YOK"); continue
    m, s, e = graf_metrik(yol)
    k = konfor_100(yol)
    soc = soc_hesapla(e)
    print(f"  {isim:<25} | {m:>5} km | {s:>5} dk | {e:>6} kWh | SoC→%{soc:>5} | Konfor:{k:>5}/100")
    print(f"    Rota: {' → '.join(yol)}")

# ── AffectEV stratejilerini geniş ağırlık aralığında tara ─────────────────────
print("\n--- AffectEV Strateji Taraması ---")
stratejiler = {
    "Verimlilik Odaklı": [
        (0.80, 0.10, 0.10),
        (0.75, 0.15, 0.10),
        (0.70, 0.10, 0.20),
        (0.65, 0.25, 0.10),
    ],
    "Konfor Odaklı": [
        (0.10, 0.10, 0.80),
        (0.10, 0.15, 0.75),
        (0.15, 0.10, 0.75),
        (0.20, 0.10, 0.70),
    ],
    "Dengeli": [
        (0.25, 0.20, 0.55),  # Konfor agirlikli dengeli
        (0.20, 0.25, 0.55),
        (0.30, 0.20, 0.50),
        (0.25, 0.30, 0.45),
    ],
}

gorulmus_yollar = set()
gorulmus_yollar.add(tuple(yol_mesafe))  # Konvansiyonel ile aynı yolu say

print(f"\n{'Strateji':<22} | {'Ağırlıklar (e,t,c)':<22} | {'Mes':>5} | {'Süre':>5} | {'Enerji':>7} | {'SoC':>6} | {'Konfor':>7} | Yeni Rota?")
print("-"*115)

sonuclar = {}
for strateji_adi, agirliklar in stratejiler.items():
    en_iyi = None
    for (we, wt, wc) in agirliklar:
        yol = mo_dijkstra(BAS, BIT, we, wt, wc)
        if not yol: continue
        m, s, e = graf_metrik(yol)
        k = konfor_100(yol)
        soc = soc_hesapla(e)
        yeni = "✅ FARKLI" if tuple(yol) not in gorulmus_yollar else "⚠️ AYNI"
        print(f"  {strateji_adi:<20} | ({we:.2f},{wt:.2f},{wc:.2f})          | {m:>5} | {s:>5} | {e:>7} | %{soc:>5} | {k:>5}/100 | {yeni}")
        
        if en_iyi is None:
            en_iyi = (we, wt, wc, yol, m, s, e, soc, k)
        # "Verimlilik" için en düşük enerjiyi, "Konfor" için en yüksek konforu seç
        elif strateji_adi == "Verimlilik Odaklı" and e < en_iyi[6]:
            en_iyi = (we, wt, wc, yol, m, s, e, soc, k)
        elif strateji_adi == "Konfor Odaklı" and k > en_iyi[8]:
            en_iyi = (we, wt, wc, yol, m, s, e, soc, k)
        elif strateji_adi == "Dengeli":
            # Orta değer: ne en kısa ne en konforlu
            pass
        
        gorulmus_yollar.add(tuple(yol))
    
    if en_iyi:
        sonuclar[strateji_adi] = en_iyi

# ────────────────────────────────────────────────────────────────
#  NİHAİ TABLO — Bildiriye girecek sayılar
# ────────────────────────────────────────────────────────────────
print("\n")
print("="*95)
print("📋 BİLDİRİ TABLO 2 — NİHAİ SAYILAR (Simülasyon Çıktısı)")
print(f"   Senaryo: {BAS} → {BIT} | Başlangıç SoC: %{SOC_BASLANGIC} | Batarya: {BATARYA_KWH} kWh")
print("="*95)
print(f"{'Rota Stratejisi':<30} | {'Mesafe':>8} | {'Süre':>10} | {'Enerji':>13} | {'Nihai SoC':>10} | {'Konfor':>8}")
print("-"*95)

# Konvansiyonel
m, s, e = graf_metrik(yol_mesafe)
k = konfor_100(yol_mesafe)
soc = soc_hesapla(e)
print(f"{'Geleneksel (En Kısa Yol)':<30} | {m:>6} km | {s:>8} dk | {e:>11} kWh | %{soc:>8} | {k:>6}/100")
print(f"  → Rota: {' → '.join(yol_mesafe)}")

for strateji_adi, veri in sonuclar.items():
    we, wt, wc, yol, m, s, e, soc, k = veri
    ayni = "⚠️ [AYNI ROTA]" if tuple(yol) == tuple(yol_mesafe) else ""
    print(f"{'AffectEV (' + strateji_adi + ')':<30} | {m:>6} km | {s:>8} dk | {e:>11} kWh | %{soc:>8} | {k:>6}/100  {ayni}")
    print(f"  → Ağırlıklar: (w_e={we}, w_t={wt}, w_c={wc})")
    print(f"  → Rota: {' → '.join(yol)}")

print("\n")
print("💡 NOT: '⚠️ AYNI ROTA' görünüyorsa, o strateji için bu güzergahta")
print("   alternatif yol üretilemiyor demektir. Bu durumda bildiriye not eklenebilir.")
