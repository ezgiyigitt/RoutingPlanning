"""
Bildiride (187.pdf, camera-ready) raporlanan sayılar — YALNIZCA karşılaştırma içindir.

Bu değerler hiçbir hesaplamada girdi olarak kullanılmaz; experiments/compare_with_paper.py
kodun ürettiği sonuçları bu değerlerin yanına koyar ve farkı raporlar.
"""

TABLE2 = {  # Yöntem: (süre ort, süre std, enerji ort, enerji std, konfor ort, konfor std, ortalama kavşak)
    "Dijkstra": (44.2, 13.4, 7.1, 2.2, 46.8, 6.9, 32.4),
    "A*": (42.0, 11.7, 7.7, 2.7, 50.5, 5.8, 30.1),
    "NSGA-II": (44.7, 13.0, 7.8, 2.9, 49.6, 7.5, 28.5),
    "AffectEV": (45.3, 13.3, 8.0, 2.9, 50.3, 6.9, 22.6),
}

TABLE3 = {  # CLS: (konfor, enerji kWh, süre dk, rejim)
    15: (47.3, 7.1, 43.5, "V"),
    30: (49.6, 7.8, 44.7, "V"),
    50: (49.6, 7.8, 44.7, "V"),
    65: (52.5, 8.6, 46.7, "K"),
    85: (52.5, 8.6, 46.7, "K"),
}

TABLE4 = {  # Keçiören → Bilkent, başlangıç SoC %75: (mesafe km, süre dk, enerji kWh, nihai SoC %, konfor)
    "A*": (23.0, 43.3, 4.99, 66.7, 39.0),
    "Düşük CLS": (23.0, 43.3, 4.99, 66.7, 39.0),
    "Yüksek CLS": (44.0, 52.8, 9.18, 59.7, 55.0),
}

FIGURE2 = {"plateau": 7.5, "plateau_from_episode": 400, "random": -7.5}
