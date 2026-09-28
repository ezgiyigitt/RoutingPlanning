# -*- coding: utf-8 -*-
"""
en_iyi_senaryo.py  - Hangi guzergahta stratejiler FARKLI rota seciyor?
"""
import sys, heapq
sys.path.insert(0, '.')
from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

g = Graf("Tesla Model 3")
k = g.komsular

E_REF, T_REF = 5.0, 60.0

def mo_dijkstra(bas, bit, w_e, w_t, w_c):
    dist = {n: float("inf") for n in k}
    prev = {n: None for n in k}
    pt   = {n: None for n in k}
    dist[bas] = 0.0
    pq = [(0.0, bas)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == bit: break
        if d > dist[u]: continue
        for (v, km, s, e, yt) in k.get(u, []):
            en = min(1.0, e / (E_REF + 1e-9))
            tn = min(1.0, s / (T_REF + 1e-9))
            baz = {"sehir":0.55,"bulvar":0.40,"otoyol":0.25,"ulke":0.35}.get(yt, 0.50)
            ra = ANKARA_DUGUMLER.get(u,(0,0,0))[2]
            rb = ANKARA_DUGUMLER.get(v,(0,0,0))[2]
            if rb - ra > 30: baz += 0.15
            if pt.get(u) and pt[u] != yt: baz += 0.08
            kn = min(1.0, baz)
            nd = dist[u] + w_e*en + w_t*tn + w_c*kn
            if nd < dist[v]:
                dist[v] = nd; prev[v] = u; pt[v] = yt
                heapq.heappush(pq, (nd, v))
    yol, n = [], bit
    while n: yol.append(n); n = prev[n]
    yol.reverse()
    return yol if yol and yol[0] == bas else []

def metrik(yol):
    mes = sure = enerji = 0.0
    tipler = []
    for i in range(len(yol)-1):
        u, v = yol[i], yol[i+1]
        for (nb, km, s, e, yt) in k.get(u, []):
            if nb == v:
                mes += km; sure += s; enerji += e; tipler.append(yt); break
    konfor_mal = {"sehir":0.65,"bulvar":0.45,"otoyol":0.30,"ulke":0.40}
    kof = round((1 - sum(konfor_mal.get(x,0.55) for x in tipler)/len(tipler))*100, 1) if tipler else 0
    return round(mes,1), round(sure,1), round(enerji,3), kof

stratejiler = [
    ("Verimlilik", 0.70, 0.20, 0.10),
    ("Dengeli",    0.33, 0.33, 0.34),
    ("Konfor",     0.10, 0.10, 0.80),
]

guzergahlar = [
    ("Kızılay",  "Çayyolu"),
    ("Batıkent", "Kavaklıdere"),
    ("Keçiören", "Bilkent"),
    ("Sincan",   "Ulus"),
    ("Ostim",    "Çankaya"),
    ("Batıkent", "Gölbaşı"),
    ("Etimesgut","Pursaklar"),
    ("Ulus",     "Gölbaşı"),
    ("Bilkent",  "Esenboğa Havalimanı"),
    ("Çayyolu",  "Esenboğa Havalimanı"),
]

print(f"Stratejilerin FARKLI rota seçtiği güzergahlar:\n")
print(f"{'Güzergah':<40} {'Verimlilik Rotası':<50} {'Konfor Rotası':<50} {'Farklı?'}")
print("-"*160)

for bas, bit in guzergahlar:
    rotalar = {}
    for isim, we, wt, wc in stratejiler:
        yol = mo_dijkstra(bas, bit, we, wt, wc)
        rotalar[isim] = tuple(yol) if yol else ()

    farkli = len(set(rotalar.values())) > 1
    verim_r = " -> ".join(rotalar["Verimlilik"])[:48]
    konfor_r = " -> ".join(rotalar["Konfor"])[:48]
    flag = "✅ FARKLI!" if farkli else "⚠️ AYNI"

    print(f"{bas+' -> '+bit:<40} {verim_r:<50} {konfor_r:<50} {flag}")

    if farkli:
        print(f"\n  *** Bu güzergah Tablo 2 için uygun! ***")
        for isim, we, wt, wc in stratejiler:
            yol = list(rotalar[isim])
            m,s,e,kof = metrik(yol)
            print(f"  {isim}: {' -> '.join(yol)}")
            print(f"    {m}km | {s}dk | {e}kWh | Konfor:{kof}/100")
        print()
