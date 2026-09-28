"""
cls_ml_modeli.py  —  AffectEV  Makine Öğrenmesi Tabanlı CLS Tahmini
====================================================================
Heuristik CLS formülünü Random Forest regresyonu ile ÖĞRENEN,
kişiselleştirilebilir bir CLS tahmin motoruna yükseltir.

Kurulum:
    pip install scikit-learn numpy joblib

Mimari:
    ┌────────────────────────────────────────────────────────────────┐
    │  Özellik Vektörü  (13 özellik)                                 │
    │      ↓                                                         │
    │  RandomForestRegressor  (CLS tahmini — regresyon)              │
    │      ↓                                                         │
    │  CLS ∈ [0, 100]                                                │
    │                                                                │
    │  Geri besleme döngüsü:                                         │
    │    yeni sefer → etiketlenmiş örnek → online fine-tune          │
    └────────────────────────────────────────────────────────────────┘

Neden Random Forest?
    - Tabular / karma veri için güçlü temel hat
    - Az hiperparametre ayarı gerektirir
    - Özellik önemini kolayca raporlar (sürücü içgörüsü)
    - Eğitim verisi az olduğunda dahi çalışır (ensemble)
    - Gerçek zamanlı tahmin < 1 ms

Özellikler (13 boyut):
    Biyometrik (3): ear_norm, blink_norm, kas_norm
    Bağlamsal  (4): saat_norm, gun_tipi_enc, is_gunu, gun_yorgunluk
    Geçmiş     (3): son_5_cls_ort, son_cls_trend, bugun_km_norm
    Kişisel    (3): stres_egilimi, yorgunluk_esigi_norm, yas_norm
"""

import json
import math
import os
import random
import threading
import warnings
warnings.filterwarnings("ignore") # Sürüm uyarılarını terminalde kalabalık yapmaması için gizler
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    import joblib
    SKLEARN_VAR = True
except ImportError:
    SKLEARN_VAR = False
    warnings.warn("scikit-learn bulunamadı. CLS ML motoru heuristik modda çalışır.")

# ─────────────────────────────────────────────────────────────────────
#  YAPILANDIRMA
# ─────────────────────────────────────────────────────────────────────
MODEL_KLASORU   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeller")
MODEL_DOSYASI   = os.path.join(MODEL_KLASORU, "cls_rf_model.joblib")
SCALER_DOSYASI  = os.path.join(MODEL_KLASORU, "cls_rf_scaler.joblib")
VERI_DOSYASI    = os.path.join(MODEL_KLASORU, "cls_egitim_verisi.json")

MIN_EGITIM_ORNEGI = 30     # Bu kadar örnek birikmeden ML modeli kullanılmaz
ONLINE_FINETUNE_ARALIK = 10  # Her bu kadar yeni örnekte modeli yeniden eğit

# ─────────────────────────────────────────────────────────────────────
#  ÖZELLİK MÜHENDİSLİĞİ
# ─────────────────────────────────────────────────────────────────────
def ozellik_vektoru_olustur(
    # Biyometrik sinyaller
    ear_norm:      float = 50.0,   # Göz açıklık sapması ∈ [0, 100]
    blink_norm:    float = 20.0,   # Göz kırpma sapması ∈ [0, 100]
    kas_norm:      float = 20.0,   # Kaş kasılma normu ∈ [0, 100]
    # Bağlamsal değişkenler
    saat:          int   = 12,     # 0-23
    gun_tipi:      str   = "sabahçı",  # sabahçı / gece / karma
    is_gunu:       bool  = True,
    # Geçmiş & kişisel
    son_cls_gecmis: List[float] = None,  # son N CLS değeri
    bugun_km:      float = 0.0,
    stres_egilimi: float = 0.40,
    yorgunluk_esigi: float = 60.0,
    yas:           int   = 35,
) -> np.ndarray:
    """
    Ham sensör/bağlam bilgisini 13 boyutlu özellik vektörüne dönüştürür.
    Tüm değerler [0, 1] aralığına normalize edilir.
    """
    # 1. Göz açıklık normu (0-100 → 0-1)
    f_ear   = np.clip(ear_norm   / 100.0, 0, 1)
    # 2. Göz kırpma normu (0-100 → 0-1)
    f_blink = np.clip(blink_norm / 100.0, 0, 1)
    # 3. Kaş kasılma normu (0-100 → 0-1)
    f_kas   = np.clip(kas_norm   / 100.0, 0, 1)

    # 4. Saat normu — 24 saatlik döngüsel kodlama (sin + cos)
    saat_sin = (math.sin(2 * math.pi * saat / 24) + 1) / 2
    saat_cos = (math.cos(2 * math.pi * saat / 24) + 1) / 2

    # 5. Gün tipi one-hot (sabahçı=0, gece=1, karma=2) → 0-1
    gun_tipi_enc = {"sabahçı": 0.0, "gece": 1.0, "karma": 0.5}.get(gun_tipi, 0.0)

    # 6. İş günü (True=1, False=0)
    f_is_gunu = 1.0 if is_gunu else 0.0

    # 7. Son 5 CLS ortalaması
    if son_cls_gecmis and len(son_cls_gecmis) >= 1:
        son_5 = son_cls_gecmis[-5:]
        f_son_cls_ort = np.clip(sum(son_5) / len(son_5) / 100.0, 0, 1)
    else:
        f_son_cls_ort = 0.4   # nötr baz

    # 8. CLS trendi (son 5 ölçümün doğrusal eğimi, normalize)
    if son_cls_gecmis and len(son_cls_gecmis) >= 5:
        egim = (son_cls_gecmis[-1] - son_cls_gecmis[-5]) / 4.0
        f_trend = np.clip((egim + 20) / 40.0, 0, 1)   # [-20, +20] → [0, 1]
    else:
        f_trend = 0.5

    # 9. Bugün sürülen km (maks 200 km'ye normalize)
    f_bugun_km = np.clip(bugun_km / 200.0, 0, 1)

    # 10. Kişisel stres eğilimi (zaten 0-1)
    f_stres = np.clip(stres_egilimi, 0, 1)

    # 11. Yorgunluk eşiği (0-100 → 0-1, tersine çevrilmiş: düşük eşik = kolay yorulur)
    f_yor_esik = 1.0 - np.clip(yorgunluk_esigi / 100.0, 0, 1)

    # 12. Yaş normu (18-80 arası, normalize)
    f_yas = np.clip((yas - 18) / 62.0, 0, 1)

    return np.array([
        f_ear, f_blink, f_kas,
        saat_sin, saat_cos, gun_tipi_enc, f_is_gunu,
        f_son_cls_ort, f_trend, f_bugun_km,
        f_stres, f_yor_esik, f_yas,
    ], dtype=np.float32)


OZELLIK_ISIMLERI = [
    "ear_norm", "blink_norm", "kas_norm",
    "saat_sin", "saat_cos", "gun_tipi_enc", "is_gunu",
    "son_cls_ort", "cls_trend", "bugun_km_norm",
    "stres_egilimi", "yorgunluk_esigi_inv", "yas_norm",
]


# ─────────────────────────────────────────────────────────────────────
#  SENTETİK EĞİTİM VERİSİ ÜRETECİ
# ─────────────────────────────────────────────────────────────────────
def sentetik_egitim_verisi_uret(n: int = 500, tohum: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Heuristik CLS formülünü (mevcut kognitif_motor.py mantığı) öğretici etiket
    olarak kullanarak sentetik eğitim veri seti üretir.

    Bu sayede:
        1. Başlangıçta sıfır gerçek veri ile model eğitilebilir.
        2. Gerçek veriler geldikçe model fine-tune edilir.

    Parametre
    ---------
    n : Üretilecek örnek sayısı.
    """
    rng = random.Random(tohum)
    X, y = [], []

    for _ in range(n):
        # Rastgele özellik değerleri üret
        ear_norm    = rng.gauss(30, 25)
        blink_norm  = rng.gauss(20, 15)
        kas_norm    = rng.gauss(25, 20)
        saat        = rng.randint(0, 23)
        gun_tipi    = rng.choice(["sabahçı", "gece", "karma"])
        is_gunu     = rng.random() > 0.28
        stres_egil  = rng.uniform(0.15, 0.80)
        yor_esik    = rng.uniform(40, 90)
        yas         = rng.randint(20, 65)
        bugun_km    = rng.gauss(35, 20)
        gecmis_cls  = [rng.gauss(40, 15) for _ in range(rng.randint(0, 10))]

        # Heuristik CLS etiketi (mevcut sistemin formülünden)
        # Göz + kırpma + kas + bağlamsal bileşeni
        baz_cls = {"yorgun": 65, "stresli": 58, "notr": 40, "enerjik": 22}.get(
            "stresli" if stres_egil > 0.6 else ("enerjik" if stres_egil < 0.25 else "notr"), 40)

        # Trafik saati etkisi
        if saat in (8, 9, 17, 18, 19):
            baz_cls = min(100, baz_cls + stres_egil * 20)

        # Gün tipi etkisi
        if gun_tipi == "sabahçı" and saat >= 21:
            baz_cls = min(100, baz_cls + (saat - 20) * 7)
        elif gun_tipi == "gece" and saat <= 5:
            baz_cls = min(100, baz_cls + (6 - saat) * 10)

        # Km etkisi
        km_etki = min(40, max(0, bugun_km) / 150 * 40)
        esik_etki = max(0, (60 - yor_esik) * 0.4)

        konteks = min(95, max(0, baz_cls + km_etki + esik_etki))

        # Ağırlıklı CLS
        cls = (0.45 * np.clip(ear_norm, 0, 100)
             + 0.25 * np.clip(blink_norm, 0, 100)
             + 0.20 * np.clip(kas_norm, 0, 100)
             + 0.10 * konteks)
        cls = float(np.clip(cls + rng.gauss(0, 3), 0, 100))

        feat = ozellik_vektoru_olustur(
            ear_norm=ear_norm, blink_norm=blink_norm, kas_norm=kas_norm,
            saat=saat, gun_tipi=gun_tipi, is_gunu=is_gunu,
            son_cls_gecmis=gecmis_cls, bugun_km=max(0, bugun_km),
            stres_egilimi=stres_egil, yorgunluk_esigi=yor_esik, yas=yas,
        )
        X.append(feat)
        y.append(cls)

    return np.array(X), np.array(y)


# ─────────────────────────────────────────────────────────────────────
#  ÖĞRENEN CLS MOTORU
# ─────────────────────────────────────────────────────────────────────
class OgrenebilirCLSMotoru:
    """
    Random Forest + online fine-tune ile kişiselleşen CLS tahmincisi.

    Başlatma Akışı:
        1. Kaydedilmiş model varsa yükler.
        2. Yoksa sentetik veriyle ilk modeli eğitir.
        3. Gerçek sürüş örnekleri geldikçe periyodik olarak yeniden eğitir.
    """

    def __init__(self, profil: Optional[Dict] = None):
        """
        profil : SurucuProfilYonetici'den gelen sürücü profil sözlüğü.
                 None ise varsayılan değerler kullanılır.
        """
        self.profil   = profil or {}
        self._model   = None     # RandomForestRegressor
        self._scaler  = None     # StandardScaler
        self._kilit   = threading.Lock()
        self._ornekler: List[Tuple[np.ndarray, float]] = []   # (X, y)
        self._yeni_ornek_sayisi = 0

        os.makedirs(MODEL_KLASORU, exist_ok=True)

        if SKLEARN_VAR:
            self._model_yukle_veya_egit()

    # ── Model Yükleme / İlk Eğitim ────────────────────────────────────
    def _model_yukle_veya_egit(self):
        """Kaydedilmiş model varsa yükler; yoksa sentetik veriyle eğitir."""
        if os.path.exists(MODEL_DOSYASI) and os.path.exists(SCALER_DOSYASI):
            try:
                self._model  = joblib.load(MODEL_DOSYASI)
                self._scaler = joblib.load(SCALER_DOSYASI)
                # Kaydedilmiş örnekleri de yükle
                if os.path.exists(VERI_DOSYASI):
                    with open(VERI_DOSYASI, "r") as f:
                        kayitli = json.load(f)
                    self._ornekler = [
                        (np.array(x, dtype=np.float32), y)
                        for x, y in zip(kayitli["X"], kayitli["y"])
                    ]
                return
            except Exception:
                pass
        # İlk eğitim — sentetik veri ile başla
        self._ilk_egitim()

    def _ilk_egitim(self, n_sentetik: int = 800):
        """Sentetik veriyle sıfırdan model oluşturur."""
        X, y = sentetik_egitim_verisi_uret(n=n_sentetik)
        self._egit(X, y, kaydet=True)

    # ── Model Eğitimi ──────────────────────────────────────────────────
    def _egit(self, X: np.ndarray, y: np.ndarray, kaydet: bool = True):
        """Random Forest regresyonu eğitir ve isteğe bağlı kaydeder."""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        rf = RandomForestRegressor(
            n_estimators=120,
            max_depth=12,
            min_samples_leaf=3,
            n_jobs=-1,
            random_state=42,
        )
        rf.fit(X_scaled, y)

        with self._kilit:
            self._model  = rf
            self._scaler = scaler

        if kaydet:
            joblib.dump(rf,     MODEL_DOSYASI)
            joblib.dump(scaler, SCALER_DOSYASI)
            self._ornekleri_kaydet()

    def _ornekleri_kaydet(self):
        """Birikmiş örnekleri JSON'a kaydeder."""
        try:
            with open(VERI_DOSYASI, "w") as f:
                json.dump({
                    "X": [x.tolist() for x, _ in self._ornekler],
                    "y": [y for _, y in self._ornekler],
                    "kayit": datetime.now().isoformat(),
                }, f)
        except OSError:
            pass

    # ── Yeni Örnek Ekle & Online Fine-tune ────────────────────────────
    def geri_besleme_ekle(self, ozellik_vektoru: np.ndarray, gercek_cls: float):
        """
        Gerçek bir sürüş seferinden gelen (özellik, CLS) çiftini biriktirir.
        ONLINE_FINETUNE_ARALIK örnekte bir yeniden eğitim tetikler.
        """
        if not SKLEARN_VAR:
            return

        with self._kilit:
            self._ornekler.append((ozellik_vektoru.copy(), float(gercek_cls)))
            # Son 2000 örneği tut (bellek sınırı)
            if len(self._ornekler) > 2000:
                self._ornekler = self._ornekler[-2000:]
            self._yeni_ornek_sayisi += 1

        if self._yeni_ornek_sayisi >= ONLINE_FINETUNE_ARALIK:
            threading.Thread(target=self._online_finetune, daemon=True).start()
            self._yeni_ornek_sayisi = 0

    def _online_finetune(self):
        """
        Birikmiş gerçek + sentetik örneklerle modeli arka planda yeniden eğitir.
        """
        with self._kilit:
            ornekler_snapshot = list(self._ornekler)

        if len(ornekler_snapshot) < MIN_EGITIM_ORNEGI:
            return

        # Gerçek örnekleri sentetiklerle birleştir (dengeleme)
        X_gercek = np.array([x for x, _ in ornekler_snapshot])
        y_gercek = np.array([y for _, y in ornekler_snapshot])
        X_sin, y_sin = sentetik_egitim_verisi_uret(n=200)

        X_birlesik = np.vstack([X_sin, X_gercek])
        y_birlesik = np.concatenate([y_sin, y_gercek])

        self._egit(X_birlesik, y_birlesik, kaydet=True)

    # ── Tahmin ────────────────────────────────────────────────────────
    def tahmin_et(self,
                  ear_norm: float = 50.0,
                  blink_norm: float = 20.0,
                  kas_norm: float = 20.0,
                  saat: Optional[int] = None,
                  gun_tipi: str = "sabahçı",
                  is_gunu: bool = True,
                  son_cls_gecmis: Optional[List[float]] = None,
                  bugun_km: float = 0.0) -> float:
        """
        Özellik değerlerinden CLS tahmini yapar.

        ML modeli kullanılamıyorsa (sklearn yok veya yeterli veri yok)
        otomatik olarak heuristik geri dönüşe geçer.

        Dönüş
        -----
        cls ∈ [0, 100]
        """
        if saat is None:
            saat = datetime.now().hour

        profil_bilgisi = {
            "stres_egilimi":  self.profil.get("stres_egilimi", 0.40),
            "yorgunluk_esigi": self.profil.get("yorgunluk_esigi", 60.0),
            "yas":            self.profil.get("yas", 35),
        }

        feat = ozellik_vektoru_olustur(
            ear_norm=ear_norm, blink_norm=blink_norm, kas_norm=kas_norm,
            saat=saat, gun_tipi=gun_tipi, is_gunu=is_gunu,
            son_cls_gecmis=son_cls_gecmis or [], bugun_km=bugun_km,
            **profil_bilgisi,
        )

        if SKLEARN_VAR and self._model is not None and self._scaler is not None:
            with self._kilit:
                X_scaled = self._scaler.transform(feat.reshape(1, -1))
                cls = float(self._model.predict(X_scaled)[0])
            return float(np.clip(cls, 0.0, 100.0))

        # Heuristik geri dönüş
        return self._heuristik_cls(ear_norm, blink_norm, kas_norm, saat, gun_tipi)

    @staticmethod
    def _heuristik_cls(ear_norm: float, blink_norm: float, kas_norm: float,
                        saat: int, gun_tipi: str) -> float:
        """Mevcut kognitif_motor.py mantığı — sklearn olmadan çalışır."""
        if gun_tipi == "sabahçı" and saat >= 21:
            konteks = (saat - 20) * 7
        elif gun_tipi == "gece" and saat <= 5:
            konteks = (6 - saat) * 10
        elif saat in (8, 9, 17, 18, 19):
            konteks = 20
        else:
            konteks = 0
        cls = 0.45 * ear_norm + 0.25 * blink_norm + 0.20 * kas_norm + 0.10 * konteks
        return float(np.clip(cls, 0, 100))

    # ── Özellik Önem Raporu ───────────────────────────────────────────
    def ozellik_onem_raporu(self) -> Dict[str, float]:
        """
        Random Forest özellik önemlerini döndürür.
        Hangi sinyalin CLS'yi daha çok etkilediğini gösterir.
        """
        if not SKLEARN_VAR or self._model is None:
            return {}
        importances = self._model.feature_importances_
        return {
            isim: round(float(imp), 4)
            for isim, imp in sorted(
                zip(OZELLIK_ISIMLERI, importances),
                key=lambda x: x[1], reverse=True
            )
        }

    # ── Cross-Validation Skoru ────────────────────────────────────────
    def model_performans_raporla(self) -> Dict:
        """
        5-katlı çapraz doğrulama ile model RMSE'sini raporlar.
        Gerçek veri yetersizse sentetik veri kullanılır.
        """
        if not SKLEARN_VAR:
            return {"hata": "scikit-learn kurulu değil"}
        with self._kilit:
            ornekler = list(self._ornekler)
        if len(ornekler) < MIN_EGITIM_ORNEGI:
            X, y = sentetik_egitim_verisi_uret(n=300)
        else:
            X = np.array([x for x, _ in ornekler])
            y = np.array([y for _, y in ornekler])
        X_s = StandardScaler().fit_transform(X)
        skorlar = cross_val_score(
            RandomForestRegressor(n_estimators=50, random_state=42),
            X_s, y, cv=5, scoring="neg_root_mean_squared_error",
        )
        return {
            "rmse_ort": round(-skorlar.mean(), 2),
            "rmse_std": round(skorlar.std(), 2),
            "n_ornek":  len(y),
            "mod":      "ML (Random Forest)" if len(ornekler) >= MIN_EGITIM_ORNEGI else "Sentetik",
        }


# ─────────────────────────────────────────────────────────────────────
#  KAYNAŞTIRMALı CLS ANALİZCİSİ
#  (Mevcut KognitivYukAnalizci ile entegrasyon için sarmalayıcı)
# ─────────────────────────────────────────────────────────────────────
class MLDestekliKognitivYukAnalizci:
    """
    Mevcut KognitivYukAnalizci ile OgrenebilirCLSMotoru'nu birleştirir.

    Geri uyumlu: Dışarıdan KognitivYukAnalizci gibi görünür.
    anlik_cls() → ML tahminini döndürür.
    """

    def __init__(self, profil: Dict):
        self.profil       = profil
        self.ml_motor     = OgrenebilirCLSMotoru(profil)
        self._son_cls     = 45.0
        self._cls_gecmis: List[float] = []
        # Mevcut OpenCV analizciyi opsiyonel olarak yükle
        try:
            from kognitif_motor import KognitivYukAnalizci, CV2_VAR
            if CV2_VAR:
                self._cv2_analizci = KognitivYukAnalizci(profil)
            else:
                self._cv2_analizci = None
        except ImportError:
            self._cv2_analizci = None

    def anlik_cls(self) -> float:
        """
        Anlık CLS değeri döndürür.
        OpenCV varsa ham biyometrik sinyalleri ML motoruna besler;
        yoksa bağlamsal değişkenlerle tahmin üretir.
        """
        bio = self.profil.get("biyometrik", {})
        saat = datetime.now().hour
        gun_tipi = self.profil.get("gun_ici_tip", "sabahçı")
        bugun_km = sum(
            s.get("km", 0)
            for g in self.profil.get("suruc_gecmis", [])[-1:]
            for s in g.get("seferler", [])
        )

        # OpenCV sinyalleri mevcutsa ondan al, yoksa sentetik üret
        if hasattr(self, '_cv2_analizci') and self._cv2_analizci and hasattr(self._cv2_analizci, '_son_sinyaller'):
            sinyaller = self._cv2_analizci._son_sinyaller
            ear_norm   = sinyaller.get("ear_norm", 30.0)
            kas_norm   = sinyaller.get("kas_norm", 25.0)
            # Göz kırpma verisi kognitif motorda ayrı tutulmuyor, ear_norm üzerinden simüle edilebilir
            blink_norm = 20.0 + (ear_norm * 0.2) 
        else:
            ear_norm   = random.gauss(30, 20)
            blink_norm = random.gauss(20, 15)
            kas_norm   = random.gauss(25, 20)

        cls = self.ml_motor.tahmin_et(
            ear_norm=float(np.clip(ear_norm, 0, 100)),
            blink_norm=float(np.clip(blink_norm, 0, 100)),
            kas_norm=float(np.clip(kas_norm, 0, 100)),
            saat=saat,
            gun_tipi=gun_tipi,
            is_gunu=datetime.now().weekday() < 5,
            son_cls_gecmis=self._cls_gecmis,
            bugun_km=bugun_km,
        )

        # Smoothing
        if len(self._cls_gecmis) >= 3:
            cls = 0.75 * cls + 0.25 * self._cls_gecmis[-1]

        cls = float(np.clip(cls + random.gauss(0, 1.5), 0, 100))
        self._son_cls = round(cls, 1)
        self._cls_gecmis.append(cls)
        if len(self._cls_gecmis) > 30:
            self._cls_gecmis.pop(0)

        return self._son_cls

    def kamera_baslat(self) -> bool:
        """Gerçek zamanlı analizci varsa kamerasını başlatır."""
        if hasattr(self, '_cv2_analizci') and self._cv2_analizci:
            return self._cv2_analizci.kamera_baslat()
        return False

    def kamera_durdur(self):
        """Gerçek zamanlı analizci varsa kamerasını durdurur."""
        if hasattr(self, '_cv2_analizci') and self._cv2_analizci:
            self._cv2_analizci.kamera_durdur()

    def geri_besleme_ver(self, gercek_cls: float):
        """
        Sürüş sonrası gözlemlenen gerçek CLS ile modeli günceller.
        SurusVeriKaydedici'nin sefer_bitir() çıktısından çağrılabilir.
        """
        bio = self.profil.get("biyometrik", {})
        saat = datetime.now().hour
        feat = ozellik_vektoru_olustur(
            saat=saat,
            gun_tipi=self.profil.get("gun_ici_tip", "sabahçı"),
            son_cls_gecmis=self._cls_gecmis,
            stres_egilimi=self.profil.get("stres_egilimi", 0.4),
            yorgunluk_esigi=self.profil.get("yorgunluk_esigi", 60.0),
            yas=self.profil.get("yas", 35),
        )
        self.ml_motor.geri_besleme_ekle(feat, gercek_cls)

    def cls_ortalama(self, n: int = 5) -> float:
        if not self._cls_gecmis:
            return self._son_cls
        return round(sum(self._cls_gecmis[-n:]) / min(n, len(self._cls_gecmis)), 1)

    def cls_trend(self) -> str:
        if len(self._cls_gecmis) < 5:
            return "stabil"
        egim = (self._cls_gecmis[-1] - self._cls_gecmis[-5]) / 4
        return "artiyor" if egim > 3 else ("azaliyor" if egim < -3 else "stabil")

    def ozellik_raporu(self) -> Dict[str, float]:
        return self.ml_motor.ozellik_onem_raporu()

    def performans_raporu(self) -> Dict:
        return self.ml_motor.model_performans_raporla()


# ─────────────────────────────────────────────────────────────────────
#  HIZLI TEST
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== AffectEV CLS ML Modeli — Test ===\n")

    if not SKLEARN_VAR:
        print("Scuru-learn bulunamadi. Heuristik modda test ediliyor.\n")

    ornek_profil = {
        "yas": 34, "gun_ici_tip": "sabahçı",
        "stres_egilimi": 0.35, "yorgunluk_esigi": 65,
        "biyometrik": {"blink_baz_dk": 16, "blink_std": 3.0,
                       "goz_acikligi_baz": 0.72, "kas_kasılma_baz": 0.12},
        "suruc_gecmis": [],
    }

    motor = OgrenebilirCLSMotoru(ornek_profil)

    print("--- Örnek CLS Tahminleri ---")
    senaryolar = [
        {"aciklama": "Enerjik sabah",    "ear_norm": 10, "blink_norm": 10, "kas_norm": 8,  "saat": 8},
        {"aciklama": "Nötr öğle",        "ear_norm": 30, "blink_norm": 20, "kas_norm": 20, "saat": 12},
        {"aciklama": "Yorgun akşam trafiği","ear_norm": 65, "blink_norm": 55, "kas_norm": 60, "saat": 18},
        {"aciklama": "Geç gece yolculuğu", "ear_norm": 80, "blink_norm": 70, "kas_norm": 75, "saat": 23},
    ]
    for s in senaryolar:
        cls = motor.tahmin_et(
            ear_norm=s["ear_norm"], blink_norm=s["blink_norm"],
            kas_norm=s["kas_norm"], saat=s["saat"])
        print(f"  [{s['aciklama']:30s}] -> CLS = {cls:.1f}")

    print("\n--- Model Performansı (5-fold CV) ---")
    perf = motor.model_performans_raporla()
    for k, v in perf.items():
        print(f"  {k}: {v}")

    print("\n--- Özellik Önemleri (ilk 5) ---")
    for k, v in list(motor.ozellik_onem_raporu().items())[:5]:
        print(f"  {k}: {v:.4f}")