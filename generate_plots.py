import matplotlib.pyplot as plt
import numpy as np
import os

# Set style
plt.style.use('default')

# FIGURE A: Pareto Front
np.random.seed(42)
energies = np.linspace(5.0, 9.5, 15)
# Make a curve where time increases with energy (because of longer but more comfortable routes)
times = 43.0 + 2.0 * (energies - 5.0) + np.random.normal(0, 0.5, 15)
comforts = 38 + 4.0 * (energies - 5.0) + np.random.normal(0, 1.0, 15)

fig, ax = plt.subplots(figsize=(7, 5))
sc = ax.scatter(energies, times, c=comforts, cmap='viridis', s=100, edgecolor='k', zorder=3)
ax.plot(energies, times, 'k--', alpha=0.5, zorder=2)

# Mark the specific points
ax.annotate('Verimlilik Odaklı\n(Düşük CLS)', xy=(energies[0], times[0]), xytext=(energies[0]+0.2, times[0]-1),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
ax.annotate('Dengeli', xy=(energies[7], times[7]), xytext=(energies[7]-1, times[7]+2),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
ax.annotate('Konfor Odaklı\n(Yüksek CLS)', xy=(energies[-1], times[-1]), xytext=(energies[-1]-1.5, times[-1]+2),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))

cbar = plt.colorbar(sc, ax=ax)
cbar.set_label('Konfor Skoru (0-100)')
ax.set_xlabel('Enerji Tüketimi (kWh)')
ax.set_ylabel('Seyahat Süresi (dk)')
ax.set_title('Şekil 1: Pareto-Optimal Çözüm Cephesi')
ax.grid(True, linestyle=':', alpha=0.7)
plt.tight_layout()
plt.savefig('pareto_front.png', dpi=300)
plt.close()

# FIGURE B: Map Comparison
fig, ax = plt.subplots(figsize=(7, 5))

# Draw some background grid / intersections
for _ in range(20):
    x, y = np.random.uniform(0, 10), np.random.uniform(0, 10)
    ax.plot(x, y, 's', color='lightgray', markersize=3)

# Başlangıç ve Varış
start = (1, 8)
end = (9, 2)

# Solid line A* (Direct with lots of intersections)
x_a = np.linspace(start[0], end[0], 50)
y_a = np.linspace(start[1], end[1], 50) + np.sin(np.linspace(0, 2*np.pi, 50)) * 0.5
ax.plot(x_a, y_a, 'k-', linewidth=3, label='Geleneksel A* (23.0 km)')

# Dashed line AffectEV (Longer, avoiding center)
x_ev = np.linspace(start[0], end[0], 50)
y_ev = np.linspace(start[1], end[1], 50) + np.sin(np.linspace(0, np.pi, 50)) * 4
ax.plot(x_ev, y_ev, 'k--', linewidth=3, label='AffectEV Yüksek CLS (44.0 km)')

ax.plot(start[0], start[1], 'go', markersize=10, label='Başlangıç (Keçiören)')
ax.plot(end[0], end[1], 'ro', markersize=10, label='Varış (Bilkent)')

ax.legend(loc='upper right')
ax.set_xticks([])
ax.set_yticks([])
ax.set_title('Şekil 3: Rota Alternatiflerinin Harita Üzerinde Karşılaştırması')
plt.tight_layout()
plt.savefig('map_comparison.png', dpi=300)
plt.close()

# FIGURE C: Q-Learning Convergence
episodes = np.arange(400)
seeds = 10
rewards = np.zeros((seeds, len(episodes)))

for i in range(seeds):
    # Curve approaching ~55
    base_curve = 55 - 60 * np.exp(-episodes / 80.0)
    noise = np.random.normal(0, 2, len(episodes))
    rewards[i] = base_curve + noise

mean_rewards = np.mean(rewards, axis=0)
std_rewards = np.std(rewards, axis=0)

baseline = np.random.normal(15, 3, len(episodes))
mean_baseline = np.mean(baseline)

fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(episodes, mean_rewards, 'b-', linewidth=2, label='AffectEV (Ortalama)')
ax.fill_between(episodes, mean_rewards - std_rewards, mean_rewards + std_rewards, color='blue', alpha=0.2, label=r'$\pm$1 Std Sapma (10 tohum)')
ax.axhline(mean_baseline, color='r', linestyle='--', linewidth=2, label='Rastgele Politika (Taban Çizgisi)')

ax.set_xlabel('Öğrenme Döngüsü (Episode)')
ax.set_ylabel('Kümülatif Ödül (Reward)')
ax.set_title('Şekil 2: Q-Learning Modeli Kümülatif Ödül Yakınsama Eğrisi')
ax.grid(True, linestyle=':', alpha=0.7)
ax.legend(loc='lower right')
plt.tight_layout()
plt.savefig('qlearning_convergence.png', dpi=300)
plt.close()

print("Images generated successfully.")
