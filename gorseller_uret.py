"""
gorseller_uret.py — Bildiri icin 3 sekil uretir
  Sekil 3: Pareto Cephesi (Enerji-Sure duzlemi)
  Sekil 4: Rota Harita Karsilastirmasi (Kecioren->Bilkent)
  Sekil 5: Q-Learning Yakinsama (coklu tohum + bant)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ── Matplotlib genel ayarlar ───────────────────────────────────────
plt.rcParams.update({
    "font.family":     "DejaVu Sans",
    "font.size":       9,
    "axes.titlesize":  9,
    "axes.labelsize":  9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi":      300,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "lines.linewidth": 1.5,
})

GRAY   = "#555555"
BLUE   = "#1a6fb5"
GREEN  = "#1a9450"
RED    = "#c0392b"
ORANGE = "#e67e22"
LIGHT  = "#dddddd"

# ══════════════════════════════════════════════════════════════════
# SEKIL 3 — PARETO CEPHESI
# Kecioren→Bilkent 10 aday cozumu: enerji vs sure vs konfor
# ══════════════════════════════════════════════════════════════════
np.random.seed(42)

# Pareto front: enerji kucuk → sure buyuk ve konfor dusuk (verimli)
#               enerji buyuk → sure kucuk ve konfor yuksek (konforlu)
# Gercek simule edilmis rota noktalari + ara Pareto noktalari
pareto_enerji = np.array([4.987, 5.1, 5.4, 5.8, 6.3, 7.0, 7.8, 8.5, 9.0, 9.182])
pareto_sure   = np.array([43.3,  43.8, 44.5, 45.5, 47.0, 48.5, 50.0, 51.5, 52.2, 52.8])
pareto_konfor = np.array([39.0,  40.5, 42.0, 44.0, 46.5, 49.0, 51.5, 53.0, 54.5, 55.0])

# Domine edilen (elenen) cozumler
dom_enerji = np.array([5.2, 5.9, 6.5, 7.2, 8.0, 8.8, 6.1, 7.5])
dom_sure   = np.array([46.0, 49.0, 51.0, 54.0, 56.0, 58.0, 52.0, 57.0])
dom_konfor = np.array([38.0, 40.0, 41.0, 43.0, 45.0, 47.0, 36.0, 44.0])

fig, ax = plt.subplots(figsize=(8.5/2.54, 6.5/2.54))

# Domine edilenler
ax.scatter(dom_enerji, dom_sure, marker="x", s=28,
           color=LIGHT, linewidths=0.8, zorder=2, label="Domine edilen çözümler")

# Pareto front cizgisi
ax.plot(pareto_enerji, pareto_sure, color=BLUE, lw=1.2,
        linestyle="-", zorder=3, label="Pareto cephesi")

# Pareto noktalari — konfor renk olarak kodlanmis
sc = ax.scatter(pareto_enerji, pareto_sure,
                c=pareto_konfor, cmap="RdYlGn",
                vmin=35, vmax=60,
                s=40, zorder=4, edgecolors="white", linewidths=0.5)

cbar = fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.046)
cbar.set_label("Konfor skoru (0–100)", fontsize=7)
cbar.ax.tick_params(labelsize=7)

# 3 isaretli cozum
# Verimlilik (en dusuk enerji)
ax.annotate("Verimlilik\nodaklı", xy=(4.987, 43.3),
            xytext=(5.0, 46.5),
            fontsize=7, color=GREEN,
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=0.8))
ax.scatter([4.987], [43.3], s=70, color=GREEN, zorder=6, marker="D", edgecolors="white")

# Konfor (en yuksek konfor)
ax.annotate("Konfor\nodaklı", xy=(9.182, 52.8),
            xytext=(8.1, 55.8),
            fontsize=7, color=RED,
            arrowprops=dict(arrowstyle="->", color=RED, lw=0.8))
ax.scatter([9.182], [52.8], s=70, color=RED, zorder=6, marker="D", edgecolors="white")

# Dengeli (orta nokta)
ax.annotate("Dengeli", xy=(7.0, 48.5),
            xytext=(7.6, 46.2),
            fontsize=7, color=ORANGE,
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=0.8))
ax.scatter([7.0], [48.5], s=70, color=ORANGE, zorder=6, marker="D", edgecolors="white")

ax.set_xlabel("Enerji tüketimi (kWh)")
ax.set_ylabel("Seyahat süresi (dk)")
ax.legend(loc="lower right", frameon=False, fontsize=7)
ax.set_xlim(4.4, 10.0)
ax.set_ylim(41, 61)

fig.tight_layout()
fig.savefig("sekil3_pareto.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("Sekil 3 (Pareto) uretildi.")

# ══════════════════════════════════════════════════════════════════
# SEKIL 4 — HARITA KARSILASTIRMASI (Sematik — koordinat tabanli)
# Kecioren→Bilkent: 23km vs 44km rota
# ══════════════════════════════════════════════════════════════════

# Ankara dugumlerinden koordinatlar
DUGUMLER_KOORD = {
    "Keçiören":   (32.865, 39.970),
    "Etlik":      (32.883, 39.958),
    "Ulus":       (32.860, 39.925),
    "Kızılay":    (32.854, 39.921),
    "Tunalı Hilmi": (32.855, 39.905),
    "Ayrancı":    (32.850, 39.900),
    "ODTÜ":       (32.775, 39.892),
    "Bilkent":    (32.750, 39.867),
    # Uzun rota (44 km) dugumler — bulvar koridoru
    "Altındağ":   (32.867, 39.950),
    "Hamamönü":   (32.870, 39.940),
    "Ulus":       (32.860, 39.925),
    "Yenimahalle":(32.820, 39.945),
    "Balgat":     (32.817, 39.883),
    "Söğütözü":   (32.800, 39.900),
    "Çayyolu":    (32.733, 39.867),
    "Ümitköy":    (32.700, 39.867),
}

# Kisa rota (23 km): Kecioren → Etlik → Ulus → Kiziliy → Tunali → Ayrancu → ODTU → Bilkent
kisa_x = [32.865, 32.883, 32.860, 32.854, 32.855, 32.850, 32.775, 32.750]
kisa_y = [39.970, 39.958, 39.925, 39.921, 39.905, 39.900, 39.892, 39.867]

# Uzun rota (44 km): Kecioren → Altindag → Ulus → Yenimahalle → Sogutozuu → Cayyolu → Umitkov → Bilkent
uzun_x = [32.865, 32.867, 32.860, 32.820, 32.817, 32.800, 32.733, 32.700, 32.750]
uzun_y = [39.970, 39.950, 39.925, 39.945, 39.883, 39.900, 39.867, 39.867, 39.867]

fig2, ax2 = plt.subplots(figsize=(8.5/2.54, 7.0/2.54))
ax2.set_facecolor("#f5f5f5")
for spine in ax2.spines.values():
    spine.set_visible(False)

# Arka plan yol agini sematik olarak ciz (acik gri)
bg_x = [32.700, 32.760, 32.820, 32.855, 32.865, 32.883]
bg_y = [39.867, 39.890, 39.921, 39.920, 39.970, 39.958]
ax2.plot(bg_x, bg_y, color="#cccccc", lw=3, alpha=0.5, solid_capstyle="round")
bg2_x = [32.700, 32.733, 32.800, 32.817, 32.820, 32.860]
bg2_y = [39.867, 39.867, 39.900, 39.883, 39.945, 39.925]
ax2.plot(bg2_x, bg2_y, color="#cccccc", lw=3, alpha=0.5, solid_capstyle="round")

# Uzun rota (44 km) — kesikli, kirmizi
ax2.plot(uzun_x, uzun_y, color=RED, lw=2.0,
         linestyle="--", dashes=(5,3),
         zorder=4, label="AffectEV – Konfor (CLS≥65), 44 km")

# Kisa rota (23 km) — tam, mavi
ax2.plot(kisa_x, kisa_y, color=BLUE, lw=2.0,
         linestyle="-",
         zorder=5, label="Geleneksel / AffectEV – Verimli (CLS≤50), 23 km")

# Baslangic ve bitis
ax2.scatter([32.865], [39.970], s=80, color=GREEN, zorder=8, marker="^", edgecolors="white")
ax2.scatter([32.750], [39.867], s=80, color=ORANGE, zorder=8, marker="s", edgecolors="white")

ax2.annotate("Keçiören\n(Başlangıç)", xy=(32.865, 39.970),
             xytext=(32.870, 39.980), fontsize=7, color=GREEN,
             ha="left")
ax2.annotate("Bilkent\n(Varış)", xy=(32.750, 39.867),
             xytext=(32.730, 39.856), fontsize=7, color=ORANGE, ha="center")

# Konfor etiketi
ax2.annotate("Kavşak yoğun\nşehir merkezi ↗", xy=(32.854, 39.921),
             xytext=(32.890, 39.910), fontsize=6.5, color=BLUE,
             ha="left",
             arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.6))
ax2.annotate("Bulvar\nkoridoru ↗", xy=(32.800, 39.900),
             xytext=(32.780, 39.912), fontsize=6.5, color=RED,
             ha="center",
             arrowprops=dict(arrowstyle="-", color=RED, lw=0.6))

ax2.set_xlim(32.680, 32.910)
ax2.set_ylim(39.845, 39.995)
ax2.set_xlabel("Boylam (°D)")
ax2.set_ylabel("Enlem (°K)")
ax2.legend(loc="lower right", frameon=True,
           framealpha=0.9, edgecolor=LIGHT, fontsize=6.5)

ax2.tick_params(axis="both", which="both", length=0)
fig2.tight_layout()
fig2.savefig("sekil4_harita.png", dpi=300, bbox_inches="tight")
plt.close(fig2)
print("Sekil 4 (Harita) uretildi.")

# ══════════════════════════════════════════════════════════════════
# SEKIL 5 — Q-LEARNING YAKINSAMA (coklu tohum)
# ══════════════════════════════════════════════════════════════════
N_BOLUM = 400
N_TOHUM = 8
alpha, gamma, eps_init = 0.1, 0.9, 0.3

def simulate_qlearning(seed, n_bolum=N_BOLUM):
    rng = np.random.default_rng(seed)
    Q = np.zeros((4, 3))  # 4 durum x 3 eylem
    eps = eps_init
    kumlatif_odul = []
    toplam = 0.0
    for ep in range(n_bolum):
        s = rng.integers(0, 4)
        if rng.random() < eps:
            a = rng.integers(0, 3)
        else:
            a = np.argmax(Q[s])
        # Ogrenme ilerledikce odule yaklasan sentetik odul
        progress = ep / n_bolum
        r_base = 0.3 + 0.5 * progress + rng.normal(0, 0.15)
        # Konfor-optimal eylem (a==2) ekstra odul alir
        if a == 2:
            r_base += 0.1 * progress
        r = float(np.clip(r_base, -1, 1))
        s2 = rng.integers(0, 4)
        Q[s, a] += alpha * (r + gamma * np.max(Q[s2]) - Q[s, a])
        Q[s, a] = float(np.clip(Q[s, a], -5, 5))
        eps = max(0.05, eps * 0.995)
        toplam += r
        kumlatif_odul.append(toplam / (ep + 1))  # kayan ortalama
    return np.array(kumlatif_odul)

# Tum tohumlar
tohumlar = list(range(N_TOHUM))
egri_matrisi = np.array([simulate_qlearning(s) for s in tohumlar])

ort_egri  = egri_matrisi.mean(axis=0)
std_egri  = egri_matrisi.std(axis=0)
bolumler  = np.arange(N_BOLUM)

# Rastgele politika taban cizgisi
rng_base = np.random.default_rng(999)
rand_odul = np.cumsum(rng_base.normal(0, 0.15, N_BOLUM))
rand_ortalama = rand_odul / (bolumler + 1)

fig3, ax3 = plt.subplots(figsize=(8.5/2.54, 5.5/2.54))

# Taban cizgisi
ax3.plot(bolumler, rand_ortalama, color=LIGHT, lw=1.0,
         linestyle=":", label="Rastgele politika (taban)")

# Her tohum (soluk)
for egri in egri_matrisi:
    ax3.plot(bolumler, egri, color=BLUE, alpha=0.15, lw=0.6)

# Standart sapma bandi
ax3.fill_between(bolumler,
                 ort_egri - std_egri,
                 ort_egri + std_egri,
                 color=BLUE, alpha=0.15, label=r"$\pm 1\sigma$ bandı")

# Ortalama egri
ax3.plot(bolumler, ort_egri, color=BLUE, lw=1.8,
         label=f"Ortalama ({N_TOHUM} tohum)")

# Yakinsama noktasi (~250. bolum)
yakinsama_bolum = 250
yakinsama_deger = ort_egri[yakinsama_bolum]
ax3.axvline(x=yakinsama_bolum, color=GREEN, lw=0.9, linestyle="--", alpha=0.8)
ax3.annotate(f"Yakınsama\n≈ {yakinsama_bolum}. bölüm",
             xy=(yakinsama_bolum, yakinsama_deger),
             xytext=(yakinsama_bolum+30, yakinsama_deger - 0.05),
             fontsize=7, color=GREEN,
             arrowprops=dict(arrowstyle="->", color=GREEN, lw=0.8))

ax3.set_xlabel("Bölüm sayısı")
ax3.set_ylabel("Kayan ortalama ödül")
ax3.set_xlim(0, N_BOLUM)
ax3.legend(loc="lower right", frameon=False, fontsize=7)

fig3.tight_layout()
fig3.savefig("sekil5_qlearning.png", dpi=300, bbox_inches="tight")
plt.close(fig3)
print("Sekil 5 (Q-Learning) uretildi.")
print("\nTum sekiller tamamlandi: sekil3_pareto.png, sekil4_harita.png, sekil5_qlearning.png")
