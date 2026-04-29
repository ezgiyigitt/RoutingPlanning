"""
duygu_regresyonu.py  —  AffectEV  Sürekli Duygu Regresyon Motoru
=================================================================
İkili (yorgun/değil) duygu sınıflandırması yerine 4 boyutlu
sürekli (regresyon) duygu çıktısı üretir.

Kurulum:
    pip install scikit-learn numpy joblib

Mimari:
    ┌─────────────────────────────────────────────────────────────────┐
    │  CLS + Biyometrik + Bağlam  →  Özellik Vektörü (16 boyut)      │
    │      ↓  MultiOutputRegressor(RandomForest)                      │
    │  Duygu Yoğunluk Vektörü  [0, 1]⁴                               │
    │      { yorgunluk, stres, sakinlik, enerji }                     │
    │      ↓  Normalize (sum=1)                                       │
    │  Duygu Karışım Vektörü  (sürekli, aşırı uçlar yok)             │
    └─────────────────────────────────────────────────────────────────┘

İkili vs. Sürekli Karşılaştırması:
    İkili : "Yorgun" / "Değil"
    Sürekli : yorgunluk=0.58, stres=0.22, sakinlik=0.12, enerji=0.08
              → CLS ağırlıkları bu oranlarla hesaplanır
              → Çok daha ince kişiselleştirme

Duygu Boyutları:
    yorgunluk (0-1) : Fiziksel/kognitif tükenme seviyesi
    stres     (0-1) : Anlık anksiyete/gerilim seviyesi
    sakinlik  (0-1) : Rahatlama / dinginlik
    enerji    (0-1) : Vitalite / uyanıklık

    NOT: Boyutlar birbirinden bağımsız değil ama toplamları mutlaka 1
         olmak zorunda değildir. Normalize adımında softmax uygulanır,
         böylece dominant duygu öne çıkar ama diğerleri sıfıra inmez.
"""

import json
import math
import os
import random
import threading
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.multioutput import MultiOutputRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_VAR = True
except ImportError:
    SKLEARN_VAR = False
    warnings.warn("scikit-learn bulunamadı. Duygu motoru kural tabanlı modda çalışır.")

# ─────────────────────────────────────────────────────────────────────
#  YAPILANDIRMA
# ─────────────────────────────────────────────────────────────────────
DUYGU_BOYUTLARI = ["yorgunluk", "stres", "sakinlik", "enerji"]

MODEL_KLASORU   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeller")
DUYGU_MODEL     = os.path.join(MODEL_KLASORU, "duygu_regresyon_model.joblib")
DUYGU_SCALER    = os.path.join(MODEL_KLASORU, "duygu_regresyon_scaler.joblib")
DUYGU_VERI      = os.path.join(MODEL_KLASORU, "duygu_egitim_verisi.json")
DUYGU_META      = os.path.join(MODEL_KLASORU, "duygu_egitim_meta.json")

MIN_ORNEK       = 40
FINETUNE_ARALIK = 15

# ── Gerçek Veri Yükleyici (opsiyonel) ──────────────────────────────
try:
    from gercek_veri_yukleyici import gercek_veri_yukle, veri_dogrula
    GERCEK_VERI_MODULU_VAR = True
except ImportError:
    GERCEK_VERI_MODULU_VAR = False


# ─────────────────────────────────────────────────────────────────────
#  DUYGU KARIŞIM HESAPLAMALARI
# ─────────────────────────────────────────────────────────────────────
def softmax_normalize(vec: np.ndarray, sicaklik: float = 1.5) -> np.ndarray:
    """
    Duygu vektörünü softmax ile normalize eder.
    Sıcaklık parametresi dağılımın keskinliğini kontrol eder:
        - Düşük sıcaklık → dominant duygu daha belirgin
        - Yüksek sıcaklık → duygu karışımı daha homojen
    """
    exp_v = np.exp((vec - vec.max()) / sicaklik)
    return exp_v / (exp_v.sum() + 1e-9)


def duygu_vektoru_to_mod(duygu_vec: Dict[str, float]) -> str:
    """
    Sürekli duygu vektörünü mevcut dört moda eşler.
    Dominant boyuta göre karar verilir, ancak eşik kontrolü yapılır.

    Eşleme mantığı:
        enerji    baskın → enerjik
        sakinlik  baskın → notr
        stres     baskın → stresli
        yorgunluk baskın → yorgun
    """
    dominant = max(duygu_vec, key=duygu_vec.get)
    eslemeler = {
        "enerji":    "enerjik",
        "sakinlik":  "notr",
        "stres":     "stresli",
        "yorgunluk": "yorgun",
    }
    return eslemeler.get(dominant, "notr")


def duygu_ağırlık_hesapla(duygu_vec: Dict[str, float]) -> Tuple[float, float, float]:
    """
    Sürekli duygu vektörünü CokAmacliRotaOptimizatoru ağırlıklarına dönüştürür.

    İkili moddan farkı:
        İkili  : CLS tek bir sayı → agirlik_hesapla(cls) heuristiği
        Sürekli: Duygu karışımı doğrudan ağırlıklara etki eder

    Ağırlık katkıları:
        w_enerji ← yorgunluk etkisi (azaltır) + sakinlik (hafif arttırır)
        w_sure   ← enerji (arttırır) − yorgunluk (azaltır)
        w_konfor ← yorgunluk + stres (belirgin artırır) − enerji (azaltır)

    Tüm ağırlıklar softmax ile [0,1] ve toplamları = 1.
    """
    yor = duygu_vec.get("yorgunluk", 0.25)
    str_ = duygu_vec.get("stres", 0.25)
    sak = duygu_vec.get("sakinlik", 0.25)
    ene = duygu_vec.get("enerji", 0.25)

    # Ham ağırlık skoru hesabı
    alpha_e = 0.60 * (sak * 0.6 + (1.0 - yor) * 0.4)  # enerji ağırlığı
    alpha_t = 0.70 * (ene * 0.7 + sak * 0.3)            # süre ağırlığı
    alpha_c = 0.75 * (yor * 0.5 + str_ * 0.5)           # konfor ağırlığı

    toplam = alpha_e + alpha_t + alpha_c + 1e-9
    return (
        round(alpha_e / toplam, 4),
        round(alpha_t / toplam, 4),
        round(alpha_c / toplam, 4),
    )


def cls_den_duygu_vektoru(cls: float) -> Dict[str, float]:
    """
    CLS skoru → sürekli duygu vektörü dönüşümü.
    Bu fonksiyon eski sistemden yeni sisteme geçiş köprüsüdür;
    ML model yokken ya da eski kodla uyumluluk için kullanılır.
    """
    n = np.clip(cls / 100.0, 0.0, 1.0)

    # Her boyut için CLS'ye bağlı eğriler
    raw = np.array([
        n ** 1.6,                              # yorgunluk: concave up (yüksek CLS'de hızlı artar)
        0.8 * np.exp(-((n - 0.55) ** 2) / 0.08),  # stres: Gauss tepe CLS≈55'te
        (1.0 - n) ** 1.4,                     # sakinlik: concave (düşük CLS'de yüksek)
        0.9 * (1.0 - n) ** 2.0,               # enerji: hızlı azalan
    ], dtype=np.float32)

    # Softmax ile normalize et
    normalized = softmax_normalize(raw, sicaklik=2.0)
    return {d: round(float(v), 4) for d, v in zip(DUYGU_BOYUTLARI, normalized)}


# ─────────────────────────────────────────────────────────────────────
#  ÖZELLİK MÜHENDİSLİĞİ (Duygu Regresyonu için)
# ─────────────────────────────────────────────────────────────────────
def duygu_ozellik_vektoru(
    cls:            float,
    ear_norm:       float = 50.0,
    blink_norm:     float = 20.0,
    kas_norm:       float = 20.0,
    saat:           int   = 12,
    bugun_km:       float = 0.0,
    is_gunu:        bool  = True,
    stres_egilimi:  float = 0.40,
    yor_esigi:      float = 60.0,
    yas:            int   = 35,
    gun_tipi:       str   = "sabahçı",
    onceki_cls_ort: float = 45.0,
) -> np.ndarray:
    """
    16 boyutlu duygu özellik vektörü.
    CLS'ye ek olarak duygu boyutlarının ayrımına yardımcı sinyaller eklenir.
    """
    # CLS'den heuristik duygu prior'u (özellik olarak ekle)
    duygu_prior = cls_den_duygu_vektoru(cls)   # 4 değer

    saat_sin = (math.sin(2 * math.pi * saat / 24) + 1) / 2
    saat_cos = (math.cos(2 * math.pi * saat / 24) + 1) / 2
    gun_enc  = {"sabahçı": 0.0, "gece": 1.0, "karma": 0.5}.get(gun_tipi, 0.0)

    return np.array([
        # CLS tabanlı prior (4)
        duygu_prior["yorgunluk"],
        duygu_prior["stres"],
        duygu_prior["sakinlik"],
        duygu_prior["enerji"],
        # Biyometrik (3)
        np.clip(ear_norm   / 100.0, 0, 1),
        np.clip(blink_norm / 100.0, 0, 1),
        np.clip(kas_norm   / 100.0, 0, 1),
        # Zaman/bağlam (4)
        saat_sin, saat_cos, gun_enc,
        1.0 if is_gunu else 0.0,
        # Geçmiş / kişisel (5)
        np.clip(bugun_km  / 200.0, 0, 1),
        np.clip(onceki_cls_ort / 100.0, 0, 1),
        np.clip(stres_egilimi, 0, 1),
        1.0 - np.clip(yor_esigi / 100.0, 0, 1),
        np.clip((yas - 18) / 62.0, 0, 1),
    ], dtype=np.float32)


DUYGU_OZELLIK_ISIMLERI = [
    "prior_yorgunluk", "prior_stres", "prior_sakinlik", "prior_enerji",
    "ear_norm", "blink_norm", "kas_norm",
    "saat_sin", "saat_cos", "gun_tipi_enc", "is_gunu",
    "bugun_km_norm", "onceki_cls_norm",
    "stres_egilimi", "yorgunluk_esigi_inv", "yas_norm",
]


# ─────────────────────────────────────────────────────────────────────
#  SENTETİK EĞİTİM VERİSİ
# ─────────────────────────────────────────────────────────────────────
def sentetik_duygu_verisi_uret(n: int = 600, tohum: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """
    CLS bazlı etiket oluşturucu ile X: özellik, y: [4 boyutlu duygu vektörü] üretir.
    """
    rng = random.Random(tohum)
    X, Y = [], []

    for _ in range(n):
        cls = rng.gauss(45, 20)
        cls = float(np.clip(cls, 0, 100))

        ear   = rng.gauss(cls * 0.5, 20)
        blink = rng.gauss(cls * 0.3, 15)
        kas   = rng.gauss(cls * 0.4, 18)
        saat  = rng.randint(0, 23)
        gun_tipi  = rng.choice(["sabahçı", "gece", "karma"])
        is_gunu   = rng.random() > 0.28
        stres_egil = rng.uniform(0.15, 0.80)
        yor_esik   = rng.uniform(40, 90)
        yas        = rng.randint(20, 65)
        km         = rng.gauss(35, 20)
        prev_cls   = float(np.clip(cls + rng.gauss(0, 10), 0, 100))

        feat = duygu_ozellik_vektoru(
            cls=cls, ear_norm=float(np.clip(ear, 0, 100)),
            blink_norm=float(np.clip(blink, 0, 100)),
            kas_norm=float(np.clip(kas, 0, 100)),
            saat=saat, bugun_km=max(0, km), is_gunu=is_gunu,
            stres_egilimi=stres_egil, yor_esigi=yor_esik, yas=yas,
            gun_tipi=gun_tipi, onceki_cls_ort=prev_cls,
        )

        # Etiket: CLS'den türetilen duygu prior + küçük gürültü
        prior = cls_den_duygu_vektoru(cls)
        y_raw = np.array([
            prior["yorgunluk"] + rng.gauss(0, 0.05),
            prior["stres"]     + rng.gauss(0, 0.05),
            prior["sakinlik"]  + rng.gauss(0, 0.05),
            prior["enerji"]    + rng.gauss(0, 0.05),
        ], dtype=np.float32)
        y_norm = softmax_normalize(np.clip(y_raw, 0, 1))

        X.append(feat)
        Y.append(y_norm)

    return np.array(X), np.array(Y)


# ─────────────────────────────────────────────────────────────────────
#  SÜREKLI DUYGU REGRESYON MODELİ
# ─────────────────────────────────────────────────────────────────────
class SurekliDuyguMotoru:
    """
    Sürekli duygu yoğunluk vektörü tahmincisi.

    Çıktı: {"yorgunluk": 0.xx, "stres": 0.xx, "sakinlik": 0.xx, "enerji": 0.xx}
           → toplamı 1.0'a normalize edilmiş, her biri [0, 1]

    Kural tabanlı eski sistemden farkı:
        ← cls_to_mod(cls)  →  tek bir etiket (ikili karar)
        ← bu sınıf         →  4 boyutlu sürekli duygu vektörü

    Avantajlar:
        • CLS=48 stresli mi, nötr mü?  →  %38 stres, %32 sakinlik, %20 enerji, %10 yorgunluk
        • Rota ağırlıkları daha nüanslı kişiselleştirme sağlar
        • Duygu değişimi gradyan olarak izlenebilir
    """

    def __init__(self, profil: Optional[Dict] = None):
        self.profil    = profil or {}
        self._model    = None
        self._scaler   = None
        self._kilit    = threading.Lock()
        self._ornekler: List[Tuple[np.ndarray, np.ndarray]] = []
        self._yeni_ornek_sayisi = 0

        os.makedirs(MODEL_KLASORU, exist_ok=True)
        if SKLEARN_VAR:
            self._model_yukle_veya_egit()

    # ── Yükleme / Eğitim ──────────────────────────────────────────────
    def _model_yukle_veya_egit(self):
        if os.path.exists(DUYGU_MODEL) and os.path.exists(DUYGU_SCALER):
            try:
                self._model  = joblib.load(DUYGU_MODEL)
                self._scaler = joblib.load(DUYGU_SCALER)
                if os.path.exists(DUYGU_VERI):
                    with open(DUYGU_VERI, "r") as f:
                        d = json.load(f)
                    self._ornekler = [
                        (np.array(x, dtype=np.float32), np.array(y, dtype=np.float32))
                        for x, y in zip(d["X"], d["Y"])
                    ]
                return
            except Exception:
                pass
        self._ilk_egitim()

    def _ilk_egitim(self, n_sentetik: int = 800):
        """
        Eğitim Öncelik Sırası:
          1. DEAP (fizyolojik, Russell Circumplex eşlemeli) + Kaggle CSV
          2. Yalnızca bu kaynaklardan biri
          3. Gerçek veri yoksa sentetik (pseudo-label fallback)

        Novel Katkı [Makale]: İlk kez DEAP fizyolojik sinyalleri
        Russell Circumplex dönüşümüyle EV rota ağırlıklarına bağlanıyor.
        """
        gercek_X, gercek_Y, kaynak = None, None, "sentetik"

        if GERCEK_VERI_MODULU_VAR:
            try:
                gercek_X, gercek_Y, kaynak = gercek_veri_yukle(verbose=True)
                if gercek_X is not None and len(gercek_X) > 0:
                    rapor = veri_dogrula(gercek_X, gercek_Y)
                    if not rapor.get("gecerli", False):
                        warnings.warn(f"[DuyguMotoru] Gerçek veri doğrulaması başarısız: {rapor.get('uyari', '?')}")
                        gercek_X, gercek_Y = None, None
                        kaynak = "sentetik"
            except Exception as e:
                warnings.warn(f"[DuyguMotoru] Gerçek veri yüklenemedi: {e}")
                gercek_X, gercek_Y = None, None
                kaynak = "sentetik"

        if gercek_X is not None and len(gercek_X) >= MIN_ORNEK:
            # ── Hibrit Eğitim: Gerçek ×3 + Sentetik ×1 (dolgu ve çeşitlilik) ──
            n_sen = max(100, n_sentetik // 4)
            X_syn, Y_syn = sentetik_duygu_verisi_uret(n=n_sen)
            X = np.vstack([gercek_X, X_syn])
            Y = np.vstack([gercek_Y, Y_syn])
            kaynak = f"{kaynak} + Sentetik({n_sen})"
            print(f"[DuyguMotoru] Hibrit egitim: {len(gercek_X)} gercek + {n_sen} sentetik ornek")
        else:
            # ── Fallback: Yalnızca sentetik ──
            X, Y = sentetik_duygu_verisi_uret(n=n_sentetik)
            kaynak = "sentetik_pseudo_label"
            print(f"[DuyguMotoru] Gercek veri bulunamadi. Sentetik pseudo-label kullaniliyor.")
            print(f"  DEAP indirme : http://www.eecs.qmul.ac.uk/mmv/datasets/deap/")
            print(f"  Kaggle CSV   : https://www.kaggle.com/datasets/dheerajperumandla/drowsiness-detection")

        self._egit_kaynak = kaynak
        self._egit(X, Y, kaydet=True)

    def _egit(self, X: np.ndarray, Y: np.ndarray, kaydet: bool = True):
        scaler  = StandardScaler()
        X_s     = scaler.fit_transform(X)
        # MultiOutputRegressor: her duygu boyutu için bağımsız RF
        model   = MultiOutputRegressor(
            RandomForestRegressor(
                n_estimators=150,
                max_depth=12,
                min_samples_leaf=3,
                n_jobs=-1,
                random_state=42,
            )
        )
        model.fit(X_s, Y)
        with self._kilit:
            self._model  = model
            self._scaler = scaler
        if kaydet:
            joblib.dump(model,  DUYGU_MODEL)
            joblib.dump(scaler, DUYGU_SCALER)
            self._ornekleri_kaydet()
            # Model metadata kaydet (makale için: hangi veri kullanıldı?)
            try:
                meta = {
                    "egitim_tarihi": datetime.now().isoformat(),
                    "ornek_sayisi":  int(len(X)),
                    "kaynak":        getattr(self, "_egit_kaynak", "bilinmiyor"),
                    "model":         "MultiOutputRegressor(RandomForest)",
                    "ozellik_boyutu": int(X.shape[1]),
                    "etiket_boyutu":  int(Y.shape[1]) if Y.ndim > 1 else 1,
                }
                with open(DUYGU_META, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _ornekleri_kaydet(self):
        try:
            with open(DUYGU_VERI, "w") as f:
                json.dump({
                    "X": [x.tolist() for x, _ in self._ornekler],
                    "Y": [y.tolist() for _, y in self._ornekler],
                    "kayit": datetime.now().isoformat(),
                }, f)
        except OSError:
            pass

    # ── Online Fine-tune ───────────────────────────────────────────────
    def geri_besleme_ekle(self, feat: np.ndarray, gercek_duygu: Dict[str, float]):
        if not SKLEARN_VAR:
            return
        y = softmax_normalize(np.array(
            [gercek_duygu.get(d, 0.25) for d in DUYGU_BOYUTLARI], dtype=np.float32
        ))
        with self._kilit:
            self._ornekler.append((feat.copy(), y))
            if len(self._ornekler) > 2000:
                self._ornekler = self._ornekler[-2000:]
            self._yeni_ornek_sayisi += 1
        if self._yeni_ornek_sayisi >= FINETUNE_ARALIK:
            threading.Thread(target=self._online_finetune, daemon=True).start()
            self._yeni_ornek_sayisi = 0

    def _online_finetune(self):
        with self._kilit:
            snap = list(self._ornekler)
        if len(snap) < MIN_ORNEK:
            return
        X_g = np.array([x for x, _ in snap])
        Y_g = np.array([y for _, y in snap])
        X_s, Y_s = sentetik_duygu_verisi_uret(n=200)
        self._egit(np.vstack([X_s, X_g]), np.vstack([Y_s, Y_g]), kaydet=True)

    # ── Ana Tahmin Metodu ──────────────────────────────────────────────
    def duygu_tahmin(self,
                     cls:          float,
                     ear_norm:     float = 50.0,
                     blink_norm:   float = 20.0,
                     kas_norm:     float = 20.0,
                     saat:         Optional[int] = None,
                     bugun_km:     float = 0.0,
                     onceki_cls:   float = 45.0) -> Dict[str, float]:
        """
        Mevcut durumdan sürekli duygu yoğunluk vektörü üretir.

        Parametreler
        ------------
        cls       : Anlık CLS değeri ∈ [0, 100]
        ear_norm  : Göz açıklık normu ∈ [0, 100]  (kameradan veya simülasyondan)
        blink_norm: Göz kırpma normu
        kas_norm  : Kaş kasılma normu
        saat      : Geçerli saat (None → sistem saati)
        bugun_km  : Bugün sürülen toplam km
        onceki_cls: Önceki ölçüm CLS değeri (trend için)

        Dönüş
        -----
        {
            "yorgunluk": 0.xx,
            "stres":     0.xx,
            "sakinlik":  0.xx,
            "enerji":    0.xx,
            "dominant":  "yorgunluk",   # en yüksek boyut
            "mod":       "yorgun",      # eski sistem uyumlu mod etiketi
        }
        """
        if saat is None:
            saat = datetime.now().hour

        profil_kisi = {
            "stres_egilimi": self.profil.get("stres_egilimi", 0.40),
            "yor_esigi":     self.profil.get("yorgunluk_esigi", 60.0),
            "yas":           self.profil.get("yas", 35),
            "gun_tipi":      self.profil.get("gun_ici_tip", "sabahçı"),
        }
        is_gunu = datetime.now().weekday() < 5

        feat = duygu_ozellik_vektoru(
            cls=cls, ear_norm=ear_norm, blink_norm=blink_norm, kas_norm=kas_norm,
            saat=saat, bugun_km=bugun_km, is_gunu=is_gunu,
            stres_egilimi=profil_kisi["stres_egilimi"],
            yor_esigi=profil_kisi["yor_esigi"],
            yas=profil_kisi["yas"],
            gun_tipi=profil_kisi["gun_tipi"],
            onceki_cls_ort=onceki_cls,
        )

        if SKLEARN_VAR and self._model is not None and self._scaler is not None:
            with self._kilit:
                X_s  = self._scaler.transform(feat.reshape(1, -1))
                pred = self._model.predict(X_s)[0]
            # Negatif değerleri temizle ve normalize et
            pred = np.clip(pred, 0, 1)
            pred = softmax_normalize(pred, sicaklik=2.0)
        else:
            # Heuristik geri dönüş
            prior = cls_den_duygu_vektoru(cls)
            pred  = np.array([prior[d] for d in DUYGU_BOYUTLARI], dtype=np.float32)

        sonuc = {d: round(float(v), 4) for d, v in zip(DUYGU_BOYUTLARI, pred)}
        dominant = max(sonuc, key=sonuc.get)
        sonuc["dominant"] = dominant
        
        # Sadece sayısal duygu boyutlarını geçirerek string-float kıyaslama hatasını önlüyoruz
        duygu_sayisal = {k: v for k, v in sonuc.items() if k in DUYGU_BOYUTLARI}
        sonuc["mod"]      = duygu_vektoru_to_mod(duygu_sayisal)
        return sonuc

    # ── Rota Ağırlıkları ──────────────────────────────────────────────
    def rota_agirliklari(self, cls: float, **kwargs) -> Tuple[float, float, float]:
        """
        Sürekli duygu vektöründen CokAmacliRotaOptimizatoru uyumlu
        (w_enerji, w_sure, w_konfor) döndürür.
        """
        duygu = self.duygu_tahmin(cls, **kwargs)
        return duygu_ağırlık_hesapla(duygu)

    # ── Duygu Değişimi Analizi ─────────────────────────────────────────
    @staticmethod
    def duygu_degisimi_analiz(
            gecmis_vektorler: List[Dict[str, float]],
    ) -> Dict[str, float]:
        """
        Son N duygu vektörü arasındaki gradyanı hesaplar.
        Sürüş boyunca duygunun nasıl evirildiğini ölçer.

        Dönüş
        -----
        {
            "yorgunluk_delta": +0.12,  # arttı (kötü)
            "stres_delta":     -0.05,  # azaldı (iyi)
            "sakinlik_delta":  +0.03,
            "enerji_delta":    -0.10,
        }
        """
        if len(gecmis_vektorler) < 2:
            return {f"{d}_delta": 0.0 for d in DUYGU_BOYUTLARI}
        ilk = gecmis_vektorler[0]
        son = gecmis_vektorler[-1]
        return {
            f"{d}_delta": round(
                son.get(d, 0.0) - ilk.get(d, 0.0), 4
            )
            for d in DUYGU_BOYUTLARI
        }

    # ── Sefer Duygu Özeti ──────────────────────────────────────────────
    @staticmethod
    def sefer_duygu_ozeti(
            sefer_vektorleri: List[Dict[str, float]],
    ) -> Dict[str, Dict[str, float]]:
        """
        Tüm sefer boyunca duygu istatistiklerini hesaplar.

        Dönüş
        -----
        {
            "ort":  {"yorgunluk": 0.xx, ...},
            "maks": {"yorgunluk": 0.xx, ...},
            "min":  {"yorgunluk": 0.xx, ...},
        }
        """
        if not sefer_vektorleri:
            return {"ort": {}, "maks": {}, "min": {}}
        ort, maks, min_ = {}, {}, {}
        for d in DUYGU_BOYUTLARI:
            vals = [v.get(d, 0.0) for v in sefer_vektorleri]
            ort[d]  = round(sum(vals) / len(vals), 4)
            maks[d] = round(max(vals), 4)
            min_[d] = round(min(vals), 4)
        return {"ort": ort, "maks": maks, "min": min_}


# ─────────────────────────────────────────────────────────────────────
#  KOGNİTİF MOTOR ENTEGRASYONU — Sarmalayıcı Fonksiyon
# ─────────────────────────────────────────────────────────────────────
def cls_ve_duygu_ile_optimize(
        cls: float,
        duygu_motoru: Optional[SurekliDuyguMotoru] = None,
        profil: Optional[Dict] = None,
) -> Dict:
    """
    Mevcut CokAmacliRotaOptimizatoru ile uyumlu arayüz sağlar.
    Sürekli duygu vektörünü hem ağırlık hesabında hem de mod bilgisinde kullanır.

    Dönüş
    -----
    {
        "w_enerji", "w_sure", "w_konfor",
        "duygu": {...},
        "mod": "stresli",
        "cls": 54.2,
        "kaynak": "SurekliDuygu_ML",
    }
    """
    if duygu_motoru is None:
        duygu_motoru = SurekliDuyguMotoru(profil)

    duygu = duygu_motoru.duygu_tahmin(cls)
    w_e, w_t, w_c = duygu_ağırlık_hesapla(duygu)

    return {
        "w_enerji":  w_e,
        "w_sure":    w_t,
        "w_konfor":  w_c,
        "duygu":     duygu,
        "mod":       duygu["mod"],
        "cls":       round(cls, 1),
        "kaynak":    "SurekliDuygu_ML",
    }


# ─────────────────────────────────────────────────────────────────────
#  HIZLI TEST
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== AffectEV Sürekli Duygu Regresyon Motoru — Test ===\n")

    if not SKLEARN_VAR:
        print("scikit-learn yok. Kural tabanli mod.\n")

    ornek_profil = {
        "yas": 34, "gun_ici_tip": "sabahçı",
        "stres_egilimi": 0.35, "yorgunluk_esigi": 65,
    }

    motor = SurekliDuyguMotoru(ornek_profil)

    print("─── CLS → Duygu Vektörü (Heuristik Referans) ───")
    for cls_val in [10, 30, 50, 70, 90]:
        d = cls_den_duygu_vektoru(cls_val)
        dom = max({k: v for k, v in d.items() if k in DUYGU_BOYUTLARI}, key=d.get)
        print(f"  CLS={cls_val:3d} | yor={d['yorgunluk']:.3f} str={d['stres']:.3f} "
              f"sak={d['sakinlik']:.3f} ene={d['enerji']:.3f} → [{dom}]")

    print("\n─── ML Duygu Tahminleri ───")
    senaryolar = [
        {"aciklama": "Sabah enerjisi",   "cls": 15, "ear_norm": 8,  "blink_norm": 10},
        {"aciklama": "Öğle yoğunluğu",  "cls": 45, "ear_norm": 35, "blink_norm": 25},
        {"aciklama": "Akşam trafiği",   "cls": 62, "ear_norm": 58, "blink_norm": 50},
        {"aciklama": "Gece yorgunluğu", "cls": 85, "ear_norm": 78, "blink_norm": 70},
    ]
    for s in senaryolar:
        d = motor.duygu_tahmin(
            cls=s["cls"], ear_norm=s["ear_norm"], blink_norm=s["blink_norm"])
        print(f"  [{s['aciklama']:20s}] CLS={s['cls']:2d} | "
              f"yor={d['yorgunluk']:.3f} str={d['stres']:.3f} "
              f"sak={d['sakinlik']:.3f} ene={d['enerji']:.3f} "
              f"→ mod={d['mod']}")

    print("\n─── Rota Ağırlıkları Karşılaştırması ───")
    print(f"  {'CLS':>4} | {'w_enerji':>10} {'w_sure':>10} {'w_konfor':>10} | {'Heuristik':>12} {'ML':>12}")
    try:
        from cls_ml_modeli import OgrenebilirCLSMotoru
        from kognitif_motor import CokAmacliRotaOptimizatoru
        for cls_val in [15, 45, 65, 85]:
            w_e_ml, w_t_ml, w_c_ml = motor.rota_agirliklari(cls_val)
            w_e_h, w_t_h, w_c_h  = CokAmacliRotaOptimizatoru.agirlik_hesapla(cls_val)
            print(f"  {cls_val:>4} | ML=({w_e_ml:.2f},{w_t_ml:.2f},{w_c_ml:.2f}) | "
                  f"Heuristik=({w_e_h:.2f},{w_t_h:.2f},{w_c_h:.2f})")
    except ImportError:
        for cls_val in [15, 45, 65, 85]:
            w_e, w_t, w_c = motor.rota_agirliklari(cls_val)
            print(f"  {cls_val:>4} | ML=({w_e:.2f},{w_t:.2f},{w_c:.2f})")

    print("\n─── Sefer Duygu Değişimi Analizi ───")
    gecmis = [motor.duygu_tahmin(cls=float(20 + i * 8)) for i in range(8)]
    delta  = SurekliDuyguMotoru.duygu_degisimi_analiz(gecmis)
    for k, v in delta.items():
        yon = "↑ arttı" if v > 0.01 else ("↓ azaldı" if v < -0.01 else "→ stabil")
        print(f"  {k:22s}: {v:+.4f}  {yon}")