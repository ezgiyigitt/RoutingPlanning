"""
nsga2_optimizasyon.py  —  AffectEV  (Saf Python NSGA-II Motoru)
================================================================
Non-dominated Sorting Genetic Algorithm II (NSGA-II) implementasyonu.

Bu modül tamamen saf Python ile yazılmıştır (numpy / scipy gerektirmez).
Grafın kenar listesinden yürüyerek "geçerli" bireyler (path individuals)
üretir, 3 boyutlu Pareto dominance ilişkisini hesaplar ve CLS skoruna
göre Pareto ön cephesinden en uygun bireyi seçer.

Algoritmik Referans:
    Deb et al., "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA–II"
    IEEE Trans. Evol. Comput. 6(2), 2002.
"""

from __future__ import annotations
import random
import math
from typing import List, Dict, Tuple, Optional, Any


# ──────────────────────────────────────────────────────────────────────────────
#  Yardımcı Tipler
# ──────────────────────────────────────────────────────────────────────────────
PathObjTuple = Tuple[List[str], float, float, float]
# (düğüm_listesi,  enerji_normalize,  süre_normalize,  konfor_maliyet)


# ──────────────────────────────────────────────────────────────────────────────
#  Geçerli Rota Üreticisi  (Random Walk)
# ──────────────────────────────────────────────────────────────────────────────
def _random_walk(
    baslangic: str,
    bitis: str,
    komsular: Dict[str, List[Tuple]],
    max_adim: int = 80,
) -> Optional[List[str]]:
    """
    Graf üzerinde rastgele yürüyerek başlangıçtan bitişe ulaşan
    geçerli bir yol bulur. Döngüleri kırmak için ziyaret listesi tutar.

    Başarısız olursa None döner.
    """
    yol   = [baslangic]
    ziyaret = {baslangic}
    mevcut  = baslangic

    for _ in range(max_adim):
        komsular_listesi = [v for v, *_ in komsular.get(mevcut, [])]
        if not komsular_listesi:
            break

        # Bitişe komşu var mı? Varsa oraya git (erken bulma)
        if bitis in komsular_listesi:
            yol.append(bitis)
            return yol

        # Ziyaret edilmemişleri tercih et; yoksa hepsinden seç
        girilmemis = [k for k in komsular_listesi if k not in ziyaret]
        secim = random.choice(girilmemis if girilmemis else komsular_listesi)

        yol.append(secim)
        ziyaret.add(secim)
        mevcut = secim

    return None  # Bitis'e ulaşılamadı


# ──────────────────────────────────────────────────────────────────────────────
#  Başlangıç Popülasyonu
# ──────────────────────────────────────────────────────────────────────────────
def populasyon_olustur(
    baslangic: str,
    bitis: str,
    komsular: Dict[str, List[Tuple]],
    boyut: int = 50,
    deneme_katsayi: int = 5,
) -> List[List[str]]:
    """
    'boyut' adet geçerli bireyden oluşan ilk popülasyonu üretir.
    Her birey için max (boyut * deneme_katsayi) deneme yapılır.
    """
    populasyon: List[List[str]] = []
    maks_deneme = boyut * deneme_katsayi

    for _ in range(maks_deneme):
        if len(populasyon) >= boyut:
            break
        yol = _random_walk(baslangic, bitis, komsular)
        if yol and yol[-1] == bitis:
            populasyon.append(yol)

    return populasyon


# ──────────────────────────────────────────────────────────────────────────────
#  Crossover (Yol Çaprazlama)
# ──────────────────────────────────────────────────────────────────────────────
def crossover(ebeveyn1: List[str], ebeveyn2: List[str]) -> Optional[List[str]]:
    """
    İki ebeveynin ortak düğümü varsa o düğümden kesip çapraz birleştirir.
    Geçerli bir yavru üretilemezse None döner.
    """
    ortak = set(ebeveyn1) & set(ebeveyn2)
    ortak.discard(ebeveyn1[0])   # Başlangıcı atla
    ortak.discard(ebeveyn1[-1])  # Bitişi atla

    if not ortak:
        return None

    kesim = random.choice(list(ortak))
    idx1  = ebeveyn1.index(kesim)
    idx2  = ebeveyn2.index(kesim)

    # Çaprazla: ebeveyn1'in başı + ebeveyn2'nin sonu
    yavru = ebeveyn1[:idx1 + 1] + ebeveyn2[idx2 + 1:]

    # Döngü denetimi: yinelenen düğüm varsa geçersiz
    if len(yavru) != len(set(yavru)):
        return None

    return yavru


# ──────────────────────────────────────────────────────────────────────────────
#  Mutasyon
# ──────────────────────────────────────────────────────────────────────────────
def mutasyon(
    birey: List[str],
    bitis: str,
    komsular: Dict[str, List[Tuple]],
    oran: float = 0.15,
) -> List[str]:
    """
    Oran olasılığıyla rastgele bir orta düğümden yeniden random_walk başlatır.
    Yeni yol geçerli değilse orijinali döner.
    """
    if random.random() > oran or len(birey) < 3:
        return birey

    kesim = random.randint(1, len(birey) - 2)
    yeni_parca = _random_walk(birey[kesim], bitis, komsular)
    if yeni_parca and yeni_parca[-1] == bitis:
        yeni = birey[:kesim] + yeni_parca
        if len(yeni) == len(set(yeni)):
            return yeni

    return birey


# ──────────────────────────────────────────────────────────────────────────────
#  Fitness Hesabı  (3 Hedef)
# ──────────────────────────────────────────────────────────────────────────────
def fitness_hesapla(
    yol: List[str],
    komsular: Dict[str, List[Tuple]],
    ankara_dugumler: Dict[str, Tuple],
    konfor_fn,              # Callable(yol_tipi, rakım_fark, onceki_tip) -> float
    konfor_hafizasi=None,   # SurucuKonforHafizasi instance (opsiyonel)
    E_REF: float = 25.0,
    T_REF: float = 150.0,
) -> Tuple[float, float, float]:
    """
    Bir bireyin 3 boyutlu fitness değerini hesaplar:
        f1 = normalize enerji  ∈ [0, 1]   (minimize)
        f2 = normalize süre    ∈ [0, 1]   (minimize)
        f3 = konfor maliyeti   ∈ [0, 1]   (minimize)
    """
    enerji_toplam = 0.0
    sure_toplam   = 0.0
    konfor_toplam = 0.0
    kenar_sayisi  = 0
    onceki_tip: Optional[str] = None

    for i in range(len(yol) - 1):
        u, v = yol[i], yol[i + 1]
        komsu_liste = komsular.get(u, [])
        kenar_bulundu = None

        for komsu_v, km, sure, enerji, yol_tipi in komsu_liste:
            if komsu_v == v:
                kenar_bulundu = (km, sure, enerji, yol_tipi)
                break

        if kenar_bulundu is None:
            continue

        km, sure, enerji, yol_tipi = kenar_bulundu
        ra = ankara_dugumler.get(u, (0, 0, 0))[2]
        rb = ankara_dugumler.get(v, (0, 0, 0))[2]

        enerji_toplam += enerji
        sure_toplam   += sure

        # Konfor: temel yol maliyeti
        baz_konfor = konfor_fn(yol_tipi, rb - ra, onceki_tip)

        # Konfor: hafıza ödülünü entegre et
        if konfor_hafizasi is not None:
            hafiza_puani = konfor_hafizasi.kenar_konfor_al(u, v)
            # Hafıza puanı yüksekse konfor maliyetini AZALT (ödüllü yol)
            baz_konfor = max(0.0, baz_konfor - 0.3 * (1.0 - hafiza_puani))

        konfor_toplam += baz_konfor
        kenar_sayisi  += 1
        onceki_tip     = yol_tipi

    f1 = min(1.0, enerji_toplam / (E_REF + 1e-9))
    f2 = min(1.0, sure_toplam   / (T_REF + 1e-9))
    f3 = (konfor_toplam / kenar_sayisi) if kenar_sayisi > 0 else 0.5

    return round(f1, 5), round(f2, 5), round(f3, 5)


# ──────────────────────────────────────────────────────────────────────────────
#  Pareto Dominance
# ──────────────────────────────────────────────────────────────────────────────
def domine_eder(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> bool:
    """a, b'yi domine ediyorsa True döner. (Her boyut ≤, en az biri <)"""
    return (all(ai <= bi for ai, bi in zip(a, b)) and
            any(ai <  bi for ai, bi in zip(a, b)))


def pareto_siralama(fitness_listesi: List[Tuple[float, float, float]]) -> List[int]:
    """
    Her bireyin ait olduğu Pareto front numarasını (0 = en iyi) döner.
    O(n²) naive implementasyon — küçük popülasyonlar için yeterince hızlı.
    """
    n = len(fitness_listesi)
    fronts = [0] * n  # başlangıçta hepsi Front 0 adayı

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if domine_eder(fitness_listesi[j], fitness_listesi[i]):
                fronts[i] = max(fronts[i], fronts[j] + 1)

    return fronts


def crowding_distance(
    bireyler_idx: List[int],
    fitness_listesi: List[Tuple[float, float, float]],
) -> Dict[int, float]:
    """
    Aynı Pareto frontundaki bireylerin kalabalıklık mesafesini hesaplar.
    Sonsuz CD → kenar çözüm (tercih edilir).
    """
    n = len(bireyler_idx)
    if n <= 2:
        return {idx: math.inf for idx in bireyler_idx}

    cd: Dict[int, float] = {idx: 0.0 for idx in bireyler_idx}

    for obj_idx in range(3):  # 3 hedef boyutu
        sirali = sorted(bireyler_idx, key=lambda i: fitness_listesi[i][obj_idx])
        f_min  = fitness_listesi[sirali[0]][obj_idx]
        f_max  = fitness_listesi[sirali[-1]][obj_idx]
        aralik = (f_max - f_min) or 1e-9

        cd[sirali[0]]  = math.inf
        cd[sirali[-1]] = math.inf

        for k in range(1, n - 1):
            prev_f = fitness_listesi[sirali[k - 1]][obj_idx]
            next_f = fitness_listesi[sirali[k + 1]][obj_idx]
            cd[sirali[k]] += (next_f - prev_f) / aralik

    return cd


# ──────────────────────────────────────────────────────────────────────────────
#  Ana NSGA-II Döngüsü
# ──────────────────────────────────────────────────────────────────────────────
def nsga2_calistir(
    baslangic: str,
    bitis: str,
    komsular: Dict[str, List[Tuple]],
    ankara_dugumler: Dict[str, Tuple],
    konfor_fn,
    konfor_hafizasi=None,
    popülasyon_boyutu: int = 50,
    nesil_sayisi: int = 15,
    mutasyon_orani: float = 0.15,
    E_REF: float = 25.0,
    T_REF: float = 150.0,
) -> List[Tuple[List[str], Tuple[float, float, float]]]:
    """
    NSGA-II algoritmasını çalıştırır.

    Dönüş Değeri:
        Pareto Front 0 üyelerinin listesi:
        [(yol_dugum_listesi, (f1_enerji, f2_sure, f3_konfor)), ...]

    Parametre           Açıklama
    ─────────────────── ──────────────────────────────────────────────
    baslangic           Başlangıç düğüm adı
    bitis               Bitiş düğüm adı
    komsular            Graf komşuluk sözlüğü
    ankara_dugumler     {dugum: (lat, lon, rakım)}
    konfor_fn           Kenar konfor maliyeti callable'ı
    konfor_hafizasi     SurucuKonforHafizasi (None → yalnız yol tipi)
    popülasyon_boyutu   P (≥ 10 önerilir, 30–50 iyi denge)
    nesil_sayisi        G (10–20 arasında yeterli yakınsama)
    mutasyon_orani      θ ∈ [0, 1]  (varsayılan 0.15)
    """
    # ── 1. Başlangıç popülasyonu
    pop = populasyon_olustur(baslangic, bitis, komsular, popülasyon_boyutu)
    if not pop:
        return []

    fit = [fitness_hesapla(p, komsular, ankara_dugumler, konfor_fn,
                           konfor_hafizasi, E_REF, T_REF) for p in pop]

    for _ in range(nesil_sayisi):
        # ── 2. Crossover + Mutasyon → Yavru Popülasyonu (Q)
        yavrular: List[List[str]]              = []
        yavru_fit: List[Tuple[float,float,float]] = []

        while len(yavrular) < popülasyon_boyutu:
            e1, e2 = random.sample(pop, 2)
            yavru  = crossover(e1, e2)
            if yavru is None:
                yavru = random.choice([e1, e2])[:]  # Klon

            yavru = mutasyon(yavru, bitis, komsular, mutasyon_orani)

            if yavru and yavru[-1] == bitis and len(yavru) == len(set(yavru)):
                f = fitness_hesapla(yavru, komsular, ankara_dugumler,
                                    konfor_fn, konfor_hafizasi, E_REF, T_REF)
                yavrular.append(yavru)
                yavru_fit.append(f)

        # ── 3. Birleştir: R = P ∪ Q
        birlesik_pop = pop + yavrular
        birlesik_fit = fit + yavru_fit

        # ── 4. Pareto sıralama + CD
        front_nos = pareto_siralama(birlesik_fit)

        front_dict: Dict[int, List[int]] = {}
        for idx, fn in enumerate(front_nos):
            front_dict.setdefault(fn, []).append(idx)

        # ── 5. Seçilim: Popülasyonu yeniden doldur
        yeni_pop: List[List[str]] = []
        yeni_fit: List[Tuple[float,float,float]] = []

        for fn in sorted(front_dict.keys()):
            front_idxler = front_dict[fn]
            kalan = popülasyon_boyutu - len(yeni_pop)

            if kalan <= 0:
                break

            if len(front_idxler) <= kalan:
                for idx in front_idxler:
                    yeni_pop.append(birlesik_pop[idx])
                    yeni_fit.append(birlesik_fit[idx])
            else:
                # Bu front tamamen sığmıyor — CD ile sırala, en iyileri al
                cd = crowding_distance(front_idxler, birlesik_fit)
                sirali = sorted(front_idxler, key=lambda i: cd[i], reverse=True)
                for idx in sirali[:kalan]:
                    yeni_pop.append(birlesik_pop[idx])
                    yeni_fit.append(birlesik_fit[idx])
                break

        pop = yeni_pop
        fit = yeni_fit

    # ── 6. Son Neslin Pareto Front 0'ını Döndür
    if not pop:
        return []

    son_front_nos = pareto_siralama(fit)
    pareto_front0 = [
        (pop[i], fit[i])
        for i in range(len(pop))
        if son_front_nos[i] == 0
    ]

    return pareto_front0


# ──────────────────────────────────────────────────────────────────────────────
#  CLS Bazlı Pareto Seçici
# ──────────────────────────────────────────────────────────────────────────────
def cls_bazli_sec(
    pareto_front: List[Tuple[List[str], Tuple[float, float, float]]],
    cls_skor: float,
    agirlik_fn=None,
) -> Optional[Tuple[List[str], Tuple[float, float, float]]]:
    """
    Pareto ön cephesinden sürücünün anlık CLS değerine en uygun
    bireyi seçer.

    Seçim Kriteri:
        CLS ağırlıklarıyla (w_e, w_t, w_c) ağırlıklı toplam hesaplanır
        ve minimum değerli birey döndürülür.

    Parametre:
        pareto_front   nsga2_calistir'dan gelen liste
        cls_skor       Anlık CLS ∈ [0, 100]
        agirlik_fn     CokAmacliRotaOptimizatoru.agirlik_hesapla (opsiyonel)
    """
    if not pareto_front:
        return None

    if agirlik_fn is not None:
        w_e, w_t, w_c = agirlik_fn(cls_skor)
    else:
        # Varsayılan eşit ağırlık
        w_e = w_t = w_c = 1.0 / 3.0

    def skor(birey_tuple):
        _, (f1, f2, f3) = birey_tuple
        return w_e * f1 + w_t * f2 + w_c * f3

    return min(pareto_front, key=skor)
