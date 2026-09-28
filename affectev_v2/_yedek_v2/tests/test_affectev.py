"""AffectEV birim testleri — her test bildirideki bir denklemi veya parametreyi doğrular.
Çalıştırma:  python -m pytest -q tests   (veya: python tests/test_affectev.py)
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from affectev.config import CLSP, COMFORT, NSGA, QL, VEHICLE  # noqa: E402
from affectev.models import (charge_time_min, cls_weights, cognitive_load_score, comfort_score,  # noqa: E402
                             energy_components_j, make_traffic, route_metrics, soc_final)
from affectev.network import load_network  # noqa: E402
from affectev.nsga2 import (DNSGA2, crowding_distance, fast_non_dominated_sort, remove_loops,  # noqa: E402
                            weighted_choice)
from affectev.qlearning import QAgent, reward  # noqa: E402
from affectev.routing import astar_time, shortest_path  # noqa: E402


def test_table1_parameters():
    assert (VEHICLE.Cd, VEHICLE.m, VEHICLE.A, VEHICLE.Cr, VEHICLE.soc_min) == (0.23, 1847.0, 2.22, 0.01, 20.0)
    assert (NSGA.population, NSGA.generations, NSGA.crossover_rate, NSGA.mutation_rate) == (100, 50, 0.8, 0.1)
    assert (QL.alpha, QL.gamma, QL.epsilon) == (0.1, 0.9, 0.1)
    assert (CLSP.lambda_f, CLSP.lambda_c, CLSP.lambda_v) == (0.40, 0.40, 0.20)
    assert (COMFORT.w_intersection, COMFORT.w_stop, COMFORT.w_traffic) == (0.50, 0.30, 0.20)
    assert (QL.theta1, QL.theta2, QL.theta3) == (10.0, 5.0, 5.0)
    assert (QL.episodes, QL.seeds) == (1000, 10)


def test_eq1_cls():
    assert abs(cognitive_load_score(50, 100, 0) - (0.4 * 50 + 0.4 * 100)) < 1e-9


def test_table3_weights():
    assert cls_weights(15) == (0.50, 0.40, 0.10)
    assert cls_weights(30) == (0.40, 0.35, 0.25)
    assert cls_weights(50) == (0.28, 0.22, 0.50)
    assert cls_weights(65) == (0.13, 0.10, 0.77)
    assert cls_weights(85) == (0.08, 0.07, 0.85)


def test_eq2_comfort():
    assert abs(comfort_score(10, 20, 50) - (100 - (0.5 * 10 + 0.3 * 20 + 0.2 * 50))) < 1e-9


def test_eq3_energy_components():
    d, v, n = 1000.0, 50 / 3.6, 2.0
    drag, roll, acc, aux = energy_components_j(d, v, n)
    assert abs(drag - 0.5 * 1.2 * 0.23 * 2.22 * v ** 2 * d) < 1e-6
    assert abs(roll - 0.01 * 1847 * 9.81 * d) < 1e-6
    assert abs(acc - 1847 * n * 0.5 * v ** 2) < 1e-6          # m·a·d, a·d = ½v² her kalkış için
    assert abs(aux - 1500 * d / v) < 1e-6


def test_eq4_eq5_soc():
    assert abs(soc_final(75.0, [6.0]) - (75.0 - 100 * 6.0 / VEHICLE.C_batt_kwh)) < 1e-9
    assert abs(soc_final(15.0, [3.0], [65.0]) - (15 - 5 + 65)) < 1e-9
    assert abs(charge_time_min(20.0) - (0.60 * VEHICLE.C_batt_kwh / VEHICLE.P_charge_kw * 60)) < 1e-9


def test_eq7_eq8_qlearning():
    assert abs(reward(0.5, 80.0, 0.1) - (10 * 0.5 + 5 * 0.8 - 5 * 0.1)) < 1e-9
    ag = QAgent(np.random.default_rng(0))
    s, s2 = (0, 0, 0, 3), (1, 1, 1, 0)
    ag.Q[s2 + (2,)] = 4.0
    ag.update(s, 1, 2.0, s2)
    assert abs(ag.Q[s + (1,)] - 0.1 * (2.0 + 0.9 * 4.0)) < 1e-9


def test_non_dominated_sort_and_crowding():
    F = np.array([[1, 5, 0], [2, 4, 0], [3, 3, 0], [2, 5, 0], [4, 4, 0]], float)
    fr = fast_non_dominated_sort(F)
    assert sorted(fr[0]) == [0, 1, 2] and sorted(fr[1]) == [3, 4] and len(fr) == 2
    cd = crowding_distance(F[[0, 1, 2]])
    assert np.isinf(cd[0]) and np.isinf(cd[2]) and np.isfinite(cd[1])


def test_remove_loops():
    assert remove_loops([1, 2, 3, 2, 4]) == [1, 2, 4]
    assert remove_loops([1, 2, 3, 4, 2, 5, 3, 6]) == [1, 2, 5, 3, 6]


def test_astar_is_optimal_and_nsga_valid():
    net = load_network()
    tr = make_traffic(net, 0)
    rng = np.random.default_rng(1)
    for _ in range(3):
        s, t = (int(x) for x in rng.integers(net.n_nodes, size=2))
        a = astar_time(net, tr, s, t)
        d = shortest_path(net, tr.time_s, s, t)
        ta = tr.time_s[net.path_edges(a)].sum()
        td = tr.time_s[net.path_edges(d)].sum()
        assert abs(ta - td) < 1e-6, "A* en hızlı rotayı bulmalı"
    s, t = int(net.nearest_node(39.998, 32.864)), int(net.nearest_node(39.870, 32.748))
    opt = DNSGA2(net, tr, np.random.default_rng(0))
    res = opt.run(s, t, generations=10)
    F = np.array([p.obj for p in res.front])
    assert len(fast_non_dominated_sort(F)[0]) == len(F), "Cephe kendi içinde baskılanmamış olmalı"
    for ind in res.population:
        assert ind.path[0] == s and ind.path[-1] == t
        assert len(set(ind.path)) == len(ind.path)
        net.path_edges(list(ind.path))  # geçersiz kenar varsa KeyError
        m = route_metrics(net, tr, net.path_edges(list(ind.path)))
        assert abs(m.energy_kwh - ind.obj[0]) < 1e-9 and abs(100 - m.comfort - ind.obj[2]) < 1e-9
    # Yüksek CLS seçimi, düşük CLS seçimine göre konforu azaltmamalı
    lo = res.front[weighted_choice(res.front, cls_weights(15))]
    hi = res.front[weighted_choice(res.front, cls_weights(85))]
    assert hi.metrics.comfort >= lo.metrics.comfort - 1e-9


def test_face_summary_mapping():
    """Yüz okuma özeti: F = kapalı göz oranı x100, V = 50 x (1 - gülümseme oranı) (CNN yoksa)."""
    from affectev.face import summarize
    frames = [{"face": True, "eyes_open": False, "smile": False}] * 3 + \
             [{"face": True, "eyes_open": True, "smile": True}] * 1 + [{"face": False}]
    r = summarize(frames)
    assert r["ok"] and r["face_frames"] == 4 and r["frames"] == 5
    assert abs(r["fatigue"] - 75.0) < 1e-9 and abs(r["valence_negative"] - 37.5) < 1e-9
    assert summarize([{"face": False}])["ok"] is False


def test_display_options_distinct():
    """Arayüzdeki üç seçenek farklı rotalar olmalı ve önerilen seçenek CLS'ye göre belirlenmeli."""
    from affectev.options import display_options, overlap
    net = load_network()
    tr = make_traffic(net, 0)
    s, t = int(net.nearest_node(39.9208, 32.8541)), int(net.nearest_node(39.8750, 32.6850))
    res = DNSGA2(net, tr, np.random.default_rng(0)).run(s, t, generations=15)
    o = display_options(net, res.front, cls_weights(85))
    ind = o["individuals"]
    assert len({ind[k].path for k in ind}) == 3, "üç seçenek farklı güzergâh olmalı"
    assert ind["Verimlilik"].obj[0] <= min(ind[k].obj[0] for k in ind) + 1e-9
    assert ind["Konfor"].obj[2] <= ind["Verimlilik"].obj[2] + 1e-9
    assert o["recommended"] in ind


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"FAIL  {name}: {e!r}")
    sys.exit(1 if fails else 0)
