"""
AffectEV — Simülasyon ve sistem parametreleri.

Bu dosyadaki değerler bildirinin Tablo 1'i ile birebir aynıdır. Tablo 1'de yer
almayan ama modelin çalışması için gereken değerler "TABLO 1 DIŞI" başlığı
altında ayrıca listelenmiştir (bildiriye eklenmesi önerilir).
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class VehicleParams:
    # ---- Tablo 1 ----
    name: str = "Tesla Model 3 Standart Range"
    Cd: float = 0.23            # Sürüklenme katsayısı
    m: float = 1847.0           # Araç kütlesi (kg)
    A: float = 2.22             # Ön kesit alanı (m^2)
    Cr: float = 0.01            # Yuvarlanma direnci katsayısı
    soc_min: float = 20.0       # Minimum SoC eşiği (%)
    # ---- TABLO 1 DIŞI ----
    rho: float = 1.2            # Hava yoğunluğu (kg/m^3)
    g: float = 9.81             # Yerçekimi ivmesi (m/s^2)
    # P_aux: bildiride sayısal değer yok. 2,0 kW (klima/ısıtma açık ortalama) seçildi; bu değerle
    # Keçiören–Bilkent A* rotasının enerji yoğunluğu bildirinin Tablo 4'teki değerine
    # (4,99 kWh / 23 km ≈ 0,217 kWh/km) yakın çıkar.
    P_aux_kw: float = 2.0       # Yardımcı sistem ortalama gücü (kW)
    C_batt_kwh: float = 60.0    # Batarya kapasitesi (kWh) — bildiri Tablo 4'ten türetilir: (75−66,7)% ↔ 4,99 kWh
    P_charge_kw: float = 50.0   # DC şarj gücü (kW)
    soc_target: float = 80.0    # Şarj hedef seviyesi (%)


@dataclass(frozen=True)
class NSGA2Params:
    # ---- Tablo 1 ----
    population: int = 100
    generations: int = 50
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1


@dataclass(frozen=True)
class QLearningParams:
    # ---- Tablo 1 ----
    alpha: float = 0.1
    gamma: float = 0.9
    epsilon: float = 0.1
    # Ödül fonksiyonu katsayıları (Denklem 8)
    theta1: float = 10.0
    theta2: float = 5.0
    theta3: float = 5.0
    # ---- Bölüm 4 ----
    episodes: int = 1000
    seeds: int = 10


@dataclass(frozen=True)
class CLSParams:
    # Bilişsel yük ağırlıkları (Denklem 1, Tablo 1)
    lambda_f: float = 0.40
    lambda_c: float = 0.40
    lambda_v: float = 0.20


@dataclass(frozen=True)
class ComfortParams:
    # Konfor ağırlıkları (Denklem 2, Tablo 1)
    w_intersection: float = 0.50
    w_stop: float = 0.30
    w_traffic: float = 0.20


# Tablo 3: CLS düzeyine göre ağırlıklar (w_e, w_t, w_c)
# Aralık sınırları: <=25, <=45, <=60, <=75, >75
CLS_WEIGHT_TABLE: Tuple[Tuple[float, Tuple[float, float, float], str], ...] = (
    (25.0, (0.50, 0.40, 0.10), "Çok Enerjik"),
    (45.0, (0.40, 0.35, 0.25), "Enerjik"),
    (60.0, (0.28, 0.22, 0.50), "Nötr"),
    (75.0, (0.13, 0.10, 0.77), "Yorgun"),
    (100.0, (0.08, 0.07, 0.85), "Stresli"),
)

# Tablo 3'te raporlanan temsili CLS değerleri
CLS_LEVELS: Tuple[Tuple[float, str], ...] = (
    (15.0, "Çok Enerjik"),
    (30.0, "Enerjik"),
    (50.0, "Nötr"),
    (65.0, "Yorgun"),
    (85.0, "Stresli"),
)

# Ablasyon: "NSGA-II (CLS yok)" sabit eşit ağırlık
FIXED_WEIGHTS: Tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)


@dataclass(frozen=True)
class ExperimentParams:
    n_scenarios: int = 50
    n_seeds: int = 10
    master_seed: int = 2026
    # Şehir içi senaryo: kuş uçuşu 8–25 km. Bildiride aralık verilmemiştir; temsili vaka
    # Keçiören–Bilkent (kuş uçuşu ~17 km) aralığın ortasında kalacak şekilde seçilmiştir.
    min_od_km: float = 8.0
    max_od_km: float = 25.0
    soc_initial_range: Tuple[float, float] = (30.0, 90.0)


@dataclass(frozen=True)
class TrafficParams:
    """Sentetik trafik modeli (Bölüm 4: 'sentetik trafik yoğunluğu ve hız profilleri')."""
    base_density: Dict[str, float] = field(default_factory=lambda: {
        "motorway": 0.30, "trunk": 0.40, "primary": 0.50, "secondary": 0.45,
        "tertiary": 0.35, "unclassified": 0.25,
    })
    center_latlon: Tuple[float, float] = (39.9208, 32.8541)   # Kızılay
    center_amp: float = 0.20
    center_sigma_km: float = 6.0
    hotspots: int = 8
    hotspot_amp: float = 0.25
    hotspot_sigma_km: Tuple[float, float] = (1.5, 4.0)
    noise_sd: float = 0.08
    speed_drop: float = 0.60        # v = v_free * (1 - speed_drop * D)
    min_speed_kmh: float = 8.0
    signal_wait_s: Tuple[float, float] = (10.0, 30.0)   # kavşakta beklenen bekleme = a + b*D (s)
    stop_prob: Tuple[float, float] = (0.30, 0.60)       # kavşakta durma olasılığı = a + b*D
    stop_go_per_km: float = 2.0                          # tıkanıklıkta dur-kalk olayı / km (x D²)
    # Dn. 3c ivme terimi: a(v̄) = max(rpa_min, rpa_a0 − rpa_a1·v̄[km/h])  (m/s²)
    rpa_a0: float = 0.30
    rpa_a1: float = 0.0028
    rpa_min: float = 0.04


VEHICLE = VehicleParams()

# ─────────────────────────────────────────────────────────────────────────────
# Arayüz için araç seçenekleri (bildiri deneyleri yalnızca Tesla Model 3 kullanır).
# Cd, kütle ve batarya: üretici verileri (evspecifications.com). Ön kesit alanı
# A ≈ 0,85 × genişlik × yükseklik yaklaşımıyla hesaplanmıştır.
# Togg T10X için Cd üretici tarafından yayımlanmamıştır; 0,30 VARSAYILMIŞTIR.
# ─────────────────────────────────────────────────────────────────────────────
VEHICLES: Dict[str, VehicleParams] = {
    "tesla_m3": VEHICLE,
    "togg_t10x": VehicleParams(name="Togg T10X V1 RWD Uzun Menzil", Cd=0.30, m=2135.0, A=2.69, C_batt_kwh=88.5),
    "ioniq5": VehicleParams(name="Hyundai IONIQ 5 77 kWh 2WD", Cd=0.288, m=2090.0, A=2.58, C_batt_kwh=77.4),
    "zoe": VehicleParams(name="Renault Zoe R135 (ZE50)", Cd=0.29, m=1577.0, A=2.37, C_batt_kwh=52.0),
}
VEHICLE_NOTES: Dict[str, str] = {
    "tesla_m3": "Bildirideki referans araç (Tablo 1)",
    "togg_t10x": "Cd yayımlanmamış, 0,30 varsayıldı",
    "ioniq5": "",
    "zoe": "",
}


@dataclass(frozen=True)
class WeatherParams:
    """Arayüz için hava durumu etkileri (model varsayımı; bildiri deneyleri 'Açık' koşulu kullanır).
    speed: serbest akış hız çarpanı; cr: yuvarlanma direnci çarpanı (ıslak/karlı zemin);
    aux_kw: ek yardımcı güç (ısıtma/klima, silecek, buğu çözme); rho: hava yoğunluğu (kg/m³)."""
    name: str
    speed: float = 1.0
    cr: float = 1.0
    aux_kw: float = 0.0
    rho: float = 1.2


WEATHER: Dict[str, WeatherParams] = {
    "acik": WeatherParams("Açık", 1.0, 1.0, 0.0, 1.20),
    "yagmurlu": WeatherParams("Yağmurlu", 0.90, 1.15, 0.3, 1.23),
    "karli": WeatherParams("Karlı / Soğuk", 0.75, 1.30, 1.5, 1.29),
    "sicak": WeatherParams("Sıcak", 1.0, 1.0, 1.0, 1.14),
}
NSGA = NSGA2Params()
QL = QLearningParams()
CLSP = CLSParams()
COMFORT = ComfortParams()
EXP = ExperimentParams()
TRAFFIC = TrafficParams()

# Arayüz ve deneylerde kullanılan Ankara noktaları (enlem, boylam)
LOCATIONS: Dict[str, Tuple[float, float]] = {
    "Kızılay": (39.9208, 32.8541),
    "Ulus": (39.9410, 32.8543),
    "Kavaklıdere": (39.9080, 32.8600),
    "Çankaya": (39.8930, 32.8600),
    "Bilkent": (39.8700, 32.7480),
    "ODTÜ": (39.8910, 32.7840),
    "Keçiören": (39.9980, 32.8640),
    "Çayyolu": (39.8750, 32.6850),
    "Batıkent": (39.9680, 32.7300),
    "Ostim": (39.9660, 32.7470),
    "Sincan": (39.9690, 32.5800),
    "Etimesgut": (39.9470, 32.6700),
    "Eryaman": (39.9760, 32.6350),
    "Gölbaşı": (39.7900, 32.8050),
    "Pursaklar": (40.0370, 32.9000),
    "Esenboğa Havalimanı": (40.1150, 32.9950),
    "Mamak": (39.9300, 32.9170),
    "AŞTİ": (39.9180, 32.8100),
    "Dikmen": (39.8840, 32.8330),
    "Balgat": (39.9000, 32.8200),
}
