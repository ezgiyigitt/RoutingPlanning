"""
entegrasyon_rehberi.py  —  AffectEV  Yeni Modüllerin Entegrasyon Kılavuzu
=========================================================================
Bu dosya; suruş_veri_kaydedici.py, cls_ml_modeli.py ve duygu_regresyonu.py
modüllerinin mevcut ev_rota_planner.py ile nasıl entegre edileceğini
açıklayan örnek kodları içerir.

KURULUM
-------
    pip install scikit-learn joblib numpy

Dizin yapısı (her dosya aynı klasörde olmalı):
    proje/
    ├── ev_rota_planner.py          (mevcut)
    ├── kognitif_motor.py           (mevcut)
    ├── experiment_run.py           (mevcut)
    ├── suruş_veri_kaydedici.py     (YENİ)
    ├── cls_ml_modeli.py            (YENİ)
    ├── duygu_regresyonu.py         (YENİ)
    ├── entegrasyon_rehberi.py      (bu dosya)
    ├── modeller/                   (otomatik oluşturulur)
    │   ├── cls_rf_model.joblib
    │   ├── cls_rf_scaler.joblib
    │   ├── duygu_regresyon_model.joblib
    │   └── ...
    └── veri/                       (otomatik oluşturulur)
        └── suruc_seferler.json
"""

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────────────────
#  MODÜL İMPORTLARI
# ─────────────────────────────────────────────────────────────────────
from ev_rota_planner     import Graf, yol_metrikleri, ANKARA_DUGUMLER, YOLLAR
from kognitif_motor      import (
    SurucuProfilYonetici, cls_to_mod, CokAmacliRotaOptimizatoru
)

# YENİ modüller
from suruş_veri_kaydedici import SurusVeriKaydedici, GpsSimulatoru
from cls_ml_modeli         import MLDestekliKognitivYukAnalizci, OgrenebilirCLSMotoru
from duygu_regresyonu      import (
    SurekliDuyguMotoru, cls_ve_duygu_ile_optimize, DUYGU_BOYUTLARI
)


# ─────────────────────────────────────────────────────────────────────
#  GELİŞTİRİLMİŞ CLS ANALİZCİ FACTORY
# ─────────────────────────────────────────────────────────────────────
def cls_analizci_olustur(profil: dict, ml_aktif: bool = True):
    """
    ml_aktif=True  → MLDestekliKognitivYukAnalizci döndürür (öncelikli)
    ml_aktif=False → Orijinal KognitivYukAnalizci döndürür (geri uyum)
    """
    if ml_aktif:
        return MLDestekliKognitivYukAnalizci(profil)
    else:
        from kognitif_motor import KognitivYukAnalizci
        return KognitivYukAnalizci(profil)


# ─────────────────────────────────────────────────────────────────────
#  GELİŞTİRİLMİŞ ROTA OPTİMİZASYON PİPELİNE'I
# ─────────────────────────────────────────────────────────────────────
class GelistirilmisRotaOptimizatoru:
    """
    Üç yeni modülü birleştiren geliştirilmiş rota optimizasyon motoru.

    Bileşenler:
        1. SurusVeriKaydedici   → Her seferin GPS/hız verisini anonim kaydeder
        2. MLDestekliKognitivYukAnalizci → CLS'yi Random Forest ile tahmin eder
        3. SurekliDuyguMotoru   → 4 boyutlu sürekli duygu vektörü üretir
    """

    def __init__(self, uid: str, arac_adi: str = "Tesla Model 3"):
        self.uid       = uid
        self.arac_adi  = arac_adi
        self.graf      = Graf()
        self.pm        = SurucuProfilYonetici()
        self.profil    = self.pm.profil_al(uid) or {}

        # Bileşen başlatma
        self.kaydedici      = SurusVeriKaydedici()
        self.cls_analizci   = MLDestekliKognitivYukAnalizci(self.profil)
        self.duygu_motoru   = SurekliDuyguMotoru(self.profil)
        self.gps_sim        = GpsSimulatoru(ANKARA_DUGUMLER)

        self._aktif_cls: float = 45.0
        self._duygu_gecmis: list = []

    # ── Sefer Başlat ──────────────────────────────────────────────────
    def sefer_baslat(self, bas: str, bit: str) -> dict:
        """
        Yeni bir sürüş seferi başlatır ve üç katmanlı analiz döngüsünü çalıştırır.

        1. Anlık CLS'yi ML modeline hesaplattır
        2. Sürekli duygu vektörü al
        3. Duygu-ağırlıklı rota optimizasyonu yap
        4. GPS kaydını başlat

        Dönüş: Rota bilgilerini içeren sözlük
        """
        # ── CLS Tahmini (ML) ──────────────────────────────────────────
        self._aktif_cls = self.cls_analizci.anlik_cls()

        # ── Sürekli Duygu Vektörü ─────────────────────────────────────
        duygu = self.duygu_motoru.duygu_tahmin(self._aktif_cls)
        self._duygu_gecmis.append(duygu)

        # ── Rota Ağırlıkları (duygu tabanlı) ─────────────────────────
        w_e, w_t, w_c = self.duygu_motoru.rota_agirliklari(self._aktif_cls)

        # ── Rota Hesapla ──────────────────────────────────────────────
        rotalar = {}
        for k in ["mesafe", "sure", "enerji"]:
            yol, _ = self.graf.dijkstra(bas, bit, k)
            rotalar[k] = yol

        mo_yol, _ = self.graf.cok_amacli_dijkstra(bas, bit, w_e, w_t, w_c)
        if mo_yol:
            rotalar["mo"] = mo_yol

        # ── En İyi Rota Seçimi ────────────────────────────────────────
        met_tum   = {k: yol_metrikleri(v, self.arac_adi) for k, v in rotalar.items() if v}
        konfor_sk = {
            k: CokAmacliRotaOptimizatoru.rota_konfor_skoru(v, ANKARA_DUGUMLER, YOLLAR)
            for k, v in rotalar.items() if v
        }
        en_iyi_krit, f_skor, detay = CokAmacliRotaOptimizatoru.en_iyi_rota_sec(
            rotalar, met_tum, konfor_sk, self._aktif_cls
        )
        aktif_yol = rotalar.get(en_iyi_krit, rotalar.get("enerji", []))

        # ── GPS Kaydını Başlat ────────────────────────────────────────
        self.kaydedici.sefer_baslat(self.uid)
        # Simüle GPS noktaları ekle (gerçek uygulamada GPS alıcısından gelir)
        import random
        for nokta in self.gps_sim.rota_sim_noktalari(aktif_yol, hiz_kmsa=50.0):
            self.kaydedici.nokta_ekle(nokta["lat"], nokta["lon"], nokta["hiz_kmsa"])
            self.kaydedici.tampon._son_kayit_zamani -= 2  # simülasyon hızlandır

        return {
            "rota":         aktif_yol,
            "krit":         en_iyi_krit,
            "metrikleri":   met_tum.get(en_iyi_krit, {}),
            "cls":          round(self._aktif_cls, 1),
            "duygu":        duygu,
            "agirliklar":   {"w_e": w_e, "w_t": w_t, "w_c": w_c},
            "f_skor":       round(f_skor, 4),
        }

    # ── Sefer Bitir ───────────────────────────────────────────────────
    def sefer_bitir(self, rota: list) -> dict:
        """
        Seferi sonlandırır, tüm modüllerin geri besleme döngüsünü tetikler.
        """
        # CLS geçmişini topla
        cls_gecmis = self.cls_analizci._cls_gecmis or [self._aktif_cls]

        # 1. GPS verisini anonim kaydet
        ozet = self.kaydedici.sefer_bitir(
            cls_gecmis=cls_gecmis,
            rota_dugum_listesi=rota,
            arac_adi=self.arac_adi,
            mod=cls_to_mod(self._aktif_cls),
        )

        # 2. ML modeline gerçek CLS ile geri besleme
        ort_cls = sum(cls_gecmis) / len(cls_gecmis) if cls_gecmis else self._aktif_cls
        self.cls_analizci.geri_besleme_ver(ort_cls)

        # 3. Duygu motoru için geri besleme
        gercek_duygu = self.duygu_motoru.duygu_tahmin(ort_cls)
        from duygu_regresyonu import duygu_ozellik_vektoru
        import numpy as np
        feat = duygu_ozellik_vektoru(cls=ort_cls, onceki_cls_ort=ort_cls)
        self.duygu_motoru.geri_besleme_ekle(feat, gercek_duygu)

        # 4. Profil güncelle
        self.pm.profil_guncelle(
            self.uid, ort_cls,
            ozet.get("mesafe_km", 0) if ozet else 0, 1.0
        )

        # 5. Sefer duygu özeti
        duygu_ozeti = SurekliDuyguMotoru.sefer_duygu_ozeti(self._duygu_gecmis)

        return {
            "sefer_ozeti":   ozet,
            "duygu_ozeti":   duygu_ozeti,
            "cls_ort":       round(ort_cls, 1),
            "ozellik_raporu": self.cls_analizci.ozellik_raporu(),
        }


# ─────────────────────────────────────────────────────────────────────
#  EXPERIMENT_RUN.PY İÇİN GELİŞTİRİLMİŞ VERSİYON
# ─────────────────────────────────────────────────────────────────────
def run_gelismis_experiment():
    """
    experiment_run.py'yi üç yeni modülle genişletir.
    Klasik Dijkstra + ÇAMD karşılaştırmasına ek olarak:
        - ML tabanlı CLS tahmini
        - Sürekli duygu vektörü tabanlı ağırlıklar
        - Anonim GPS kayıt istatistikleri
    """
    with open("gelismis_deneysel_sonuclar.md", "w", encoding="utf-8") as f:
        def w(text=""):
            f.write(text + "\n")

        w("# Geliştirilmiş Deneysel Sonuçlar — ML + Sürekli Duygu\n")
        w("Bu rapor; Random Forest tabanlı CLS tahmini ve sürekli duygu regresyonu "
          "ile elde edilen rota optimizasyon sonuçlarını klasik ÇAMD ile karşılaştırır.\n")

        senaryolar = [
            ("Kızılay", "Çayyolu",             "Orta Mesafe - Şehir İçi"),
            ("Ulus",    "Gölbaşı",             "Orta-Uzun Mesafe - Çevre Yolu"),
            ("Bilkent", "Esenboğa Havalimanı", "Uzun Mesafe - Karma Yol"),
        ]
        cls_durumlari = [
            (15.0, "Enerjik   (CLS=15)"),
            (45.0, "Nötr      (CLS=45)"),
            (75.0, "Yorgun    (CLS=75)"),
        ]

        graf        = Graf()
        arac        = "Tesla Model 3"
        duygu_motor = SurekliDuyguMotoru()
        ml_motor    = OgrenebilirCLSMotoru()

        for (bas, bit, aciklama) in senaryolar:
            w(f"## Senaryo: {bas} ➔ {bit} ({aciklama})")

            for cls_val, cls_isim in cls_durumlari:
                # ── Klasik ÇAMD ────────────────────────────────────────
                w_e_h, w_t_h, w_c_h = CokAmacliRotaOptimizatoru.agirlik_hesapla(cls_val)

                # ── ML Tabanlı CLS (tahmin edilen değer)
                ml_cls = ml_motor.tahmin_et(
                    ear_norm  = cls_val * 0.8,
                    blink_norm= cls_val * 0.5,
                    kas_norm  = cls_val * 0.6,
                    saat      = 9,
                )

                # ── Sürekli Duygu Ağırlıkları ──────────────────────────
                w_e_d, w_t_d, w_c_d = duygu_motor.rota_agirliklari(cls_val)
                duygu = duygu_motor.duygu_tahmin(cls_val)

                # ── Rotalar ────────────────────────────────────────────
                rotalar = {}
                for k in ["mesafe", "sure", "enerji"]:
                    yol, _ = graf.dijkstra(bas, bit, k)
                    rotalar[k] = yol

                # ÇAMD rotası
                camd_yol, _ = graf.cok_amacli_dijkstra(bas, bit, w_e_h, w_t_h, w_c_h)
                if camd_yol:
                    rotalar["camd"] = camd_yol

                # ML+Duygu rotası
                ml_yol, _ = graf.cok_amacli_dijkstra(bas, bit, w_e_d, w_t_d, w_c_d)
                if ml_yol:
                    rotalar["ml_duygu"] = ml_yol

                # Metrik + konfor
                met   = {k: yol_metrikleri(v, arac) for k, v in rotalar.items() if v}
                konfor = {
                    k: CokAmacliRotaOptimizatoru.rota_konfor_skoru(v, ANKARA_DUGUMLER, YOLLAR)
                    for k, v in rotalar.items() if v
                }

                w(f"### {cls_isim}")
                w(f"**ML Tahmini CLS:** {ml_cls:.1f}  |  "
                  f"Duygu: yor={duygu['yorgunluk']:.2f} str={duygu['stres']:.2f} "
                  f"sak={duygu['sakinlik']:.2f} ene={duygu['enerji']:.2f}\n")
                w(f"**ÇAMD Ağırlıkları:**  Enerji={w_e_h:.2%} Süre={w_t_h:.2%} Konfor={w_c_h:.2%}")
                w(f"**ML+Duygu Ağırlıkları:** Enerji={w_e_d:.2%} Süre={w_t_d:.2%} Konfor={w_c_d:.2%}\n")

                w("| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |")
                w("|--------|--------|------|--------|--------|--------|------|")

                isimler = {
                    "mesafe":    "B1: Kısa Yol",
                    "sure":      "B2: Hızlı Yol",
                    "enerji":    "B3: Eko Rota",
                    "camd":      "ÇAMD (Heuristik)",
                    "ml_duygu":  "**ML+Duygu (Önerilen)**",
                }

                for k, isim in isimler.items():
                    if k not in met:
                        continue
                    r  = met[k]
                    c  = konfor.get(k, 0.5)
                    fh = CokAmacliRotaOptimizatoru.f_objective(
                        r["enerji_kwh"], r["sure_dk"], c, w_e_h, w_t_h, w_c_h)
                    fd = CokAmacliRotaOptimizatoru.f_objective(
                        r["enerji_kwh"], r["sure_dk"], c, w_e_d, w_t_d, w_c_d)
                    w(f"| {isim} | {r['mesafe_km']} km | {r['sure_dk']} dk | "
                      f"{r['enerji_kwh']} kWh | {c:.3f} | {fh:.4f} | {fd:.4f} |")
                w("")

        w("\n## Anonim Veri Kayıt İstatistikleri\n")
        kaydedici = SurusVeriKaydedici()
        ist = kaydedici.genel_istatistik()
        if ist:
            for k, v in ist.items():
                w(f"- **{k}**: {v}")
        else:
            w("- Henüz kayıtlı sefer yok (modüller ilk çalıştırılıyor).")

        w("\n## Özellik Önemleri (CLS ML Modeli)\n")
        ml = OgrenebilirCLSMotoru()
        for isim, onem in list(ml.ozellik_onem_raporu().items())[:7]:
            bar = "█" * int(onem * 50)
            w(f"- `{isim:30s}` {onem:.4f}  {bar}")

        w("\n## ML Model Performansı (5-fold CV)\n")
        perf = ml.model_performans_raporla()
        for k, v in perf.items():
            w(f"- **{k}**: {v}")

    print("Geliştirilmiş sonuçlar 'gelismis_deneysel_sonuclar.md' dosyasına kaydedildi.")


# ─────────────────────────────────────────────────────────────────────
#  EV_ROTA_PLANNER.PY'ye YAPILMASI GEREKEN DEĞİŞİKLİKLER
# ─────────────────────────────────────────────────────────────────────
ENTEGRASYON_YAMASI = """
# ═══════════════════════════════════════════════════════════════════════
#  ev_rota_planner.py  — Gerekli Değişiklikler  (yorum bloğu)
# ═══════════════════════════════════════════════════════════════════════
#
# 1. İmport Bloğuna Ekle (try/except ile opsiyonel bırak):
#
#    try:
#        from suruş_veri_kaydedici import SurusVeriKaydedici, GpsSimulatoru
#        from cls_ml_modeli         import MLDestekliKognitivYukAnalizci
#        from duygu_regresyonu      import SurekliDuyguMotoru, cls_ve_duygu_ile_optimize
#        GELISMIS_VAR = True
#    except ImportError:
#        GELISMIS_VAR = False
#
#
# 2. EVRotaGUI.__init__() içinde (KOGNITIF_VAR bloğunun hemen altına):
#
#    if GELISMIS_VAR:
#        self.kaydedici   = SurusVeriKaydedici()
#        self.duygu_motor = SurekliDuyguMotoru(
#            self.pm.profil_al(self.aktif_uid) if self.pm else None
#        )
#        # Mevcut KognitivYukAnalizci'yi ML desteklisiyle değiştir:
#        if self.kognitif_aktif and self.aktif_uid:
#            profil = self.pm.profil_al(self.aktif_uid) or {}
#            self.analizci = MLDestekliKognitivYukAnalizci(profil)
#
#
# 3. rota_ciz() içinde — CLS ağırlık hesabını sürekli duygu ile değiştir:
#
#    if GELISMIS_VAR and hasattr(self, 'duygu_motor'):
#        # Eski satır:  w_e, w_t, w_c = CokAmacliRotaOptimizatoru.agirlik_hesapla(self.aktif_cls)
#        # Yeni satır:
#        w_e, w_t, w_c = self.duygu_motor.rota_agirliklari(self.aktif_cls)
#        duygu = self.duygu_motor.duygu_tahmin(self.aktif_cls)
#        # duygu["dominant"] ve duygu["mod"] GUI'da gösterilebilir
#
#
# 4. rota_ciz() sonunda — GPS kaydı başlat:
#
#    if GELISMIS_VAR and hasattr(self, 'kaydedici'):
#        self.kaydedici.sefer_baslat(self.aktif_uid)
#        for nokta in GpsSimulatoru(ANKARA_DUGUMLER).rota_sim_noktalari(aktif_yol):
#            self.kaydedici.nokta_ekle(nokta["lat"], nokta["lon"], nokta["hiz_kmsa"])
#        # Sefer bitişinde (pencere kapanırken veya varış butonu ile):
#        self.kaydedici.sefer_bitir(
#            cls_gecmis=self.analizci._cls_gecmis,
#            rota_dugum_listesi=aktif_yol,
#            arac_adi=arac,
#            mod=self.aktif_mod
#        )
#
# ═══════════════════════════════════════════════════════════════════════
"""


# ─────────────────────────────────────────────────────────────────────
#  DEMO ÇALIŞTIRICI
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  AffectEV — Geliştirilmiş Sistem Demo")
    print("=" * 60)

    print("\n[1/3] Geliştirilmiş rota optimizasyonu deniyor...")
    try:
        opt = GelistirilmisRotaOptimizatoru(uid="U01", arac_adi="Tesla Model 3")
        sonuc = opt.sefer_baslat("Kızılay", "Çayyolu")
        print(f"  ✅  Rota: {' → '.join(sonuc['rota'][:4])}...")
        print(f"  CLS={sonuc['cls']}  Mod={sonuc['duygu']['mod']}")
        print(f"  Duygu: yor={sonuc['duygu']['yorgunluk']:.2f} "
              f"str={sonuc['duygu']['stres']:.2f} "
              f"sak={sonuc['duygu']['sakinlik']:.2f} "
              f"ene={sonuc['duygu']['enerji']:.2f}")
        print(f"  Ağırlıklar: E={sonuc['agirliklar']['w_e']:.2f} "
              f"T={sonuc['agirliklar']['w_t']:.2f} "
              f"C={sonuc['agirliklar']['w_c']:.2f}")
        bitis = opt.sefer_bitir(sonuc["rota"])
        print(f"  Sefer kaydedildi. Duygu özeti: {bitis.get('duygu_ozeti', {}).get('ort', {})}")
    except Exception as e:
        print(f"  ⚠️  Hata: {e}")

    print("\n[2/3] Geliştirilmiş deney raporu oluşturuluyor...")
    try:
        run_gelismis_experiment()
    except Exception as e:
        print(f"  ⚠️  Hata: {e}")

    print("\n[3/3] Entegrasyon yamalarını göster:")
    print(ENTEGRASYON_YAMASI[:500] + "\n  ...")

    print("\n✅  Demo tamamlandı.")
    print("  Oluşturulan dosyalar:")
    print("    gelismis_deneysel_sonuclar.md")
    print("    modeller/cls_rf_model.joblib")
    print("    modeller/duygu_regresyon_model.joblib")
    print("    veri/suruc_seferler.json")