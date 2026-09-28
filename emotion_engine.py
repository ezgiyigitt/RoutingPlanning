"""
AffectEV Emotion Engine  (MediaPipe'sız, saf OpenCV + RAF-DB CNN)
=================================================================
Mimari:
  1. OpenCV Haar Cascade  →  Yüz bul & kırp
  2. Haar Eye Cascade     →  Göz açık/kapalı (minNeighbors iyileştirildi)
  3. RAF-DB CNN (Keras)   →  Duygu sınıflandırması
     • Sınıflar: surprise | fear | disgust | happiness | sadness | anger | neutral

Bağımlılıklar:  pip install opencv-python numpy tensorflow
Python 3.13 ile tam uyumlu – MediaPipe GEREKMİYOR.
"""

import cv2
import numpy as np
import os
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ─── Ortam değişkenleri (TF loglarını kapat) ──────────────────────────────────
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"

# ─── TensorFlow / Keras ────────────────────────────────────────────────────────
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except Exception as _e:
    TF_AVAILABLE = False
    logger.warning(f"TensorFlow yüklenemedi: {_e}")

# ─── Sabitler ─────────────────────────────────────────────────────────────────
IMG_SIZE       = (48, 48)
RAF_EMOTIONS   = ["surprise", "fear", "disgust", "happiness",
                  "sadness", "anger", "neutral"]
RAF_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "modeller", "raf_db_emotion_model.keras"
)

# Haar Cascade dosyaları (OpenCV ile birlikte gelir)
_FACE_CASCADE_PATH  = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_EYE_CASCADE_PATH   = cv2.data.haarcascades + "haarcascade_eye.xml"
_SMILE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_smile.xml"


# ══════════════════════════════════════════════════════════════════════════════
# 1. SINGLETON CASCADE YÜKLEYİCİ  (her çağrıda yeniden yükleme yok)
# ══════════════════════════════════════════════════════════════════════════════

_face_cascade  = None
_eye_cascade   = None
_smile_cascade = None


def _get_cascades():
    global _face_cascade, _eye_cascade, _smile_cascade
    if _face_cascade is None:
        _face_cascade  = cv2.CascadeClassifier(_FACE_CASCADE_PATH)
        _eye_cascade   = cv2.CascadeClassifier(_EYE_CASCADE_PATH)
        _smile_cascade = cv2.CascadeClassifier(_SMILE_CASCADE_PATH)
    return _face_cascade, _eye_cascade, _smile_cascade


# ══════════════════════════════════════════════════════════════════════════════
# 2. RAF-DB CNN  (singleton yükleme)
# ══════════════════════════════════════════════════════════════════════════════

_raf_model = None


def _load_raf_model():
    global _raf_model
    if _raf_model is not None:
        return _raf_model
    if not TF_AVAILABLE:
        return None
    if os.path.exists(RAF_MODEL_PATH):
        try:
            _raf_model = keras.models.load_model(RAF_MODEL_PATH, compile=False)
            logger.info(f"RAF-DB modeli yüklendi: {RAF_MODEL_PATH}")
        except Exception as e:
            logger.warning(f"RAF-DB model yükleme hatası: {e}")
    else:
        logger.warning(f"RAF-DB model bulunamadı: {RAF_MODEL_PATH}")
    return _raf_model


def _predict_emotion(face_roi_bgr):
    """
    Kırpılmış yüz görüntüsüne bakarak RAF-DB CNN'den duygu tahmini alır.
    Başarılı olursa (etiket, güven) tuple döner; değilse None.
    """
    model = _load_raf_model()
    if model is None or face_roi_bgr is None or face_roi_bgr.size == 0:
        return None
    try:
        face = cv2.resize(face_roi_bgr, IMG_SIZE)
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        preds = model.predict(np.expand_dims(face, 0), verbose=0)[0]
        idx   = int(np.argmax(preds))
        return RAF_EMOTIONS[idx], float(preds[idx])
    except Exception as e:
        logger.debug(f"RAF tahmin hatası: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 3. GÖZ AÇIKLIK DEĞERLENDİRMESİ  (Haar Eye Cascade tabanlı)
# ══════════════════════════════════════════════════════════════════════════════

def _detect_eyes_open(face_roi_gray, face_h):
    """
    Yüzün gri-tonlama ROI'si içinden göz tespiti yapar.

    Gelişmeler:
    - Yalnızca yüzün üst %55'ine bakılır (burun/ağız bölgesi göz sanılmaz).
    - minNeighbors=10 ile titreme azaltılır.
    - En az 2 göz bulunursa "açık" kabul edilir.

    Returns:
        eyes_open (bool)
        eye_count (int)  – bulunan göz adedi
    """
    _, eye_c, _ = _get_cascades()

    # Yalnızca üst %55'e bak
    upper_roi  = face_roi_gray[: int(face_h * 0.55), :]
    eyes       = eye_c.detectMultiScale(
        upper_roi,
        scaleFactor=1.1,
        minNeighbors=10,   # Daha az gürültü
        minSize=(20, 20),
        maxSize=(80, 80),
    )
    count      = len(eyes)
    eyes_open  = count >= 2
    return eyes_open, count


# ══════════════════════════════════════════════════════════════════════════════
# 4. ANA TESPİT FONKSİYONU
# ══════════════════════════════════════════════════════════════════════════════

def detect_smile_and_eyes(frame_bgr):
    """
    OpenCV + RAF-DB CNN ile sürücü durum analizi.

    Adımlar:
      1. Haar Cascade → Yüzü bul & kırp
      2. Haar Eye     → Göz açık mı?
      3. RAF-DB CNN   → Duygu (happiness → gülümseme)
      4. Haar Smile   → CNN yoksa/güvensizse yedek gülümseme

    Returns
    -------
    smile_detected : bool
    eyes_open      : bool
    confidence     : float  (0-1)
    debug_info     : dict
        source, emotion, emotion_conf, eye_count, smile_method
    """
    debug_info = {
        "source":       "opencv_haar",
        "emotion":      "unknown",
        "emotion_conf": 0.0,
        "eye_count":    0,
        "smile_method": "none",
    }

    smile_detected = False
    eyes_open      = False
    confidence     = 0.5

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    # Gürültü azalt
    gray = cv2.equalizeHist(gray)

    face_c, _, smile_c = _get_cascades()

    # ── 1. Yüz Tespiti ────────────────────────────────────────────────────────
    faces = face_c.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        # Yüz bulunamadı → hiçbir şey tespit edemiyoruz
        debug_info["source"] = "no_face_detected"
        return False, False, 0.3, debug_info

    # En büyük yüzü al
    faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    x, y, wf, hf = faces_sorted[0]
    face_roi_bgr  = frame_bgr[y:y + hf, x:x + wf]
    face_roi_gray = gray[y:y + hf, x:x + wf]

    # ── 2. Göz Açıklık Tespiti ────────────────────────────────────────────────
    eyes_open, eye_count = _detect_eyes_open(face_roi_gray, hf)
    debug_info["eye_count"] = eye_count

    # Güven: 2 göz bulunduysa yüksek, 1 göz → orta, 0 göz → düşük
    eye_conf = {0: 0.35, 1: 0.55}.get(eye_count, 0.80)

    # ── 3. RAF-DB CNN ile Duygu ───────────────────────────────────────────────
    raf = _predict_emotion(face_roi_bgr)
    if raf is not None:
        emotion, conf_e = raf
        debug_info["emotion"]      = emotion
        debug_info["emotion_conf"] = round(conf_e, 4)
        debug_info["source"]       = "opencv_haar + raf_db_cnn"

        # happiness & güven eşiği (>%40)
        smile_detected = (emotion == "happiness" and conf_e > 0.40)
        debug_info["smile_method"] = "raf_db_cnn"
        confidence = round((eye_conf + conf_e) / 2, 3)
    else:
        # ── 4. Yedek: Haar Smile ──────────────────────────────────────────────
        smiles = smile_c.detectMultiScale(
            face_roi_gray,
            scaleFactor=1.7,
            minNeighbors=22,
            minSize=(30, 30),
        )
        smile_detected = len(smiles) > 0
        debug_info["smile_method"] = "haar_smile_fallback"
        confidence = eye_conf

    return smile_detected, eyes_open, confidence, debug_info


# ══════════════════════════════════════════════════════════════════════════════
# 5. CLI TEST  (python emotion_engine.py)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print(f"TensorFlow  : {'✅' if TF_AVAILABLE else '❌'}")
    print(f"RAF-DB model: {'✅' if os.path.exists(RAF_MODEL_PATH) else '❌ (model bulunamadı)'}")
    print("\n📷 Kamera testi başlatılıyor (q ile çık)...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Kamera açılamadı.")
        sys.exit(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        smile, eyes_open, conf, dbg = detect_smile_and_eyes(frame)

        eye_col  = (0, 255, 0) if eyes_open else (0, 0, 255)
        eye_lbl  = f"GOZLER: {'ACIK' if eyes_open else 'KAPALI'} ({dbg['eye_count']} göz)"
        sml_lbl  = f"GULUMSE: {'EVET' if smile else 'HAYIR'}"
        emo_lbl  = f"DUYGU: {dbg['emotion']} ({dbg['emotion_conf']:.0%})"
        src_lbl  = f"Kaynak: {dbg['source']}"

        cv2.putText(frame, eye_lbl, (10, 35),  cv2.FONT_HERSHEY_SIMPLEX, 0.75, eye_col, 2)
        cv2.putText(frame, sml_lbl, (10, 65),  cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 200, 0), 2)
        cv2.putText(frame, emo_lbl, (10, 95),  cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 0), 2)
        cv2.putText(frame, src_lbl, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        cv2.imshow("AffectEV – OpenCV + RAF-DB CNN", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
