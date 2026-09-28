"""
Kamera ile yüz okuma (deneysel, isteğe bağlı modül).

Bildiri kapsamı notu: Bildiride CLS kontrollü senaryo parametresi olarak atanmış,
biyometrik kestirim modülünün eğitimi/doğrulanması kapsam dışı bırakılmıştır.
Bu modül yalnızca arayüzde Dn. (1)'in F ve V girdilerini kameradan ÖNERMEK için
kullanılır; bildirideki deney sonuçlarında kullanılmaz ve doğrulanmış değildir.

Yöntem:
  1. OpenCV Haar Cascade ile yüz tespiti (en büyük yüz).
  2. Yüzün üst %55'inde Haar göz tespiti → göz açık/kapalı (kare başına).
  3. Duygu: RAF-DB CNN modeli (TensorFlow kuruluysa ve model dosyası varsa);
     yoksa Haar gülümseme tespiti (yedek).
  4. Kareler üzerinden özet:
       F (yorgunluk)        = 100 × gözlerin kapalı olduğu kare oranı (PERCLOS benzeri)
       V (olumsuz değerlik) = CNN varsa 100 × ortalama P(korku+iğrenme+üzüntü+öfke);
                              yoksa 50 × (1 − gülümseme oranı)
       C (bilişsel yük)     = kameradan ölçülmez; kullanıcı girer.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

CV2_PROBLEM = None
try:
    import cv2
    # Birden fazla OpenCV paketi (opencv-python / -headless / -contrib, ör. MediaPipe ile gelen)
    # üst üste kurulunca 'cv2' modülü yarım kalabilir: import başarılı olur ama sınıflar eksiktir.
    if not hasattr(cv2, "CascadeClassifier"):
        CV2_PROBLEM = (f"OpenCV kurulumu bozuk (cv2 modülünde CascadeClassifier yok; konum: "
                       f"{getattr(cv2, '__file__', '?')}). Tüm AffectEV pencerelerini kapatıp "
                       f"OpenCV_Onar.bat dosyasını çalıştırın.")
        CV2_AVAILABLE = False
    else:
        CV2_AVAILABLE = True
except Exception as _e:  # pragma: no cover
    cv2 = None
    CV2_AVAILABLE = False
    CV2_PROBLEM = f"OpenCV yüklenemedi ({_e}). OpenCV_Onar.bat dosyasını çalıştırın."

HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_CANDIDATES = [
    os.path.join(os.path.dirname(HERE), "models", "raf_db_emotion_model.keras"),
    os.path.join(os.path.dirname(os.path.dirname(HERE)), "modeller", "raf_db_emotion_model.keras"),
]
RAF_EMOTIONS = ["surprise", "fear", "disgust", "happiness", "sadness", "anger", "neutral"]
EMOTION_TR = {"surprise": "şaşkınlık", "fear": "korku", "disgust": "iğrenme", "happiness": "mutluluk",
              "sadness": "üzüntü", "anger": "öfke", "neutral": "nötr"}
NEGATIVE = {"fear", "disgust", "sadness", "anger"}

_cascades = None
_model = None
_model_tried = False


CASCADE_DIR = os.path.join(os.path.dirname(HERE), "data", "haarcascades")   # projeyle gelen kopyalar
CASCADE_FILES = ("haarcascade_frontalface_default.xml", "haarcascade_eye.xml", "haarcascade_smile.xml")


def _load_cascade(name: str):
    """Haar sınıflandırıcısını yükler. Önce projeyle gelen dosya, sonra OpenCV'nin kendi kopyası denenir.
    Yol yüklemesi başarısız olursa (ör. Türkçe karakterli yol) dosya bellekten okunur."""
    dirs = [CASCADE_DIR]
    data = getattr(cv2, "data", None)
    if data is not None and getattr(data, "haarcascades", None):
        dirs.append(data.haarcascades)
    tried = []
    for d in dirs:
        path = os.path.join(d, name)
        if not os.path.exists(path):
            tried.append(f"{path} (yok)")
            continue
        clf = cv2.CascadeClassifier(path)
        if not clf.empty():
            return clf
        try:
            with open(path, "r", encoding="utf-8") as f:
                xml = f.read()
            fs = cv2.FileStorage(xml, cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
            clf = cv2.CascadeClassifier()
            if clf.read(fs.getFirstTopLevelNode()) and not clf.empty():
                return clf
        except Exception:
            pass
        tried.append(f"{path} (okunamadı)")
    raise RuntimeError(f"Haar sınıflandırıcısı yüklenemedi: {name}. OpenCV {cv2.__version__}. "
                       f"Denenen: {'; '.join(tried)}. OpenCV_Onar.bat dosyasını çalıştırın.")


def _get_cascades():
    global _cascades
    if _cascades is None:
        _cascades = tuple(_load_cascade(n) for n in CASCADE_FILES)
    return _cascades


def _get_model():
    """RAF-DB CNN'i (varsa) bir kez yükler."""
    global _model, _model_tried
    if _model_tried:
        return _model
    _model_tried = True
    path = next((p for p in _MODEL_CANDIDATES if os.path.exists(p)), None)
    if path is None:
        return None
    try:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        from tensorflow import keras  # type: ignore
        _model = keras.models.load_model(path, compile=False)
        logger.info("RAF-DB modeli yüklendi: %s", path)
    except Exception as e:  # TensorFlow yoksa sessizce yedek yönteme geç
        logger.info("RAF-DB modeli kullanılamıyor (%s); Haar gülümseme yedeği kullanılacak.", e)
        _model = None
    return _model


def status() -> Dict[str, object]:
    return {"opencv": CV2_AVAILABLE, "problem": CV2_PROBLEM, "emotion_model": _get_model() is not None if CV2_AVAILABLE else False}


def decode_image(b64: str):
    if "," in b64[:64]:
        b64 = b64.split(",", 1)[1]
    arr = np.frombuffer(base64.b64decode(b64), np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Görüntü çözülemedi")
    return img


def _predict_emotion(model, roi_bgr) -> Optional[np.ndarray]:
    """RAF-DB CNN tahmini; modelin girdi biçimi (RGB/gri, boyut) otomatik uyarlanır.
    Herhangi bir hata olursa None döner ve Haar gülümseme yedeğine geçilir."""
    global _model
    try:
        shape = getattr(model, "input_shape", (None, 48, 48, 3))
        if isinstance(shape, list):
            shape = shape[0]
        h, w = int(shape[1] or 48), int(shape[2] or 48)
        ch = int(shape[3] or 3) if len(shape) > 3 else 1
        img = cv2.resize(roi_bgr, (w, h))
        if ch == 1:
            x = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255.0
        else:
            x = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        p = np.asarray(model.predict(x[None], verbose=0)[0], dtype=float).ravel()
        if p.size != len(RAF_EMOTIONS) or not np.all(np.isfinite(p)):
            raise ValueError(f"beklenmeyen model çıktısı: {p.shape}")
        p = np.clip(p, 0, None)
        return p / p.sum() if p.sum() > 0 else None
    except Exception as e:
        logger.warning("RAF-DB tahmini başarısız, Haar yedeğine geçiliyor: %s", e)
        _model = None          # bu oturumda tekrar denenmesin
        return None


def analyze_frame(frame_bgr) -> Dict[str, object]:
    face_c, eye_c, smile_c = _get_cascades()
    if frame_bgr.shape[1] > 640:
        k = 640.0 / frame_bgr.shape[1]
        frame_bgr = cv2.resize(frame_bgr, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    gray = cv2.equalizeHist(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY))
    h_img = gray.shape[0]
    faces = face_c.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=8, minSize=(max(60, h_img // 8),) * 2)
    if len(faces) == 0:
        return {"face": False}
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    roi_c = frame_bgr[y:y + h, x:x + w]
    roi_g = cv2.resize(gray[y:y + h, x:x + w], (200, 200))   # ölçekten bağımsız tespit
    eyes = eye_c.detectMultiScale(roi_g[:110, :], scaleFactor=1.1, minNeighbors=8,
                                  minSize=(20, 20), maxSize=(100, 100))
    out: Dict[str, object] = {"face": True, "box": [int(x), int(y), int(w), int(h)],
                              "eye_count": int(len(eyes)), "eyes_open": bool(len(eyes) >= 2)}
    model = _get_model()
    p = _predict_emotion(model, roi_c) if model is not None else None
    if p is not None:
        out["emotion_probs"] = {e: float(v) for e, v in zip(RAF_EMOTIONS, p)}
        out["emotion"] = RAF_EMOTIONS[int(np.argmax(p))]
        out["smile"] = bool(out["emotion"] == "happiness" and p.max() > 0.4)
    else:
        smiles = smile_c.detectMultiScale(roi_g[100:, :], scaleFactor=1.5, minNeighbors=20, minSize=(40, 20))
        out["smile"] = bool(len(smiles) > 0)
    return out


def summarize(frames: List[Dict[str, object]]) -> Dict[str, object]:
    faced = [f for f in frames if f.get("face")]
    n, nf = len(frames), len(faced)
    if nf == 0:
        return {"frames": n, "face_frames": 0, "ok": False,
                "message": "Yüz bulunamadı. Kameraya önden bakın ve ortamın aydınlık olduğundan emin olun."}
    closed = float(np.mean([not f["eyes_open"] for f in faced]))
    smile = float(np.mean([f["smile"] for f in faced]))
    res: Dict[str, object] = {"frames": n, "face_frames": nf, "ok": True,
                              "eyes_closed_ratio": round(closed, 3), "smile_ratio": round(smile, 3)}
    probs = [f["emotion_probs"] for f in faced if "emotion_probs" in f]
    if probs:
        mean = {e: float(np.mean([p[e] for p in probs])) for e in RAF_EMOTIONS}
        neg = sum(mean[e] for e in NEGATIVE)
        dom = max(mean, key=mean.get)
        res.update({"method": "Haar + RAF-DB CNN", "emotion": dom, "emotion_tr": EMOTION_TR[dom],
                    "emotion_probs": {k: round(v, 3) for k, v in mean.items()},
                    "valence_negative": round(100 * neg, 1)})
    else:
        res.update({"method": "Haar (göz + gülümseme)", "emotion": None, "emotion_tr": None,
                    "valence_negative": round(50.0 * (1.0 - smile), 1)})
    res["fatigue"] = round(100 * closed, 1)
    res["suggested"] = {"F": res["fatigue"], "V": res["valence_negative"]}
    return res


def analyze_batch(images_b64: List[str]) -> Dict[str, object]:
    if not CV2_AVAILABLE:
        raise RuntimeError(CV2_PROBLEM or "OpenCV kullanılamıyor. OpenCV_Onar.bat dosyasını çalıştırın.")
    frames, errors = [], []
    for b in images_b64:
        try:
            frames.append(analyze_frame(decode_image(b)))
        except Exception as e:          # bozuk kare veya OpenCV hatası: kareyi atla
            errors.append(f"{type(e).__name__}: {e}")
            frames.append({"face": False})
    if errors and len(errors) == len(images_b64):
        raise RuntimeError(errors[0])
    res = summarize(frames)
    if errors:
        res["skipped_frames"] = len(errors)
    return res
