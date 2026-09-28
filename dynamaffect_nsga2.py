"""
dynamaffect_nsga2.py - D-NSGA-II: Dynamic NSGA-II with DynamAffect
===================================================================
Real-time emotional state → dynamic objective weighting

FIX (PART 2):
1. Affect-based cost weighting - Duygu durumuna göre cost değişimi
2. Charge constraint enforcement - Batarya sınırını enforcing
3. Complexity-based diversification - Gerçek rota çeşitliliği
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from dynamaffect_core import (
    AffectStateTensor,
    AffectStateCalculator,
    DynamicWeightingFunction,
    AffectivePenaltyFunction,
    AffectAwareEnergyModel,
    BatterySoCManager
)


@dataclass
class RouteSegmentMetrics:
    """Bir rota segmentinin detaylı metrikleri"""
    node_from: str
    node_to: str
    distance_km: float
    elevation_m: float
    avg_speed_kmh: float
    traffic_density: float  # [0, 1]
    
    # GÜNCELLEME: Kompleksite metrikleri
    sharp_turns: int  # Keskin viraj sayısı
    curvature_index: float  # [0, 1] - Yolun eğriliği
    lane_changes_required: int  # Gereken şerit değişimi
    is_highway_merge: bool
    road_type: str  # 'sehir', 'bulvar', 'otoyol', 'ulke'
    
    def get_segment_as_dict(self) -> Dict:
        """Segment'i dict'e çevir"""
        return {
            'node_from': self.node_from,
            'node_to': self.node_to,
            'distance_km': self.distance_km,
            'elevation_m': self.elevation_m,
            'avg_speed_kmh': self.avg_speed_kmh,
            'traffic_density': self.traffic_density,
            'sharp_turns': self.sharp_turns,
            'curvature_index': self.curvature_index,
            'lane_changes_required': self.lane_changes_required,
            'is_highway_merge': self.is_highway_merge,
            'road_type': self.road_type,
        }


@dataclass
class Route:
    """Bir rota temsili"""
    nodes: List[str]  # [origin, ..., destination]
    distance: float   # km
    energy: float     # kWh
    time: float       # minutes
    complexity_score: float  # [0, 100] - Viraj/Kompleksite endeksi
    segments: List[Dict] = None
    
    # GÜNCELLEME: İlave konfor metrikleri
    comfort_index: float = 0.0  # [0, 100] - Yüksek = Konforlu
    efficiency_index: float = 0.0  # [0, 100] - Yüksek = Verimli
    
    def __post_init__(self):
        if self.segments is None:
            self.segments = []
        # Comfort ve Efficiency indekslerini hesapla
        self._calculate_indices()
    
    def _calculate_indices(self):
        """Comfort ve Efficiency indekslerini hesapla"""
        if not self.segments:
            self.comfort_index = 50.0
            self.efficiency_index = 50.0
            return
        
        # Comfort Index = 100 - Complexity Score (düşük kompleksite = yüksek konfor)
        self.comfort_index = max(0, 100 - self.complexity_score)
        
        # Efficiency Index = Distance/Time optimize ve Energy düşüklüğü
        # Normalize metrics for efficiency
        speed_efficiency = 50.0 + (50.0 * min(1.0, self.distance / 100.0))  # Normalize to 100km
        energy_efficiency = 50.0 + (50.0 * max(0, 1.0 - (self.energy / 20.0)))  # Normalize to 20kWh
        
        self.efficiency_index = (0.6 * speed_efficiency + 0.4 * energy_efficiency)


@dataclass
class ParetoSolution:
    """Pareto-optimal çözüm"""
    route: Route
    f1: float  # Distance (weighted)
    f2: float  # Energy (weighted)
    f3: float  # Time (weighted)
    apf: float  # Affective Penalty
    fitness: float  # Combined score
    rank: int = 0
    crowding_distance: float = 0.0


class DynamicNSGA2:
    """
    D-NSGA-II: NSGA-II + Dynamic Weighting based on ASI
    
    FIX: Duygu ve batarya tabanlı cost weighting
    """
    
    def __init__(self, 
                 population_size: int = 100,
                 generations: int = 50,
                 mutation_rate_base: float = 0.05):
        self.pop_size = population_size
        self.max_gen = generations
        self.mut_base = mutation_rate_base
        
        self.affect_calc = AffectStateCalculator()
        self.apf = AffectivePenaltyFunction(sensitivity=2.0)
        self.energy_model = AffectAwareEnergyModel()
        self.battery_mgr = BatterySoCManager()
        
        self.current_asi = 0.0
        self.current_psi = None
        self.current_soc = 100.0
    
    # ────────────────────────────────────────────────────────────
    # Core NSGA-II Methods
    # ────────────────────────────────────────────────────────────
    
    def initialize_population(self, 
                            graph: Dict,
                            origin: str,
                            destination: str) -> List[Route]:
        """Random initial population"""
        population = []
        
        # Simple: Generate random paths using BFS-based sampling
        for _ in range(self.pop_size):
            route = self._generate_random_route(graph, origin, destination)
            if route:
                population.append(route)
        
        return population[:self.pop_size]
    
    def _generate_random_route(self, 
                              graph: Dict,
                              origin: str,
                              destination: str) -> Optional[Route]:
        """Generate a feasible route"""
        visited = {origin}
        path = [origin]
        current = origin
        
        # Greedy random walk
        for _ in range(1000):  # Max depth
            if current == destination:
                break
            
            neighbors = graph.get(current, {})
            unvisited = [n for n in neighbors.keys() if n not in visited]
            
            if not unvisited:
                break
            
            # Random choice with some bias toward destination
            if destination in unvisited and np.random.random() < 0.5:
                next_node = destination
            else:
                next_node = np.random.choice(unvisited)
            
            visited.add(next_node)
            path.append(next_node)
            current = next_node
        
        if current != destination:
            # Fallback: Simple BFS to find ANY path
            import collections
            queue = collections.deque([[origin]])
            bfs_visited = {origin}
            while queue:
                path_bfs = queue.popleft()
                node = path_bfs[-1]
                if node == destination:
                    path = path_bfs
                    break
                for neighbor in graph.get(node, {}):
                    if neighbor not in bfs_visited:
                        bfs_visited.add(neighbor)
                        queue.append(path_bfs + [neighbor])
            
            if path[-1] != destination:
                return None
        
        # Calculate metrics
        dist, energy, time = self._calculate_route_metrics(path, graph)
        complexity = self._calculate_complexity(path, graph)
        segments = self._get_segments(path, graph)
        
        return Route(
            nodes=path,
            distance=dist,
            energy=energy,
            time=time,
            complexity_score=complexity,
            segments=segments
        )
    
    def _calculate_route_metrics(self, path: List[str], graph: Dict) -> Tuple[float, float, float]:
        """Distance, Energy, Time"""
        total_dist = 0.0
        total_elev = 0.0
        total_time = 0.0
        total_energy = 0.0
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge = graph.get(u, {}).get(v, {})
            
            dist = edge.get('distance_km', 10.0)
            elev = edge.get('elevation_m', 0.0)
            speed = edge.get('avg_speed_kmh', 60.0)
            
            total_dist += dist
            total_elev += abs(elev)
            total_time += (dist / speed) * 60  # minutes
            
            # Detailed Physics Model Evaluation (Eq 3.4 - 3.8)
            asi_val = self.current_asi if hasattr(self, 'current_asi') else 0.0
            seg_energy = self.energy_model.calculate_energy(
                distance=dist,
                elevation_change=elev,
                avg_speed=speed,
                asi=asi_val
            )
            total_energy += seg_energy
        
        return total_dist, total_energy, total_time
    
    def _calculate_complexity(self, path: List[str], graph: Dict) -> float:
        """
        Rotanın kompleksitesini hesapla (0-100)
        Yüksek = zor, düşük = kolay
        
        FIX: Duygu ve şarj durumuna göre kompleksite penalty
        """
        complexity = 0.0
        segment_count = 0
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge = graph.get(u, {}).get(v, {})
            
            # Base complexity from segment features
            traffic = edge.get('traffic_density', 0.5)
            turns = edge.get('sharp_turns', 2)
            curve = edge.get('curvature_index', 0.3)
            lane_changes = edge.get('lane_changes_required', 1)
            
            segment_complexity = (traffic * 30 + turns * 5 + curve * 40 + lane_changes * 5)
            complexity += segment_complexity
            segment_count += 1
        
        # Average complexity
        if segment_count > 0:
            base_complexity = complexity / segment_count
        else:
            base_complexity = 50.0
        
        # FIX: ASI'ye göre kompleksite cezalandırması
        # Eğer sürücü stresliyse (ASI < -0.3), trafikli/virajlı yollar daha cezalı
        if self.current_asi < -0.3:  # Stressed driver
            # Trafikli ve virajlı yolları daha cezalı yap
            traffic_penalty = sum(
                graph.get(path[i], {}).get(path[i+1], {}).get('traffic_density', 0.5) * 20
                for i in range(len(path) - 1)
            )
            base_complexity += traffic_penalty / max(1, len(path) - 1)
        
        # Batarya constraint'i kontrol et
        if self.current_soc < 30:
            # Düşük bataryada uzun yollar cezalı
            base_complexity += 15
        
        return min(100.0, max(0.0, base_complexity))
    
    def _get_segments(self, path: List[str], graph: Dict) -> List[Dict]:
        """Rotanın tüm segmentlerini çıkar"""
        segments = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge = graph.get(u, {}).get(v, {})
            
            segments.append({
                'from': u,
                'to': v,
                'distance_km': edge.get('distance_km', 10.0),
                'traffic_density': edge.get('traffic_density', 0.5),
                'road_type': edge.get('road_type', 'bulvar'),
                'avg_speed_kmh': edge.get('avg_speed_kmh', 60),
                'sharp_turns': edge.get('sharp_turns', 2),
                'curvature_index': edge.get('curvature_index', 0.3),
            })
        
        return segments
    
    # ────────────────────────────────────────────────────────────
    # Fitness Evaluation (FIX: Affect & Charge Aware)
    # ────────────────────────────────────────────────────────────
    
    def evaluate_population(self,
                           population: List[Route],
                           psi: AffectStateTensor) -> List[ParetoSolution]:
        """
        FIX: Duygu ve batarya constraint'ini doğrudan fitness'e katı
        """
        self.current_asi = self.affect_calc.calculate_asi(psi)
        self.current_psi = psi
        
        solutions = []
        
        for route in population:
            # ┌─ Objective Functions (3 amaç) ──────────────────────────┐
            # F1: Distance with traffic weighting
            traffic_factor = 1.0 + sum(
                seg.get('traffic_density', 0.5)
                for seg in route.segments
            ) / max(1, len(route.segments))
            f1 = route.distance * traffic_factor
            
            # F2: Energy consumption
            f2 = route.energy
            
            # F3: Time
            f3 = route.time
            
            # ┌─ Dynamic Weighting (ASI-based) ─────────────────────────┐
            # Eğer sürücü stresliyse → Comfort (low complexity) ağırlığını artır
            # Eğer acele ediyorsa → Efficiency (low time) ağırlığını artır
            
            if self.current_asi < -0.3:  # Stressed/Fatigued
                # Comfort routeı tercih et: kompleksiteyi minimize et
                comfort_penalty = route.complexity_score * 2.5  # Complexity'yi 2.5x cezalandır
                f1 += comfort_penalty
            elif self.current_asi > 0.3:  # Alert/Confident
                # Efficiency routeyi tercih et: time'ı minimize et
                f3 *= 0.8  # Time'ı %20 azalt (efficient yollar tercih edilsin)
            
            # ┌─ Battery Constraint (Charge Routing) ────────────────────┐
            # FIX: Batarya sınırı aşılmışsa, sharpten penalty
            battery_penalty = 0.0
            if self.current_soc < 30:
                # Düşük bataryada uzun mesafeler çok cezalı
                battery_penalty = route.distance * 1.5
                f1 += battery_penalty
            elif self.current_soc < 50:
                # Orta bataryada moderate penalty
                battery_penalty = route.distance * 0.5
                f1 += battery_penalty
            
            # ┌─ Affective Penalty Function ─────────────────────────────┐
            apf_score = self.apf.calculate_penalty(
                route.segments,
                self.current_asi
            )
            
            # ┌─ Final Fitness (Combined) ───────────────────────────────┐
            # Multi-objective: minimize all three with APF penalty
            fitness = f1 + f2 + f3 + apf_score
            
            # Create solution object
            sol = ParetoSolution(
                route=route,
                f1=f1,
                f2=f2,
                f3=f3,
                apf=apf_score,
                fitness=fitness
            )
            
            solutions.append(sol)
        
        return solutions
    
    # ────────────────────────────────────────────────────────────
    # Non-Dominated Sorting
    # ────────────────────────────────────────────────────────────
    
    def non_dominated_sort(self, solutions: List[ParetoSolution]) -> List[List[ParetoSolution]]:
        """Non-dominated sorting (Fast NSGA-II)"""
        fronts = []
        
        # Domination check
        for p in solutions:
            p.rank = 0
        
        current_front = []
        for i, sol_i in enumerate(solutions):
            sol_i.domination_count = 0
            sol_i.dominated = []
            
            for j, sol_j in enumerate(solutions):
                if i == j:
                    continue
                
                # Check if sol_i dominates sol_j
                if (sol_i.f1 <= sol_j.f1 and sol_i.f2 <= sol_j.f2 and 
                    sol_i.f3 <= sol_j.f3 and
                    (sol_i.f1 < sol_j.f1 or sol_i.f2 < sol_j.f2 or sol_i.f3 < sol_j.f3)):
                    sol_i.dominated.append(j)
                elif (sol_j.f1 <= sol_i.f1 and sol_j.f2 <= sol_i.f2 and 
                      sol_j.f3 <= sol_i.f3 and
                      (sol_j.f1 < sol_i.f1 or sol_j.f2 < sol_i.f2 or sol_j.f3 < sol_i.f3)):
                    sol_i.domination_count += 1
            
            if sol_i.domination_count == 0:
                sol_i.rank = 1
                current_front.append(i)
        
        fronts.append([solutions[i] for i in current_front])
        
        # Subsequent fronts
        rank = 1
        while current_front:
            next_front = []
            for i in current_front:
                for j in solutions[i].dominated:
                    solutions[j].domination_count -= 1
                    if solutions[j].domination_count == 0:
                        solutions[j].rank = rank + 1
                        next_front.append(j)
            
            if next_front:
                fronts.append([solutions[i] for i in next_front])
            current_front = next_front
            rank += 1
        
        return fronts
    
    # ────────────────────────────────────────────────────────────
    # Crowding Distance
    # ────────────────────────────────────────────────────────────
    
    def calculate_crowding_distance(self, front: List[ParetoSolution]) -> None:
        """Calculate crowding distance for diversity"""
        for sol in front:
            sol.crowding_distance = 0.0
        
        if len(front) <= 2:
            for sol in front:
                sol.crowding_distance = float('inf')
            return
        
        # Sort by each objective and assign distances
        for obj_idx in range(3):
            if obj_idx == 0:
                front.sort(key=lambda x: x.f1)
            elif obj_idx == 1:
                front.sort(key=lambda x: x.f2)
            else:
                front.sort(key=lambda x: x.f3)
            
            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')
            
            obj_range = front[-1].__getattribute__(f'f{obj_idx+1}') - \
                       front[0].__getattribute__(f'f{obj_idx+1}')
            
            if obj_range > 0:
                for i in range(1, len(front) - 1):
                    front[i].crowding_distance += \
                        (front[i+1].__getattribute__(f'f{obj_idx+1}') -
                         front[i-1].__getattribute__(f'f{obj_idx+1}')) / obj_range
    
    # ────────────────────────────────────────────────────────────
    # Selection & Reproduction
    # ────────────────────────────────────────────────────────────
    
    def tournament_selection(self, 
                            solutions: List[ParetoSolution],
                            tournament_size: int = 2) -> List[ParetoSolution]:
        """Tournament selection"""
        selected = []
        for _ in range(len(solutions)):
            candidates = np.random.choice(solutions, tournament_size, replace=False)
            winner = min(candidates, 
                        key=lambda x: (x.rank, -x.crowding_distance))
            selected.append(winner)
        
        return selected
    
    def adaptive_mutation(self, route: Route, asi: float) -> Route:
        """Adaptive mutation based on ASI"""
        mut_rate = self.mut_base + 0.15 * abs(asi)
        
        if np.random.random() < mut_rate:
            # 2-opt or segment swap
            new_route = route
            # Simple: Reverse a segment
            if len(route.nodes) > 3:
                i, j = sorted(np.random.choice(len(route.nodes), 2, replace=False))
                new_nodes = route.nodes[:i] + route.nodes[i:j][::-1] + route.nodes[j:]
                new_route.nodes = new_nodes
        
        return route
    
    # ────────────────────────────────────────────────────────────
    # Main Optimization Loop
    # ────────────────────────────────────────────────────────────
    
    def optimize(self,
                graph: Dict,
                origin: str,
                destination: str,
                psi: AffectStateTensor,
                current_soc: float = 100.0,
                generations: int = None) -> Tuple[List[Route], List[ParetoSolution]]:
        """
        D-NSGA-II Main Loop
        
        FIX: current_soc parametresi eklendi
        
        Returns: (best_routes, pareto_front)
        """
        self.current_soc = current_soc
        
        if generations is None:
            generations = self.max_gen
        
        # Initialize
        P = self.initialize_population(graph, origin, destination)
        
        for gen in range(generations):
            # Evaluate
            solutions = self.evaluate_population(P, psi)
            
            # Sort by rank
            fronts = self.non_dominated_sort(solutions)
            
            # Crowding distance
            for front in fronts:
                self.calculate_crowding_distance(front)
            
            # Select best N
            all_ranked = []
            for front in fronts:
                all_ranked.extend(front)
                if len(all_ranked) >= self.pop_size:
                    break
            
            P = [sol.route for sol in all_ranked[:self.pop_size]]
            
            # Reproduction
            selected = self.tournament_selection(all_ranked[:self.pop_size])
            Q = []
            
            for route in selected:
                new_route = self.adaptive_mutation(route.route, self.current_asi)
                Q.append(new_route)
            
            P.extend(Q)
        
        # Final evaluation
        if not P:
            return [], []
        final_solutions = self.evaluate_population(P, psi)
        final_fronts = self.non_dominated_sort(final_solutions)
        
        best_pareto = final_fronts[0] if final_fronts else []
        best_routes = [sol.route for sol in best_pareto]
        
        return best_routes, best_pareto
    
    # ────────────────────────────────────────────────────────────
    # Utility: Route Diversification (FIX: Complexity-based)
    # ────────────────────────────────────────────────────────────
    
    def get_diversified_routes(self, 
                              best_routes: List[Route], 
                              psi: AffectStateTensor = None,
                              count: int = 3) -> List[Tuple[Route, str]]:
        """
        FIX: Pareto routalardan COMFORT vs EFFICIENT olmak üzere çeşitlendir
        Duygu durumuna (ASI) göre route tipini sınıflandır
        
        Returns: [(Route, 'COMFORT'|'BALANCED'|'EFFICIENT'), ...]
        """
        if not best_routes:
            return []
        
        # Current ASI dari Pareto front
        current_asi = self.current_asi if hasattr(self, 'current_asi') else 0.0
        
        # ┌─ Strategy: Route seçimini ASI'ye göre yapıştır ──────────┐
        # Stressed (ASI < -0.3) → Comfort'ı daha fazla tercih et
        # Alert (ASI > 0.3) → Efficient'i daha fazla tercih et
        
        result = []
        
        # 1. COMFORT: Yüksek comfort index (low complexity, low traffic)
        comfort_route = min(best_routes, key=lambda r: r.complexity_score)
        result.append((comfort_route, 'COMFORT'))
        
        # 2. EFFICIENT: Minimum energy tüketim
        efficient_route = min(best_routes, key=lambda r: r.energy)
        result.append((efficient_route, 'EFFICIENT'))
        
        # 3. BALANCED: Ortada bir rota
        if len(best_routes) > 2:
            # Distance'a göre ortanca rota seç
            sorted_by_dist = sorted(best_routes, key=lambda r: r.distance)
            balanced_route = sorted_by_dist[len(sorted_by_dist) // 2]
            result.append((balanced_route, 'BALANCED'))
        
        return result[:count]