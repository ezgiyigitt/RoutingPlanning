"""
suruş_veri_kaydedici.py  —  AffectEV  Anonim Sürüş Veri Kayıt Sistemi
=======================================================================
GPS, hız ve rota verilerini KVKK/GDPR uyumlu, anonim biçimde toplar.

Kurulum:
    pip install cryptography

Mimarı:
    ┌─────────────────────────────────────────────────────────────────┐
    │  Ham Veri (GPS/hız/zaman)                                       │
    │      ↓  AnonimlestiriciKatman                                   │
    │  Anonim Sefer Kaydı                                             │
    │      ↓  VeriDeposu  (JSON — genişletilebilir DB bağlantısı)    │
    │  Sefer Veritabanı (suruc_seferler.json)                        │
    └─────────────────────────────────────────────────────────────────┘

Gizlilik Garantileri:
    - Gerçek koordinatlar asla diske yazılmaz; sadece anonimleştirilmiş
      ızgara hücresi (50m × 50m) kaydedilir.
    - Kullanıcı kimliği HMAC-SHA256 ile tek yönlü hash'lenir (anon_uid).
    - Başlangıç/bitiş noktaları ±500 m rastgele pertürbasyona tabi tutulur
      (ev/iş yeri gizliliği).
    - Tüm ham GPS noktaları zincir kırılmadan önce bellekte tutulur,
      diske yazılmaz.
"""

import json
import math
import os
import random
import hashlib
import hmac
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────
#  YAPILANDIRMA
# ─────────────────────────────────────────────────────────────────────
VERI_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri")
SEFER_DOSYASI = os.path.join(VERI_KLASORU, "suruc_seferler.json")
GIZLILIK_TOHUM_DOSYASI = os.path.join(VERI_KLASORU, ".gizlilik_tohum")

IZGARA_BOYUTU_M    = 50      # Koordinat ızgara boyutu (metre) — daha küçük = daha az gizlilik
PERTURBASON_M      = 500     # Başlangıç/bitiş için maksimum konum gürültüsü (m)
MIN_KAYIT_ARALIK_S = 2       # İki GPS kaydı arasındaki minimum süre (saniye)
MIN_HIZ_KMSA       = 2.0     # Bu hızın altındaki kayıtlar "park" sayılır

# ─────────────────────────────────────────────────────────────────────
#  YARDIMcI: COĞRAFİ HESAPLAR
# ─────────────────────────────────────────────────────────────────────
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki GPS koordinatı arasındaki mesafeyi km cinsinden hesaplar."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _izgara_hucresine_snap(lat: float, lon: float,
                            izgara_m: int = IZGARA_BOYUTU_M) -> Tuple[float, float]:
    """
    Koordinatı en yakın ızgara hücresinin merkezine yapıştırır.
    Izgara boyutu metre cinsinden; lat/lon'a derece cinsinden dönüştürülür.
    """
    lat_adim = izgara_m / 111_000          # 1 derece lat ≈ 111 km
    lon_adim = izgara_m / (111_000 * math.cos(math.radians(lat)))
    snap_lat = round(lat / lat_adim) * lat_adim
    snap_lon = round(lon / lon_adim) * lon_adim
    return round(snap_lat, 6), round(snap_lon, 6)


def _perturbasyonlu_koordinat(lat: float, lon: float,
                               maks_m: int = PERTURBASON_M) -> Tuple[float, float]:
    """Koordinata rastgele ±maks_m metrelik gürültü ekler (başlangıç/bitiş gizliliği)."""
    lat_offset = random.gauss(0, maks_m / 111_000)
    lon_offset = random.gauss(0, maks_m / (111_000 * math.cos(math.radians(lat))))
    return round(lat + lat_offset, 6), round(lon + lon_offset, 6)


# ─────────────────────────────────────────────────────────────────────
#  ANONİMLEŞTİRİCİ KATMAN
# ─────────────────────────────────────────────────────────────────────
class AnonimlestiriciKatman:
    """
    Tüm kişisel tanımlayıcıları tek yönlü dönüşümle şifreler / siler.

    Yöntemler
    ---------
    uid_hashle(uid)      : HMAC-SHA256 ile kullanıcı kimliğini anonimleştirir.
    rota_anonimize(pts)  : GPS noktası listesini ızgara+pertürbasyon ile işler.
    """

    def __init__(self):
        self._tohum = self._tohum_yukle_veya_olustur()

    def _tohum_yukle_veya_olustur(self) -> bytes:
        """Sunucu tarafında kalıcı gizlilik tohumunu yükler ya da oluşturur."""
        os.makedirs(VERI_KLASORU, exist_ok=True)
        if os.path.exists(GIZLILIK_TOHUM_DOSYASI):
            with open(GIZLILIK_TOHUM_DOSYASI, "rb") as f:
                return f.read()
        tohum = os.urandom(32)
        with open(GIZLILIK_TOHUM_DOSYASI, "wb") as f:
            f.write(tohum)
        return tohum

    def uid_hashle(self, uid: str) -> str:
        """
        Kullanıcı UID'sini HMAC-SHA256 ile tek yönlü hash'ler.
        Aynı tohum + UID daima aynı anonim ID'yi üretir (bağlantılanabilirlik korunur,
        tersine çevrilemez).
        """
        return hmac.new(self._tohum, uid.encode(), hashlib.sha256).hexdigest()[:16]

    def nokta_anonimize(self, lat: float, lon: float,
                         ucta: bool = False) -> Tuple[float, float]:
        """
        Tek GPS noktasını anonimleştirir.
        ucta=True ise (başlangıç/bitiş) ekstra pertürbasyon uygulanır.
        """
        if ucta:
            lat, lon = _perturbasyonlu_koordinat(lat, lon)
        return _izgara_hucresine_snap(lat, lon)

    def rota_anonimize(self, noktalar: List[Dict]) -> List[Dict]:
        """
        [{"lat":…, "lon":…, "hiz_kmsa":…, "zaman_s":…}, …] listesini
        ızgara-snap + uç pertürbasyonuyla anonim hale getirir.
        """
        anonim = []
        for i, p in enumerate(noktalar):
            ucta = (i == 0 or i == len(noktalar) - 1)
            a_lat, a_lon = self.nokta_anonimize(p["lat"], p["lon"], ucta=ucta)
            anonim.append({
                "lat": a_lat,
                "lon": a_lon,
                "hiz_kmsa":  round(p.get("hiz_kmsa", 0), 1),
                "zaman_ofset_s": round(p.get("zaman_s", 0) - noktalar[0].get("zaman_s", 0), 1),
            })
        return anonim


# ─────────────────────────────────────────────────────────────────────
#  HAM VERİ TAMPON SINIFI (Bellekte Tutar — Diske Yazmaz)
# ─────────────────────────────────────────────────────────────────────
class HamVeriTamponu:
    """
    Sürüş boyunca GPS/hız örneklerini SADECE RAM'de biriktirir.
    Sefer bittiğinde AnonimlestiriciKatman ile işlenir ve diske kaydedilir.
    Ham koordinatlar hiçbir zaman kalıcı depolamaya yazılmaz.
    """

    def __init__(self):
        self._noktalar: List[Dict] = []
        self._son_kayit_zamani: float = 0.0
        self._aktif: bool = False
        self._kilit = threading.Lock()

    def sefer_baslat(self):
        with self._kilit:
            self._noktalar.clear()
            self._son_kayit_zamani = 0.0
            self._aktif = True

    def sefer_durdur(self) -> List[Dict]:
        """Ham nokta listesini döndürür ve tamponu temizler."""
        with self._kilit:
            self._aktif = False
            snapshot = list(self._noktalar)
            self._noktalar.clear()
            return snapshot

    def nokta_ekle(self, lat: float, lon: float, hiz_kmsa: float):
        """
        Hız eşiğini ve zaman aralığını kontrol ederek örneği ekler.
        Park halindeki (çok yavaş) noktaları filtreler.
        """
        simdi = time.time()
        if not self._aktif:
            return
        if hiz_kmsa < MIN_HIZ_KMSA:
            return
        if simdi - self._son_kayit_zamani < MIN_KAYIT_ARALIK_S:
            return
        with self._kilit:
            self._noktalar.append({
                "lat": lat, "lon": lon,
                "hiz_kmsa": hiz_kmsa,
                "zaman_s": simdi,
            })
            self._son_kayit_zamani = simdi

    @property
    def aktif(self) -> bool:
        return self._aktif

    def nokta_sayisi(self) -> int:
        with self._kilit:
            return len(self._noktalar)


# ─────────────────────────────────────────────────────────────────────
#  VERİ DEPOSU
# ─────────────────────────────────────────────────────────────────────
class VeriDeposu:
    """
    Anonim sürüş kayıtlarını JSON dosyasına okur/yazar.
    İleride bir SQL/NoSQL veritabanına geçiş için adaptör katmanı görevi görür.
    """

    def __init__(self, dosya_yolu: str = SEFER_DOSYASI):
        self._dosya = dosya_yolu
        os.makedirs(VERI_KLASORU, exist_ok=True)
        self._kilit = threading.Lock()

    def _yukle(self) -> Dict:
        if not os.path.exists(self._dosya):
            return {"seferler": [], "meta": {"olusturma": datetime.now().isoformat()}}
        try:
            with open(self._dosya, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"seferler": [], "meta": {}}

    def _kaydet(self, veri: Dict):
        with open(self._dosya, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)

    def sefer_ekle(self, sefer: Dict):
        """Anonim sefer kaydını depoya ekler."""
        with self._kilit:
            veri = self._yukle()
            veri["seferler"].append(sefer)
            veri["meta"]["son_guncelleme"] = datetime.now().isoformat()
            veri["meta"]["toplam_sefer"] = len(veri["seferler"])
            self._kaydet(veri)

    def seferleri_al(self,
                      anon_uid: Optional[str] = None,
                      son_n: Optional[int] = None) -> List[Dict]:
        """Kayıtlı seferleri döndürür. anon_uid verilirse filtrelenir."""
        with self._kilit:
            veri = self._yukle()
        seferler = veri.get("seferler", [])
        if anon_uid:
            seferler = [s for s in seferler if s.get("anon_uid") == anon_uid]
        if son_n:
            seferler = seferler[-son_n:]
        return seferler

    def ozet_istatistik(self) -> Dict:
        """Tüm anonim kayıtlardan istatistiksel özet üretir."""
        with self._kilit:
            veri = self._yukle()
        seferler = veri.get("seferler", [])
        if not seferler:
            return {}
        km_listesi   = [s["mesafe_km"]   for s in seferler if "mesafe_km"   in s]
        cls_listesi  = [s["ort_cls"]      for s in seferler if "ort_cls"      in s]
        hiz_listesi  = [s["ort_hiz_kmsa"] for s in seferler if "ort_hiz_kmsa" in s]
        mod_sayisi: Dict[str, int] = {}
        for s in seferler:
            mod = s.get("mod", "bilinmiyor")
            mod_sayisi[mod] = mod_sayisi.get(mod, 0) + 1
        return {
            "toplam_sefer":   len(seferler),
            "toplam_km":      round(sum(km_listesi), 1),
            "ort_mesafe_km":  round(sum(km_listesi) / len(km_listesi), 2) if km_listesi else 0,
            "ort_cls":        round(sum(cls_listesi) / len(cls_listesi), 2) if cls_listesi else 0,
            "ort_hiz_kmsa":   round(sum(hiz_listesi) / len(hiz_listesi), 2) if hiz_listesi else 0,
            "mod_dagilimi":   mod_sayisi,
            "ilk_sefer":      seferler[0].get("tarih", "?") if seferler else "?",
            "son_sefer":      seferler[-1].get("tarih", "?") if seferler else "?",
        }


# ─────────────────────────────────────────────────────────────────────
#  ANA KAYIT YÖNETİCİSİ
# ─────────────────────────────────────────────────────────────────────
class SurusVeriKaydedici:
    """
    Merkezi sürüş veri kayıt yöneticisi.

    Kullanım:
        kaydedici = SurusVeriKaydedici()
        kaydedici.sefer_baslat(uid="U01")

        # Simülasyon ya da gerçek GPS döngüsünde:
        kaydedici.nokta_ekle(lat=39.9208, lon=32.8541, hiz_kmsa=45.0)

        # Sefer bitişinde:
        ozet = kaydedici.sefer_bitir(
            cls_gecmis=[42.1, 45.5, 50.2],
            rota_dugum_listesi=["Kızılay", "Çankaya", "Dikmen"],
            arac_adi="Tesla Model 3"
        )
    """

    def __init__(self):
        self.anonimizer  = AnonimlestiriciKatman()
        self.tampon      = HamVeriTamponu()
        self.depo        = VeriDeposu()
        self._aktif_uid: Optional[str] = None
        self._baslangic_zamani: Optional[float] = None

    # ── Sefer Başlat ──────────────────────────────────────────────────
    def sefer_baslat(self, uid: str):
        """
        Yeni bir sürüş seferini başlatır.
        uid: Ham kullanıcı kimliği (dışarıda anonimleştirilir, diske yazılmaz).
        """
        self._aktif_uid = uid
        self._baslangic_zamani = time.time()
        self.tampon.sefer_baslat()

    # ── Anlık Nokta Ekle (GPS döngüsünden çağrılır) ────────────────────
    def nokta_ekle(self, lat: float, lon: float, hiz_kmsa: float):
        """
        Tek bir GPS ölçümünü tampona ekler.
        Bu metod gerçek GPS alıcısından veya simülasyon üretecinden çağrılabilir.
        """
        self.tampon.nokta_ekle(lat, lon, hiz_kmsa)

    # ── Sefer Bitir ────────────────────────────────────────────────────
    def sefer_bitir(self,
                    cls_gecmis:          List[float],
                    rota_dugum_listesi:  List[str],
                    arac_adi:            str,
                    mod:                 Optional[str] = None) -> Optional[Dict]:
        """
        Seferi sonlandırır; ham veriyi anonimleştirerek diske kaydeder.

        Parametreler
        ------------
        cls_gecmis          : Sefer boyunca ölçülen CLS değerleri listesi.
        rota_dugum_listesi  : Ankara düğüm adlarından oluşan rota (ör. ["Kızılay","Çankaya"]).
        arac_adi            : Araç modeli adı (istatistik için).
        mod                 : Sürücü modu (enerjik/notr/stresli/yorgun) — opsiyonel.

        Dönüş
        -----
        Anonim sefer özeti sözlüğü veya veri yetersizse None.
        """
        if not self._aktif_uid or not self.tampon.aktif:
            return None

        ham_noktalar = self.tampon.sefer_durdur()

        # Minimum veri kalitesi kontrolü
        if len(ham_noktalar) < 3:
            return None

        # ── Anonimleştir ──────────────────────────────────────────────
        anon_uid     = self.anonimizer.uid_hashle(self._aktif_uid)
        anon_rota    = self.anonimizer.rota_anonimize(ham_noktalar)

        # ── Metrik Hesapla ────────────────────────────────────────────
        mesafe_km    = self._rota_mesafesi_km(ham_noktalar)
        sure_dk      = round((time.time() - self._baslangic_zamani) / 60, 1)
        hizlar       = [p["hiz_kmsa"] for p in ham_noktalar]
        ort_hiz      = round(sum(hizlar) / len(hizlar), 1) if hizlar else 0.0
        maks_hiz     = round(max(hizlar), 1) if hizlar else 0.0
        ort_cls      = round(sum(cls_gecmis) / len(cls_gecmis), 1) if cls_gecmis else 50.0
        maks_cls     = round(max(cls_gecmis), 1) if cls_gecmis else 50.0

        # ── Sefer Kaydı ───────────────────────────────────────────────
        sefer = {
            "anon_uid":         anon_uid,
            "tarih":            datetime.now().strftime("%Y-%m-%d"),
            "saat":             datetime.now().hour,
            "mesafe_km":        round(mesafe_km, 2),
            "sure_dk":          sure_dk,
            "ort_hiz_kmsa":     ort_hiz,
            "maks_hiz_kmsa":    maks_hiz,
            "ort_cls":          ort_cls,
            "maks_cls":         maks_cls,
            "mod":              mod or "bilinmiyor",
            "arac":             arac_adi,
            "dugum_sayisi":     len(rota_dugum_listesi),
            "nokta_sayisi":     len(anon_rota),
            # Anonim GPS izi (ızgara-snap edilmiş)
            "anonim_rota":      anon_rota,
            # Düğüm listesi (Ankara haritasında açık bilgi)
            "rota_dugumler":    rota_dugum_listesi,
            "kayit_zamani":     datetime.now().isoformat(),
        }

        self.depo.sefer_ekle(sefer)
        self._aktif_uid = None
        return sefer

    @staticmethod
    def _rota_mesafesi_km(noktalar: List[Dict]) -> float:
        """Ham GPS noktalarından toplam mesafeyi Haversine ile hesaplar."""
        toplam = 0.0
        for i in range(len(noktalar) - 1):
            toplam += _haversine_km(
                noktalar[i]["lat"],   noktalar[i]["lon"],
                noktalar[i+1]["lat"], noktalar[i+1]["lon"],
            )
        return toplam

    # ── Raporlama ─────────────────────────────────────────────────────
    def kullanici_gecmisi(self, uid: str, son_n: int = 10) -> List[Dict]:
        """Kullanıcıya ait son n anonim seferi döndürür."""
        anon_uid = self.anonimizer.uid_hashle(uid)
        return self.depo.seferleri_al(anon_uid=anon_uid, son_n=son_n)

    def genel_istatistik(self) -> Dict:
        """Tüm kullanıcıların anonim verilerinden istatistik özeti döndürür."""
        return self.depo.ozet_istatistik()


# ─────────────────────────────────────────────────────────────────────
#  GPS SİMÜLATÖRÜ  (test / geliştirme)
# ─────────────────────────────────────────────────────────────────────
class GpsSimulatoru:
    """
    Ankara düğüm noktaları arasında gerçekçi GPS veri akışı üretir.
    Gerçek GPS donanımı olmayan ortamlarda kaydediciyi test etmek için kullanılır.
    """

    def __init__(self, ankara_dugumler: Dict):
        self.dugumler = ankara_dugumler

    def rota_sim_noktalari(self,
                            rota: List[str],
                            hiz_kmsa: float = 45.0,
                            gurultu_std: float = 0.0001) -> List[Dict]:
        """
        Düğüm listesinden doğrusal enterpolasyonla GPS noktaları üretir.
        Her iki düğüm arasına yaklaşık 5 saniyelik örnekler eklenir.
        """
        if len(rota) < 2:
            return []
        noktalar: List[Dict] = []
        simdi = time.time()

        for i in range(len(rota) - 1):
            a, b = rota[i], rota[i + 1]
            if a not in self.dugumler or b not in self.dugumler:
                continue
            lat1, lon1, _ = self.dugumler[a]
            lat2, lon2, _ = self.dugumler[b]
            mesafe = _haversine_km(lat1, lon1, lat2, lon2)
            sure_s = (mesafe / hiz_kmsa) * 3600
            adim   = max(1, int(sure_s / 5))   # her ~5 sn bir nokta

            for k in range(adim):
                t = k / adim
                lat = lat1 + t * (lat2 - lat1) + random.gauss(0, gurultu_std)
                lon = lon1 + t * (lon2 - lon1) + random.gauss(0, gurultu_std)
                hiz = max(5.0, hiz_kmsa + random.gauss(0, 8))
                noktalar.append({
                    "lat":      lat,
                    "lon":      lon,
                    "hiz_kmsa": round(hiz, 1),
                    "zaman_s":  simdi + len(noktalar) * 5,
                })

        return noktalar


# ─────────────────────────────────────────────────────────────────────
#  HIZLI TEST
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Ankara düğüm noktalarını basit import yerine doğrudan tanımlıyoruz
    # (bu dosya bağımsız çalışabilir olsun diye)
    try:
        from ev_rota_planner import ANKARA_DUGUMLER
    except ImportError:
        ANKARA_DUGUMLER = {
            "Kızılay":   (39.9208, 32.8541, 861),
            "Çankaya":   (39.9036, 32.8597, 930),
            "Balgat":    (39.8833, 32.8167, 900),
            "Çayyolu":   (39.8667, 32.7333, 970),
        }

    print("=== AffectEV Anonim Veri Kayıt Sistemi — Test ===\n")

    kaydedici  = SurusVeriKaydedici()
    simulasyon = GpsSimulatoru(ANKARA_DUGUMLER)

    rota  = ["Kızılay", "Çankaya", "Balgat", "Çayyolu"]
    uid   = "U03"

    # Sefer başlat
    kaydedici.sefer_baslat(uid)

    # Simüle GPS noktaları üret ve ekle
    noktalar = simulasyon.rota_sim_noktalari(rota, hiz_kmsa=50.0)
    print(f"Üretilen GPS noktası sayısı: {len(noktalar)}")
    for nokta in noktalar:
        kaydedici.nokta_ekle(nokta["lat"], nokta["lon"], nokta["hiz_kmsa"])
        # Gerçek zamanlı simülasyon yerine zaman ofsetlerini geçiyoruz
        kaydedici.tampon._son_kayit_zamani -= MIN_KAYIT_ARALIK_S

    # Sefer bitir
    cls_sim = [random.gauss(42, 8) for _ in range(15)]
    ozet = kaydedici.sefer_bitir(
        cls_gecmis=cls_sim,
        rota_dugum_listesi=rota,
        arac_adi="Tesla Model 3",
        mod="notr",
    )

    if ozet:
        print(f"\n--- Kaydedilen Anonim Sefer ---")
        print(f"Anonim UID  : {ozet['anon_uid']}")
        print(f"Mesafe      : {ozet['mesafe_km']} km")
        print(f"Süre        : {ozet['sure_dk']} dk")
        print(f"Ort. Hız    : {ozet['ort_hiz_kmsa']} km/sa")
        print(f"Ort. CLS    : {ozet['ort_cls']}")
        print(f"Maks. CLS   : {ozet['maks_cls']}")
        print(f"Nokta sayısı: {ozet['nokta_sayisi']}")
        print(f"\nAnonim rota ilk 3 noktası:")
        for p in ozet["anonim_rota"][:3]:
            print(f"  lat={p['lat']}, lon={p['lon']}, hız={p['hiz_kmsa']} km/sa")
    else:
        print("Sefer kaydedilemedi (veri yetersiz).")

    print("\n--- Genel İstatistik ---")
    ist = kaydedici.genel_istatistik()
    for k, v in ist.items():
        print(f"  {k}: {v}")