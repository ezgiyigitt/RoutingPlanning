"""
Q-Learning adaptasyonu (Bölüm 3, Dn. 6–9) ve sentetik kullanıcı modeli.

Durum   s = (CLS, SoC_level, Traffic_level, Route_type)                 (Dn. 6)
          CLS: Tablo 3'teki 5 düzey; SoC: düşük(<40)/orta(40–70)/yüksek(>70);
          Trafik: düşük(<40)/orta(40–60)/yüksek(>60) (D_traffic, 0–100);
          Route_type: bir önceki seyahatte seçilen rota kategorisi (ilk seyahatte 'yok').
Eylem   a ∈ {Konfor, Dengeli, Verimlilik}  (D-NSGA-II kategorileri)
Güncelleme Q(s,a) ← Q(s,a) + α[r + γ·max_a' Q(s',a') − Q(s,a)]          (Dn. 7)
Ödül    r = θ1·feedback + θ2·comfort − θ3·delay                         (Dn. 8)
          feedback ∈ [−1, 1] (kullanıcı modeli), comfort = Comfort/100,
          delay = (t_a − t_min)/t_min (seçilen rotanın en hızlı seçeneğe göre göreli gecikmesi)
Politika ε-greedy                                                        (Dn. 9)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import CLS_WEIGHT_TABLE, QL, QLearningParams

ACTIONS = ("Konfor", "Dengeli", "Verimlilik")
SOC_LEVELS = ("düşük", "orta", "yüksek")
TRAFFIC_LEVELS = ("düşük", "orta", "yüksek")
ROUTE_TYPES = ACTIONS + ("yok",)


def cls_level(cls: float) -> int:
    for i, (upper, _, _) in enumerate(CLS_WEIGHT_TABLE):
        if cls <= upper:
            return i
    return len(CLS_WEIGHT_TABLE) - 1


def soc_level(soc: float) -> int:
    return 0 if soc < 40 else (1 if soc <= 70 else 2)


def traffic_level(d100: float) -> int:
    return 0 if d100 < 40 else (1 if d100 <= 60 else 2)


def encode_state(cls: float, soc: float, traffic_d100: float, prev_action: Optional[int]) -> Tuple[int, int, int, int]:
    return (cls_level(cls), soc_level(soc), traffic_level(traffic_d100), 3 if prev_action is None else prev_action)


@dataclass
class TripOption:
    """Bir seyahat için üç kategori rotasının metrikleri (D-NSGA-II çıktısından)."""
    energy: Tuple[float, float, float]     # ACTIONS sırasıyla
    time: Tuple[float, float, float]
    comfort: Tuple[float, float, float]
    traffic_d100: float


def reward(feedback: float, comfort: float, delay: float, p: QLearningParams = QL) -> float:
    """Dn. (8)."""
    return p.theta1 * feedback + p.theta2 * (comfort / 100.0) - p.theta3 * delay


class SyntheticUser:
    """Gizli tercihleri olan sentetik sürücü.
    Yorgunluk duyarlılığı β(CLS) = 1 / (1 + exp(−(CLS − 50)/10)): CLS arttıkça konfor önem kazanır.
    SoC < 40 iken menzil kaygısı enerjiye ek ağırlık verir.
    Memnuniyet (feedback): seçilen seçeneğin üç seçenek arasındaki göreli faydası, [−1, 1], gürültülü."""

    def __init__(self, rng: np.random.Generator, noise_sd: float = 0.2):
        self.rng = rng
        self.noise_sd = noise_sd

    def utilities(self, opt: TripOption, cls: float, soc: float) -> np.ndarray:
        def norm(x, higher_better=False):
            x = np.asarray(x, dtype=float)
            span = x.max() - x.min()
            z = (x - x.min()) / span if span > 1e-9 else np.zeros_like(x)
            return z if higher_better else -z
        beta = 1.0 / (1.0 + np.exp(-(cls - 50.0) / 10.0))
        anxiety = 0.5 if soc < 40 else 0.0
        c = norm(opt.comfort, higher_better=True)
        e = norm(opt.energy)
        t = norm(opt.time)
        return beta * c + (1 - beta) * (0.5 * e + 0.5 * t) + anxiety * e

    def feedback(self, opt: TripOption, cls: float, soc: float, a: int) -> float:
        u = self.utilities(opt, cls, soc)
        span = u.max() - u.min()
        f = 1.0 - 2.0 * (u.max() - u[a]) / span if span > 1e-9 else 1.0
        return float(np.clip(f + self.rng.normal(0.0, self.noise_sd), -1.0, 1.0))


class QAgent:
    def __init__(self, rng: np.random.Generator, p: QLearningParams = QL):
        self.p = p
        self.rng = rng
        self.Q = np.zeros((len(CLS_WEIGHT_TABLE), 3, 3, 4, len(ACTIONS)))

    def act(self, s: Tuple[int, int, int, int], greedy: bool = False) -> int:
        """Dn. (9): ε-greedy."""
        if not greedy and self.rng.random() < self.p.epsilon:
            return int(self.rng.integers(len(ACTIONS)))
        q = self.Q[s]
        best = np.flatnonzero(q == q.max())
        return int(self.rng.choice(best))

    def update(self, s, a: int, r: float, s_next) -> None:
        """Dn. (7)."""
        target = r + self.p.gamma * self.Q[s_next].max()
        self.Q[s + (a,)] += self.p.alpha * (target - self.Q[s + (a,)])

    # --- kalıcılık (arayüz/API için) ---
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.save(path, self.Q)

    def load(self, path: str) -> bool:
        if os.path.exists(path):
            self.Q = np.load(path)
            return True
        return False


def run_training(trips: Sequence[TripOption], seed: int, episodes: int = QL.episodes,
                 policy: str = "q") -> np.ndarray:
    """Bir tohum için eğitim; bölüm başına ödül dizisini döndürür.
    policy='q' → Q-Learning (ε-greedy), policy='random' → rastgele politika (taban çizgisi).
    Her iki politika da aynı seyahat/sürücü dizisini görür."""
    env_rng = np.random.default_rng(seed)
    user = SyntheticUser(np.random.default_rng(seed + 10_000))
    agent = QAgent(np.random.default_rng(seed + 20_000))
    pol_rng = np.random.default_rng(seed + 30_000)

    def sample():
        k = int(env_rng.integers(len(trips)))
        return trips[k], float(env_rng.uniform(0, 100)), float(env_rng.uniform(20, 95))

    rewards = np.zeros(episodes)
    prev = None
    trip, cls, soc = sample()
    s = encode_state(cls, soc, trip.traffic_d100, prev)
    for ep in range(episodes):
        a = agent.act(s) if policy == "q" else int(pol_rng.integers(len(ACTIONS)))
        fb = user.feedback(trip, cls, soc, a)
        tmin = min(trip.time)
        delay = (trip.time[a] - tmin) / tmin if tmin > 0 else 0.0
        r = reward(fb, trip.comfort[a], delay)
        rewards[ep] = r
        trip, cls, soc = sample()
        s_next = encode_state(cls, soc, trip.traffic_d100, a)
        if policy == "q":
            agent.update(s, a, r, s_next)
        s = s_next
    return rewards
