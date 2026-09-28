"""
Bildirideki tüm sonuçları sırayla yeniden üretir:
  1) 50 senaryo × 10 tohum deneyi       → results/raw_runs.csv
  2) Tablo 2 ve Tablo 3                  → results/tablo2.md, tablo3.md, summary.json
  3) Örnek vaka: Tablo 4, Şekil 1, Şekil 3
  4) Q-Learning deneyi: Şekil 2

Kullanım:  python experiments/run_all.py
(2 çekirdekli bir bilgisayarda yaklaşık 10–15 dakika sürer.)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for script in ("run_experiments.py", "make_tables.py", "case_study.py", "qlearning_experiment.py"):
    print(f"\n=== {script} ===", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)] + sys.argv[1:] * (script == "run_experiments.py"))
    if r.returncode != 0:
        sys.exit(r.returncode)
print("\nTüm sonuçlar results/ klasöründe.")
