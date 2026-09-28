"""
AffectEV — Sürücü Yorgunluk/Uykululuk Veri Seti Üretici
=========================================================
EAR, Blink Rate, PERCLOS ve CLS değerlerinden oluşan
gerçekçi bir sürücü veri seti üretir.

Çıktı: veri/gercek_veri/drowsiness_features.csv
"""

import csv
import math
import os
import random

random.seed(42)

CIKTI_YOLU = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "veri", "gercek_veri", "drowsiness_features.csv"
)

os.makedirs(os.path.dirname(CIKTI_YOLU), exist_ok=True)

def gauss_clip(mu, sigma, lo=0.0, hi=1.0):
    return max(lo, min(hi, random.gauss(mu, sigma)))

N_SURUCUCU   = 30   # farklı sürücü profili
N_SEFER_BASE = 20   # her sürücüden yaklaşık sefer sayısı

satirlar = []

for surucu_id in range(1, N_SURUCUCU + 1):
    # Her sürücünün kişisel bazal değerleri
    yas            = random.randint(22, 58)
    baz_ear        = gauss_clip(0.28, 0.04, 0.18, 0.40)   # kişisel göz açıklık bazı
    baz_blink      = gauss_clip(16,   4,    8,    28)       # dakikadaki kırpma
    stres_egilimi  = gauss_clip(0.35, 0.15, 0.10, 0.80)
    gun_tipi       = random.choice(["sabahci", "gece", "karma"])

    n_sefer = N_SEFER_BASE + random.randint(-5, 10)

    for _ in range(n_sefer):
        saat       = random.randint(0, 23)
        is_gunu    = 1 if random.random() > 0.28 else 0
        bugun_km   = gauss_clip(45, 30, 0, 200)

        # Saat etkisi (sabah trafiği / geç gece)
        saat_etki = 0.0
        if saat in (7, 8, 9, 17, 18, 19):
            saat_etki = gauss_clip(0.12, 0.05, 0, 0.25)
        elif saat in (0, 1, 2, 3, 4, 5):
            saat_etki = gauss_clip(0.20, 0.07, 0, 0.35)

        # Yorgunluk seviyesi (0=uyanık, 1=çok yorgun)
        yorgunluk = gauss_clip(
            stres_egilimi * 0.4 + saat_etki + bugun_km / 400,
            0.10, 0, 1
        )

        # EAR: yorgun → düşer
        ear = gauss_clip(baz_ear - yorgunluk * 0.12, 0.03, 0.10, 0.45)

        # Blink rate: yorgun → önce artar sonra düşer (ters U)
        blink_peak = gauss_clip(baz_blink + yorgunluk * 8 - yorgunluk**2 * 12, 2, 4, 40)
        blink_rate = round(blink_peak, 1)

        # PERCLOS (gözlerin kapalı olduğu süre oranı)
        perclos = gauss_clip(yorgunluk * 0.35 + (1 - ear / baz_ear) * 0.15, 0.02, 0, 0.8)

        # Kaş kasılma (stres belirteci)
        kas_norm = gauss_clip(stres_egilimi * 0.5 + saat_etki * 0.3, 0.05, 0, 1) * 100

        # GSR (galvanik deri direnci proxy)
        gsr = gauss_clip(0.3 + stres_egilimi * 0.4 + saat_etki * 0.2, 0.08, 0, 1)

        # Etiket: uykulu mu?
        drowsy = 1 if (perclos > 0.25 or ear < 0.20) and yorgunluk > 0.45 else 0

        # CLS skoru (0-100, yüksek = daha yorgun/stresli)
        cls = round(
            0.45 * (1 - ear / 0.40) * 100
            + 0.25 * perclos * 100
            + 0.20 * kas_norm
            + 0.10 * (saat_etki * 100),
            1
        )
        cls = max(0, min(100, cls))

        satirlar.append({
            "surucu_id":    surucu_id,
            "yas":          yas,
            "gun_tipi":     gun_tipi,
            "saat":         saat,
            "is_gunu":      is_gunu,
            "bugun_km":     round(bugun_km, 1),
            "EAR":          round(ear, 4),
            "Blink_Rate":   blink_rate,
            "PERCLOS":      round(perclos, 4),
            "kas_norm":     round(kas_norm, 2),
            "gsr_norm":     round(gsr * 100, 2),
            "CLS":          cls,
            "Drowsy":       drowsy,
        })

# Karıştır
random.shuffle(satirlar)

sutunlar = [
    "surucu_id", "yas", "gun_tipi", "saat", "is_gunu",
    "bugun_km", "EAR", "Blink_Rate", "PERCLOS",
    "kas_norm", "gsr_norm", "CLS", "Drowsy"
]

with open(CIKTI_YOLU, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=sutunlar)
    writer.writeheader()
    writer.writerows(satirlar)

print(f"✅ Dataset oluşturuldu: {CIKTI_YOLU}")
print(f"   Toplam satır : {len(satirlar)}")
print(f"   Sürücü sayısı: {N_SURUCUCU}")
drowsy_count = sum(1 for s in satirlar if s["Drowsy"] == 1)
print(f"   Uykulu örnek : {drowsy_count} ({drowsy_count/len(satirlar)*100:.1f}%)")
print(f"   Uyanık örnek : {len(satirlar)-drowsy_count} ({(len(satirlar)-drowsy_count)/len(satirlar)*100:.1f}%)")
print(f"\n   Sütunlar: {', '.join(sutunlar)}")
