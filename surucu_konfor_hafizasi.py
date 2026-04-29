"""
surucu_konfor_hafizasi.py  —  AffectEV  (Deneyimsel Öğrenme Sistemi)
======================================================================
Sürücülerin verdikleri geri bildirimlerden (1–5 yıldız) yol kenarlarının
konfor puanlarını öğrenen ve saklayan Q-Learning benzeri hafıza modülü.

Çalışma Prensibi:
    1. Kullanıcı bir rotayı tamamladıktan sonra "Bu rota nasıldı?" (1–5) sorusu sorulur.
    2. Rota boyunca geçilen her (u → v) kenarı bu puanla güncellenir.
    3. Gelecekteki NSGA-II çalıştırmalarında kenar konfor maliyetleri
       bu birikmiş deneyimden etkilenir.

Hafıza Formatı (JSON):
    {
      "Kızılay→Ulus": {
          "toplam_puan": 18.0,
          "sayim": 5,
          "ortalama": 3.6,
          "son_guncelleme": "2026-04-15T15:30:00"
      },
      ...
    }
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Tuple


HAFIZA_DOSYASI = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "surucu_konfor_hafizasi.json"
)

# Puan ölçeği: 1 (çok kötü) → 5 (mükemmel)
PUAN_MIN = 1
PUAN_MAX = 5


class SurucuKonforHafizasi:
    """
    Kenar tabanlı konfor deneyimi hafızası.

    Kullanım:
        hafiza = SurucuKonforHafizasi()
        hafiza.guncelle(yol_listesi, puan=4)
        maliyet = hafiza.kenar_konfor_al("Kızılay", "Ulus")
    """

    def __init__(self, dosya_yolu: str = HAFIZA_DOSYASI):
        self.dosya_yolu = dosya_yolu
        self._veri: Dict[str, Dict] = self._yukle()

    # ──────────────────────────────────────────────────────────
    #  Yükleme / Kaydetme
    # ──────────────────────────────────────────────────────────
    def _yukle(self) -> Dict:
        if os.path.exists(self.dosya_yolu):
            try:
                with open(self.dosya_yolu, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def kaydet(self) -> None:
        """Hafızayı JSON dosyasına yazar."""
        try:
            with open(self.dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(self._veri, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[KonforHafizasi] Kayıt hatası: {e}")

    # ──────────────────────────────────────────────────────────
    #  Anahtar Formatı
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _anahtar(u: str, v: str) -> str:
        """Yönden bağımsız kenar anahtarı (alfabetik sıra)."""
        return f"{min(u,v)}→{max(u,v)}"

    # ──────────────────────────────────────────────────────────
    #  Güncelleme (Rota Puanlama)
    # ──────────────────────────────────────────────────────────
    def guncelle(self, yol: List[str], puan: float) -> None:
        """
        Rota boyunca her kenarı kullanıcı puanıyla günceller.

        Parametre:
            yol    Düğüm listesi (örn: ["Kızılay", "Ulus", "Hacettepe"])
            puan   1–5 arası kullanıcı puanı
        """
        puan = max(PUAN_MIN, min(PUAN_MAX, float(puan)))
        zaman = datetime.now().isoformat(timespec="seconds")

        for i in range(len(yol) - 1):
            anahtar = self._anahtar(yol[i], yol[i + 1])
            if anahtar not in self._veri:
                self._veri[anahtar] = {
                    "toplam_puan": 0.0,
                    "sayim":       0,
                    "ortalama":    0.0,
                    "son_guncelleme": zaman,
                }

            kayit = self._veri[anahtar]
            kayit["toplam_puan"]    += puan
            kayit["sayim"]          += 1
            kayit["ortalama"]        = round(kayit["toplam_puan"] / kayit["sayim"], 4)
            kayit["son_guncelleme"]  = zaman

        self.kaydet()

    # ──────────────────────────────────────────────────────────
    #  Sorgulama
    # ──────────────────────────────────────────────────────────
    def kenar_konfor_al(self, u: str, v: str) -> float:
        """
        Kenar için normalize edilmiş konfor skoru döner ∈ [0, 1].

            0.0 → çok kötü (puan ~1)
            0.5 → nötr / bilinmeyen
            1.0 → mükemmel (puan ~5)

        Kenar hafızada yoksa (hiç deneyim yoksa) nötr 0.5 döner.
        """
        anahtar = self._anahtar(u, v)
        if anahtar not in self._veri:
            return 0.5  # Bilinmeyen → nötr

        ort = self._veri[anahtar]["ortalama"]
        # 1→0.0  2→0.25  3→0.5  4→0.75  5→1.0
        return round((ort - PUAN_MIN) / (PUAN_MAX - PUAN_MIN), 4)

    def rota_ortalama_konfor(self, yol: List[str]) -> float:
        """
        Rota boyunca tüm kenarların ortalama hafıza konfor skorunu döner.
        """
        if len(yol) < 2:
            return 0.5
        skorlar = [self.kenar_konfor_al(yol[i], yol[i+1]) for i in range(len(yol)-1)]
        return round(sum(skorlar) / len(skorlar), 4)

    def kenar_sayisi(self) -> int:
        """Hafızada kaç kenar deneyimi olduğunu döner."""
        return len(self._veri)

    def istatistikler(self) -> Dict:
        """Basit hafıza istatistikleri."""
        if not self._veri:
            return {"kenar_sayisi": 0, "genel_ortalama": 0.5}
        ortalamalar = [v["ortalama"] for v in self._veri.values()]
        return {
            "kenar_sayisi":    len(self._veri),
            "genel_ortalama":  round(sum(ortalamalar) / len(ortalamalar), 3),
            "en_iyi_kenar":    max(self._veri, key=lambda k: self._veri[k]["ortalama"]),
            "en_kotu_kenar":   min(self._veri, key=lambda k: self._veri[k]["ortalama"]),
        }


# ── Singleton Erişim ─────────────────────────────────────────────────────────
_hafiza_instance: Optional[SurucuKonforHafizasi] = None


def get_konfor_hafizasi() -> SurucuKonforHafizasi:
    """Global singleton hafıza örneğini döner (lazy init)."""
    global _hafiza_instance
    if _hafiza_instance is None:
        _hafiza_instance = SurucuKonforHafizasi()
    return _hafiza_instance
