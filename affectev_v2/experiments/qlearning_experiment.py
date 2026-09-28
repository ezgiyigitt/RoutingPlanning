"""
Şekil 2: Q-Learning bölüm başına ödül eğrisi (1000 bölüm, 10 tohum, ±1 std) ve
rastgele politika taban çizgisi.

Seyahat havuzu, ana deneyin D-NSGA-II çıktılarından (results/trip_options.json) gelir:
her seyahat, gerçek bir (senaryo, tohum) çalıştırmasının Konfor/Dengeli/Verimlilik
rotalarının enerji, süre ve konfor değerleridir.

Çıktılar: results/sekil2_qlearning.png, results/qlearning_summary.json, results/qlearning_rewards.npz
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from affectev.config import QL  # noqa: E402
from affectev.qlearning import ACTIONS, TripOption, run_training  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
WINDOW = 50

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "savefig.dpi": 300})


def load_trips():
    with open(os.path.join(RESULTS, "trip_options.json"), encoding="utf-8") as f:
        raw = json.load(f)
    return [TripOption(energy=tuple(t[a]["energy"] for a in ACTIONS), time=tuple(t[a]["time"] for a in ACTIONS),
                       comfort=tuple(t[a]["comfort"] for a in ACTIONS), traffic_d100=t["traffic_d100"]) for t in raw]


def moving_avg(x, w=WINDOW):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.empty_like(x)
    for i in range(len(x)):
        lo = max(0, i - w + 1)
        out[i] = (c[i + 1] - c[lo]) / (i + 1 - lo)
    return out


def main():
    trips = load_trips()
    Rq = np.array([run_training(trips, seed=s, episodes=QL.episodes, policy="q") for s in range(QL.seeds)])
    Rr = np.array([run_training(trips, seed=s, episodes=QL.episodes, policy="random") for s in range(QL.seeds)])
    np.savez(os.path.join(RESULTS, "qlearning_rewards.npz"), q=Rq, random=Rr)
    Mq = np.array([moving_avg(r) for r in Rq])
    Mr = np.array([moving_avg(r) for r in Rr])
    mq, sq = Mq.mean(0), Mq.std(0)
    mr = Mr.mean(0)
    ep = np.arange(1, QL.episodes + 1)

    fig, ax = plt.subplots(figsize=(8.5 / 2.54, 6.5 / 2.54))
    ax.fill_between(ep, mq - sq, mq + sq, color="0.8", lw=0, label=f"± 1 std (n = {QL.seeds} tohum)")
    ax.plot(ep, mq, c="k", lw=1.4, label="AffectEV Q-Learning (ortalama)")
    ax.plot(ep, mr, c="k", lw=0.9, ls=":", label="Rastgele politika (taban)")
    ax.set_xlabel("Eğitim bölümü")
    ax.set_ylabel(f"Bölüm başına ödül\n({WINDOW} bölümlük hareketli ort.)")
    ax.set_xlim(0, QL.episodes)
    ax.grid(alpha=0.25, lw=0.4)
    ax.legend(fontsize=6, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "sekil2_qlearning.png"), bbox_inches="tight")
    plt.close(fig)

    last = slice(QL.episodes - 200, QL.episodes)
    first = slice(0, 100)
    summ = {
        "episodes": QL.episodes, "seeds": QL.seeds, "n_trips": len(trips),
        "q_first100_mean": float(Rq[:, first].mean()), "q_last200_mean": float(Rq[:, last].mean()),
        "q_last200_sd_across_seeds": float(Rq[:, last].mean(1).std(ddof=1)),
        "random_mean": float(Rr.mean()),
        "improvement_over_random_last200": float(Rq[:, last].mean() - Rr[:, last].mean()),
        "episode_ma_exceeds_random_by_1sd_first": int(np.argmax(mq - sq > mr)) + 1,
    }
    with open(os.path.join(RESULTS, "qlearning_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=2)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
