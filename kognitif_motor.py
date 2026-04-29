"""
kognitif_motor.py  —  AffectEV Kognitif Yük & Duygu Motoru (OpenCV‑only)
=============================================================================
"""

import json
import os
import random
import threading
import time
from datetime import datetime
from typing import Dict, List

import cv2
import numpy as np

# ── Haar Cascade for face detection ────────────────────────────────────────
_FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# ── Configuration ────────────────────────────────────────────────────────
_MODUL_DIR = os.path.dirname(os.path.abspath(__file__))
PROFIL_DOSYASI = os.path.join(_MODUL_DIR, "surucucler.json")

# ── Emotion / CLS tables (only neutral used) ─────────────────────────────────
DUYGU_ETIKETLER = ["neutral"]
DUYGU_CLS_KATKISI = {"neutral": 35}

CV2_VAR = True
MOD_PARAMETRELERI = {
    "enerjik": {"renk": "#00FF00", "ikon": "😊"},
    "notr":    {"renk": "#00CFFF", "ikon": "😐"},
    "stresli": {"renk": "#FFA500", "ikon": "😟"},
    "yorgun":  {"renk": "#FF0000", "ikon": "😫"},
}

def cls_to_mod(cls: float) -> str:
    if cls >= 70:
        return "yorgun"
    elif cls >= 50:
        return "stresli"
    elif cls >= 30:
        return "notr"
    else:
        return "enerjik"

# ── Synthetic driver generator ──────────────────────────────────────────────
_SABLON_SURUCUCLER = [
    {"isim": "Ahmet Y.", "yas": 34, "dominant_duygu": "notr", "blink_baz_dk": 16},
    {"isim": "Zeynep K.", "yas": 29, "dominant_duygu": "stresli", "blink_baz_dk": 22},
    {"isim": "Murat D.", "yas": 52, "dominant_duygu": "notr", "blink_baz_dk": 14},
    {"isim": "Elif S.", "yas": 24, "dominant_duygu": "enerjik", "blink_baz_dk": 18},
    {"isim": "Hasan B.", "yas": 44, "dominant_duygu": "stresli", "blink_baz_dk": 20},
]

def sentetik_surucucu_uret() -> List[Dict]:
    suruculer = []
    for i, s in enumerate(_SABLON_SURUCUCLER):
        suruculer.append({
            "uid": f"U{i+1:02d}",
            "isim": s["isim"],
            "yas": s["yas"],
            "yorgunluk_esigi": 60,
            "sarj_konfor": 20,
            "dominant_duygu": s["dominant_duygu"],
            "biyometrik": {"blink_baz_dk": s["blink_baz_dk"]},
            "suruc_gecmis": [],
        })
    return suruculer

# ── Haar Cascades ────────────────────────────────────────────────────────────
_FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_EYE_CASCADE  = cv2.CascadeClassifier("haarcascade_eye.xml")
_SMILE_CASCADE = cv2.CascadeClassifier("haarcascade_smile.xml")

# ── Cognitive Load Analyzer (Enhanced) ──────────────────────────────────────
class KognitivYukAnalizci:
    def __init__(self, profil: Dict):
        self.profil = profil
        self._kamera = None
        self._aktif = False
        self._son_cls = 45.0
        self._frame_sayac = 0
        self._blink_sayisi = 0
        self._kapat_kare = 0
        self._yorgunluk_skoru = 0.0
        
        # Sinyaller
        self._son_sinyaller = {
            "ear_norm": 30.0,   # Göz kapalılık/yorgunluk (0-100, 100=çok yorgun/kapalı)
            "kas_norm": 20.0,   # Kaş/stres (simüle)
            "blink_norm": 20.0, # Kırpma hızı
            "mar_norm": 0.0,    # Ağız açıklığı (esneme)
            "distraction": 0.0, # Dikkat dağınıklığı
            "duygu": "neutral",
            "blink_sayisi": 0,
        }
        self._son_yuz = None
        self._son_frame = None
        self._display = False
        self._dummy_mode = False
        
        # ML Motoru Entegrasyonu
        try:
            from cls_ml_modeli import OgrenebilirCLSMotoru
            self._ml_motor = OgrenebilirCLSMotoru(profil)
        except ImportError:
            self._ml_motor = None

    def kamera_baslat(self, display: bool = False) -> bool:
        self._display = display
        self._kamera = cv2.VideoCapture(0)
        if self._kamera.isOpened():
            self._aktif = True
            self._dummy_mode = False
            threading.Thread(target=self._kamera_dongusu, daemon=True).start()
            return True
        
        self._dummy_mode = True
        self._aktif = True
        threading.Thread(target=self._kamera_dongusu, daemon=True).start()
        return True

    def kamera_durdur(self):
        self._aktif = False
        if self._kamera:
            self._kamera.release()
            self._kamera = None

    def _kamera_dongusu(self):
        while self._aktif:
            if self._dummy_mode:
                frame = np.full((480, 640, 3), 40, dtype=np.uint8)
                cv2.putText(frame, "KAMERA YOK - SIMULASYON", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                time.sleep(0.1)
            else:
                ret, frame = self._kamera.read()
                if not ret: continue
            
            self._frame_sayac += 1
            if self._frame_sayac % 3 == 0:
                self._frame_analiz(frame)
            
            self._son_frame = self._ciz(frame.copy())
            if self._display:
                cv2.imshow("AffectEV Monitor", self._son_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        self.kamera_durdur()

    def _frame_analiz(self, frame):
        if self._dummy_mode:
            # Simülasyonda CLS'yi yavaşça dalgalandır
            self._son_cls = round(max(10.0, min(95.0, self._son_cls + random.uniform(-1, 1))), 1)
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            self._son_sinyaller["distraction"] = min(100.0, self._son_sinyaller["distraction"] + 5)
            return
        
        self._son_sinyaller["distraction"] = max(0.0, self._son_sinyaller["distraction"] - 2)
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        self._son_yuz = (x, y, w, h)
        
        # ── Göz Analizi (EAR Simülasyonu)
        roi_gray_eyes = gray[y:y+int(h/2), x:x+w]
        eyes = _EYE_CASCADE.detectMultiScale(roi_gray_eyes, 1.1, 10)
        
        if len(eyes) < 2:
            self._kapat_kare += 1
            if self._kapat_kare > 5: # Gözler kapalı/tespit edilemiyor
                self._son_sinyaller["ear_norm"] = min(100.0, self._son_sinyaller["ear_norm"] + 10)
        else:
            if self._kapat_kare >= 2:
                self._blink_sayisi += 1
            self._kapat_kare = 0
            self._son_sinyaller["ear_norm"] = max(0.0, self._son_sinyaller["ear_norm"] - 5)

        # ── Ağız Analizi (MAR / Esneme)
        roi_gray_mouth = gray[y+int(h*0.6):y+h, x:x+w]
        smiles = _SMILE_CASCADE.detectMultiScale(roi_gray_mouth, 1.7, 20)
        if len(smiles) > 0: # Ağız açık/gülümseme
            self._son_sinyaller["mar_norm"] = min(100.0, self._son_sinyaller["mar_norm"] + 15)
        else:
            self._son_sinyaller["mar_norm"] = max(0.0, self._son_sinyaller["mar_norm"] - 5)

        # ── CLS Hesaplama (ML Motoru ile)
        if self._ml_motor:
            self._son_cls = self._ml_motor.tahmin_et(
                ear_norm=self._son_sinyaller["ear_norm"],
                blink_norm=min(100, self._blink_sayisi * 5),
                kas_norm=self._son_sinyaller.get("kas_norm", 20.0),
                bugun_km=0.0 # sim
            )
        else:
            # Fallback kural tabanlı
            self._son_cls = (self._son_sinyaller["ear_norm"] * 0.5 + 
                             self._son_sinyaller["mar_norm"] * 0.3 + 
                             self._son_sinyaller["distraction"] * 0.2)

    def _ciz(self, frame):
        color = (0, 255, 0)
        if self._son_cls > 70: color = (0, 0, 255)
        elif self._son_cls > 40: color = (0, 255, 255)

        if self._son_yuz:
            x, y, w, h = self._son_yuz
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"AffectEV Driver: {cls_to_mod(self._son_cls).upper()}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Overlay Info
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (220, 120), (0,0,0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        cv2.putText(frame, f"CLS: {self._son_cls}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Fatigue (EAR): {int(self._son_sinyaller['ear_norm'])}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(frame, f"Yawn (MAR): {int(self._son_sinyaller['mar_norm'])}%", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(frame, f"Blinks: {self._blink_sayisi}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        
        return frame

    def anlik_cls(self) -> float:
        return self._son_cls

    def anlik_sinyaller(self) -> Dict:
        return self._son_sinyaller

class MLDestekliKognitivYukAnalizci(KognitivYukAnalizci):
    def __init__(self, profil: Dict):
        super().__init__(profil)

# ── Driver Profile Manager ───────────────────────────────────────────────────
class SurucuProfilYonetici:
    def __init__(self):
        self.suruculer = []
        self._yukle()
        if not self.suruculer:
            self.suruculer = sentetik_surucucu_uret()
            self._kaydet()

    def _yukle(self):
        if os.path.exists(PROFIL_DOSYASI):
            with open(PROFIL_DOSYASI, "r", encoding="utf-8") as f:
                self.suruculer = json.load(f)

    def _kaydet(self):
        with open(PROFIL_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(self.suruculer, f, ensure_ascii=False, indent=2)

    def profil_al(self, uid):
        return next((p for p in self.suruculer if p["uid"] == uid), None)

    def profil_guncelle(self, uid, cls, km, tuk_carpan):
        for p in self.suruculer:
            if p["uid"] == uid:
                p.setdefault("gecmis", []).append({"cls": cls, "km": km, "tuk": tuk_carpan})
                break
        self._kaydet()

    def istatistik_ozet(self, uid):
        return {"cls_ort": 40}

# ── Optimization Classes ─────────────────────────────────────
class DuyguRotaOptimizatoru:
    def __init__(self, pm):
        pass

    def optimize_parametreler(self, uid, cls, arac):
        return {
            "rota_krit": "enerji",
            "sarj_esik": 10,
            "sarj_hedef": 80,
            "hiz_carpan": 1.0,
            "tuk_carpan": 1.0,
            "ikon": "😐",
            "renk": "#00CFFF",
            "aciklama": "Normal mod",
            "oneriler": ["✅ İyi sürüşler!"],
        }

class CokAmacliRotaOptimizatoru:
    E_REF = 8.0
    T_REF = 45.0

    @staticmethod
    def agirlik_hesapla(cls):
        return (0.33, 0.33, 0.33)

    @staticmethod
    def kenar_konfor_maliyeti(yt, r, p=None):
        return 0.5

    @staticmethod
    def rota_konfor_skoru(rotasyon, ankara_dugumler, YOLLAR):
        if not rotasyon:
            return 0.0
        
        # Eğer YOLLAR bir list ise (ev_rota_planner formatı), dict'e çevir
        if isinstance(YOLLAR, list):
            y_dict = {}
            for item in YOLLAR:
                if len(item) >= 3:
                    u, v, d = item[0], item[1], item[2]
                    y_dict[(u, v)] = {"mesafe_km": d}
                    y_dict[(v, u)] = {"mesafe_km": d}
            YOLLAR = y_dict

        km = 0.0
        for i in range(len(rotasyon) - 1):
            edge = (rotasyon[i], rotasyon[i + 1])
            data = YOLLAR.get(edge) or YOLLAR.get((edge[1], edge[0]), {})
            km += data.get("mesafe_km", 0.0)
        km_norm = min(km / 100.0, 1.0)
        kavsak_norm = min((len(rotasyon) - 1) / 30.0, 1.0)
        score = 100.0 - (km_norm * 50 + kavsak_norm * 30)
        return max(0.0, min(100.0, score))

    @staticmethod
    def en_iyi_rota_sec(rotalar, met_tum, konfor_sk, cls, **kwargs):
        if "mesafe" in rotalar and rotalar["mesafe"]:
            return "mesafe", {}, {}
        first_key = next(iter(rotalar))
        return first_key, {}, {}
