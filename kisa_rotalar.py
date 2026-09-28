# -*- coding: utf-8 -*-
"""
kisa_rotalar.py  -  Kizilai -> Cayyolu en kisa 20 rota
"""
import sys, heapq
sys.path.insert(0, '.')
from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

g = Graf("Tesla Model 3")
k = g.komsular

BAS = "Kızılay"
BIT = "Çayyolu"

def dfs_rotalar(bas, bit, max_km=35, max_dep=8):
    sonuc = []
    def _dfs(yol, visited, toplam_km):
        if toplam_km > max_km: return
        if len(yol) > max_dep: return
        u = yol[-1]
        if u == bit:
            sonuc.append((toplam_km, list(yol)))
            return
        for (nb, km, s, e, yt) in k.get(u, []):
            if nb not in visited:
                visited.add(nb)
                yol.append(nb)
                _dfs(yol, visited, toplam_km + km)
                yol.pop()
                visited.remove(nb)
    _dfs([bas], {bas}, 0)
    sonuc.sort(key=lambda x: x[0])
    return sonuc

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
    return round(mes,1), round(sure,1), round(enerji,3), kof, tipler

print(f"{'#':<4} {'Rota':<70} {'km':>5} {'dk':>6} {'kWh':>7} {'Konfor':>8}")
print("-"*110)

rotalar = dfs_rotalar(BAS, BIT, max_km=35, max_dep=9)

# Benzersiz rotalar (ayni dugum sirasi)
gorulmus = set()
for i, (toplam_km, yol) in enumerate(rotalar):
    anahtar = tuple(yol)
    if anahtar in gorulmus: continue
    gorulmus.add(anahtar)
    m, s, e, kof, t = metrik(yol)
    rota_str = " -> ".join(yol)
    print(f"{len(gorulmus):<4} {rota_str:<70} {m:>5} {s:>6} {e:>7} {kof:>7}/100")
    print(f"     Tipler: {t}")
    print()
    if len(gorulmus) >= 20:
        break

print(f"\nToplam benzersiz rota (35km altinda): {len(gorulmus)}")
