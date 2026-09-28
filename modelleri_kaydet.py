"""
modelleri_kaydet.py — AffectEV Model Kaydedici
===============================================
Q-Learning ve D-NSGA-II modellerini modeller/ klasörüne kaydeder.
"""

import json
import os
import shutil
from datetime import datetime

PROJE_KOK  = os.path.dirname(os.path.abspath(__file__))
MODELLER   = os.path.join(PROJE_KOK, "modeller")
Q_NETWORKS = os.path.join(PROJE_KOK, "driver_q_networks")

os.makedirs(MODELLER, exist_ok=True)

print("=" * 55)
print("  AffectEV — Model Kaydedici")
print("=" * 55)

# ─────────────────────────────────────────────────────────
#  1. Q-LEARNING MODELLERİ
#     driver_q_networks/*.json → modeller/qlearning/
# ─────────────────────────────────────────────────────────
q_hedef = os.path.join(MODELLER, "qlearning")
os.makedirs(q_hedef, exist_ok=True)

q_dosyalari = [f for f in os.listdir(Q_NETWORKS) if f.endswith(".json")]
print(f"\n[1] Q-Learning Modelleri ({len(q_dosyalari)} sürücü)")

q_istatistik = {
    "model_turu": "Q-Learning (ε-greedy, tabular)",
    "algoritma": "DriverQNetwork — Q(s,a) ← Q(s,a) + α[r + γ·maxQ(s') - Q(s,a)]",
    "parametreler": {
        "learning_rate_alpha": 0.1,
        "discount_factor_gamma": 0.9,
        "epsilon_baslangic": 0.3,
        "epsilon_minimum": 0.05,
        "epsilon_bozunma": 0.995
    },
    "durum_uzayi": "origin × destination × ASI × time_of_day × weather × route_type",
    "eylem_uzayi": ["fast_route", "economic_route", "scenic_route", "balanced_route"],
    "odül_fonksiyonu": {
        "rota_tamamlama": "+10",
        "erken_cikis": "-15",
        "surücü_geri_bildirim": "(stars-3)×2",
        "sert_hizlanma": "-10",
        "trafik_olayı": "-5"
    },
    "surucu_sayisi": len(q_dosyalari),
    "surucu_dosyalari": [],
    "kayit_tarihi": datetime.now().isoformat()
}

toplam_durum = 0
toplam_episode = 0

for dosya in sorted(q_dosyalari):
    kaynak = os.path.join(Q_NETWORKS, dosya)
    hedef  = os.path.join(q_hedef, dosya)
    shutil.copy2(kaynak, hedef)

    with open(kaynak, "r") as f:
        veri = json.load(f)

    durum_sayisi = len(veri.get("Q", {}))
    episode      = veri.get("episode_count", 0)
    epsilon      = veri.get("epsilon", 0.3)
    toplam_durum += durum_sayisi
    toplam_episode += episode

    q_istatistik["surucu_dosyalari"].append({
        "surucu_id":   veri.get("driver_id", dosya.replace("_q.json", "")),
        "dosya":       dosya,
        "durum_sayisi": durum_sayisi,
        "episode_sayisi": episode,
        "epsilon_mevcut": round(epsilon, 4)
    })
    print(f"   ✅ {dosya:20s} — {durum_sayisi} durum, {episode} episode")

q_istatistik["toplam_durum_sayisi"]   = toplam_durum
q_istatistik["toplam_episode_sayisi"] = toplam_episode

# Özet JSON kaydet
ozet_dosya = os.path.join(MODELLER, "qlearning_model_ozeti.json")
with open(ozet_dosya, "w", encoding="utf-8") as f:
    json.dump(q_istatistik, f, ensure_ascii=False, indent=2)
print(f"\n   📄 Özet kaydedildi: modeller/qlearning_model_ozeti.json")

# ─────────────────────────────────────────────────────────
#  2. D-NSGA-II MODEL BİLGİSİ
#     (Evrimsel algoritma — joblib ile kaydedilemez,
#      parametreler ve mimari bilgisi JSON olarak kaydedilir)
# ─────────────────────────────────────────────────────────
print(f"\n[2] D-NSGA-II Model Bilgisi")

nsga2_bilgisi = {
    "model_turu": "D-NSGA-II (Dynamic NSGA-II)",
    "tam_adi": "Dynamic Non-dominated Sorting Genetic Algorithm II",
    "referans": "Deb et al., 'A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II', IEEE TEC, 2002",
    "ozellik": "Duygu durumuna (ASI) göre dinamik ağırlık güncelleme",
    "parametreler": {
        "populasyon_boyutu": 100,
        "nesil_sayisi": 50,
        "mutasyon_orani_baz": 0.05,
        "mutasyon_orani_max": "0.05 + 0.15 × |ASI|  (adaptif)",
        "secim_yontemi": "Tournament (k=2)",
        "caprazlama": "2-opt segment swap"
    },
    "amac_fonksiyonlari": {
        "F1": "Mesafe × (1 + ort_trafik_yogunlugu)  [km]",
        "F2": "Enerji tüketimi  [kWh]",
        "F3": "Seyahat süresi  [dakika]"
    },
    "dinamik_agirliklar": {
        "stresli_surucu_ASI_lt_minus_03": "Konfor rotası (kompleksite ×2.5 cezalandırılır)",
        "alert_surucu_ASI_gt_plus_03":    "Verimli rota (süre ×0.8 indirimli)",
        "notr_surucu":                    "Dengeli rota"
    },
    "batarya_kisiti": {
        "SoC_lt_30": "Mesafe ×1.5 ceza",
        "SoC_lt_50": "Mesafe ×0.5 ceza",
        "SoC_gte_50": "Ceza yok"
    },
    "affective_penalty_function": {
        "aciklama": "APF(rota, ASI) — Duygu-yol uyumsuzluğunu cezalandırır",
        "hassasiyet": 2.0,
        "yuksek_trafik_stresli_surucu": "Ekstra ceza"
    },
    "pareto_ciktisi": {
        "COMFORT":   "Minimum kompleksite skoru",
        "EFFICIENT": "Minimum enerji tüketimi",
        "BALANCED":  "Mesafeye göre ortanca rota"
    },
    "test_senaryolari": 50,
    "guzergahlar": 10,
    "cls_seviyeleri": [15, 30, 50, 65, 85],
    "arac": "Tesla Model 3",
    "kayit_tarihi": datetime.now().isoformat(),
    "not": "Evrimsel algoritma parametre bazlı çalışır; joblib ile kaydedilemez. Bu dosya model mimarisi ve parametrelerini belgeler."
}

nsga2_dosya = os.path.join(MODELLER, "dnsga2_model_bilgisi.json")
with open(nsga2_dosya, "w", encoding="utf-8") as f:
    json.dump(nsga2_bilgisi, f, ensure_ascii=False, indent=2)
print(f"   ✅ D-NSGA-II bilgisi kaydedildi: modeller/dnsga2_model_bilgisi.json")

# ─────────────────────────────────────────────────────────
#  3. GENEL MODEL ENVANTERİ
# ─────────────────────────────────────────────────────────
print(f"\n[3] Model Envanteri Güncelleniyor...")

envanter = {
    "proje": "AffectEV — Affective Computing Tabanlı EV Rota Optimizasyonu",
    "guncelleme": datetime.now().isoformat(),
    "modeller": [
        {
            "ad": "CLS Random Forest Regressor",
            "dosya": "cls_rf_model.joblib",
            "scaler": "cls_rf_scaler.joblib",
            "tur": "Makine Öğrenmesi — Regresyon",
            "algoritma": "Random Forest (120 ağaç, max_depth=12)",
            "giris": "13 özellik (biyometrik + bağlamsal + kişisel)",
            "cikis": "CLS skoru ∈ [0, 100]",
            "performans": "RMSE = 4.75 ± 0.27 (5-fold CV)",
            "boyut": "~3 MB"
        },
        {
            "ad": "Duygu Regresyon Modeli",
            "dosya": "duygu_regresyon_model.joblib",
            "scaler": "duygu_regresyon_scaler.joblib",
            "tur": "Makine Öğrenmesi — Regresyon",
            "algoritma": "Gradient Boosting / Random Forest",
            "giris": "16 özellik (CLS prior + biyometrik + bağlamsal)",
            "cikis": "4D duygu vektörü [yorgunluk, stres, sakinlik, enerji]",
            "boyut": "~13 MB"
        },
        {
            "ad": "Q-Learning Kişiselleştirme Modeli",
            "klasor": "qlearning/",
            "ozet": "qlearning_model_ozeti.json",
            "tur": "Pekiştirmeli Öğrenme — Tabular Q-Learning",
            "algoritma": "ε-greedy Q-Learning",
            "surucu_sayisi": len(q_dosyalari),
            "boyut": "~1-2 KB / sürücü"
        },
        {
            "ad": "D-NSGA-II Rota Optimizasyon Motoru",
            "bilgi_dosyasi": "dnsga2_model_bilgisi.json",
            "tur": "Evrimsel Algoritma — Çok Amaçlı Optimizasyon",
            "algoritma": "Dynamic NSGA-II",
            "amac_sayisi": 3,
            "populasyon": 100,
            "nesil": 50
        }
    ]
}

envanter_dosya = os.path.join(MODELLER, "model_envanteri.json")
with open(envanter_dosya, "w", encoding="utf-8") as f:
    json.dump(envanter, f, ensure_ascii=False, indent=2)
print(f"   ✅ Envanter kaydedildi: modeller/model_envanteri.json")

# ─────────────────────────────────────────────────────────
#  ÖZET
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  TAMAMLANDI — modeller/ klasörü içeriği:")
print("=" * 55)
for dosya in sorted(os.listdir(MODELLER)):
    yol  = os.path.join(MODELLER, dosya)
    if os.path.isdir(yol):
        icerik = os.listdir(yol)
        print(f"  📁 {dosya}/  ({len(icerik)} dosya)")
    else:
        boyut = os.path.getsize(yol)
        boyut_str = f"{boyut/1024:.1f} KB" if boyut < 1024*1024 else f"{boyut/1024/1024:.1f} MB"
        print(f"  📄 {dosya:45s} {boyut_str}")
print()
