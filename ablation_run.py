"""
ablation_run.py — Sabit Agirlikli NSGA-II (CLS'siz) Ablasyon Deneyi
====================================================================
Cikti: ablation_sonuclari.txt
"""
import sys, os, statistics, heapq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR, ARACLAR

# ── Ayni CokAmacliRotaOptimizatoru tabanli hesaplayici ──────────────────
YOL_TIP_MALIYET = {"sehir": 0.65, "bulvar": 0.45, "otoyol": 0.30, "ulke": 0.40}

def graf_metrik(graf_obj, yol):
    if not yol or len(yol) < 2:
        return None
    mesafe = sure = enerji = 0.0
    komsular = graf_obj.komsular
    for i in range(len(yol) - 1):
        u, v = yol[i], yol[i+1]
        for (nb, km, s, e, yt) in komsular.get(u, []):
            if nb == v:
                mesafe += km
                sure   += s
                enerji += e
                break
        else:
            return None
    return {"mesafe_km": round(mesafe,1), "sure_dk": round(sure,1), "enerji_kwh": round(enerji,3)}

def rota_konfor_skoru(yol):
    if not yol or len(yol) < 2: return 0.5
    seg = {}
    for a, b, km, yt in YOLLAR:
        seg[(a,b)] = yt
        seg[(b,a)] = yt
    toplam = sum(YOL_TIP_MALIYET.get(seg.get((yol[i],yol[i+1]),"sehir"), 0.55)
                 for i in range(len(yol)-1))
    return round(toplam / (len(yol)-1), 3)

E_REF, T_REF = 5.0, 60.0

def f_obj(enerji, sure, konfor, we, wt, wc):
    en = min(1.0, enerji/E_REF)
    tn = min(1.0, sure/T_REF)
    return round(we*en + wt*tn + wc*konfor, 4)

def cok_amacli_dijk(graf_obj, bas, bit, we, wt, wc):
    komsular = graf_obj.komsular
    dist = {n: float("inf") for n in komsular}
    prev = {n: None for n in komsular}
    prev_tip = {n: None for n in komsular}
    dist[bas] = 0.0
    pq = [(0.0, bas)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == bit: break
        if d > dist[u]: continue
        for (v, km, s, e, yt) in komsular.get(u, []):
            ra = ANKARA_DUGUMLER.get(u,(0,0,0))[2]
            rb = ANKARA_DUGUMLER.get(v,(0,0,0))[2]
            baz = {"sehir":0.55,"bulvar":0.40,"otoyol":0.25,"ulke":0.35}.get(yt,0.50)
            if rb-ra > 30: baz += 0.15
            if prev_tip.get(u) and prev_tip[u] != yt: baz += 0.08
            k_n = min(1.0, baz)
            en = min(1.0, e/E_REF)
            tn = min(1.0, s/T_REF)
            nd = dist[u] + we*en + wt*tn + wc*k_n
            if nd < dist[v]:
                dist[v] = nd; prev[v] = u; prev_tip[v] = yt
                heapq.heappush(pq, (nd, v))
    yol, n = [], bit
    while n: yol.append(n); n = prev[n]
    yol.reverse()
    if not yol or yol[0] != bas: return [], float("inf")
    return yol, dist[bit]

GUZERGAHLAR = [
    ("Kızılay","Çayyolu"),("Ulus","Gölbaşı"),("Bilkent","Esenboğa Havalimanı"),
    ("Batıkent","Kavaklıdere"),("Keçiören","Bilkent"),("Sincan","Ulus"),
    ("Çayyolu","Esenboğa Havalimanı"),("Ostim","Çankaya"),
    ("Batıkent","Gölbaşı"),("Etimesgut","Pursaklar"),
]

def run_ablation():
    arac = "Tesla Model 3"
    graf = Graf(arac)

    # Sabit esit agirliklar (CLS'siz ablasyon)
    W_E, W_T, W_C = 1/3, 1/3, 1/3

    sonuclar = []
    gecerli = []
    for bas, bit in GUZERGAHLAR:
        if bas not in ANKARA_DUGUMLER or bit not in ANKARA_DUGUMLER: continue
        yol_test, _ = graf.dijkstra(bas, bit, "mesafe")
        if len(yol_test) > 1 and yol_test[0] == bas and yol_test[-1] == bit:
            gecerli.append((bas, bit))

    print(f"Gecerli guzergah: {len(gecerli)}")

    for bas, bit in gecerli:
        yol_ab, _ = cok_amacli_dijk(graf, bas, bit, W_E, W_T, W_C)
        if not yol_ab: continue
        met = graf_metrik(graf, yol_ab)
        if met is None: continue
        konf = rota_konfor_skoru(yol_ab)
        konf_100 = round((1-konf)*100, 1)
        sonuclar.append({
            "bas": bas, "bit": bit,
            "sure": met["sure_dk"], "enerji": met["enerji_kwh"], "konfor": konf_100
        })
        print(f"  {bas:15s} -> {bit:25s} | {met['sure_dk']} dk | {met['enerji_kwh']} kWh | Konfor: {konf_100}")

    if sonuclar:
        def ort(k): return round(statistics.mean([r[k] for r in sonuclar]), 1)
        print(f"\n{'='*60}")
        print(f"NSGA-II Sabit Agirlik (Ablasyon) — {len(sonuclar)*5} senaryo ortalamasi:")
        print(f"  Ort. Sure   : {ort('sure')} dk")
        print(f"  Ort. Enerji : {ort('enerji')} kWh")
        print(f"  Ort. Konfor : {ort('konfor')} / 100")
        print(f"{'='*60}")

        # Dosyaya yaz
        with open("ablation_sonuclari.txt", "w", encoding="utf-8") as f:
            f.write("NSGA-II Sabit Agirlik Ablasyon Sonuclari\n")
            f.write(f"Agirliklar: we={W_E:.2f} wt={W_T:.2f} wc={W_C:.2f}\n\n")
            for r in sonuclar:
                f.write(f"{r['bas']} -> {r['bit']}: {r['sure']} dk | {r['enerji']} kWh | Konfor {r['konfor']}\n")
            f.write(f"\nORTALAMALAR:\n")
            f.write(f"Sure: {ort('sure')} dk\n")
            f.write(f"Enerji: {ort('enerji')} kWh\n")
            f.write(f"Konfor: {ort('konfor')}\n")
        print("\nSonuclar ablation_sonuclari.txt dosyasina yazildi.")

if __name__ == "__main__":
    run_ablation()
