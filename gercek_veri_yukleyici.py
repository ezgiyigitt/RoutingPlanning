"""
gercek_veri_yukleyici.py  —  AffectEV Gerçek Veri Yükleyicisi
==============================================================
Literatürde İlk: DEAP fizyolojik verisi + Russell Circumplex eşlemesi
kullanılarak EV rota planlayıcısı için 4D sürekli duygu vektörü elde
edilmesi. Bu kombinasyon hiçbir EV routing makalesinde yer almamaktadır.

─── Akademik Referanslar ──────────────────────────────────────────────
[1] Koelstra S. et al., "DEAP: A Database for Emotion Analysis Using
    Physiological Signals", IEEE TAFF 3(1):18-31, 2012.
    DOI: 10.1109/T-AFFC.2011.15

[2] Russell J. A., "A Circumplex Model of Affect",
    J. Personality Soc. Psychol. 39(6):1161-1178, 1980.
    DOI: 10.1037/h0077714

[3] Mauss I.B. & Robinson M.D., "Measures of emotion: A review",
    Cognition & Emotion 23(2): 209-237, 2009.

─── Novel Katkı ──────────────────────────────────────────────────────
  1. DEAP EOG/EMG kanalları → EAR/blink/kas_norm (biyometrik köprü)
  2. Valence + Arousal → Russell Circumplex → 4D duygu (yorgunluk,
     stres, sakinlik, enerji) — softmax normalizasyonlu eşleme
  3. Bu 4D vektör → AffectEV NSGA-II ağırlık fonksiyonu (w_e, w_t, w_c)
  → Tamamen fizyolojik gerçek veriye dayalı EV rota kişiselleştirme.

─── Veri İndirme ─────────────────────────────────────────────────────
  DEAP  : http://www.eecs.qmul.ac.uk/mmv/datasets/deap/
          Kayıt gerekli. "data_preprocessed_python.zip" indir.
          → veri/gercek_veri/deap/ klasörüne aç.

  Kaggle: https://www.kaggle.com/datasets/dheerajperumandla/drowsiness-detection
          Kayıt gerekmez. CSV indir.
          → veri/gercek_veri/drowsiness_features.csv olarak kaydet.

Kurulum:
    pip install numpy scipy scikit-learn
"""

from __future__ import annotations

import json
import math
import os
import pickle
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np

# ─────────────────────────────────────────────────────────────────────
#  YAPILANDIRMA
# ─────────────────────────────────────────────────────────────────────
PROJE_KOK   = os.path.dirname(os.path.abspath(__file__))
GERCEK_VERI = os.path.join(PROJE_KOK, "veri", "gercek_veri")

DEAP_KLASORU = os.path.join(GERCEK_VERI, "deap")
KAGGLE_CSV   = os.path.join(GERCEK_VERI, "drowsiness_features.csv")

# 4D duygu boyutları (AffectEV standardı)
DUYGU_BOYUTLARI = ["yorgunluk", "stres", "sakinlik", "enerji"]

# DEAP kanal indeksleri (data_preprocessed_python formatı)
# Ref: Koelstra et al. 2012, Tablo I
DEAP_KANAL = {
    "eog_yatay":   32,   # Horizontal EOG
    "eog_dikey":   33,   # Vertical EOG   → blink detection
    "emg_zygo":    34,   # Zygomaticus major EMG (yanak, gülümseme)
    "emg_trapez":  35,   # Trapezius EMG (omuz/boyun gerilimi → stres)
    "gsr":         36,   # Galvanic Skin Response → arousal proxy
    "solunum":     37,   # Respiration amplitude
    "pleth":       38,   # Plethysmography (kalp hızı)
    "cilt_sicak":  39,   # Skin temperature
}

DEAP_ORNEKLEME_HZ = 128   # Preprocessed veri örnekleme hızı


# ─────────────────────────────────────────────────────────────────────
#  RUSSELL CİRCUMPLEX EŞLEMESİ
#  Ref: Russell (1980) — 4 quadrant → 4D softmax duygu
# ─────────────────────────────────────────────────────────────────────

def softmax_normalize(arr: np.ndarray, sicaklik: float = 1.5) -> np.ndarray:
    """Softmax ile normalize. Sıcaklık parametresi dağılım keskinliğini ayarlar."""
    x = (arr - arr.max()) / sicaklik
    e = np.exp(x)
    return e / (e.sum() + 1e-9)


def russell_circumplex_esle(
    valence: float,
    arousal: float,
    valence_aralik: Tuple[float, float] = (1.0, 9.0),
    arousal_aralik: Tuple[float, float] = (1.0, 9.0),
) -> Dict[str, float]:
    """
    Russell (1980) Duygu Çemberi Eşlemesi:
    (Valence, Arousal) → {yorgunluk, stres, sakinlik, enerji}

    ┌─────────────────────────────────────────┐
    │     YÜKSEK AROUSAL (yukarı)             │
    │  Stres (kızgın) │ Enerji (heyecanlı)   │
    │ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
    │Yorgunluk(üzgün) │ Sakinlik (huzurlu)   │
    │     DÜŞÜK AROUSAL (aşağı)               │
    │    DÜŞÜK VALENCE ←→ YÜKSEK VALENCE     │
    └─────────────────────────────────────────┘

    Matematiksel model:
        v_n = (valence - v_min) / (v_max - v_min)  ∈ [0, 1]
        a_n = (arousal - a_min) / (a_max - a_min)  ∈ [0, 1]

        yorgunluk = (1 - v_n)^γ × (1 - a_n)^γ     (Q3: düşük V, düşük A)
        stres     = (1 - v_n)^γ × a_n^γ            (Q2: düşük V, yüksek A)
        sakinlik  = v_n^γ × (1 - a_n)^γ            (Q4: yüksek V, düşük A)
        enerji    = v_n^γ × a_n^γ                  (Q1: yüksek V, yüksek A)

        γ = 1.5  (güç parametresi — dominant duygu öne çıkar)
        → softmax normalize → Σ = 1
    """
    v_min, v_max = valence_aralik
    a_min, a_max = arousal_aralik

    v_n = float(np.clip((valence - v_min) / (v_max - v_min), 0.0, 1.0))
    a_n = float(np.clip((arousal - a_min) / (a_max - a_min), 0.0, 1.0))

    gamma = 1.5   # Dominant duygu vurgusu

    raw = np.array([
        (1.0 - v_n) ** gamma * (1.0 - a_n) ** gamma,  # yorgunluk (Q3)
        (1.0 - v_n) ** gamma * a_n          ** gamma,  # stres     (Q2)
        v_n          ** gamma * (1.0 - a_n) ** gamma,  # sakinlik  (Q4)
        v_n          ** gamma * a_n          ** gamma,  # enerji    (Q1)
    ], dtype=np.float32)

    normalized = softmax_normalize(raw, sicaklik=2.0)
    return {d: round(float(v), 4) for d, v in zip(DUYGU_BOYUTLARI, normalized)}


# ─────────────────────────────────────────────────────────────────────
#  DEAP KANAL → BİYOMETRİK ÖZELLİK KÖPRÜSÜ
# ─────────────────────────────────────────────────────────────────────

def deap_pencere_ozellik_cikart(
    pencere: np.ndarray,
    ornekleme_hz: int = DEAP_ORNEKLEME_HZ,
) -> Dict[str, float]:
    """
    Tek bir DEAP zaman penceresi (shape: [n_kanal, n_sample]) için
    AffectEV biyometrik feature'larını çıkarır.

    Kanal Eşlemesi (Koelstra et al. 2012 Tablo I):
        EOG dikey  (ch 33) → Blink tespiti → blink_norm + ear_proxy
        Trapez EMG (ch 35) → Omuz gerilimi → kas_norm (stres belirteci)
        GSR        (ch 36) → Galvanik deri → gsr_norm (arousal proxy)
        Solunum    (ch 37) → Nefes hızı    → solunum_norm

    Döndürülen değerler AffectEV özellik vektörüyle uyumludur.
    """
    n_sample = pencere.shape[1]

    # ── EOG Dikey (ch 33): Blink tespiti ─────────────────────────────
    eog_v = pencere[DEAP_KANAL["eog_dikey"]]
    # Blink: EOG'da ani yüksek-frekans geçiş (sıfır geçişi sayımı)
    eog_aralik  = float(eog_v.max() - eog_v.min() + 1e-9)
    eog_std     = float(eog_v.std())
    # Yüksek std → aktif blink hareketi → daha yüksek blink_norm
    blink_raw   = min(1.0, eog_std / (eog_aralik * 0.35 + 1e-9))
    blink_norm  = float(np.clip(blink_raw * 100.0, 0.0, 100.0))

    # EAR proxy: EOG dikey ortalama. Göz kapalıyken (blink) değer düşer.
    # Normalize: EOG ortalaması → ters çevrilmiş [0-100]
    eog_ort     = float(eog_v.mean())
    eog_min     = float(eog_v.min())
    ear_raw     = (eog_ort - eog_min) / (eog_aralik + 1e-9)
    ear_norm    = float(np.clip((1.0 - ear_raw) * 100.0, 0.0, 100.0))

    # ── Trapez EMG (ch 35): Omuz/boyun gerilimi ──────────────────────
    emg_trap = pencere[DEAP_KANAL["emg_trapez"]]
    trap_power = float(np.sqrt(np.mean(emg_trap ** 2)))   # RMS güç
    # GSR ile normalize (kişi bağımsız)
    gsr_ref    = float(pencere[DEAP_KANAL["gsr"]].mean()) + 1e-9
    kas_raw    = min(1.0, trap_power / gsr_ref)
    kas_norm   = float(np.clip(kas_raw * 100.0, 0.0, 100.0))

    # ── GSR (ch 36): Stres/Arousal Proxy ─────────────────────────────
    gsr       = pencere[DEAP_KANAL["gsr"]]
    gsr_norm  = float(np.clip(
        (gsr.mean() - gsr.min()) / (gsr.max() - gsr.min() + 1e-9) * 100.0,
        0.0, 100.0
    ))

    # ── Solunum (ch 37): Hız ve Ritim ────────────────────────────────
    sol    = pencere[DEAP_KANAL["solunum"]]
    sol_hz = float(np.clip(
        np.sum(np.diff(np.sign(sol - sol.mean())) != 0) / (n_sample / ornekleme_hz) / 2,
        0.1, 0.5
    ))   # Nefes/saniye
    solunum_norm = float(np.clip((sol_hz - 0.1) / 0.4 * 100.0, 0.0, 100.0))

    return {
        "ear_norm":     round(ear_norm,  2),
        "blink_norm":   round(blink_norm, 2),
        "kas_norm":     round(kas_norm,   2),
        "gsr_norm":     round(gsr_norm,   2),
        "solunum_norm": round(solunum_norm, 2),
    }


# ─────────────────────────────────────────────────────────────────────
#  DEAP YÜKLEYİCİ
# ─────────────────────────────────────────────────────────────────────

class DEAPYukleyici:
    """
    DEAP veri seti yükleyici ve Russell Circumplex dönüştürücüsü.

    Kullanım:
        yukleyici = DEAPYukleyici(klasor="veri/gercek_veri/deap")
        X, Y = yukleyici.ozellik_etiket_uret(pencere_sn=2.0)
        # X: (n, 16) özellik matrisi — AffectEV formatı
        # Y: (n, 4)  duygu vektörleri — Russell Circumplex eşlemeli
    """

    def __init__(self, klasor: str = DEAP_KLASORU):
        self.klasor = klasor
        self._katilimcilar: List[Dict] = []
        self._yukle()

    # ── Yükleme ───────────────────────────────────────────────────────
    def _yukle(self) -> None:
        """s01.pkl ... s32.pkl dosyalarını yükler."""
        if not os.path.isdir(self.klasor):
            warnings.warn(
                f"[DEAPYukleyici] Klasör bulunamadı: {self.klasor}\n"
                f"  Lütfen DEAP verisini indirip bu klasöre koyun.\n"
                f"  URL: http://www.eecs.qmul.ac.uk/mmv/datasets/deap/"
            )
            return

        for i in range(1, 33):
            dosya = os.path.join(self.klasor, f"s{i:02d}.pkl")
            if not os.path.exists(dosya):
                continue
            try:
                with open(dosya, "rb") as f:
                    data = pickle.load(f, encoding="latin1")
                # data["data"]   : (40, 40, 8064)  trial × kanal × örnek
                # data["labels"] : (40, 4)          trial × [valence, arousal, dominance, liking]
                self._katilimcilar.append({
                    "id":      i,
                    "veri":    data["data"],      # ndarray (40, 40, 8064)
                    "etiket":  data["labels"],    # ndarray (40, 4)
                })
            except Exception as e:
                warnings.warn(f"[DEAPYukleyici] s{i:02d}.pkl yüklenemedi: {e}")

    @property
    def katilimci_sayisi(self) -> int:
        return len(self._katilimcilar)

    @property
    def hazir(self) -> bool:
        return self.katilimci_sayisi > 0

    # ── Özellik & Etiket Üretimi ──────────────────────────────────────
    def ozellik_etiket_uret(
        self,
        pencere_sn: float = 2.0,
        kaydirma_sn: float = 1.0,
        duygu_sicaklik: float = 2.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Tüm katılımcı × deneme × pencerelerden (X, Y) çiftleri üretir.

        Parametre
        ---------
        pencere_sn    : Analiz penceresi (saniye). 2.0 → 256 örnek @128 Hz
        kaydirma_sn   : Pencere kaydırma adımı (saniye).
        duygu_sicaklik: Russell eşleme softmax sıcaklığı.

        Dönüş
        -----
        X : (n, 16) float32 — AffectEV 16-özellik formatı
        Y : (n, 4)  float32 — 4D duygu vektörü [yorgunluk, stres, sakinlik, enerji]
        """
        if not self.hazir:
            return np.empty((0, 16), dtype=np.float32), np.empty((0, 4), dtype=np.float32)

        pencere_boy  = int(pencere_sn   * DEAP_ORNEKLEME_HZ)
        kaydirma_boy = int(kaydirma_sn  * DEAP_ORNEKLEME_HZ)

        X_listesi: List[np.ndarray] = []
        Y_listesi: List[np.ndarray] = []

        for katilimci in self._katilimcilar:
            veri   = katilimci["veri"]    # (40, 40, 8064)
            etiket = katilimci["etiket"]  # (40, 4)

            n_deneme = veri.shape[0]
            n_sample = veri.shape[2]

            for deneme_idx in range(n_deneme):
                # ── Russell Circumplex Etiket ─────────────────────────
                valence = float(etiket[deneme_idx, 0])  # [1-9]
                arousal = float(etiket[deneme_idx, 1])  # [1-9]
                duygu   = russell_circumplex_esle(valence, arousal)
                y_vec   = np.array(
                    [duygu[d] for d in DUYGU_BOYUTLARI], dtype=np.float32
                )

                # CLS proxy: Arousal [1-9] → [0-100]
                cls_proxy = (arousal - 1) / 8.0 * 100.0

                # ── Kayan Pencere Analizi ─────────────────────────────
                bas = 0
                while bas + pencere_boy <= n_sample:
                    pencere = veri[deneme_idx, :, bas: bas + pencere_boy]
                    bio = deap_pencere_ozellik_cikart(pencere)

                    # ── AffectEV 16-özellik vektörü ───────────────────
                    x_vec = _deap_ozellik_vektoru_yap(
                        cls_proxy = cls_proxy,
                        bio       = bio,
                        valence   = valence,
                        arousal   = arousal,
                    )

                    X_listesi.append(x_vec)
                    Y_listesi.append(y_vec)

                    bas += kaydirma_boy

        if not X_listesi:
            return np.empty((0, 16), dtype=np.float32), np.empty((0, 4), dtype=np.float32)

        return (
            np.array(X_listesi, dtype=np.float32),
            np.array(Y_listesi, dtype=np.float32),
        )

    def istatistik(self) -> Dict:
        """Yüklenen DEAP verisinin özet istatistiği."""
        return {
            "katilimci_sayisi": self.katilimci_sayisi,
            "toplam_deneme":    self.katilimci_sayisi * 40,
            "klasor":           self.klasor,
            "hazir":            self.hazir,
        }


# ─────────────────────────────────────────────────────────────────────
#  AffectEV 16-ÖZELLİK VEKTÖRܜ OLUŞTURUCU  (DEAP → AffectEV formatı)
# ─────────────────────────────────────────────────────────────────────

def _deap_ozellik_vektoru_yap(
    cls_proxy: float,
    bio: Dict[str, float],
    valence: float,
    arousal: float,
) -> np.ndarray:
    """
    DEAP biyometrik çıktısını AffectEV'in 16-boyutlu özellik vektörüne
    dönüştürür. duygu_regresyonu.py :: duygu_ozellik_vektoru() ile
    tamamen uyumlu format.

    Özellikler (16):
        [0–3]  : CLS prior'dan türetilen duygu vektörü (4 boyut)
        [4–6]  : Biyometrik (ear_norm, blink_norm, kas_norm) — DEAP kanallarından
        [7–10] : Zaman/bağlam (saat_sin, saat_cos, gün_tipi, iş_günü)
                 → DEAP'ta saat bilgisi yok; nötr (0.5) olarak bırak
        [11–15]: Kişisel (bugun_km, onceki_cls, stres_egilimi, yor_esigi, yas_norm)
                 → DEAP'ta sürüş km yok; arousal + valence ile proxy yap
    """
    from duygu_regresyonu import cls_den_duygu_vektoru, DUYGU_BOYUTLARI as _DB

    # [0-3] CLS prior
    prior = cls_den_duygu_vektoru(cls_proxy)
    p0 = float(prior["yorgunluk"])
    p1 = float(prior["stres"])
    p2 = float(prior["sakinlik"])
    p3 = float(prior["enerji"])

    # [4-6] Biyometrik
    ear   = float(np.clip(bio["ear_norm"]   / 100.0, 0, 1))
    blink = float(np.clip(bio["blink_norm"] / 100.0, 0, 1))
    kas   = float(np.clip(bio["kas_norm"]   / 100.0, 0, 1))

    # [7-10] Zaman bağlamı — DEAP'ta bilinmiyor, nötr değerler
    saat_sin = 0.5   # gün ortası proxy (saat = 12)
    saat_cos = 0.5
    gun_enc  = 0.5   # "karma" tip
    is_gunu  = 1.0   # deneysel ortam → iş günü varsayımı

    # [11] Bugün km — DEAP'ta yok
    #       Arousal yüksekse daha fazla km sürülmüş gibi proxy
    bugun_km_norm = float(np.clip((arousal - 1) / 8.0 * 0.5, 0, 1))

    # [12] Önceki CLS ortalaması proxy (arousaldan)
    onceki_cls_norm = float(np.clip((arousal - 1) / 8.0, 0, 1))

    # [13] Stres eğilimi proxy — valence düşükse stres eğilimi yüksek
    stres_egil = float(np.clip(1.0 - (valence - 1) / 8.0, 0, 1)) * 0.6 + 0.2

    # [14] Yorgunluk eşiği — yüksek arousal → düşük yorgunluk eşiği (hassas)
    yor_esigi_inv = float(np.clip((arousal - 1) / 8.0 * 0.4 + 0.3, 0, 1))

    # [15] Yaş норму — DEAP katılımcı ortalama yaşı ~26.9
    yas_norm = float(np.clip((26.9 - 18) / 62.0, 0, 1))

    return np.array([
        p0, p1, p2, p3,
        ear, blink, kas,
        saat_sin, saat_cos, gun_enc, is_gunu,
        bugun_km_norm, onceki_cls_norm,
        stres_egil, yor_esigi_inv, yas_norm,
    ], dtype=np.float32)


# ─────────────────────────────────────────────────────────────────────
#  KAGGLE DROWSINESS CSV YÜKLEYİCİ  (fallback / ek veri)
# ─────────────────────────────────────────────────────────────────────

class KaggleUykululukYukleyici:
    """
    Kaggle üzerindeki sürücü uykululuk tespiti CSV veri setleri için yükleyici.

    Desteklenen sütun şemaları (otomatik algılanır):
      1. EAR, Blink_Rate, Drowsy  (0/1 etiket)
      2. ear, perclos, blink, label
      3. eye_open, blink_per_min, drowsy_label

    Etiket eşleme:
      drowsy=1 → {yorgunluk: 0.70, stres: 0.15, sakinlik: 0.05, enerji: 0.10}
      drowsy=0 → {yorgunluk: 0.10, stres: 0.15, sakinlik: 0.35, enerji: 0.40}
      (Literatür: uykulu sürücü düşük enerji, yüksek yorgunluk)
    """

    # Bilinen etiket sütun adı alternatifleri
    _ETIKET_ADLARI = [
        "Drowsy", "drowsy", "label", "Label", "drowsiness", "Drowsiness",
        "drowsy_label", "sleeping", "class", "Class", "target",
    ]
    _EAR_ADLARI    = ["EAR", "ear", "eye_open", "Eye_Aspect_Ratio", "ear_value"]
    _BLINK_ADLARI  = [
        "Blink_Rate", "blink_rate", "blink", "blink_per_min",
        "BlinkRate", "blinks_per_min",
    ]
    _PERCLOS_ADLARI = ["PERCLOS", "perclos", "Perclos", "eye_closure_ratio"]

    def __init__(self, csv_yolu: str = KAGGLE_CSV):
        self.csv_yolu = csv_yolu
        self._df      = None
        self._yukle()

    def _yukle(self) -> None:
        if not os.path.exists(self.csv_yolu):
            warnings.warn(
                f"[KaggleYukleyici] CSV bulunamadı: {self.csv_yolu}\n"
                f"  İndirme: https://www.kaggle.com/datasets/dheerajperumandla/drowsiness-detection\n"
                f"  → {self.csv_yolu} olarak kaydet."
            )
            return
        try:
            import pandas as pd
            self._df = pd.read_csv(self.csv_yolu)
        except ImportError:
            # pandas yoksa numpy ile oku
            try:
                raw = np.genfromtxt(self.csv_yolu, delimiter=",", names=True, dtype=None, encoding="utf-8")
                self._df = raw
            except Exception as e:
                warnings.warn(f"[KaggleYukleyici] CSV okunamadı: {e}")

    @property
    def hazir(self) -> bool:
        return self._df is not None

    def _sutun_bul(self, adaylar: List[str]) -> Optional[str]:
        """Mevcut sütunlarda aday isimlerden ilk bulunanı döner."""
        if self._df is None:
            return None
        try:
            sutunlar = list(self._df.dtype.names) if hasattr(self._df, "dtype") else list(self._df.columns)
        except Exception:
            return None
        for aday in adaylar:
            if aday in sutunlar:
                return aday
        return None

    def ozellik_etiket_uret(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        CSV'den (X, Y) çiftleri üretir.

        X: (n, 16) — AffectEV özellik formatı (mevcut olmayan sütunlar nötr doldurulur)
        Y: (n, 4)  — Russell-uyumlu 4D duygu etiketi
        """
        if not self.hazir:
            return np.empty((0, 16), dtype=np.float32), np.empty((0, 4), dtype=np.float32)

        try:
            import pandas as pd
            df = self._df if isinstance(self._df, pd.DataFrame) else None
            if df is None:
                # numpy structured array → dict listesi
                df_data = {name: self._df[name] for name in self._df.dtype.names}
            else:
                df_data = {col: df[col].values for col in df.columns}
        except Exception as e:
            warnings.warn(f"[KaggleYukleyici] Veri okunamadı: {e}")
            return np.empty((0, 16), dtype=np.float32), np.empty((0, 4), dtype=np.float32)

        n = len(next(iter(df_data.values())))

        # Sütunları bul
        ear_sut    = self._sutun_bul(self._EAR_ADLARI)
        blink_sut  = self._sutun_bul(self._BLINK_ADLARI)
        perclos_sut= self._sutun_bul(self._PERCLOS_ADLARI)
        etiket_sut = self._sutun_bul(self._ETIKET_ADLARI)

        X_liste: List[np.ndarray] = []
        Y_liste: List[np.ndarray] = []

        for i in range(n):
            # Değerleri al (sütun varsa, yoksa nötr)
            ear_val   = float(df_data[ear_sut][i])    if ear_sut    else 50.0
            blink_val = float(df_data[blink_sut][i])  if blink_sut  else 15.0
            pc_val    = float(df_data[perclos_sut][i]) if perclos_sut else 0.3
            drowsy    = int(df_data[etiket_sut][i])   if etiket_sut  else 0

            # EAR: genellikle [0-1] → [0-100] dönüşüm
            ear_norm   = float(np.clip(ear_val * 100 if ear_val <= 1.0 else ear_val, 0, 100))
            blink_norm = float(np.clip(blink_val, 0, 100))
            kas_norm   = float(np.clip(pc_val * 100 if pc_val <= 1.0 else pc_val, 0, 100))

            # CLS proxy: drowsy=1 → yüksek CLS, drowsy=0 → düşük CLS
            # PERCLOS → CLS dönüşümü (literatür: PERCLOS > 0.25 → yorgunluk)
            cls_proxy = float(np.clip(
                (pc_val if pc_val > 1.0 else pc_val * 100) + drowsy * 30, 0, 100
            ))

            # Duygu etiketi: Kaggle sadece drowsy/alert → 4D yaklaşım
            if drowsy == 1:
                y_raw = np.array([0.65, 0.15, 0.08, 0.12], dtype=np.float32)
            else:
                y_raw = np.array([0.10, 0.15, 0.35, 0.40], dtype=np.float32)
            y_norm = softmax_normalize(y_raw, sicaklik=2.5)

            # 16-özellik vektörü
            x_vec = _kaggle_ozellik_vektoru_yap(cls_proxy, ear_norm, blink_norm, kas_norm)

            X_liste.append(x_vec)
            Y_liste.append(y_norm)

        return (
            np.array(X_liste, dtype=np.float32),
            np.array(Y_liste, dtype=np.float32),
        )


def _kaggle_ozellik_vektoru_yap(
    cls_proxy: float,
    ear_norm: float,
    blink_norm: float,
    kas_norm: float,
) -> np.ndarray:
    """Kaggle satırından 16-özellik vektörü oluşturur."""
    try:
        from duygu_regresyonu import cls_den_duygu_vektoru, DUYGU_BOYUTLARI as _DB
        prior = cls_den_duygu_vektoru(cls_proxy)
        p = [float(prior[d]) for d in _DB]
    except ImportError:
        # duygu_regresyonu yüklenemezse basit prior
        n = cls_proxy / 100.0
        p = [n**1.6, 0.8*math.exp(-((n-0.55)**2)/0.08), (1-n)**1.4, 0.9*(1-n)**2]
        s = sum(p) + 1e-9
        p = [x/s for x in p]

    return np.array([
        p[0], p[1], p[2], p[3],
        np.clip(ear_norm   / 100.0, 0, 1),
        np.clip(blink_norm / 100.0, 0, 1),
        np.clip(kas_norm   / 100.0, 0, 1),
        0.5, 0.5, 0.5, 1.0,       # saat/gün bağlamı: nötr
        0.2, cls_proxy / 100.0,    # km, önceki CLS
        0.4, 0.4, 0.4,             # stres eğilimi, yor eşiği, yaş
    ], dtype=np.float32)


# ─────────────────────────────────────────────────────────────────────
#  ANA YÜKLEME FONKSİYONU  (duygu_regresyonu.py tarafından çağrılır)
# ─────────────────────────────────────────────────────────────────────

def gercek_veri_yukle(
    deap_klasor: str = DEAP_KLASORU,
    kaggle_csv:  str = KAGGLE_CSV,
    deap_pencere_sn: float = 2.0,
    verbose: bool = True,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], str]:
    """
    Hem DEAP hem Kaggle verilerini yüklemeye çalışır, birleştirir.

    Öncelik sırası:
        1. DEAP (.pkl) — akademik, fizyolojik, Russell eşlemeli
        2. Kaggle CSV  — pratik, uykululuk odaklı
        3. Her ikisi de yoksa → (None, None) döner → sentetik kullanılır

    Dönüş
    -----
    X       : (n, 16) özellik matrisi veya None
    Y       : (n, 4)  duygu etiketi veya None
    kaynak  : str — hangi kaynağın kullanıldığını açıklar
    """
    X_parcalar: List[np.ndarray] = []
    Y_parcalar: List[np.ndarray] = []
    kaynaklar: List[str] = []

    # ── DEAP ──────────────────────────────────────────────────────────
    deap = DEAPYukleyici(klasor=deap_klasor)
    if deap.hazir:
        if verbose:
            print(f"[GercekVeri] DEAP yükleniyor: {deap.katilimci_sayisi} katılımcı...")
        X_d, Y_d = deap.ozellik_etiket_uret(pencere_sn=deap_pencere_sn)
        if len(X_d) > 0:
            # DEAP verisini 3x ağırlıklandır (akademik kaynak önceliği)
            X_parcalar.append(np.tile(X_d, (3, 1)))
            Y_parcalar.append(np.tile(Y_d, (3, 1)))
            kaynaklar.append(f"DEAP({len(X_d)} örnek ×3)")
            if verbose:
                print(f"  ✅ DEAP: {len(X_d)} pencere → {len(X_d)*3} örnek (×3 ağırlık)")

    # ── Kaggle CSV ────────────────────────────────────────────────────
    kaggle = KaggleUykululukYukleyici(csv_yolu=kaggle_csv)
    if kaggle.hazir:
        if verbose:
            print(f"[GercekVeri] Kaggle CSV yükleniyor...")
        X_k, Y_k = kaggle.ozellik_etiket_uret()
        if len(X_k) > 0:
            X_parcalar.append(X_k)
            Y_parcalar.append(Y_k)
            kaynaklar.append(f"Kaggle({len(X_k)} örnek)")
            if verbose:
                print(f"  ✅ Kaggle: {len(X_k)} örnek")

    # ── Birleştir ─────────────────────────────────────────────────────
    if not X_parcalar:
        if verbose:
            print("[GercekVeri] ⚠️  Gerçek veri bulunamadı. Sentetik veri kullanılacak.")
        return None, None, "sentetik"

    X_final = np.vstack(X_parcalar).astype(np.float32)
    Y_final = np.vstack(Y_parcalar).astype(np.float32)
    kaynak_str = " + ".join(kaynaklar)

    if verbose:
        print(f"[GercekVeri] ✅ Birleşik veri: {len(X_final)} örnek | Kaynak: {kaynak_str}")

    return X_final, Y_final, kaynak_str


# ─────────────────────────────────────────────────────────────────────
#  DOĞRULAMA ARAÇLARI
# ─────────────────────────────────────────────────────────────────────

def veri_dogrula(X: np.ndarray, Y: np.ndarray) -> Dict:
    """
    Yüklenen veri kalitesini doğrular. Raporu döner.
    """
    if X is None or Y is None or len(X) == 0:
        return {"gecerli": False, "hata": "Boş veri"}

    rapor = {
        "gecerli":          True,
        "ornek_sayisi":     len(X),
        "ozellik_boyutu":   X.shape[1] if X.ndim > 1 else 1,
        "etiket_boyutu":    Y.shape[1] if Y.ndim > 1 else 1,
        "X_nan_sayisi":     int(np.isnan(X).sum()),
        "Y_nan_sayisi":     int(np.isnan(Y).sum()),
        "Y_toplam_1_mi":    bool(np.allclose(Y.sum(axis=1), 1.0, atol=0.05)),
        "duygu_dagilim":    {},
    }

    # Baskın duygu dağılımı
    if Y.ndim == 2 and Y.shape[1] == 4:
        dominant_idx = np.argmax(Y, axis=1)
        for idx, isim in enumerate(DUYGU_BOYUTLARI):
            rapor["duygu_dagilim"][isim] = int((dominant_idx == idx).sum())

    # NaN varsa uyar
    if rapor["X_nan_sayisi"] > 0 or rapor["Y_nan_sayisi"] > 0:
        rapor["gecerli"] = False
        rapor["uyari"]   = f"NaN değerleri var: X={rapor['X_nan_sayisi']}, Y={rapor['Y_nan_sayisi']}"

    return rapor


def russell_tablosu_yazdir() -> None:
    """
    Russell Circumplex eşlemesini tablo olarak yazdırır (tez/rapor için).
    """
    print("\n═══ Russell (1980) Circumplex → AffectEV 4D Duygu Eşlemesi ═══")
    print(f"{'Valence':>8} {'Arousal':>8} | {'Yorgunluk':>10} {'Stres':>8} {'Sakinlik':>10} {'Enerji':>8} | {'Baskın':>10}")
    print("─" * 75)
    for v in [1, 3, 5, 7, 9]:
        for a in [1, 3, 5, 7, 9]:
            d = russell_circumplex_esle(float(v), float(a))
            baskin = max(d, key=d.get)
            print(
                f"{v:>8} {a:>8} |"
                f" {d['yorgunluk']:>10.3f} {d['stres']:>8.3f}"
                f" {d['sakinlik']:>10.3f} {d['enerji']:>8.3f}"
                f" | {baskin:>10}"
            )
    print("═" * 75)


# ─────────────────────────────────────────────────────────────────────
#  TEST
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═══ AffectEV Gerçek Veri Yükleyici — Test ═══\n")

    # Russell Circumplex tablosunu göster
    russell_tablosu_yazdir()

    print("\n─── Örnek Eşlemeler ───")
    ornekler = [
        (1.0, 9.0, "Maksimum stres (düşük V, yüksek A)"),
        (9.0, 9.0, "Tam enerji (yüksek V, yüksek A)"),
        (1.0, 1.0, "Yorgunluk (düşük V, düşük A)"),
        (9.0, 1.0, "Sakinlik (yüksek V, düşük A)"),
        (5.0, 5.0, "Nötr (orta V, orta A)"),
    ]
    for v, a, aciklama in ornekler:
        d = russell_circumplex_esle(v, a)
        baskin = max(d, key=d.get)
        print(f"  {aciklama:<40} → {baskin}")

    print("\n─── Veri Durumu ───")
    X, Y, kaynak = gercek_veri_yukle(verbose=True)
    if X is not None:
        rapor = veri_dogrula(X, Y)
        print(f"\n  Kaynak      : {kaynak}")
        print(f"  Örnek sayısı: {rapor['ornek_sayisi']}")
        print(f"  Duygu dağılımı: {rapor['duygu_dagilim']}")
    else:
        print("\n  ⚠️  Gerçek veri yok.")
        print("  DEAP indirme: http://www.eecs.qmul.ac.uk/mmv/datasets/deap/")
        print("  Kaggle CSV  : https://www.kaggle.com/datasets/dheerajperumandla/drowsiness-detection")
