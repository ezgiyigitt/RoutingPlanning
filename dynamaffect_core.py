"""

streamlit run app.py



dynamaffect_core.py - DynamAffect Modeli Core Engine
=====================================================
Affect State Tensor (Ψ), Affect State Index (ASI) ve Dynamic Weighting

GÜNCELLEME (PART 1):
1. Batarya SoC Sınırları: %20 (alt) - %80 (üst) kısıtları eklendi
2. Kompleksite/Viraj İndeksi + APF Cezalandırması
"""

import numpy as np
from typing import Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict


@dataclass
class AffectStateTensor:
    """Ψ(t) = [CLS(t), EV(t), FA(t), PR(t)]"""
    cls_t: float  # Cognitive Load Score [0, 100]
    ev_t: float   # Emotional Valence [-1, 1]
    fa_t: float   # Fatigue Accumulation [0, 1]
    pr_t: float   # Personalization Reference [0, 1]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        self.cls_t = max(0, min(100, self.cls_t))
        self.ev_t = max(-1, min(1, self.ev_t))
        self.fa_t = max(0, min(1, self.fa_t))
        self.pr_t = max(0, min(1, self.pr_t))
    
    def to_vector(self) -> np.ndarray:
        """4D vektöre çevir"""
        return np.array([self.cls_t, self.ev_t, self.fa_t, self.pr_t])


class AffectStateCalculator:
    """AST bileşenlerini hesaplayan motor"""
    
    def __init__(self):
        # CLS parametreleri
        self.lambda_1 = 0.02  # Pupil dilation sigmoid
        self.lambda_2 = 0.03  # Steering variance sigmoid
        self.alpha_traffic = 0.4
        self.alpha_lane = 0.3
        self.alpha_weather = 0.3
        
        # EV parametreleri
        self.beta_au12 = 0.5   # Smile
        self.beta_au15 = 0.4   # Sadness
        self.beta_au4 = 0.6    # Anger
        self.gamma_eda = 2.0
        
        # FA parametreleri
        self.rho = 0.3  # CLS to fatigue
        self.sigma = 0.1  # Acceleration impact
        
        # ASI ağırlıkları
        self.w_cls = 0.5
        self.w_ev = 0.4
        self.w_fa = 0.1
        self.w_pr = 0.0
    
    # ────────────────────────────────────────────────────────────
    # CLS(t) Hesaplama
    # ────────────────────────────────────────────────────────────
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid function"""
        return 1.0 / (1.0 + np.exp(-x))
    
    def calculate_cls(self, 
                     pupil_dilation: float,
                     steering_variance: float,
                     traffic_density: float,
                     lane_clarity: float,
                     weather_severity: float) -> float:
        """
        CLS(t) = 30 + 40·h_internal + 30·h_external
        
        Args:
            pupil_dilation: [0, 100] (yüzde)
            steering_variance: [0, 100] (yüzde)
            traffic_density: [0, 1]
            lane_clarity: [0, 1]
            weather_severity: [0, 1]
        """
        h_internal = (1 - np.exp(-self.lambda_1 * pupil_dilation)) * \
                    (1 - np.exp(-self.lambda_2 * steering_variance))
        
        h_external = min(1.0, 
                        self.alpha_traffic * traffic_density + 
                        self.alpha_lane * (1 - lane_clarity) + 
                        self.alpha_weather * weather_severity)
        
        cls = 30 + 40 * h_internal + 30 * h_external
        return float(cls)
    
    # ────────────────────────────────────────────────────────────
    # EV(t) Hesaplama
    # ────────────────────────────────────────────────────────────
    
    def calculate_ev(self,
                    au12: float,  # [0, 1] Smile
                    au15: float,  # [0, 1] Sadness
                    au4: float,   # [0, 1] Anger
                    eda_level: float,  # [0, 1] Stress arousal
                    eda_baseline: float = 0.3) -> float:
        """
        EV(t) = w₁·FAU_to_Valance + w₂·EDA_to_Arousal - 0.5
        
        Output: [-1, 1]
        -1: Very stressed/angry
        +1: Very calm/happy
        """
        # FAU to Valence
        fau_valance = np.tanh(self.beta_au12 * au12 - 
                             self.beta_au15 * au15 - 
                             self.beta_au4 * au4)
        
        # EDA to Arousal
        eda_norm = (eda_level - eda_baseline) / max(0.01, eda_baseline)
        eda_arousal = self._sigmoid(self.gamma_eda * eda_norm)
        
        # Combine
        ev = 0.6 * fau_valance - 0.4 * (2 * eda_arousal - 1)
        return float(np.clip(ev, -1, 1))
    
    # ────────────────────────────────────────────────────────────
    # FA(t) Hesaplama
    # ────────────────────────────────────────────────────────────
    
    def calculate_fa(self,
                    fa_prev: float,
                    cls_t: float,
                    accel_magnitude: float,
                    dt: float = 1.0) -> float:
        """
        FA(t) = FA(t-Δt) + Δt·[ρ·CLS(t) + σ·|dv/dt|²]
        
        Args:
            fa_prev: Previous fatigue [0, 1]
            cls_t: Current CLS [0, 100]
            accel_magnitude: |dv/dt| [0, 10] m/s²
            dt: Time step [seconds]
        """
        cls_norm = cls_t / 100.0
        accel_norm = min(1.0, accel_magnitude / 5.0)  # 5 m/s² = max
        
        delta_fa = dt * (self.rho * cls_norm + self.sigma * (accel_norm ** 2))
        fa = fa_prev + delta_fa
        return float(np.clip(fa, 0, 1))
    
    def reset_fatigue(self, fa: float, reset_factor: float = 0.3) -> float:
        """Rest point: FA ← reset_factor · FA"""
        return fa * reset_factor
    
    # ────────────────────────────────────────────────────────────
    # PR(t) - Personalization Reference
    # ────────────────────────────────────────────────────────────
    
    def calculate_pr(self,
                    speed_pref: float,
                    comfort_pref: float,
                    scenic_pref: float) -> float:
        """
        PR(t) = 0.5·speed + 0.3·comfort + 0.2·scenic
        
        All inputs: [0, 1]
        Output: [0, 1]
        """
        pr = 0.5 * speed_pref + 0.3 * comfort_pref + 0.2 * scenic_pref
        return float(np.clip(pr, 0, 1))
    
    # ────────────────────────────────────────────────────────────
    # ASI - Affect State Index
    # ────────────────────────────────────────────────────────────
    
    def calculate_asi(self, psi: AffectStateTensor) -> float:
        """
        ASI(t) = Ψ(t) · π
        π = [0.3, 0.35, 0.2, 0.15]
        
        Normalize to [-1, 1]:
        ASI_norm = (CLS - 50) / 50 * 0.3 + EV * 0.35 + FA * 0.2 + PR * 0.15
        """
        # CLS and FA should decrease ASI (higher load/fatigue = more stress)
        # EV and PR should increase ASI (higher valence/preference alignment = calmer)
        cls_norm = (psi.cls_t - 50) / 50  # [ -0.4 to 1.0 ]
        
        asi = (-self.w_cls * cls_norm + 
               self.w_ev * psi.ev_t - 
               self.w_fa * psi.fa_t + 
               self.w_pr * psi.pr_t)
        
        return float(np.clip(asi, -1, 1))
    
    def get_stress_category(self, asi: float) -> str:
        """ASI'ye göre stres kategorisi"""
        if asi < -0.6:
            return "VERY_STRESSED"
        elif asi < -0.3:
            return "STRESSED"
        elif asi < 0.3:
            return "NEUTRAL"
        else:
            return "CALM_ENERGETIC"


# ──────────────────────────────────────────────────────────────────
# DYNAMIC WEIGHTING FUNCTION
# ──────────────────────────────────────────────────────────────────

class DynamicWeightingFunction:
    """w(ASI) - ASI'ye bağlı dinamik ağırlıklar"""
    
    @staticmethod
    def calculate_weights(asi: float) -> Tuple[float, float, float]:
        """
        w₁(ASI) = 0.25 - 0.15·tanh(2·ASI)  [Distance]
        w₂(ASI) = 0.40 + 0.10·tanh(2·ASI)  [Energy]
        w₃(ASI) = 0.35 + 0.05·tanh(2·ASI)  [Time/Comfort]
        
        Returns: (w1_distance, w2_energy, w3_comfort)
        """
        tanh_asi = np.tanh(2 * asi)
        
        w1 = 0.25 - 0.15 * tanh_asi
        w2 = 0.40 + 0.10 * tanh_asi
        w3 = 0.35 + 0.05 * tanh_asi
        
        # Normalization check
        total = w1 + w2 + w3
        if total > 0:
            w1, w2, w3 = w1/total, w2/total, w3/total
        
        return float(w1), float(w2), float(w3)
    
    @staticmethod
    def apply_weights(distances: float, 
                     energies: float, 
                     times: float,
                     w1: float, w2: float, w3: float) -> float:
        """
        Normalize ve ağırlıklandır:
        score = w1·(d/d_ref) + w2·(e/e_ref) + w3·(t/t_ref)
        """
        d_ref = 100.0  # km
        e_ref = 20.0   # kWh
        t_ref = 60.0   # minutes
        
        score = (w1 * (distances / d_ref) + 
                w2 * (energies / e_ref) + 
                w3 * (times / t_ref))
        
        return float(score)


# ──────────────────────────────────────────────────────────────────
# AFFECTIVE PENALTY FUNCTION - v2: KOMPL. + VİRAJ İNDEKSİ
# ──────────────────────────────────────────────────────────────────

class AffectivePenaltyFunction:
    """
    APF - Psikolojik olarak ağır rotaları cezalandır
    
    GÜNCELLEME: Viraj/Kompleksite İndeksi eklendi
    - Sürücü stresli → virajlı yollara yüksek ceza
    - Sürücü sakin → virajlı yollara daha az ceza
    """
    
    def __init__(self, sensitivity: float = 2.0):
        self.beta = sensitivity
        # Viraj kompleksitesi parametreleri
        self.turn_complexity_weight = 0.6  # Viraj etkisi ağırlığı
        self.traffic_complexity_weight = 0.4  # Trafik etkisi ağırlığı
    
    def calculate_turn_complexity_index(self, segment: Dict) -> float:
        """
        Bir yol segmentinin viraj/kompleksite indeksini hesapla
        
        TCI = w₁·(sharp_turns / max_turns) + w₂·(curvature)
        
        Returns: [0, 1] - 0: Düz, 1: Çok virajlı
        """
        sharp_turns = segment.get('sharp_turns', 0)
        curvature = segment.get('curvature_index', 0.0)  # [0, 1]
        lane_changes_req = segment.get('lane_changes_required', 0)
        
        # Normalize turns (max expected: 10 sharp turns per segment)
        turns_norm = min(1.0, sharp_turns / 10.0)
        
        # Lane change complexity
        lane_norm = min(1.0, lane_changes_req / 5.0)
        
        # Combined complexity index
        tci = (0.45 * turns_norm + 
               0.35 * curvature + 
               0.20 * lane_norm)
        
        return float(np.clip(tci, 0, 1))
    
    def calculate_segment_complexity(self, segment: Dict) -> float:
        """
        Segmentin toplam kompleksitesi
        
        SC = w_turn·TCI + w_traffic·(traffic_density)
        """
        tci = self.calculate_turn_complexity_index(segment)
        traffic_density = segment.get('traffic_density', 0.3)
        
        segment_complexity = (self.turn_complexity_weight * tci +
                            self.traffic_complexity_weight * traffic_density)
        
        return float(np.clip(segment_complexity, 0, 1))
    
    def calculate_penalty(self,
                         route_segments: list,
                         asi: float) -> float:
        """
        APF = Σᵢ [Complexity_i · Stress_Response(ASI)]
        
        Stress Response Function:
        - ASI >= 0.3  (sakin): penalty = 0
        - -0.3 <= ASI < 0.3 (nötr): penalty = 0.5·complexity
        - -0.6 <= ASI < -0.3 (stresli): penalty = 1.2·complexity
        - ASI < -0.6 (çok stresli): penalty = 2.0·complexity
        
        Args:
            route_segments: Liste [{traffic_density, sharp_turns, curvature_index}, ...]
            asi: Affect State Index [-1, 1]
        
        Returns:
            Penalty score [0, ...]
        """
        if asi >= 0.3:  # Sakin/Enerjik → penalty yok
            return 0.0
        
        # Stress response factor
        if asi >= -0.3:
            stress_factor = 0.5
        elif asi >= -0.6:
            stress_factor = 1.2
        else:
            stress_factor = 2.0
        
        total_penalty = 0.0
        
        for seg in route_segments:
            # Segment kompleksitesi hesapla
            seg_complexity = self.calculate_segment_complexity(seg)
            
            # Viraj/kompleksite cezası
            penalty_component = seg_complexity * stress_factor
            
            # Ek: Traffic-related complexity (stresli durumda)
            if asi < -0.5:
                if seg.get('traffic_density', 0) > 0.7:
                    penalty_component *= 1.15  # +15% ceza
            
            # Ek: Highway merge difficulty (çok stresli)
            if asi < -0.7 and seg.get('is_highway_merge', False):
                penalty_component *= 1.3  # +30% ceza
            
            total_penalty += penalty_component
        
        return float(min(total_penalty, 100.0))  # Cap at 100


# ──────────────────────────────────────────────────────────────────
# ENERGY CONSUMPTION AFFECT-AWARE
# ──────────────────────────────────────────────────────────────────

class AffectAwareEnergyModel:
    """Sürücü durumuyla ilişkili enerji tüketim modeli"""
    
    def __init__(self, vehicle_mass: float = 1500, efficiency: float = 0.85):
        self.m = vehicle_mass
        self.eta = efficiency
        self.g = 9.81
    
    def calculate_energy(self,
                        distance: float,
                        elevation_change: float,
                        avg_speed: float,
                        asi: float) -> float:
        """
        E_consumed = E_base + ΔE_stress
        
        Args:
            distance: [km]
            elevation_change: [m]
            avg_speed: [km/h]
            asi: [-1, 1]
        
        Returns:
            Energy [kWh]
        """
        # ────────────────────────────────────────────────────────────
        # THESIS PHYSICS MODEL (Equations 3.4 - 3.8)
        # ────────────────────────────────────────────────────────────
        rho = 1.225   # Air density (kg/m^3)
        c_d = 0.28    # Drag coefficient
        A_area = 2.2  # Frontal area (m^2)
        c_rr = 0.012  # Rolling resistance coefficient
        p_aux = 1.5   # Auxiliary power (kW)
        
        v_m_s = avg_speed / 3.6
        t_seconds = (distance * 1000) / max(1.0, v_m_s)
        t_hours = t_seconds / 3600.0
        
        # 1. Aerodynamic drag (Eq 3.5): 0.5 * ρ * C_d * A * v³ * t
        e_drag_j = 0.5 * rho * c_d * A_area * (v_m_s ** 3) * t_seconds
        e_drag_kwh = e_drag_j / 3_600_000
        
        # 2. Rolling resistance (Eq 3.6): C_rr * m * g * d
        e_roll_j = c_rr * self.m * self.g * (distance * 1000)
        if elevation_change > 0:
            e_roll_j += self.m * self.g * elevation_change  # Potential energy
        e_roll_kwh = e_roll_j / 3_600_000
        
        # 3. Acceleration (Eq 3.7): 0.5 * m * (v^2)
        # Assuming an average of 1 stop/acceleration per kilometer in urban routing
        accel_events = max(1, int(distance))
        e_accel_j = accel_events * 0.5 * self.m * (v_m_s ** 2)
        e_accel_kwh = e_accel_j / 3_600_000
        
        # 4. Auxiliary energy (Eq 3.8): P_aux * t
        e_aux_kwh = p_aux * t_hours
        
        # Total Base Consumption (Eq 3.4)
        e_base = (e_drag_kwh + e_roll_kwh + e_accel_kwh + e_aux_kwh) / self.eta
        
        # Stress-related delta
        if asi < -0.6:
            stress_factor = 1.15  # +15%
        elif asi < -0.3:
            stress_factor = 1.08  # +8%
        elif asi < 0.3:
            stress_factor = 1.0   # 0%
        else:
            stress_factor = 0.95  # -5%
        
        e_total = e_base * stress_factor
        return float(e_total)


# ──────────────────────────────────────────────────────────────────
# BATTERY SoC CONSTRAINTS - v2: 20%-80% SINIRLARI
# ──────────────────────────────────────────────────────────────────

class BatterySoCManager:
    """
    Batarya SoC Sınırları Yöneticisi
    
    MADDE 1: %20 (alt sınır) - %80 (üst sınır) kısıtları
    - Rota planlama bu aralıkları koruyacak
    - Şarj istasyonu duraklarını otomatik hesapla
    """
    
    def __init__(self, 
                 battery_capacity_kwh: float = 75.0,
                 soc_lower_limit: float = 20.0,
                 soc_upper_limit: float = 80.0):
        """
        Args:
            battery_capacity_kwh: Batarya kapasitesi (kWh)
            soc_lower_limit: Minimum SoC (%) - Default %20
            soc_upper_limit: Maximum SoC (%) - Default %80
        """
        self.battery_cap = battery_capacity_kwh
        self.soc_min = soc_lower_limit
        self.soc_max = soc_upper_limit
    
    def get_usable_energy_kwh(self) -> float:
        """Kullanılabilir enerji (kWh)"""
        usable_range = (self.soc_max - self.soc_min) / 100.0
        return self.battery_cap * usable_range
    
    def get_minimum_safe_energy_kwh(self) -> float:
        """Minimum güvenli enerji (kWh) - alt sınırda"""
        return self.battery_cap * (self.soc_min / 100.0)
    
    def is_soc_in_bounds(self, current_soc: float) -> bool:
        """Mevcut SoC sınırlarda mı?"""
        return self.soc_min <= current_soc <= self.soc_max
    
    def check_charging_needed(self, 
                            current_soc: float,
                            required_energy: float) -> Tuple[bool, float]:
        """
        Şarj gerekli mi? Gereken miktarı hesapla
        
        Args:
            current_soc: Mevcut SoC (%)
            required_energy: Rota için gerekli enerji (kWh)
        
        Returns:
            (charging_needed: bool, energy_needed_kwh: float)
        """
        available_energy = self.battery_cap * (current_soc / 100.0)
        
        if required_energy > available_energy:
            # Şarj gerekli - soc_max'e kadar şarj ettikten sonra güvenli mi?
            energy_after_charge = self.battery_cap * (self.soc_max / 100.0)
            if required_energy <= energy_after_charge:
                energy_needed = self.battery_cap * ((self.soc_max - current_soc) / 100.0)
                return (True, energy_needed)
            else:
                # İhtiyaç çok fazla - birden fazla şarj gerekli
                return (True, float('inf'))
        
        return (False, 0.0)
    
    def find_charging_points_for_route(self,
                                       current_soc: float,
                                       route_segments: List[Dict],
                                       energy_consumption_per_km: float) -> List[Dict]:
        """
        Rota boyunca gerekli şarj noktalarını belirle
        
        Args:
            current_soc: Başlangıç SoC (%)
            route_segments: Rota segmentleri [{distance_km, location, ...}, ...]
            energy_consumption_per_km: Km başına enerji tüketimi
        
        Returns:
            Şarj noktaları: [{segment_index, location, soc_on_arrival, charging_to_soc}, ...]
        """
        charging_points = []
        current_energy = self.battery_cap * (current_soc / 100.0)
        min_safe_energy = self.get_minimum_safe_energy_kwh()
        
        cumulative_distance = 0.0
        
        for seg_idx, segment in enumerate(route_segments):
            distance = segment.get('distance_km', 0.0)
            energy_needed = distance * energy_consumption_per_km
            
            current_energy -= energy_needed
            cumulative_distance += distance
            current_soc_calc = (current_energy / self.battery_cap) * 100.0
            
            # Alt sınıra yaklaştığımızda şarj noktası ekle
            if current_energy < min_safe_energy * 1.2:  # %20'nin %120'si kadar kaldığında
                charging_points.append({
                    'segment_index': seg_idx,
                    'location': segment.get('location', f'Segment {seg_idx}'),
                    'soc_on_arrival_percent': max(self.soc_min, current_soc_calc),
                    'charge_target_soc_percent': self.soc_max,
                    'cumulative_distance_km': cumulative_distance,
                    'urgency': 'HIGH' if current_soc_calc < self.soc_min + 5 else 'NORMAL'
                })
                
                # Şarj sonrası enerjileri güncelle
                current_energy = self.battery_cap * (self.soc_max / 100.0)
        
        return charging_points


# ──────────────────────────────────────────────────────────────────
# CHARGING STATION SELECTION
# ──────────────────────────────────────────────────────────────────

class AffectAwareChargingStation:
    """Stres seviyesine göre şarj istasyonu seçimi"""
    
    @staticmethod
    def station_score(capacity: float,
                     distance: float,
                     crowd_level: float,
                     asi: float) -> float:
        """
        Station_Score = capacity·w_cap - distance·w_dist - crowd·w_crowd
        
        w_cap(ASI) = 0.2 + 0.3·sigmoid(-ASI)
        w_dist(ASI) = 0.4 - 0.2·sigmoid(-ASI)
        w_crowd(ASI) = 0.4 + 0.3·sigmoid(-ASI)
        """
        sigmoid_asi = 1.0 / (1.0 + np.exp(asi))  # sigmoid(-ASI)
        
        w_cap = 0.2 + 0.3 * sigmoid_asi
        w_dist = 0.4 - 0.2 * sigmoid_asi
        w_crowd = 0.4 + 0.3 * sigmoid_asi
        
        score = (capacity * w_cap - 
                distance * w_dist - 
                crowd_level * w_crowd)
        
        return float(score)
    
    @staticmethod
    def charging_duration(soc: float, asi: float) -> float:
        """
        Duration = Base_Time(SOC) + Stress_Adjustment(ASI)
        
        Args:
            soc: State of Charge [0, 100] %
            asi: [-1, 1]
        
        Returns:
            Minutes
        """
        base_time = 20 + 40 * (100 - soc) / 100
        
        if asi < -0.7:
            adjustment = 10  # +10 min
        elif asi < -0.3:
            adjustment = 5   # +5 min
        elif asi < 0.3:
            adjustment = 0   # 0 min
        else:
            adjustment = -3  # -3 min
        
        return float(max(15, base_time + adjustment))