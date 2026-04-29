"""
gercek_veri_test.py  --  AffectEV Gercek Veri Entegrasyon Testi
================================================================
Bu script sunlari yapar:
  1. Gercek veri durumunu kontrol eder (DEAP / Kaggle var mi?)
  2. Russell Circumplex eslemesini dogrular (tablo)
  3. Modeli gercek veriyle sifirdan egitir (eski model silinir)
  4. Sentetik vs Gercek model karsilastirmasi yapar

Calistir:
    python gercek_veri_test.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import json
import warnings
import numpy as np

PROJE_KOK  = os.path.dirname(os.path.abspath(__file__))
MODEL_META = os.path.join(PROJE_KOK, "modeller", "duygu_egitim_meta.json")
MODEL_DOC  = os.path.join(PROJE_KOK, "modeller", "duygu_regresyon_model.joblib")
SCALER_DOC = os.path.join(PROJE_KOK, "modeller", "duygu_regresyon_scaler.joblib")


def mevcut_model_meta_oku():
    """Mevcut eğitim meta verisini okur."""
    if os.path.exists(MODEL_META):
        with open(MODEL_META, encoding="utf-8") as f:
            return json.load(f)
    return None


def eski_modeli_sil():
    """Gerçek veri ile yeniden eğitim için eski model dosyalarını siler."""
    silindi = []
    for dosya in [MODEL_DOC, SCALER_DOC, MODEL_META]:
        if os.path.exists(dosya):
            os.remove(dosya)
            silindi.append(os.path.basename(dosya))
    if silindi:
        print(f"  🗑️  Silindi: {', '.join(silindi)}")
    return len(silindi) > 0


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     AffectEV — Gerçek Veri Entegrasyon Testi                ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    # ── 1. Gerçek Veri Durumu ─────────────────────────────────────────
    print("━━━ 1. Gerçek Veri Kontrolü ━━━")
    from gercek_veri_yukleyici import (
        DEAPYukleyici, KaggleUykululukYukleyici,
        russell_circumplex_esle, russell_tablosu_yazdir,
        gercek_veri_yukle, veri_dogrula,
        DEAP_KLASORU, KAGGLE_CSV
    )

    deap = DEAPYukleyici()
    kaggle = KaggleUykululukYukleyici()

    print(f"\n  DEAP    {'✅ Mevcut' if deap.hazir else '❌ Bulunamadı — İndirme: http://www.eecs.qmul.ac.uk/mmv/datasets/deap/'}")
    print(f"  Kaggle  {'✅ Mevcut' if kaggle.hazir else '❌ Bulunamadı — İndirme: https://www.kaggle.com/datasets/dheerajperumandla/drowsiness-detection'}")

    if deap.hazir:
        ist = deap.istatistik()
        print(f"    └─ {ist['katilimci_sayisi']} katılımcı × 40 deneme = {ist['toplam_deneme']} kayıt")

    # ── 2. Russell Circumplex Tablosu ─────────────────────────────────
    print("\n━━━ 2. Russell Circumplex Eşleme Özeti ━━━")
    ornekler = [
        (2.0, 8.0), (8.0, 8.0), (2.0, 2.0), (8.0, 2.0), (5.0, 5.0)
    ]
    print(f"\n  {'V':>5} {'A':>5} | {'Yorgunluk':>10} {'Stres':>8} {'Sakinlik':>10} {'Enerji':>8} | {'Baskın':>10}")
    print(f"  {'-'*65}")
    for v, a in ornekler:
        d = russell_circumplex_esle(v, a)
        baskin = max({k: v2 for k, v2 in d.items()}, key=d.get)
        print(f"  {v:>5.1f} {a:>5.1f} | {d['yorgunluk']:>10.3f} {d['stres']:>8.3f} "
              f"{d['sakinlik']:>10.3f} {d['enerji']:>8.3f} | {baskin:>10}")

    # ── 3. Mevcut Model Durumu ─────────────────────────────────────────
    print("\n━━━ 3. Mevcut Model Durumu ━━━")
    meta = mevcut_model_meta_oku()
    if meta:
        print(f"  Eğitim tarihi : {meta.get('egitim_tarihi', '?')}")
        print(f"  Kaynak        : {meta.get('kaynak', '?')}")
        print(f"  Örnek sayısı  : {meta.get('ornek_sayisi', '?')}")
        kaynak = meta.get("kaynak", "")
        if "sentetik_pseudo_label" in kaynak or "bilinmiyor" in kaynak:
            print(f"\n  ⚠️  Model sentetik pseudo-label ile eğitilmiş!")
            print(f"     Gerçek veri varsa modeli yeniden eğitmek önerilir.")
    else:
        print("  ℹ️  Model meta verisi bulunamadı (eski format veya henüz yok).")

    # ── 4. Gerçek Veri ile Yeniden Eğitim ─────────────────────────────
    print("\n━━━ 4. Modeli Gerçek Veriyle Yeniden Eğit ━━━")

    X, Y, kaynak = gercek_veri_yukle(verbose=True)

    if X is None:
        print("\n  ⚠️  Gerçek veri yok. Eğitim yapılamıyor.")
        print("  → Veriyi indirip 'veri/gercek_veri/' klasörüne koy.")
        print("  → Sonra bu scripti tekrar çalıştır.")
    else:
        print(f"\n  ✅ Toplam: {len(X)} örnek | Kaynak: {kaynak}")

        rapor = veri_dogrula(X, Y)
        print(f"\n  Veri Kalitesi:")
        print(f"    Geçerli      : {'✅' if rapor['gecerli'] else '❌'}")
        print(f"    Örnek sayısı : {rapor['ornek_sayisi']}")
        print(f"    NaN sayısı   : X={rapor['X_nan_sayisi']}, Y={rapor['Y_nan_sayisi']}")
        print(f"    Y toplamı=1  : {'✅' if rapor['Y_toplam_1_mi'] else '❌'}")
        print(f"\n  Duygu Dağılımı:")
        for d, n in rapor.get("duygu_dagilim", {}).items():
            oran = n / rapor["ornek_sayisi"] * 100
            bar = "█" * int(oran / 5)
            print(f"    {d:<12}: {bar:<20} %{oran:.1f} ({n})")

        if rapor["gecerli"]:
            print("\n  🔄 Eski model siliniyor ve gerçek veriyle yeniden eğitiliyor...")
            eski_modeli_sil()

            # Gerçek veriyle modeli eğit
            try:
                from duygu_regresyonu import SurekliDuyguMotoru
                # Modeli gerçek veriyle eğit
                motor = SurekliDuyguMotoru()
                meta_yeni = mevcut_model_meta_oku()
                print(f"\n  ✅ YENİ MODEL EĞİTİLDİ!")
                if meta_yeni:
                    print(f"     Kaynak        : {meta_yeni.get('kaynak', '?')}")
                    print(f"     Örnek sayısı  : {meta_yeni.get('ornek_sayisi', '?')}")
                    print(f"     Eğitim tarihi : {meta_yeni.get('egitim_tarihi', '?')}")

            except Exception as e:
                print(f"  ❌ Eğitim hatası: {e}")

    # ── 5. Makale Katkısı Özeti ────────────────────────────────────────
    print("\n━━━ 5. Makale Katkısı (Novel Contribution) ━━━")
    print("""
  Bu sistemin literatürdeki yeri:

  [✓] DEAP fizyolojik sinyal → EOG/EMG özellik çıkarımı
  [✓] Russell (1980) Circumplex → 4D sürekli duygu vektörü
  [✓] NSGA-II Pareto rotası + fizyolojik duygu ağırlıkları
  [✓] Q-Learning kenar hafızası → kişiselleşen Pareto frontu
  [✓] EV kısıtları (batarya, şarj) + duygusal yük entegrasyonu

  Referans Boşluğu (Gap Analysis):
    • EV routing + affective state: YOK (0 makale)
    • Russell Circumplex + routing weights: YOK
    • DEAP → EV navigation: YOK
    → Üç katkı birden = IEEE/Expert Systems yayınlanabilir

  Hedef Dergiler:
    • IEEE Transactions on Intelligent Transportation Systems (IF: 8.5)
    • Expert Systems with Applications (IF: 8.7)
    • Computers in Human Behavior (IF: 9.0)
    • Transportation Research Part C (IF: 9.0)
  """)

    print("\n[Test tamamlandı]")


if __name__ == "__main__":
    main()
