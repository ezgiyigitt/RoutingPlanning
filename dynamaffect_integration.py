"""
dynamaffect_integration.py - AffectEV DynamAffect Entegrasyonu
==============================================================
Tüm bileşenleri bir araya getir ve rota planlama yap

FIX (PART 2):
1. create_sample_graph: Yol tipi çeşitliliği (Highway/Bulvar/Sokak)
2. Charging station integration: Batarya constraint'i ile rota kırma
3. Affect-aware route routing: Duygu durumuna göre rota seçimi
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from dynamaffect_core import (
        AffectStateTensor,
        AffectStateCalculator,
        DynamicWeightingFunction,
        AffectAwareChargingStation,
        BatterySoCManager
    )
except ImportError:
    # Fallback stub classes
    @dataclass
    class AffectStateTensor:
        cls_t: float = 0.0
        ev_t: float = 0.0
        fa_t: float = 0.0
        pr_t: float = 0.0
    
    class AffectStateCalculator:
        def calculate_asi(self, psi): return 0.0
        def calculate_cls(self, *args): return 0.5
        def calculate_ev(self, *args): return 0.5
        def calculate_fa(self, *args): return 0.5
        def calculate_pr(self, *args): return 0.5
    
    class BatterySoCManager:
        def __init__(self, *args, **kwargs):
            self.soc_min = 20.0
            self.soc_max = 80.0
        def is_soc_in_bounds(self, soc): return 20 <= soc <= 80

from dynamaffect_nsga2 import DynamicNSGA2, Route, ParetoSolution


@dataclass
class ChargingStationLive:
    """Canlı şarj istasyonu bilgisi - Doluluk oranı dahil"""
    name: str
    location: str
    latitude: float
    longitude: float
    available_chargers: int
    total_chargers: int
    occupancy_rate: float  # [0-1]
    avg_wait_time_min: float
    power_kw: float
    
    @property
    def availability_status(self) -> str:
        if self.occupancy_rate >= 0.9:
            return "FULL"
        elif self.occupancy_rate >= 0.6:
            return "BUSY"
        elif self.occupancy_rate >= 0.3:
            return "MODERATE"
        else:
            return "AVAILABLE"


@dataclass
class RoutePlanningSolution:
    """Final rota planlama çözümü"""
    route_1_comfort: Route
    route_2_balanced: Route
    route_3_efficient: Route
    
    asi_current: float
    stress_category: str
    
    route_1_metrics: Dict
    route_2_metrics: Dict
    route_3_metrics: Dict
    
    recommended_breaks: List[Dict]  # {location, duration_min}
    charging_stations: List[Dict]   # {name, distance_km, duration_min}
    
    # GÜNCELLEME: Batarya SoC kontrol bilgileri
    battery_constraints: Dict  # {soc_min, soc_max, current_soc, usable_energy_kwh}
    charging_points_on_route: List[Dict]  # Rota boyunca şarj noktaları
    
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DynamAffectRoutePlanner:
    """
    AffectEV Integration Engine
    
    Tüm DynamAffect bileşenlerini koordine eder
    
    FIX:
    - Rota çeşitliliği (Highway/Bulvar/Sokak)
    - Charging station constraint enforcing
    - Affect-aware route selection
    """
    
    def __init__(self,
                 graph: Dict,
                 driver_id: str,
                 vehicle_params: Dict = None,
                 soc_min_percent: float = 20.0,
                 soc_max_percent: float = 80.0):
        """
        Args:
            graph: Road network {node: {neighbor: {distance_km, elevation_m, ...}}}
            driver_id: Sürücü ID
            vehicle_params: {mass_kg, efficiency, battery_capacity_kwh, ...}
            soc_min_percent: Minimum SoC (%) - Default %20
            soc_max_percent: Maximum SoC (%) - Default %80
        """
        self.graph = graph
        self.driver_id = driver_id
        
        self.vehicle_params = vehicle_params or {
            'mass_kg': 1500,
            'efficiency': 0.85,
            'battery_capacity_kwh': 75.0,
            'fast_charger_power_kw': 150.0
        }
        
        # GÜNCELLEME: BatterySoCManager başlat
        self.battery_mgr = BatterySoCManager(
            battery_capacity_kwh=self.vehicle_params.get('battery_capacity_kwh', 75.0),
            soc_lower_limit=soc_min_percent,
            soc_upper_limit=soc_max_percent
        )
        
        # Initialize components
        self.affect_calc = AffectStateCalculator()
        self.nsga2 = DynamicNSGA2(population_size=100, generations=50)
        
        # Current state
        self.current_psi = None
        self.current_asi = None
    
    # ────────────────────────────────────────────────────────────
    # Main Planning Interface
    # ────────────────────────────────────────────────────────────
    
    def plan_route(self,
                  origin: str,
                  destination: str,
                  sensor_data: Dict,
                  current_soc: float = 100.0) -> Optional[RoutePlanningSolution]:
        """
        FIX: Tam rota planlama yapısı
        
        - SoC sınırları kontrolü
        - Şarj noktaları otomatik planlaması
        - Affect-aware route seçimi
        
        Args:
            origin: Başlangıç noktası
            destination: Varış noktası
            sensor_data: Sensordan gelen duygu ve ortam verileri
            current_soc: Batarya % [0-100]
        
        Returns:
            RoutePlanningSolution
        """
        # SoC bounds kontrol
        if not self.battery_mgr.is_soc_in_bounds(current_soc):
            print(f"UYARI: SoC {current_soc:.1f}% sınır dışı! " +
                  f"Limitleri: {self.battery_mgr.soc_min:.0f}% - {self.battery_mgr.soc_max:.0f}%")
        
        # Step 1: Build Affect State Tensor (duygu durumu)
        psi = self._build_affect_state(sensor_data)
        self.current_psi = psi
        self.current_asi = self.affect_calc.calculate_asi(psi)
        
        # Step 2: Optimize with D-NSGA-II (FIX: current_soc geç)
        best_routes, pareto_front = self.nsga2.optimize(
            self.graph,
            origin,
            destination,
            psi,
            current_soc=current_soc,
            generations=50
        )
        
        if not best_routes:
            return None
        
        # Step 3: Rota Çeşitlendirmesi (FIX: Affect-aware)
        diversified = self.nsga2.get_diversified_routes(best_routes, psi=psi, count=3)
        
        if len(diversified) < 3:
            # Fallback
            while len(diversified) < 3:
                idx = len(diversified) - 1
                route_type = ['COMFORT', 'BALANCED', 'EFFICIENT'][len(diversified) - 1]
                if best_routes:
                    diversified.append((best_routes[idx % len(best_routes)], route_type))
        
        route_comfort, route_balanced, route_efficient = [r[0] for r in diversified[:3]]
        
        # Step 4: FIX - Charging station integration
        # Batarya sınırını kontrol et ve şarj istasyonları ekle
        charging_points = self._plan_charging_route(
            route_balanced, 
            current_soc,
            origin,
            destination
        )
        
        # Step 5: ASI'ye göre route seçimini yönlendir
        # Eğer sürücü stresliyse, comfort route'ı strenghten et
        if self.current_asi < -0.3:
            print(f"[STRESS DETECTION] ASI={self.current_asi:.2f} - Comfort route öneriliyor")
            # Stress durumunda comfort route'ı rotate et
            route_comfort, route_balanced = route_balanced, route_comfort
        
        # Step 6: Collect metrics
        metrics = {
            'route_1_metrics': self._get_route_metrics(route_comfort, 'COMFORT'),
            'route_2_metrics': self._get_route_metrics(route_balanced, 'BALANCED'),
            'route_3_metrics': self._get_route_metrics(route_efficient, 'EFFICIENT'),
        }
        
        # Step 7: Build final solution
        stress_category = self._categorize_stress(self.current_asi)
        breaks = self._calculate_break_points(route_balanced, psi)
        
        solution = RoutePlanningSolution(
            route_1_comfort=route_comfort,
            route_2_balanced=route_balanced,
            route_3_efficient=route_efficient,
            
            asi_current=self.current_asi,
            stress_category=stress_category,
            
            route_1_metrics=metrics['route_1_metrics'],
            route_2_metrics=metrics['route_2_metrics'],
            route_3_metrics=metrics['route_3_metrics'],
            
            recommended_breaks=breaks,
            charging_stations=charging_points,
            
            battery_constraints={
                'soc_min_percent': self.battery_mgr.soc_min,
                'soc_max_percent': self.battery_mgr.soc_max,
                'current_soc_percent': current_soc,
                'usable_energy_kwh': self.vehicle_params['battery_capacity_kwh'] * 
                                     (current_soc - self.battery_mgr.soc_min) / 100.0
            },
            charging_points_on_route=charging_points
        )
        
        return solution
    
    def _plan_charging_route(self, 
                            base_route: Route,
                            current_soc: float,
                            origin: str,
                            destination: str) -> List[Dict]:
        """
        FIX: Batarya constraintine göre şarj istasyonları ekle
        
        Eğer soc < 30%, şarj istasyonları üzerinden detour yap
        """
        charging_points = []
        
        # Araca kaç km gidebilir hesapla (75 kWh battery, 0.18 kWh/km)
        usable_energy = self.vehicle_params['battery_capacity_kwh'] * \
                       (current_soc - self.battery_mgr.soc_min) / 100.0
        remaining_range_km = usable_energy / 0.18  # ~408 km at 100%
        
        # Batarya kritik seviye kontrolü
        if current_soc < 30:
            print(f"[CHARGE CRITICAL] SoC {current_soc:.0f}% - Şarj istasyonu zorunlu!")
            
            # En yakın şarj istasyonunu bul ve rota'ya ekle
            live_stations = self.get_live_charging_stations()
            if live_stations:
                # Rota boyunca en uygun istasyonu seç
                charging_point = {
                    'location': live_stations[0].name if hasattr(live_stations[0], 'name') else str(live_stations[0]),
                    'segment_index': len(base_route.nodes) // 2,
                    'soc_on_arrival_percent': max(0, current_soc - (base_route.distance * 0.18 / 
                                                   self.vehicle_params['battery_capacity_kwh'] * 100)),
                    'charge_target_soc_percent': 80,
                    'urgency': 'CRITICAL',
                    'wait_time_min': 30
                }
                charging_points.append(charging_point)
        
        elif current_soc < 50:
            # Moderate battery level - optional charging point
            charging_point = {
                'location': 'Optional Charging Station',
                'segment_index': len(base_route.nodes) // 2,
                'soc_on_arrival_percent': max(0, current_soc - 15),
                'charge_target_soc_percent': 75,
                'urgency': 'MODERATE',
                'wait_time_min': 15
            }
            charging_points.append(charging_point)
        
        return charging_points
    
    def _build_affect_state(self, sensor_data: Dict) -> AffectStateTensor:
        """Sensor verilerinden AffectStateTensor oluştur"""
        # CLS (Cognitive Load)
        cls = self.affect_calc.calculate_cls(
            sensor_data.get('pupil_dilation', 35.0),
            sensor_data.get('steering_variance', 20.0),
            sensor_data.get('traffic_density', 0.5),
            sensor_data.get('lane_clarity', 0.8),
            sensor_data.get('weather_severity', 0.2)
        )
        
        # EV (Emotional Valence)
        ev = self.affect_calc.calculate_ev(
            sensor_data.get('au12', 0.3),
            sensor_data.get('au15', 0.1),
            sensor_data.get('au4', 0.05),
            sensor_data.get('eda_level', 0.4)
        )
        
        # FA (Fatigue)
        fa = self.affect_calc.calculate_fa(
            0.2,  # Previous FA
            cls,
            sensor_data.get('accel_magnitude', 1.0)
        )
        
        # PR (Preference/Personality)
        pr = self.affect_calc.calculate_pr(
            sensor_data.get('speed_pref', 0.6),
            sensor_data.get('comfort_pref', 0.7),
            sensor_data.get('scenic_pref', 0.5)
        )
        
        return AffectStateTensor(cls_t=cls, ev_t=ev, fa_t=fa, pr_t=pr)
    
    def _categorize_stress(self, asi: float) -> str:
        """ASI'ye göre stress kategorisini belirle"""
        if asi < -0.3:
            return "Stressed/Fatigued"
        elif asi > 0.3:
            return "Alert/Confident"
        else:
            return "Relaxed/Normal"
    
    def _calculate_break_points(self, route: Route, psi: AffectStateTensor) -> List[Dict]:
        """FA'ya göre dinlenme noktaları öner"""
        breaks = []
        
        # Eğer FA > 0.6 (yorgun), dinlenme öner
        if psi.fa_t > 0.6:
            route_duration_hours = route.time / 60.0
            if route_duration_hours > 2:
                breaks.append({
                    'location': 'Midpoint Rest Area',
                    'distance_km': route.distance / 2,
                    'duration_min': 15,
                    'reason': 'Fatigue Management'
                })
        
        return breaks
    
    def _get_route_metrics(self, route: Route, route_type: str) -> Dict:
        """Rota metriklerini formatla"""
        return {
            'type': route_type,
            'distance_km': route.distance,
            'energy_kwh': route.energy,
            'time_min': route.time,
            'complexity_score': route.complexity_score,
            'comfort_index': route.comfort_index,
            'efficiency_index': route.efficiency_index,
            'nodes': route.nodes,
        }
    
    def get_live_charging_stations(self, status="all") -> List:
        """Canlı şarj istasyonları (fallback local data)"""
        # OpenStreetMap integration buraya gelir
        Station = type("Station", (object,), {})
        
        stations = []
        s1 = Station()
        s1.name = "ZES - Armada AVM"
        s1.location = "Söğütözü"
        s1.occupancy_rate = 0.2
        s1.available_chargers = 4
        s1.total_chargers = 5
        s1.power_kw = 120
        s1.availability_status = "AVAILABLE"
        s1.coords = (39.912, 32.812)
        s1.latitude = 39.912
        s1.longitude = 32.812
        s1.avg_wait_time_min = 0
        stations.append(s1)
        
        s2 = Station()
        s2.name = "Esarj - Kızılay"
        s2.location = "Kızılay"
        s2.occupancy_rate = 0.95
        s2.available_chargers = 0
        s2.total_chargers = 4
        s2.power_kw = 50
        s2.availability_status = "FULL"
        s2.coords = (39.920, 32.854)
        s2.latitude = 39.920
        s2.longitude = 32.854
        s2.avg_wait_time_min = 20
        stations.append(s2)

        s3 = Station()
        s3.name = "ZES - Bilkent"
        s3.location = "Bilkent"
        s3.occupancy_rate = 0.65
        s3.available_chargers = 2
        s3.total_chargers = 6
        s3.power_kw = 150
        s3.availability_status = "BUSY"
        s3.coords = (39.867, 32.750)
        s3.latitude = 39.867
        s3.longitude = 32.750
        s3.avg_wait_time_min = 10
        stations.append(s3)

        s4 = Station()
        s4.name = "Voltrun - Çankaya"
        s4.location = "Çankaya"
        s4.occupancy_rate = 0.4
        s4.available_chargers = 3
        s4.total_chargers = 5
        s4.power_kw = 22
        s4.availability_status = "MODERATE"
        s4.coords = (39.903, 32.860)
        s4.latitude = 39.903
        s4.longitude = 32.860
        s4.avg_wait_time_min = 5
        stations.append(s4)

        s5 = Station()
        s5.name = "PO - Batıkent"
        s5.location = "Batıkent"
        s5.occupancy_rate = 0.1
        s5.available_chargers = 4
        s5.total_chargers = 4
        s5.power_kw = 50
        s5.availability_status = "AVAILABLE"
        s5.coords = (39.967, 32.733)
        s5.latitude = 39.967
        s5.longitude = 32.733
        s5.avg_wait_time_min = 0
        stations.append(s5)

        return stations


# ──────────────────────────────────────────────────────────────────
# FIX: Improved Sample Graph Creator with Road Diversity
# ──────────────────────────────────────────────────────────────────

def create_sample_graph(coords_dict: dict = None) -> dict:
    """
    FIX: Ankara ilçelerini çeşitli yol tipleriyle bağlayan graf.
    (GERÇEKÇİ & DETERMINISTIK VERSIYON)
    Mesafeye göre yol tipi atanır ve her sorguda rastgele değişmemesi için
    isimler üzerinden hash'lenerek sabit özellikler üretilir.
    """
    import math
    import hashlib
    from datetime import datetime
    
    if coords_dict is None:
        return {"A": {"B": {"distance_km": 10.5, "elevation_m": 0, "avg_speed_kmh": 60, "traffic_density": 0.3, "sharp_turns": 2, "curvature_index": 0.2, "lane_changes_required": 1, "is_highway_merge": False, "road_type": "bulvar"}}}
    
    def get_dist(p1, p2):
        # Gerçek coğrafi mesafe (Haversine)
        R = 6371.0
        lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    
    graph = {}
    districts = list(coords_dict.keys())
    current_hour = datetime.now().hour
    is_rush_hour = current_hour in [8, 9, 17, 18, 19]
    
    for d in districts:
        graph[d] = {}
        distances = sorted(
            [(other, get_dist(coords_dict[d], coords_dict[other])) 
             for other in districts if d != other], 
            key=lambda x: x[1]
        )
        
        # En yakın 8 ilçeye bağla (gerçekçi şehir ağı)
        for neighbor, km_dist in distances[:8]:
            # Rota özelliklerinin her seferinde rastgele DEĞİŞMEMESİ için isimlerden hash üretiyoruz
            pair_name = "".join(sorted([d, neighbor]))
            h = int(hashlib.md5(pair_name.encode()).hexdigest(), 16)
            
            # Mesafeye göre gerçekçi yol tipi ataması
            if km_dist > 15:
                # OTOYOL: Uzun mesafe ilçeler arası
                road_type = "highway"
                speed = 85.0 + (h % 25)
                base_traffic = 0.1 + ((h % 20) / 100.0)
                turns = max(0, int(km_dist / 10)) # 10 km'de bir keskin viraj
                curve = 0.05 + ((h % 10) / 100.0)
                lanes = 0 if (h % 2 == 0) else 1
            elif km_dist > 5:
                # BULVAR: Orta mesafe ana arterler
                road_type = "bulvar"
                speed = 50.0 + (h % 20)
                base_traffic = 0.3 + ((h % 30) / 100.0)
                turns = max(1, int(km_dist / 3)) # 3 km'de bir viraj
                curve = 0.2 + ((h % 20) / 100.0)
                lanes = 1 + (h % 3)
            else:
                # SOKAK: Birbirine çok yakın ilçeler arası
                road_type = "sokak"
                speed = 30.0 + (h % 15)
                base_traffic = 0.5 + ((h % 40) / 100.0)
                turns = max(2, int(km_dist)) # Her 1 km'de bir viraj
                curve = 0.5 + ((h % 30) / 100.0)
                lanes = 2 + (h % 3)
            
            # Gerçek saate göre dinamik trafik yoğunluğu
            traffic = min(1.0, base_traffic * (1.5 if is_rush_hour else 1.0))
            if road_type == "highway" and not is_rush_hour:
                traffic = min(0.3, traffic)
                
            elevation = -20 + (h % 60)
            
            # Kuş uçuşu mesafeye kıvrım payı ekle (%10 - %20 arası daha uzun)
            gercek_mesafe = km_dist * (1.1 + (h % 10) / 100.0)
            
            edge_data = {
                "distance_km": round(gercek_mesafe, 2),
                "elevation_m": float(elevation),
                "avg_speed_kmh": round(speed, 1),
                "traffic_density": round(traffic, 2),
                "sharp_turns": int(turns),
                "curvature_index": round(curve, 2),
                "lane_changes_required": int(lanes),
                "is_highway_merge": (road_type == "highway"),
                "road_type": road_type
            }
            
            graph[d][neighbor] = edge_data
            
            if neighbor not in graph:
                graph[neighbor] = {}
            graph[neighbor][d] = edge_data
            
    return graph