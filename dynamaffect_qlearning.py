"""
dynamaffect_qlearning.py - Q-Learning Personalization for DynamAffect
=====================================================================
Sürücü tercihlerini dinamik olarak öğren ve güncelle
"""

import numpy as np
import json
import os
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class QState:
    """Q-Learning State"""
    origin: str
    destination: str
    asi: float  # [-1, 1]
    time_of_day: int  # [0-23]
    weather: str  # 'clear', 'rain', 'snow'
    route_type: str  # 'short', 'economic', 'scenic', 'balanced'
    
    def to_key(self) -> str:
        """State'i string key'e çevir"""
        return f"{self.origin}|{self.destination}|{int(self.asi*10)}|{self.time_of_day}|{self.weather}|{self.route_type}"


class QAction:
    """Q-Learning Actions"""
    FAST = "fast_route"
    ECONOMIC = "economic_route"
    SCENIC = "scenic_route"
    BALANCED = "balanced_route"
    
    ALL = [FAST, ECONOMIC, SCENIC, BALANCED]


@dataclass
class RewardSignal:
    """Reward için sinyaller"""
    completed: bool = False  # Rota tamamlandı mı?
    early_exit: bool = False  # Erken çıktı mı?
    driver_feedback: float = 0.0  # [1-5] stars
    harsh_accel: bool = False  # Sert hızlanma?
    traffic_incident: bool = False  # Trafik olayı?
    time_efficiency: float = 1.0  # Tahminden ne kadar etkili?
    
    def calculate_reward(self) -> float:
        """Toplam reward hesapla"""
        reward = 0.0
        
        if self.completed and not self.early_exit:
            reward += 10.0
        elif self.early_exit:
            reward -= 15.0
        
        if self.driver_feedback > 0:
            # 1→-4, 2→-2, 3→0, 4→+2, 5→+5
            reward += (self.driver_feedback - 3) * 2
        
        if self.harsh_accel:
            reward -= 10.0
        
        if self.traffic_incident:
            reward -= 5.0
        
        reward *= self.time_efficiency
        
        return float(reward)


class DriverQNetwork:
    """
    Q-Learning network for a single driver
    
    Q(s, a) → value function
    """
    
    def __init__(self, 
                 driver_id: str,
                 learning_rate: float = 0.1,
                 discount_factor: float = 0.9,
                 epsilon_init: float = 0.3):
        self.driver_id = driver_id
        self.alpha = learning_rate  # Learning rate
        self.gamma = discount_factor  # Discount factor
        self.epsilon = epsilon_init  # Exploration rate
        
        self.Q = {}  # Q-table: {state_key: {action: q_value}}
        self.state_visits = {}  # Ziyaret sayıları
        self.episode_count = 0
    
    def _ensure_state(self, state_key: str) -> None:
        """State'in Q-table'da olduğundan emin ol"""
        if state_key not in self.Q:
            self.Q[state_key] = {action: 0.0 for action in QAction.ALL}
            self.state_visits[state_key] = 0
    
    def select_action(self, state: QState, exploit: bool = False) -> str:
        """
        ε-greedy action selection
        
        exploit=True → hiçbir exploration yok (deployment)
        exploit=False → ε exploration
        """
        state_key = state.to_key()
        self._ensure_state(state_key)
        self.state_visits[state_key] += 1
        
        if exploit:
            # Pure exploitation
            best_action = max(self.Q[state_key], 
                            key=self.Q[state_key].get)
            return best_action
        
        if np.random.random() < self.epsilon:
            # Exploration
            return np.random.choice(QAction.ALL)
        else:
            # Exploitation
            return max(self.Q[state_key], 
                      key=self.Q[state_key].get)
    
    def update_q(self,
                 state: QState,
                 action: str,
                 reward: float,
                 next_state: Optional[QState] = None) -> None:
        """
        Q-learning update:
        Q(s,a) ← Q(s,a) + α[r + γ·max_a'(Q(s',a')) - Q(s,a)]
        """
        state_key = state.to_key()
        self._ensure_state(state_key)
        
        # Current Q value
        current_q = self.Q[state_key][action]
        
        # Max Q for next state
        if next_state is None:
            max_next_q = 0.0
        else:
            next_state_key = next_state.to_key()
            self._ensure_state(next_state_key)
            max_next_q = max(self.Q[next_state_key].values())
        
        # Update
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.Q[state_key][action] = float(new_q)
        
        # Decay epsilon
        self.epsilon = max(0.05, self.epsilon * 0.995)
    
    def get_policy(self, state: QState) -> Dict[str, float]:
        """
        Softmax policy from Q-values
        
        π(a|s) = exp(Q(s,a)) / Σ_a exp(Q(s,a))
        """
        state_key = state.to_key()
        self._ensure_state(state_key)
        
        q_values = np.array([self.Q[state_key][a] for a in QAction.ALL])
        
        # Softmax
        q_shifted = q_values - np.max(q_values)  # For numerical stability
        exp_q = np.exp(q_shifted / 0.1)  # Temperature = 0.1
        policy = exp_q / np.sum(exp_q)
        
        return {action: float(policy[i]) for i, action in enumerate(QAction.ALL)}
    
    def get_best_action_value(self, state: QState) -> float:
        """Best Q-value for state"""
        state_key = state.to_key()
        self._ensure_state(state_key)
        return max(self.Q[state_key].values())
    
    def save(self, filepath: str) -> None:
        """Save Q-table to JSON"""
        data = {
            'driver_id': self.driver_id,
            'Q': self.Q,
            'state_visits': self.state_visits,
            'episode_count': self.episode_count,
            'epsilon': self.epsilon,
            'saved_at': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, filepath: str) -> bool:
        """Load Q-table from JSON"""
        if not os.path.exists(filepath):
            return False
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.driver_id = data.get('driver_id', self.driver_id)
        self.Q = data.get('Q', {})
        self.state_visits = data.get('state_visits', {})
        self.episode_count = data.get('episode_count', 0)
        self.epsilon = data.get('epsilon', 0.3)
        
        return True
    
    def get_statistics(self) -> Dict:
        """Q-network istatistikleri"""
        total_updates = sum(self.state_visits.values())
        
        all_q_values = []
        for state_q in self.Q.values():
            all_q_values.extend(state_q.values())
        
        return {
            'driver_id': self.driver_id,
            'states_explored': len(self.Q),
            'total_state_visits': total_updates,
            'episodes': self.episode_count,
            'epsilon': self.epsilon,
            'mean_q_value': float(np.mean(all_q_values)) if all_q_values else 0.0,
            'max_q_value': float(np.max(all_q_values)) if all_q_values else 0.0,
        }


class DynamAffectPersonalization:
    """
    Multi-driver Q-learning management system
    """
    
    def __init__(self, storage_dir: str = "./driver_q_networks"):
        self.storage_dir = storage_dir
        self.networks: Dict[str, DriverQNetwork] = {}
        os.makedirs(storage_dir, exist_ok=True)
    
    def get_or_create_network(self, driver_id: str) -> DriverQNetwork:
        """Driver'a ait Q-network'ü al veya yarat"""
        if driver_id not in self.networks:
            network = DriverQNetwork(driver_id)
            
            # Load if exists
            filepath = os.path.join(self.storage_dir, f"{driver_id}_q.json")
            network.load(filepath)
            
            self.networks[driver_id] = network
        
        return self.networks[driver_id]
    
    def select_best_route(self,
                         driver_id: str,
                         state: QState,
                         route_options: list,
                         exploit: bool = False) -> Tuple[str, str, float]:
        """
        En iyi rotayı Q-learning'e göre seç
        
        Returns: (route_index, action_type, confidence)
        """
        network = self.get_or_create_network(driver_id)
        action = network.select_action(state, exploit=exploit)
        
        # Map action to route
        route_map = {
            QAction.FAST: 0,  # Fastest
            QAction.ECONOMIC: 1,  # Most efficient
            QAction.SCENIC: 2,  # Most comfortable
            QAction.BALANCED: 3,  # Balanced
        }
        
        route_idx = route_map.get(action, 1)
        
        # Confidence = softmax probability
        policy = network.get_policy(state)
        confidence = policy.get(action, 0.5)
        
        return route_idx, action, confidence
    
    def learn_from_episode(self,
                          driver_id: str,
                          state: QState,
                          action: str,
                          reward_signal: RewardSignal,
                          next_state: Optional[QState] = None) -> None:
        """Learn from completed trip"""
        network = self.get_or_create_network(driver_id)
        reward = reward_signal.calculate_reward()
        network.update_q(state, action, reward, next_state)
        network.episode_count += 1
    
    def save_all(self) -> None:
        """Tüm driver networks'ü kaydet"""
        for driver_id, network in self.networks.items():
            filepath = os.path.join(self.storage_dir, f"{driver_id}_q.json")
            network.save(filepath)
    
    def get_driver_preference_vector(self, driver_id: str, state: QState) -> np.ndarray:
        """
        Driver'ın mevcut state'de tercih vektörü
        [P(Fast), P(Economic), P(Scenic), P(Balanced)]
        """
        network = self.get_or_create_network(driver_id)
        policy = network.get_policy(state)
        
        return np.array([
            policy.get(QAction.FAST, 0.25),
            policy.get(QAction.ECONOMIC, 0.25),
            policy.get(QAction.SCENIC, 0.25),
            policy.get(QAction.BALANCED, 0.25),
        ])


# ──────────────────────────────────────────────────────────────────
# Utility: Preference Learning from Feedback
# ──────────────────────────────────────────────────────────────────

class PreferenceFeedback:
    """
    Sürücüdan 1-5 yıldız feedback toplayıp Q-learning'e dönüştür
    """
    
    @staticmethod
    def stars_to_reward_modifier(stars: float) -> float:
        """
        1 star → -4.0
        2 stars → -2.0
        3 stars → 0.0
        4 stars → +2.0
        5 stars → +5.0
        """
        return (stars - 3) * 2
    
    @staticmethod
    def completion_bonus(completed: bool, early_exit: bool) -> float:
        """Completion signal"""
        if completed and not early_exit:
            return 10.0
        elif early_exit:
            return -15.0
        return 0.0