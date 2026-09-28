# -*- coding: utf-8 -*-
"""
optimal_agirlik_bul.py
Hangi agirlik kombinasyonunda hangi rota seciliyor?
"""
import sys, heapq
sys.path.insert(0, '.')
from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

g = Graf("Tesla Model 3")
k = g.komsular

BAS = "Kızılay"
BIT = "Çayyolu"
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
            baz = {"sehir":0.65,"bulvar":0.45,"otoyol":0.30,"ulke":0.40}.get(yt, 0.55)
            ra = ANKARA_DUGUMLER.get(u, (0,0,0))[2]
            rb = ANKARA_DUGUMLER.get(v, (0,0,0))[2]
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

# 3 strateji
stratejiler = [
    ("Verimlilik (w_e=0.7, w_t=0.2, w_c=0.1)", 0.70, 0.20, 0.10),
    ("Dengeli    (w_e=0.33,w_t=0.33,w_c=0.34)", 0.33, 0.33, 0.34),
    ("Konfor     (w_e=0.1, w_t=0.1, w_c=0.8)",  0.10, 0.10, 0.80),
]

print(f"\n{'Strateji':<50} {'Rota':<60} {'km':>5} {'dk':>6} {'kWh':>7} {'Konfor':>8}")
print("-"*140)
for isim, we, wt, wc in stratejiler:
    yol = mo_dijkstra(BAS, BIT, we, wt, wc)
    if yol:
        m,s,e,kof = metrik(yol)
        rota_str = " -> ".join(yol)
        print(f"{isim:<50} {rota_str:<60} {m:>5} {s:>6} {e:>7} {kof:>7}/100")
    else:
        print(f"{isim:<50} ROTA BULUNAMADI")

# Ek: Konfor agirligini çok artirinca ne olur?
print("\n--- Konfor agirligini artirarak test ---")
for wc in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
    we = (1-wc)/2; wt = (1-wc)/2
    yol = mo_dijkstra(BAS, BIT, we, wt, wc)
    if yol:
        m,s,e,kof = metrik(yol)
        print(f"w_c={wc:.2f}: {' -> '.join(yol)}  [{m}km, {kof}/100 konfor]")
