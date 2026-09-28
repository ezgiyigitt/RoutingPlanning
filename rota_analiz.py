# -*- coding: utf-8 -*-
"""
rota_analiz.py  -  Kizilai -> Cayyolu tum fiziksel rotalar ve metrikleri
"""
import sys, heapq
sys.path.insert(0, '.')
from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

g = Graf("Tesla Model 3")
k = g.komsular

BAS = "Kızılay"
BIT = "Çayyolu"

# ── 1. Mevcut komşular ──────────────────────────────────────────────
print("=== Ilgili Dugum Komşulari ===\n")
ilgili = ["Kızılay", "Söğütözü", "Balgat", "Bilkent", "Çayyolu",
          "Dikmen", "Çankaya", "AŞTİ", "Emek", "Tandoğan", "ODTÜ", "Ümitköy"]
for d in ilgili:
    nbrs = k.get(d, [])
    if nbrs:
        print(f"{d}:")
        for (nb, km, s, e, yt) in nbrs:
            print(f"  -> {nb}: {km}km, {s:.1f}dk, {e:.3f}kWh, {yt}")
    else:
        print(f"{d}: [GRAFTA YOK veya kenar yok]")
    print()

# ── 2. DFS ile tüm rotalar ──────────────────────────────────────────
print("\n=== Tum Fiziksel Rotalar (DFS, max 10 dugum) ===\n")

def dfs_rotalar(bas, bit, max_dep=10):
    sonuc = []
    def _dfs(yol, visited):
        if len(yol) > max_dep: return
        u = yol[-1]
        if u == bit:
            sonuc.append(list(yol)); return
        for (nb, km, s, e, yt) in k.get(u, []):
            if nb not in visited:
                visited.add(nb)
                yol.append(nb)
                _dfs(yol, visited)
                yol.pop()
                visited.remove(nb)
    _dfs([bas], {bas})
    return sonuc

def metrik(yol):
    mes = sure = enerji = 0.0
    tipler = []
    for i in range(len(yol)-1):
        u, v = yol[i], yol[i+1]
        for (nb, km, s, e, yt) in k.get(u, []):
            if nb == v:
                mes += km; sure += s; enerji += e; tipler.append(yt); break
    return round(mes,1), round(sure,1), round(enerji,3), tipler

rotalar = dfs_rotalar(BAS, BIT)
rotalar.sort(key=lambda r: sum(
    km for i in range(len(r)-1)
    for (nb,km,s,e,yt) in k.get(r[i],[]) if nb==r[i+1]
))

print(f"Toplam {len(rotalar)} rota bulundu.\n")
for i, yol in enumerate(rotalar):
    m, s, e, t = metrik(yol)
    konfor_mal = {"sehir":0.65,"bulvar":0.45,"otoyol":0.30,"ulke":0.40}
    kof = round((1 - sum(konfor_mal.get(x,0.55) for x in t)/len(t))*100, 1) if t else 0
    print(f"Rota {i+1}: {' -> '.join(yol)}")
    print(f"  {m}km | {s}dk | {e}kWh | Konfor:{kof}/100 | Tipler:{t}")
    print()
