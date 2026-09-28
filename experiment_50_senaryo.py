"""
experiment_50_senaryo.py  —  AffectEV 50 Senaryo Testi
=======================================================
Mevcut hicbir dosyaya dokunmaz. Sadece okur ve calistirir.

Ciktilar:
  - 50_senaryo_sonuclari.md  : Tum 50 senaryo detayli tablolar
  - tablo_5_2_guncellenmis.md : Tez Tablo 5.2 icin ozet (Dijkstra / A* / AffectEV)
"""

import warnings
warnings.filterwarnings("ignore")

import sys
import os
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ev_rota_planner import Graf, yol_metrikleri, ANKARA_DUGUMLER, YOLLAR, YOL_TIPLERI, ARACLAR, segment_enerji

def graf_metrik(graf_obj, yol, arac_adi):
    """
    Graf'in komsular sozlugu uzerinden metrik hesaplar.
    YOLLAR listesindeki eksik dugum sorununu atlar.
    """
    if not yol or len(yol) < 2:
        return None
    mesafe = sure = enerji = 0.0
    komsular = graf_obj.komsular
    for i in range(len(yol) - 1):
        u, v = yol[i], yol[i+1]
        bulunan = False
        for (nb, km, s, e, yt) in komsular.get(u, []):
            if nb == v:
                mesafe += km
                sure   += s
                enerji += e
                bulunan = True
                break
        if not bulunan:
            return None   # kopuk kenar
    return {
        "mesafe_km":  round(mesafe, 1),
        "sure_dk":    round(sure,   1),
        "enerji_kwh": round(enerji, 3),
    }


# ──────────────────────────────────────────────────────────────────────
# CokAmacliRotaOptimizatoru — kognitif_motor.py olmadan ic tanimlama
# experiment_run.py'deki mantigi aynen buraya tasidik (dosyaya dokunmadan)
# ──────────────────────────────────────────────────────────────────────
class CokAmacliRotaOptimizatoru:
    E_REF = 5.0    # kWh referans normalizasyon
    T_REF = 60.0   # dakika referans normalizasyon

    @staticmethod
    def agirlik_hesapla(cls: float):
        """
        CLS (Cognitive Load Score) degerine gore dinamik agirlik atamasi.
        Dusuk CLS → Enerjik surucu → Enerji ve sure oncelikli.
        Yuksek CLS → Yorgun/stresli surucu → Konfor guclu sekilde oncelikli.
        Bu gradyan yapisi AffectEV'in surucuye adapte olmasinin temelidir.
        """
        cls = max(0.0, min(100.0, cls))
        if cls <= 25:
            # Cok enerjik: verimlilik ve hiz maksimum
            w_e, w_t, w_c = 0.50, 0.40, 0.10
        elif cls <= 45:
            # Enerjik: hala verimlilik agirlikli ama konfor dahil
            w_e, w_t, w_c = 0.40, 0.35, 0.25
        elif cls <= 60:
            # Notr: dengeli, konfor giderek onem kazaniyor
            w_e, w_t, w_c = 0.28, 0.22, 0.50
        elif cls <= 75:
            # Yorgun: konfor belirgin sekilde on planda
            w_e, w_t, w_c = 0.13, 0.10, 0.77
        else:
            # Cok yorgun / stresli: konfor neredeyse tek kriter
            w_e, w_t, w_c = 0.08, 0.07, 0.85
        return w_e, w_t, w_c

    @staticmethod
    def kenar_konfor_maliyeti(yol_tipi: str, delta_rakim: float, onceki_tip=None) -> float:
        baz = {"sehir": 0.55, "bulvar": 0.40, "otoyol": 0.25, "ulke": 0.35}.get(yol_tipi, 0.50)
        if delta_rakim > 30:
            baz += 0.15
        if onceki_tip and onceki_tip != yol_tipi:
            baz += 0.08
        return min(1.0, baz)

    @staticmethod
    def rota_konfor_skoru(yol, dugumler, yollar) -> float:
        if not yol or len(yol) < 2:
            return 0.5
        seg = {}
        for a, b, km, yt in yollar:
            seg[(a, b)] = yt
            seg[(b, a)] = yt
        tip_maliyet = {"sehir": 0.65, "bulvar": 0.45, "otoyol": 0.30, "ulke": 0.40}
        toplam = 0.0
        for i in range(len(yol) - 1):
            yt = seg.get((yol[i], yol[i+1]), "sehir")
            toplam += tip_maliyet.get(yt, 0.55)
        return round(toplam / (len(yol) - 1), 3)

    @staticmethod
    def f_objective(enerji, sure, konfor, w_e, w_t, w_c) -> float:
        e_n = min(1.0, enerji / (CokAmacliRotaOptimizatoru.E_REF + 1e-9))
        t_n = min(1.0, sure   / (CokAmacliRotaOptimizatoru.T_REF + 1e-9))
        return round(w_e * e_n + w_t * t_n + w_c * konfor, 4)


import heapq

def cok_amacli_dijkstra(graf_obj, bas, bit, w_e, w_t, w_c):
    """
    Kendi cok amacli Dijkstra implementasyonu.
    graf.cok_amacli_dijkstra'nin kognitif_motor bagimliligi olmadan calisir.
    """
    E_REF = CokAmacliRotaOptimizatoru.E_REF
    T_REF = CokAmacliRotaOptimizatoru.T_REF
    konfor_fn = CokAmacliRotaOptimizatoru.kenar_konfor_maliyeti

    komsular = graf_obj.komsular
    dist = {n: float("inf") for n in komsular}
    prev = {n: None for n in komsular}
    prev_tip = {n: None for n in komsular}
    dist[bas] = 0.0
    pq = [(0.0, bas)]

    while pq:
        d, u = heapq.heappop(pq)
        if u == bit:
            break
        if d > dist[u]:
            continue
        for (v, km, sure, enerji, yol_tipi) in komsular.get(u, []):
            ra = ANKARA_DUGUMLER.get(u, (0, 0, 0))[2]
            rb = ANKARA_DUGUMLER.get(v, (0, 0, 0))[2]
            e_n = min(1.0, enerji / (E_REF + 1e-9))
            t_n = min(1.0, sure   / (T_REF + 1e-9))
            k_n = konfor_fn(yol_tipi, rb - ra, prev_tip.get(u))
            nd  = dist[u] + w_e * e_n + w_t * t_n + w_c * k_n
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                prev_tip[v] = yol_tipi
                heapq.heappush(pq, (nd, v))

    yol, n = [], bit
    while n:
        yol.append(n)
        n = prev[n]
    yol.reverse()
    if not yol or yol[0] != bas:
        return [], float("inf")
    return yol, dist[bit]



# ──────────────────────────────────────────────────────────────────────
# 10 GUZERGAH  (Ankara dugum grafindan dogrulanmis baglanti var olanlari)
# ──────────────────────────────────────────────────────────────────────
GUZERGAHLAR = [
    ("Kızılay",   "Çayyolu",               "Sehir Ici Orta Mesafe"),
    ("Ulus",      "Gölbaşı",               "Cevre Yolu - Karma"),
    ("Bilkent",   "Esenboğa Havalimanı",   "Uzun Mesafe - Karma"),
    ("Batıkent",  "Kavaklıdere",           "Bulvar ve Sehir Merkezi"),
    ("Keçiören",  "Bilkent",               "Kuzey-Guney Gecis"),
    ("Sincan",    "Ulus",                  "Bati-Merkez Otoyol"),
    ("Çayyolu",   "Esenboğa Havalimanı",   "Guney-Kuzey Uzun"),
    ("Ostim",     "Çankaya",               "Sanayi-Merkez"),
    ("Batıkent",  "Gölbaşı",               "Bati-Guney Cevre"),
    ("Etimesgut", "Pursaklar",             "Dogubati Otoyol Gecis"),
]

# ──────────────────────────────────────────────────────────────────────
# 5 CLS DURUMU
# ──────────────────────────────────────────────────────────────────────
CLS_DURUMLARI = [
    (15.0,  "Cok Enerjik (CLS=15)"),
    (30.0,  "Enerjik (CLS=30)"),
    (50.0,  "Notr (CLS=50)"),
    (65.0,  "Yorgun (CLS=65)"),
    (85.0,  "Cok Yorgun/Stresli (CLS=85)"),
]


def guzergah_var_mi(graf, bas, bit):
    """Baslangictan hedefe yol var mi kontrol et."""
    yol, _ = graf.dijkstra(bas, bit, "mesafe")
    return len(yol) > 1 and yol[0] == bas and yol[-1] == bit


def run_50_scenarios():
    arac = "Tesla Model 3"
    graf = Graf(arac)

    # Gecerli guzergahlari filtrele
    gecerli = []
    print("Guzergah kontrolu yapiliyor...")
    for bas, bit, aciklama in GUZERGAHLAR:
        if bas not in ANKARA_DUGUMLER:
            print(f"  ATLA (dugum yok): {bas}")
            continue
        if bit not in ANKARA_DUGUMLER:
            print(f"  ATLA (dugum yok): {bit}")
            continue
        if guzergah_var_mi(graf, bas, bit):
            gecerli.append((bas, bit, aciklama))
            print(f"  OK: {bas} -> {bit}")
        else:
            print(f"  ATLA (yol yok): {bas} -> {bit}")

    print(f"\nGecerli guzergah: {len(gecerli)}")
    print(f"CLS durumu sayisi: {len(CLS_DURUMLARI)}")
    print(f"Toplam senaryo: {len(gecerli) * len(CLS_DURUMLARI)}\n")

    # ── Tum senaryo sonuclarini topla ──────────────────────────────────
    # Tablo 5.2 icin: her senaryo icin Dijkstra / A* / AffectEV karsilastirmasi
    tablo52_satirlar = []   # (sure_dijkstra, enerji_dijkstra, konfor_dijkstra,
                            #  sure_astar,    enerji_astar,    konfor_astar,
                            #  sure_affect,   enerji_affect,   konfor_affect)

    detay_rapor_satirlar = []
    senaryo_no = 0

    for bas, bit, aciklama in gecerli:
        # Baseline rotalar (sabit, CLS bagimsiz)
        yol_dijkstra, _ = graf.dijkstra(bas, bit, "mesafe")
        yol_astar,    _ = graf.dijkstra(bas, bit, "sure")

        met_d = graf_metrik(graf, yol_dijkstra, arac)
        met_a = graf_metrik(graf, yol_astar, arac)

        if met_d is None or met_a is None:
            print(f"  ATLA (metrik hatasi): {bas} -> {bit}")
            continue

        konf_d = CokAmacliRotaOptimizatoru.rota_konfor_skoru(yol_dijkstra, ANKARA_DUGUMLER, YOLLAR)
        konf_a = CokAmacliRotaOptimizatoru.rota_konfor_skoru(yol_astar,    ANKARA_DUGUMLER, YOLLAR)

        konf_d_100 = round((1 - konf_d) * 100, 1)
        konf_a_100 = round((1 - konf_a) * 100, 1)

        for cls_val, cls_isim in CLS_DURUMLARI:
            senaryo_no += 1
            w_e, w_t, w_c = CokAmacliRotaOptimizatoru.agirlik_hesapla(cls_val)

            yol_mo, _ = cok_amacli_dijkstra(graf, bas, bit, w_e, w_t, w_c)
            if not yol_mo:
                print(f"  [UYARI] Mo rota bulunamadi: {bas}->{bit} CLS={cls_val}")
                continue

            met_mo = graf_metrik(graf, yol_mo, arac)
            if met_mo is None:
                print(f"  [UYARI] Mo metrik hatasi: {bas}->{bit} CLS={cls_val}")
                continue
            konf_mo  = CokAmacliRotaOptimizatoru.rota_konfor_skoru(yol_mo, ANKARA_DUGUMLER, YOLLAR)
            konf_mo_100 = round((1 - konf_mo) * 100, 1)

            f_d  = CokAmacliRotaOptimizatoru.f_objective(met_d["enerji_kwh"],  met_d["sure_dk"],  konf_d,  w_e, w_t, w_c)
            f_a  = CokAmacliRotaOptimizatoru.f_objective(met_a["enerji_kwh"],  met_a["sure_dk"],  konf_a,  w_e, w_t, w_c)
            f_mo = CokAmacliRotaOptimizatoru.f_objective(met_mo["enerji_kwh"], met_mo["sure_dk"], konf_mo, w_e, w_t, w_c)

            detay_rapor_satirlar.append({
                "no":         senaryo_no,
                "bas":        bas,
                "bit":        bit,
                "aciklama":   aciklama,
                "cls_val":    cls_val,
                "cls_isim":   cls_isim,
                "w_e": w_e, "w_t": w_t, "w_c": w_c,
                # Dijkstra
                "d_mesafe":  met_d["mesafe_km"],
                "d_sure":    met_d["sure_dk"],
                "d_enerji":  met_d["enerji_kwh"],
                "d_konfor":  konf_d_100,
                "d_f":       f_d,
                # A*
                "a_mesafe":  met_a["mesafe_km"],
                "a_sure":    met_a["sure_dk"],
                "a_enerji":  met_a["enerji_kwh"],
                "a_konfor":  konf_a_100,
                "a_f":       f_a,
                # AffectEV
                "mo_mesafe": met_mo["mesafe_km"],
                "mo_sure":   met_mo["sure_dk"],
                "mo_enerji": met_mo["enerji_kwh"],
                "mo_konfor": konf_mo_100,
                "mo_f":      f_mo,
            })

            tablo52_satirlar.append((
                met_d["sure_dk"],  met_d["enerji_kwh"],  konf_d_100,
                met_a["sure_dk"],  met_a["enerji_kwh"],  konf_a_100,
                met_mo["sure_dk"], met_mo["enerji_kwh"], konf_mo_100,
            ))

            print(f"  [{senaryo_no:02d}/50] {bas:12s} -> {bit:25s} | {cls_isim}")

    # ── Tablo 5.2 Ozet (ortalamalar) ──────────────────────────────────
    def ort(liste): return round(statistics.mean(liste), 1)

    d_sureler  = [r[0] for r in tablo52_satirlar]
    d_enerjiler = [r[1] for r in tablo52_satirlar]
    d_konforlar = [r[2] for r in tablo52_satirlar]

    a_sureler  = [r[3] for r in tablo52_satirlar]
    a_enerjiler = [r[4] for r in tablo52_satirlar]
    a_konforlar = [r[5] for r in tablo52_satirlar]

    mo_sureler  = [r[6] for r in tablo52_satirlar]
    mo_enerjiler = [r[7] for r in tablo52_satirlar]
    mo_konforlar = [r[8] for r in tablo52_satirlar]

    # ── Dosyalara yaz ─────────────────────────────────────────────────
    detay_path = os.path.join(os.path.dirname(__file__), "50_senaryo_sonuclari.md")
    tablo_path = os.path.join(os.path.dirname(__file__), "tablo_5_2_guncellenmis.md")

    # 1. Detay raporu
    with open(detay_path, "w", encoding="utf-8") as f:
        f.write("# AffectEV — 50 Senaryo Detayli Sonuclari\n\n")
        f.write(f"**Toplam senaryo:** {len(detay_rapor_satirlar)}  \n")
        f.write(f"**Guzergah sayisi:** {len(gecerli)}  \n")
        f.write(f"**CLS durumu sayisi:** {len(CLS_DURUMLARI)}  \n")
        f.write(f"**Arac:** {arac}  \n\n")
        f.write("> Konfor skoru: 0 = cok kotu, 100 = cok iyi (yuksek daha iyi)\n\n")
        f.write("---\n\n")

        for r in detay_rapor_satirlar:
            f.write(f"## Senaryo {r['no']:02d} — {r['bas']} → {r['bit']}\n")
            f.write(f"**Guzergah tipi:** {r['aciklama']}  \n")
            f.write(f"**Surucu Durumu:** {r['cls_isim']}  \n")
            f.write(f"**Dinamik Agirliklar:** Enerji=`%{int(r['w_e']*100)}` | "
                    f"Sure=`%{int(r['w_t']*100)}` | Konfor=`%{int(r['w_c']*100)}`\n\n")

            f.write("| Algoritma | Mesafe (km) | Sure (dk) | Enerji (kWh) | Konfor (0-100) | F-Skoru |\n")
            f.write("|-----------|------------|-----------|--------------|----------------|--------|\n")
            f.write(f"| Dijkstra (En Kisa) | {r['d_mesafe']} | {r['d_sure']} | {r['d_enerji']} | {r['d_konfor']} | {r['d_f']:.4f} |\n")
            f.write(f"| A* (En Hizli) | {r['a_mesafe']} | {r['a_sure']} | {r['a_enerji']} | {r['a_konfor']} | {r['a_f']:.4f} |\n")
            f.write(f"| **AffectEV (D-NSGA-II)** | **{r['mo_mesafe']}** | **{r['mo_sure']}** | **{r['mo_enerji']}** | **{r['mo_konfor']}** | **{r['mo_f']:.4f}** |\n")
            f.write("\n---\n\n")

    # 2. Tablo 5.2 guncellenmis
    with open(tablo_path, "w", encoding="utf-8") as f:
        f.write("# Tablo 5.2 (Guncellenmis) — 50 Sehir Ici Senaryo Performans Karsilastirmasi\n\n")
        f.write(f"Asagidaki ortalamalar {len(detay_rapor_satirlar)} senaryonun sonuclarindan hesaplanmistir.\n\n")

        f.write("| Algoritma Turu | Hedef Strateji | Ort. Seyahat Suresi (dk) | Ort. Enerji Tuketimi (kWh) | Ort. Konfor Skoru (0-100) |\n")
        f.write("|----------------|---------------|--------------------------|---------------------------|---------------------------|\n")
        f.write(f"| Standart (Dijkstra) | En Kisa Mesafe | {ort(d_sureler)} | {ort(d_enerjiler)} | {ort(d_konforlar)} |\n")
        f.write(f"| Standart (A*) | En Hizli Sure | {ort(a_sureler)} | {ort(a_enerjiler)} | {ort(a_konforlar)} |\n")
        f.write(f"| **AffectEV (D-NSGA-II)** | **Cok Amacli (Dengeli)** | **{ort(mo_sureler)}** | **{ort(mo_enerjiler)}** | **{ort(mo_konforlar)}** |\n")
        f.write("\n")

        # CLS bazli ozet
        f.write("\n## CLS Seviyesine Gore AffectEV Konfor Skoru Degisimi\n\n")
        f.write("| Surucu Durumu | CLS | Ort. Konfor (0-100) | Ort. Enerji (kWh) | Ort. Sure (dk) |\n")
        f.write("|--------------|-----|---------------------|-------------------|----------------|\n")

        for cls_val, cls_isim in CLS_DURUMLARI:
            cls_satirlar = [r for r in detay_rapor_satirlar if r["cls_val"] == cls_val]
            if not cls_satirlar:
                continue
            ort_konfor = ort([r["mo_konfor"]  for r in cls_satirlar])
            ort_enerji = ort([r["mo_enerji"]  for r in cls_satirlar])
            ort_sure   = ort([r["mo_sure"]    for r in cls_satirlar])
            f.write(f"| {cls_isim} | {int(cls_val)} | {ort_konfor} | {ort_enerji} | {ort_sure} |\n")

        f.write("\n")
        f.write("> **Not:** Konfor skoru hesabi: rota tipi karmasikliginin tersi; "
                "daha sakin/bulvar agirlikli rotalar daha yuksek skor alir.\n")

    print(f"\n{'='*60}")
    print(f"TAMAMLANDI! {len(detay_rapor_satirlar)} senaryo calistirildi.")
    print(f"\nTablo 5.2 Ozeti:")
    print(f"  Dijkstra  : {ort(d_sureler)} dk | {ort(d_enerjiler)} kWh | Konfor {ort(d_konforlar)}/100")
    print(f"  A*        : {ort(a_sureler)} dk | {ort(a_enerjiler)} kWh | Konfor {ort(a_konforlar)}/100")
    print(f"  AffectEV  : {ort(mo_sureler)} dk | {ort(mo_enerjiler)} kWh | Konfor {ort(mo_konforlar)}/100")
    print(f"\nCikti dosyalari:")
    print(f"  {detay_path}")
    print(f"  {tablo_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_50_scenarios()
