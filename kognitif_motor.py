"""
kognitif_motor.py  —  AffectEV Kognitif Yük & Duygu Motoru
===========================================================
Kurulum : pip install opencv-python opencv-contrib-python numpy  (opsiyonel)
"""

import json, math, os, random, time, threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ── Opsiyonel OpenCV
try:
    import cv2, numpy as np
    CV2_VAR = True
except ImportError:
    CV2_VAR = False

PROFIL_DOSYASI = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "surucucler.json"
)

# ─────────────────────────────────────────────
#  MOD SİSTEMİ
# ─────────────────────────────────────────────
def cls_to_mod(cls: float) -> str:
    """CLS skorunu duygu moduna çevirir."""
    if cls >= 70:   return "yorgun"
    elif cls >= 50: return "stresli"
    elif cls >= 30: return "notr"
    else:           return "enerjik"

MOD_PARAMETRELERI = {
    "yorgun":  {
        "rota_krit": "mesafe", "sarj_esik": 20, "sarj_hedef": 85,
        "hiz_carpan": 0.80, "mola_aralik_km": 25, "trafik_kac": True,
        "tuk_carpan": 1.22, "ikon": "😴", "renk": "#FF4444",
        "aciklama": "Yorgun sürücü — kısa rota, sık şarj, düşük hız",
        "oneriler": [
            "⚠️ Yorgunluk tespit edildi — mola önerilir",
            "☕ İlk şarj durağında dinlenme fırsatı var",
        ],
    },
    "stresli": {
        "rota_krit": "sure",   "sarj_esik": 15, "sarj_hedef": 80,
        "hiz_carpan": 0.90, "mola_aralik_km": 40, "trafik_kac": True,
        "tuk_carpan": 1.12, "ikon": "😰", "renk": "#FFB800",
        "aciklama": "Stresli sürücü — trafiksiz yol, sakin hız",
        "oneriler": [
            "🛤️ Trafiksiz alternatif rota seçildi",
            "🎵 Sakinleştirici müzik profili önerilir",
        ],
    },
    "notr": {
        "rota_krit": "enerji", "sarj_esik": 10, "sarj_hedef": 80,
        "hiz_carpan": 1.00, "mola_aralik_km": 60, "trafik_kac": False,
        "tuk_carpan": 1.00, "ikon": "😐", "renk": "#00CFFF",
        "aciklama": "Normal mod — enerji-duyarlı rota",
        "oneriler": [
            "✅ İyi sürüşler! Her şey normal görünüyor.",
        ],
    },
    "enerjik": {
        "rota_krit": "sure",   "sarj_esik": 8,  "sarj_hedef": 75,
        "hiz_carpan": 1.10, "mola_aralik_km": 80, "trafik_kac": False,
        "tuk_carpan": 0.95, "ikon": "😄", "renk": "#00FF88",
        "aciklama": "Enerjik sürücü — en hızlı rota",
        "oneriler": [
            "🚀 Enerji yüksek — rota hız için optimize edildi",
        ],
    },
}

# ─────────────────────────────────────────────
#  SENTETİK SÜRÜCÜ VERİLERİ
# ─────────────────────────────────────────────
_SABLON_SURUCUCLER = [
    {"isim": "Ahmet Y.",  "yas": 34, "meslek": "Yazılım Müh.",   "gun_ici_tip": "sabahçı",
     "stres_egilimi": 0.35, "yorgunluk_esigi": 65, "tercih_hizi": 70,
     "sarj_konfor": 30, "km_yil": 18000, "dominant_duygu": "notr",    "blink_baz_dk": 16},
    {"isim": "Zeynep K.", "yas": 29, "meslek": "Doktor",          "gun_ici_tip": "gece",
     "stres_egilimi": 0.72, "yorgunluk_esigi": 45, "tercih_hizi": 55,
     "sarj_konfor": 25, "km_yil": 22000, "dominant_duygu": "stresli", "blink_baz_dk": 22},
    {"isim": "Murat D.",  "yas": 52, "meslek": "Yönetici",        "gun_ici_tip": "sabahçı",
     "stres_egilimi": 0.40, "yorgunluk_esigi": 55, "tercih_hizi": 80,
     "sarj_konfor": 40, "km_yil": 30000, "dominant_duygu": "notr",    "blink_baz_dk": 14},
    {"isim": "Elif S.",   "yas": 24, "meslek": "Öğrenci",         "gun_ici_tip": "gece",
     "stres_egilimi": 0.28, "yorgunluk_esigi": 80, "tercih_hizi": 90,
     "sarj_konfor": 15, "km_yil":  8000, "dominant_duygu": "enerjik", "blink_baz_dk": 18},
    {"isim": "Hasan B.",  "yas": 44, "meslek": "Tıbbi Temsilci",  "gun_ici_tip": "karma",
     "stres_egilimi": 0.55, "yorgunluk_esigi": 50, "tercih_hizi": 75,
     "sarj_konfor": 35, "km_yil": 45000, "dominant_duygu": "stresli", "blink_baz_dk": 20},
    {"isim": "Selin A.",  "yas": 38, "meslek": "Mimar",           "gun_ici_tip": "sabahçı",
     "stres_egilimi": 0.30, "yorgunluk_esigi": 70, "tercih_hizi": 65,
     "sarj_konfor": 30, "km_yil": 15000, "dominant_duygu": "notr",    "blink_baz_dk": 17},
    {"isim": "Emre T.",   "yas": 27, "meslek": "Kurye",           "gun_ici_tip": "karma",
     "stres_egilimi": 0.48, "yorgunluk_esigi": 55, "tercih_hizi": 85,
     "sarj_konfor": 20, "km_yil": 40000, "dominant_duygu": "yorgun",  "blink_baz_dk": 24},
    {"isim": "Fatma Ö.",  "yas": 61, "meslek": "Emekli",          "gun_ici_tip": "sabahçı",
     "stres_egilimi": 0.20, "yorgunluk_esigi": 60, "tercih_hizi": 50,
     "sarj_konfor": 45, "km_yil":  6000, "dominant_duygu": "notr",    "blink_baz_dk": 12},
    {"isim": "Burak Ç.",  "yas": 33, "meslek": "Sporcu/Antrenör", "gun_ici_tip": "sabahçı",
     "stres_egilimi": 0.18, "yorgunluk_esigi": 85, "tercih_hizi": 95,
     "sarj_konfor": 10, "km_yil": 20000, "dominant_duygu": "enerjik", "blink_baz_dk": 15},
    {"isim": "Derya M.",  "yas": 46, "meslek": "Öğretmen",        "gun_ici_tip": "sabahçı",
     "stres_egilimi": 0.42, "yorgunluk_esigi": 58, "tercih_hizi": 60,
     "sarj_konfor": 35, "km_yil": 12000, "dominant_duygu": "notr",    "blink_baz_dk": 16},
]


def _cls_sablon_hesapla(sablon: Dict, saat: int, gun_no: int) -> float:
    baz = {"yorgun": 65, "stresli": 58, "notr": 40, "enerjik": 22}.get(
        sablon["dominant_duygu"], 40)
    if sablon["gun_ici_tip"] == "sabahçı" and saat >= 20: baz += 15
    elif sablon["gun_ici_tip"] == "gece"   and saat <= 9:  baz += 20
    if saat in (8, 9, 17, 18, 19): baz += sablon["stres_egilimi"] * 25
    baz += (gun_no % 7) * 1.2
    return min(95, max(5, baz))


def _cls_tuketim_carpani(cls: float) -> float:
    if cls < 30:   return random.uniform(0.92, 0.98)
    elif cls < 50: return random.uniform(0.98, 1.05)
    elif cls < 70: return random.uniform(1.05, 1.18)
    else:          return random.uniform(1.18, 1.35)


def sentetik_surucucu_uret() -> List[Dict]:
    suruculer = []
    random.seed(42)
    for i, s in enumerate(_SABLON_SURUCUCLER):
        uid = f"U{i+1:02d}"
        gecmis = []
        baz_tarih = datetime.now() - timedelta(days=30)
        for gun in range(30):
            tarih    = baz_tarih + timedelta(days=gun)
            is_gunu  = tarih.weekday() < 5
            n_sefer  = random.randint(1, 4) if is_gunu else random.randint(0, 2)
            gun_sefer = []
            for _ in range(n_sefer):
                saat = random.choice(
                    [7, 8, 9] if s["gun_ici_tip"] == "sabahçı"
                    else ([19, 20, 21, 22] if s["gun_ici_tip"] == "gece"
                          else [7, 12, 17, 21]))
                km  = max(1, round(random.gauss(s["km_yil"] / 365, 5), 1))
                cls = max(0, min(100, random.gauss(
                    _cls_sablon_hesapla(s, saat, gun), 12)))
                gun_sefer.append({
                    "saat": saat, "km": km,
                    "cls_ort": round(cls, 1),
                    "tuk_carpan": round(_cls_tuketim_carpani(cls), 3),
                    "mod": cls_to_mod(cls),
                })
            gecmis.append({"tarih": tarih.strftime("%Y-%m-%d"),
                           "seferler": gun_sefer})

        n_kull = random.randint(0, 25)
        suruculer.append({
            "uid": uid, "isim": s["isim"], "yas": s["yas"],
            "meslek": s["meslek"], "gun_ici_tip": s["gun_ici_tip"],
            "stres_egilimi": s["stres_egilimi"],
            "yorgunluk_esigi": s["yorgunluk_esigi"],
            "tercih_hizi": s["tercih_hizi"],
            "sarj_konfor": s["sarj_konfor"],
            "km_yil": s["km_yil"],
            "dominant_duygu": s["dominant_duygu"],
            "biyometrik": {
                "blink_baz_dk":     s["blink_baz_dk"],
                "blink_std":        round(random.uniform(2, 5), 2),
                "goz_acikligi_baz": round(random.uniform(0.65, 0.85), 3),
                "kas_kasılma_baz":  round(random.uniform(0.05, 0.20), 3),
            },
            "yuz_embedding":       [round(random.gauss(0, 1), 4) for _ in range(128)],
            "taninma_dogrulugu":   round(min(0.99, 0.60 + n_kull * 0.016), 3),
            "kullanim_sayisi":     n_kull,
            "suruc_gecmis":        gecmis,
            "olusturma":           datetime.now().isoformat(),
            "son_cls": None, "son_mod": None,
        })
    return suruculer


# ─────────────────────────────────────────────
#  KOGNİTİF YÜK ANALİZCİSİ
# ─────────────────────────────────────────────
def _baglamsal_yorgunluk(profil: Dict) -> float:
    """
    Saate, gün-içi tipe ve bugünkü km'ye göre bağlamsal yorgunluk skoru (0-100) döndürür.
    """
    saat      = datetime.now().hour
    tip       = profil.get("gun_ici_tip", "sabahçı")
    yor_esigi = profil.get("yorgunluk_esigi", 60)  # kişiye özel eşik

    if tip == "sabahçı":
        # Geç gece (21-23) ve çok erken sabah (0-5) yorucu
        if saat >= 21:
            saat_etki = (saat - 20) * 7   # 21→7, 22→14, 23→21
        elif saat <= 5:
            saat_etki = (6 - saat) * 8    # 5→8, 4→16, 0→48
        elif saat in (8, 9):               # pik trafik saatleri sabahçıyı gerer
            saat_etki = 8
        else:
            saat_etki = 0
    elif tip == "gece":
        # Sabahın erken saatlerinde (0-10) uykusuz
        if saat <= 5:
            saat_etki = (6 - saat) * 10
        elif saat <= 10:
            saat_etki = (11 - saat) * 5
        elif saat in (17, 18, 19):
            saat_etki = 8   # gece sürücüsü akşam trafik saatinde de gerilir
        else:
            saat_etki = 0
    else:  # karma
        saat_etki = 12 if saat in (8, 9, 17, 18, 19) else 0

    # Bugün sürülen km → arttıkça yorgunluk artar (maks +40)
    bugun_km = sum(s.get("km", 0)
                   for g in profil.get("suruc_gecmis", [])[-1:]
                   for s in g.get("seferler", []))
    km_etki = min(40, bugun_km / 150 * 40)

    # Kişinin yorgunluk eşiği ne kadar düşükse o kadar çabuk yorulur (+0 to +20)
    esik_etki = max(0, (60 - yor_esigi) * 0.4)

    return min(95.0, max(0.0, saat_etki + km_etki + esik_etki))


class KognitivYukAnalizci:
    """
    Kameradan yüz okuyarak kognitif yük skoru (CLS 0-100) hesaplar.
    Skor, seçilen kullanıcının baz biyometrik değerlerine göre normalize edilir.
    OpenCV yoksa simülasyon modunda çalışır.
    """

    def __init__(self, profil: Dict):
        self.profil       = profil
        self.bio          = profil["biyometrik"]
        self._kamera      = None
        self._aktif       = False
        self._son_cls     = 45.0
        self._cls_gecmis: List[float] = []
        self._frame_sayac = 0

        if CV2_VAR:
            try:
                self._yuz_dedek = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                self._goz_dedek = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_eye.xml")
            except Exception:
                pass

    # ── Kamerayı aç, önizleme başlat
    def kamera_baslat(self) -> bool:
        if not CV2_VAR:
            return False
        try:
            self._kamera = cv2.VideoCapture(0)
            if not self._kamera.isOpened():
                return False
            self._aktif = True
            threading.Thread(target=self._kamera_dongusu, daemon=True).start()
            return True
        except Exception:
            return False

    def kamera_durdur(self):
        self._aktif = False
        time.sleep(0.15)
        if self._kamera:
            self._kamera.release()
            self._kamera = None
        if CV2_VAR:
            try: cv2.destroyWindow("AffectEV — Kamera")
            except Exception: pass

    # ── Kamera döngüsü (OpenCV)
    def _kamera_dongusu(self):
        pencere = "AffectEV — Kamera"
        cv2.namedWindow(pencere, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(pencere, 700, 480)
        try: cv2.setWindowProperty(pencere, cv2.WND_PROP_TOPMOST, 1)
        except Exception: pass

        while self._aktif and self._kamera and self._kamera.isOpened():
            ret, frame = self._kamera.read()
            if not ret:
                time.sleep(0.05)
                continue
            self._frame_sayac += 1
            if self._frame_sayac % 15 == 0:
                cls = self._frame_analiz(frame)
                self._kaydet(cls)
            cv2.imshow(pencere, self._ciz(frame.copy()))
            if cv2.waitKey(30) & 0xFF in (ord('q'), ord('Q'), 27):
                break
        self.kamera_durdur()

    def _frame_analiz(self, frame) -> float:
        """
        Gerçek kameradan CLS hesapla.
        Kullanıcının baz değerleriyle (goz_acikligi_baz) karşılaştırılır.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:   yuzler = self._yuz_dedek.detectMultiScale(gray, 1.1, 5, minSize=(80,80))
        except Exception: yuzler = []
        if len(yuzler) == 0:
            return self._son_cls

        x, y, fw, fh = yuzler[0]

        # ── Göz açıklığı (EAR — Eye Aspect Ratio): gw/gh
        # Göz yatay açılırken gw artar, gh azalır → yorgunlukta gh/gw DÜŞER
        # Doğru oran: gw / (gh + ε)  → büyük değer = açık göz = uyanık
        try:   gozler = self._goz_dedek.detectMultiScale(gray[y:y+fh, x:x+fw], 1.1, 5, minSize=(20,20))
        except Exception: gozler = []

        ear_ref = self.bio["goz_acikligi_baz"]  # profilin baz açıklık oranı (0.65-0.85)
        if len(gozler) > 0:
            # EAR  = yükseklik / genişlik  (küçül → göz kapanıyor → yorgun)
            ear = sum(gh / (gw + 0.001) for _, _, gw, gh in gozler) / len(gozler)
        else:
            ear = ear_ref * 0.80  # göz tespit edilemedi → biraz daha kapalı varsay

        # ear < ear_ref  →  göz referanstan daha kapalı  →  yorgun
        ear_sapma = max(0.0, ear_ref - ear)          # ne kadar kapandı?
        # sapma / baz ile oranla, 0-100'e ölçekle
        ear_norm  = min(100.0, (ear_sapma / (ear_ref + 0.001)) * 250)

        # ── Kaş/Alın kasılması (pixel std — yüksek std = kasılmış = stresli)
        kas_roi = gray[y + int(fh * 0.08):y + int(fh * 0.38),
                       x + int(fw * 0.15):x + int(fw * 0.85)]
        kas_baz = self.bio.get("kas_kasılma_baz", 0.10) * 255  # piksel bazı
        if kas_roi.size > 0:
            kas_std  = float(kas_roi.std())
            # Bazın üzerindeki her birim → stres göstergesi
            kas_norm = min(100.0, max(0.0, (kas_std - kas_baz) / (kas_baz + 1.0) * 80 + 20))
        else:
            kas_norm = 20.0

        # ── Bağlamsal yorgunluk (saat, gün tipi, bugün km)
        konteks = _baglamsal_yorgunluk(self.profil)

        # Ağırlıklı CLS (toplam 1.0)
        # ear_norm en güvenilir sinyal → en yüksek ağırlık
        cls = 0.45 * ear_norm + 0.35 * kas_norm + 0.20 * konteks
        return max(0.0, min(100.0, cls))

    def _ciz(self, frame):
        """Kamera görüntüsüne CLS çubuğu ve mod yazısı ekler."""
        h, w    = frame.shape[:2]
        cls     = self._son_cls
        mod     = cls_to_mod(cls)
        bgr     = {"yorgun":(0,68,255),"stresli":(0,184,255),
                   "notr":(255,207,0),"enerjik":(136,255,0)}.get(mod,(200,200,200))
        cv2.rectangle(frame, (0,0), (w,55), (15,15,30), -1)
        cv2.putText(frame, "AffectEV | Kognitif Yuk",
                    (12,22), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0,255,136), 2)
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S"),
                    (w-110,22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100,200,255), 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:   yuzler = self._yuz_dedek.detectMultiScale(gray, 1.1, 5, minSize=(80,80))
        except Exception: yuzler = []
        for (fx,fy,fw,fh) in yuzler:
            k = 18
            for px,py,qx,qy in [(fx,fy,fx+k,fy),(fx,fy,fx,fy+k),(fx+fw,fy,fx+fw-k,fy),
                                  (fx+fw,fy,fx+fw,fy+k),(fx,fy+fh,fx+k,fy+fh),
                                  (fx,fy+fh,fx,fy+fh-k),(fx+fw,fy+fh,fx+fw-k,fy+fh),
                                  (fx+fw,fy+fh,fx+fw,fy+fh-k)]:
                cv2.line(frame,(px,py),(qx,qy),bgr,3)
        py0 = h - 95
        cv2.rectangle(frame, (0,py0), (w,h), (15,15,30), -1)
        cv2.line(frame, (0,py0), (w,py0), bgr, 2)
        bx, by, bw, bh2 = 12, py0+14, w-24, 20
        cv2.rectangle(frame,(bx,by),(bx+bw,by+bh2),(40,40,60),-1)
        dw = int(cls/100*bw)
        if dw: cv2.rectangle(frame,(bx,by),(bx+dw,by+bh2),bgr,-1)
        cv2.rectangle(frame,(bx,by),(bx+bw,by+bh2),(80,80,100),1)
        cv2.putText(frame,f"Kognitif Yuk: {cls:.0f} / 100",
                    (bx+6,by+15), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255,255,255), 1)
        isim = {"yorgun":"YORGUN","stresli":"STRESLI","notr":"NOTR","enerjik":"ENERJIK"}.get(mod,mod)
        cv2.putText(frame, isim, (12,py0+58), cv2.FONT_HERSHEY_SIMPLEX, 0.85, bgr, 2)
        cv2.putText(frame,"Q: Kapat",(w-90,py0+88),cv2.FONT_HERSHEY_SIMPLEX,0.38,(80,80,80),1)
        return frame

    # ── Simülasyon CLS hesabı (CV2 yoksa)
    def sim_cls_hesapla(self) -> float:
        """
        Kamera olmadan CLS simüle eder.
        Kullanıcının baz biyometrik değerleri + bağlamsal faktörler kullanılır.
        Tüm bileşenler 0-100 skalasına normalize edilip ağırlıklı birleştirilir.
        """
        saat = datetime.now().hour

        # ── Bileşen 1: Kişinin dominant duygu eğilimine göre baz CLS (0-100)
        baz_cls = {"yorgun": 70.0, "stresli": 57.0,
                   "notr": 38.0, "enerjik": 20.0}.get(
            self.profil.get("dominant_duygu", "notr"), 38.0)

        # Trafik saatlerinde stres etkisi (kişinin stres_egilimi ölçeğinde)
        if saat in (7, 8, 9, 17, 18, 19):
            baz_cls = min(100.0, baz_cls + self.profil.get("stres_egilimi", 0.4) * 20)

        # ── Bileşen 2: Göz kırpma sapması → 0-100
        # Bazdan çok sapan kırpma (çok hızlı veya çok yavaş) yorgunluk/stres belirtisi
        blink_gercek = self.bio["blink_baz_dk"] + random.gauss(0, self.bio["blink_std"])
        blink_sapma  = abs(blink_gercek - self.bio["blink_baz_dk"])
        # std cinsinden sapma → 2 std üstü = tam anlamıyla anormal
        blink_norm   = min(100.0, (blink_sapma / (self.bio["blink_std"] + 0.01)) * 50)

        # ── Bileşen 3: Göz kapanma simülasyonu → 0-100
        # Ne kadar kapandı? Baz değerden 0 ile 0.25 arası sapma mümkün
        max_sapma   = 0.25
        goz_sapma   = random.uniform(0, max_sapma)
        goz_norm    = min(100.0, (goz_sapma / max_sapma) * 100)

        # ── Bileşen 4: Bağlamsal yorgunluk → zaten 0-100
        konteks = _baglamsal_yorgunluk(self.profil)

        # Ağırlıklı CLS — toplam = 1.0
        # baz_cls kişilik bazı, diğerleri anlık sapma göstergeleri
        cls = (0.40 * baz_cls
             + 0.25 * blink_norm
             + 0.20 * goz_norm
             + 0.15 * konteks)

        # ── Smoothing: sadece tarihçe yeterliyse önceki ölçümle karıştır
        # İlk ölçümlerde smoothing yapmayarak başlangıç değerinin (45.0) etkisini önle
        if len(self._cls_gecmis) >= 3:
            cls = 0.75 * cls + 0.25 * self._cls_gecmis[-1]

        # Küçük gürültü ekle (gerçek sensör varyasyonu benzeri)
        cls = max(0.0, min(100.0, cls + random.gauss(0, 1.8)))
        self._kaydet(cls)
        return round(cls, 1)

    def _kaydet(self, cls: float):
        self._son_cls = cls
        self._cls_gecmis.append(cls)
        if len(self._cls_gecmis) > 30:
            self._cls_gecmis.pop(0)

    def anlik_cls(self) -> float:
        """Her zaman çağrılabilir. Kamera açıksa gerçek, değilse simülasyon döner."""
        if CV2_VAR and self._aktif:
            return self._son_cls
        return self.sim_cls_hesapla()

    def cls_ortalama(self, n: int = 5) -> float:
        """Son n ölçümün ortalamasını döndürür. Daha kararlı tahmin için kullanılır."""
        if not self._cls_gecmis:
            return self._son_cls
        son = self._cls_gecmis[-n:]
        return round(sum(son) / len(son), 1)

    def cls_trend(self) -> str:
        if len(self._cls_gecmis) < 5: return "stabil"
        egim = (self._cls_gecmis[-1] - self._cls_gecmis[-5]) / 4
        if egim >  3: return "artiyor"
        if egim < -3: return "azaliyor"
        return "stabil"


# ─────────────────────────────────────────────
#  SÜRÜCÜ PROFİL YÖNETİCİSİ
# ─────────────────────────────────────────────
class SurucuProfilYonetici:
    def __init__(self):
        self.suruculer: List[Dict] = []
        self._yukle()
        if not self.suruculer:
            self.suruculer = sentetik_surucucu_uret()
            self._kaydet()

    def _yukle(self):
        if os.path.exists(PROFIL_DOSYASI):
            try:
                with open(PROFIL_DOSYASI, "r", encoding="utf-8") as f:
                    self.suruculer = json.load(f)
            except Exception:
                self.suruculer = []

    def _kaydet(self):
        try:
            with open(PROFIL_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(self.suruculer, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def profil_al(self, uid: str) -> Optional[Dict]:
        return next((p for p in self.suruculer if p["uid"] == uid), None)

    def profil_guncelle(self, uid: str, cls: float, km: float, tuk_carpan: float):
        p = self.profil_al(uid)
        if not p: return
        p["son_cls"] = round(cls, 1)
        p["son_mod"] = cls_to_mod(cls)
        p["kullanim_sayisi"] = p.get("kullanim_sayisi", 0) + 1
        p["taninma_dogrulugu"] = round(min(0.99, 0.60 + p["kullanim_sayisi"]*0.016), 3)
        bugun   = datetime.now().strftime("%Y-%m-%d")
        sefer   = {"saat": datetime.now().hour, "km": round(km,1),
                   "cls_ort": round(cls,1), "tuk_carpan": round(tuk_carpan,3),
                   "mod": cls_to_mod(cls)}
        gecmis  = p.get("suruc_gecmis", [])
        if gecmis and gecmis[-1]["tarih"] == bugun:
            gecmis[-1]["seferler"].append(sefer)
        else:
            gecmis.append({"tarih": bugun, "seferler": [sefer]})
        p["suruc_gecmis"] = gecmis[-60:]
        self._kaydet()

    def istatistik_ozet(self, uid: str) -> Dict:
        p = self.profil_al(uid)
        if not p: return {}
        seferler = [s for g in p.get("suruc_gecmis",[]) for s in g.get("seferler",[])]
        if not seferler: return {}
        cls_l = [s["cls_ort"]    for s in seferler]
        tuk_l = [s["tuk_carpan"] for s in seferler]
        km_l  = [s["km"]         for s in seferler]
        mod_s: Dict[str,int] = {}
        for s in seferler: mod_s[s["mod"]] = mod_s.get(s["mod"],0) + 1
        return {
            "toplam_sefer":   len(seferler),
            "toplam_km":      round(sum(km_l), 1),
            "cls_ort":        round(sum(cls_l)/len(cls_l), 1),
            "cls_max":        round(max(cls_l), 1),
            "cls_min":        round(min(cls_l), 1),
            "tuk_carpan_ort": round(sum(tuk_l)/len(tuk_l), 3),
            "mod_dagilim":    mod_s,
            "dominant_mod":   max(mod_s, key=mod_s.get),
        }


# ─────────────────────────────────────────────
#  DUYGU ROTA OPTİMİZATÖRÜ
# ─────────────────────────────────────────────
class DuyguRotaOptimizatoru:
    def __init__(self, profil_yonetici: SurucuProfilYonetici):
        self.pm = profil_yonetici

    def optimize_parametreler(self, uid: str, cls: float, arac_adi: str) -> Dict:
        mod    = cls_to_mod(cls)
        params = MOD_PARAMETRELERI[mod].copy()
        profil = self.pm.profil_al(uid)
        oneriler = list(params.get("oneriler", []))

        if profil:
            params["sarj_esik"] = max(params["sarj_esik"],
                                      profil.get("sarj_konfor", 20) - 10)
            istat = self.pm.istatistik_ozet(uid)
            cls_ort = istat.get("cls_ort", 40)
            if cls > cls_ort + 20:
                oneriler.append(
                    f"📈 CLS ortalamanızın ({cls_ort:.0f}) çok üzerinde — mola öneririz")

        tuk_carpan = params["tuk_carpan"]
        if arac_adi in ("Renault Zoe", "BMW iX3"):
            tuk_carpan *= 1.05

        return {
            "rota_krit":  params["rota_krit"],
            "sarj_esik":  params["sarj_esik"],
            "sarj_hedef": params["sarj_hedef"],
            "hiz_carpan": params["hiz_carpan"],
            "tuk_carpan": round(tuk_carpan, 3),
            "trafik_kac": params["trafik_kac"],
            "mod":        mod,
            "cls":        round(cls, 1),
            "ikon":       params["ikon"],
            "renk":       params["renk"],
            "aciklama":   params["aciklama"],
            "oneriler":   oneriler,
        }


# ─────────────────────────────────────────────
#  ÇOK AMAÇLI OPTİMİZASYON MODELİ
# ─────────────────────────────────────────────
class CokAmacliRotaOptimizatoru:
    """
    CLS tabanlı çok amaçlı ağırlıklı rota optimizasyonu.

    ─────────────── Matematiksel Model ───────────────────────────
    Objective Function  (minimize et):

        F(r) = w_e(CLS) · Ê(r)  +  w_t(CLS) · T̂(r)  +  w_c(CLS) · Ĉ(r)

    Normalize Değişkenler  [∈ 0, 1]:
        Ê(r) = enerji_kwh(r) / E_REF
        T̂(r) = sure_dk(r)   / T_REF
        Ĉ(r) = mean[ Ĉ_kenar(e)  for e in r ]

    Ağırlık Fonksiyonları  (CLS → α → softmax-normalize → w):
        α_e(n) = 0.60 · exp(−8 · (n − 0.40)²)   # Gauss çan, nötrde zirve
        α_t(n) = 0.70 · (1 − n)^1.8              # güç fnk, enerjikken max
        α_c(n) = 0.75 · n^1.6                     # güç fnk, yorgunken max
        w_i    = α_i / Σα_j                        # Σ w_i = 1,  n = CLS/100

    Kenar Konfor Maliyeti  [∈ 0, 1]:
        Ĉ_e = yol_baz + egim_etki + gecis_etki
        yol_baz   : otoyol=0.15, ulke=0.30, bulvar=0.52, sehir=0.78
        egim_etki : min(0.25,  |Δrakım| / 600)
        gecis_etki: 0.10  eğer yol tipi değişiyorsa
    ──────────────────────────────────────────────────────────────

    CLS Bölgesi  → Ağırlık Örüntüsü       → Rota Tercihi
    ───────────  ──────────────────────── ─────────────────────
    0–30  Enerjik  w_t >> w_e >> w_c       En hızlı güzergah
    30–50 Nötr     w_e >> w_t ≈ w_c        Enerji verimli
    50–70 Stresli  w_c ↑, w_t orta         Konforlu, az kavşak
    70–100 Yorgun  w_c >> w_e >> w_t       Sakin, kısa mesafeli
    """

    E_REF: float = 25.0   # kWh — Ankara içi referans maksimum enerji
    T_REF: float = 150.0  # dk  — Ankara içi referans maksimum süre

    # ── Ağırlık Hesabı ──────────────────────────────────────────
    @staticmethod
    def agirlik_hesapla(cls: float) -> Tuple[float, float, float]:
        """
        CLS ∈ [0, 100]  →  (w_enerji, w_sure, w_konfor)

        Tüm ağırlıklar ≥ 0  ve  Σ = 1  (softmax benzeri normalize).

        Türetme:
            cls_n  = cls / 100  ∈ [0, 1]
            α_e    = 0.60 · exp(−8 · (cls_n − 0.40)²)   Gauss, μ=0.40, σ≈0.25
            α_t    = 0.70 · (1 − cls_n)^1.8              konveks azalan
            α_c    = 0.75 · cls_n^1.6                     konveks artan
            w_i    = α_i / (α_e + α_t + α_c)
        """
        import math
        cls_n   = max(0.0, min(1.0, cls / 100.0))
        alpha_e = 0.60 * math.exp(-8.0 * (cls_n - 0.40) ** 2)
        alpha_t = 0.70 * (1.0 - cls_n) ** 1.8
        alpha_c = 0.75 * cls_n ** 1.6
        toplam  = alpha_e + alpha_t + alpha_c + 1e-9
        return (
            round(alpha_e / toplam, 4),
            round(alpha_t / toplam, 4),
            round(alpha_c / toplam, 4),
        )

    # ── Kenar Konfor Maliyeti ────────────────────────────────────
    @staticmethod
    def kenar_konfor_maliyeti(yol_tipi: str,
                               rakım_fark_m: float,
                               onceki_yol_tipi: Optional[str] = None) -> float:
        """
        Tek bir kenarın sürücü konfor maliyeti ∈ [0, 1].

        Bileşen         Etki
        ──────────────  ──────────────────────────────────────────
        yol_baz         yol tipine özgü stres/kavşak yoğunluğu
        egim_etki       keskin rakım farkı → fiziksel yorgunluk (maks 0.25)
        gecis_etki      yol tipi değişimi → bilişsel geçiş maliyeti (0.10)
        """
        KONFOR   = {"otoyol": 0.15, "ulke": 0.30, "bulvar": 0.52, "sehir": 0.78}
        yol_baz  = KONFOR.get(yol_tipi, 0.60)
        egim     = min(0.25, abs(rakım_fark_m) / 600.0)
        gecis    = 0.10 if (onceki_yol_tipi and onceki_yol_tipi != yol_tipi) else 0.0
        return round(min(1.0, yol_baz + egim + gecis), 4)

    # ── Rota Konfor Skoru ────────────────────────────────────────
    @classmethod
    def rota_konfor_skoru(cls_klas,
                           yol: List[str],
                           ankara_dugumler: Dict,
                           yollar: List) -> float:
        """
        Rota boyunca tüm kenar konfor maliyetlerinin ortalaması ∈ [0, 1].
        Düşük skor → sürücü için daha konforlu güzergah.
        """
        seg_tip: Dict = {}
        for a, b, _, yol_tipi in yollar:
            seg_tip[(a, b)] = yol_tipi
            seg_tip[(b, a)] = yol_tipi

        maliyetler: List[float] = []
        onceki_tip: Optional[str] = None
        for i in range(len(yol) - 1):
            a, b = yol[i], yol[i + 1]
            if a not in ankara_dugumler or b not in ankara_dugumler:
                continue
            yol_tipi = seg_tip.get((a, b), "sehir")
            ra       = ankara_dugumler[a][2]
            rb       = ankara_dugumler[b][2]
            maliyet  = cls_klas.kenar_konfor_maliyeti(yol_tipi, rb - ra, onceki_tip)
            maliyetler.append(maliyet)
            onceki_tip = yol_tipi

        return round(sum(maliyetler) / len(maliyetler), 4) if maliyetler else 0.50

    # ── Objective Function ───────────────────────────────────────
    @classmethod
    def f_objective(cls_klas,
                    enerji_kwh:  float,
                    sure_dk:     float,
                    konfor_skor: float,
                    w_e: float,
                    w_t: float,
                    w_c: float) -> float:
        """
        Çok amaçlı objective function:

            F(r) = w_e · Ê(r)  +  w_t · T̂(r)  +  w_c · Ĉ(r)   ∈ [0, 1]

            F → 0 : ideal rota  (az enerji + hızlı + konforlu)
            F → 1 : kötü rota

        Normalizasyon:
            Ê = min(enerji_kwh / E_REF, 1.0)
            T̂ = min(sure_dk   / T_REF, 1.0)
            Ĉ = konfor_skor   (zaten [0, 1])
        """
        e_norm = min(1.0, enerji_kwh / (cls_klas.E_REF + 1e-9))
        t_norm = min(1.0, sure_dk    / (cls_klas.T_REF + 1e-9))
        return round(w_e * e_norm + w_t * t_norm + w_c * konfor_skor, 4)

    # ── En İyi Rota Seçimi ───────────────────────────────────────
    @classmethod
    def en_iyi_rota_sec(cls_klas,
                         rotalar:         Dict[str, List[str]],
                         metrikleri:      Dict[str, Dict],
                         konfor_skorlari: Dict[str, float],
                         cls_skor:        float) -> Tuple[str, float, Dict]:
        """
        Aday rotalar arasından F(r) değeri en küçük olanı seçer.

        Parametre           Açıklama
        ─────────────────── ──────────────────────────────────────────────
        rotalar             {"mesafe": [...], "sure": [...], "mo": [...]}
        metrikleri          {krit: {"enerji_kwh": x, "sure_dk": y}, ...}
        konfor_skorlari     {krit: float ∈ [0,1], ...}
        cls_skor            Anlık CLS değeri ∈ [0, 100]

        Dönüş
        ─────
        (en_iyi_krit,  f_degeri,  detay_dict)
        """
        w_e, w_t, w_c = cls_klas.agirlik_hesapla(cls_skor)
        f_skorlar: Dict[str, float] = {}

        for krit, met in metrikleri.items():
            if not rotalar.get(krit):
                continue
            f = cls_klas.f_objective(
                met.get("enerji_kwh", 0.0),
                met.get("sure_dk",    0.0),
                konfor_skorlari.get(krit, 0.5),
                w_e, w_t, w_c,
            )
            f_skorlar[krit] = f

        if not f_skorlar:
            return "enerji", 0.5, {}

        en_iyi = min(f_skorlar, key=f_skorlar.get)
        return en_iyi, f_skorlar[en_iyi], {
            "agirliklar": {
                "w_enerji": w_e,
                "w_sure":   w_t,
                "w_konfor": w_c,
            },
            "f_skorlar":      f_skorlar,
            "konfor_skorlar": {k: round(v, 4) for k, v in konfor_skorlari.items()},
            "metrikleri":     metrikleri,
            "cls":  round(cls_skor, 1),
            "mod":  cls_to_mod(cls_skor),
        }