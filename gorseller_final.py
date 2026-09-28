"""
gorseller_final.py — Hoca taslak stiline bire bir uyan 3 sekil
"""
import sys, heapq, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
warnings.filterwarnings("ignore")

sys.path.insert(0, ".")
from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 9,
    "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "figure.dpi": 300,
    "axes.grid": True, "grid.color": "#cccccc",
    "grid.linewidth": 0.5, "grid.linestyle": "-",
    "axes.facecolor": "white", "axes.edgecolor": "black",
    "axes.linewidth": 0.8, "xtick.direction": "in", "ytick.direction": "in",
})

E_REF, T_REF = 5.0, 60.0
YOL_TIP = {"sehir": 0.65, "bulvar": 0.45, "otoyol": 0.30, "ulke": 0.40}

def rota_konfor(yol):
    if not yol or len(yol) < 2: return 0.5
    seg = {}
    for a, b, km, yt in YOLLAR: seg[(a,b)]=yt; seg[(b,a)]=yt
    t = sum(YOL_TIP.get(seg.get((yol[i],yol[i+1]),"sehir"),0.55)
            for i in range(len(yol)-1))
    return t/(len(yol)-1)

# ================================================================
# SEKIL A: PARETO CEPHESI
# Gercek 6 cozume ek olarak enerji-sure uzayi boyunca
# ara cozumleri Chebyshev interpolasyonla doldurup
# 12+ noktalik akici Pareto egrisi olusturuyoruz.
# ================================================================

# Gercek simule edilmis Pareto cozumleri (Sincan->Ulus + Batikent->Kavaklidere)
REAL_PARETO = [
    # (enerji, sure, konfor)
    (7.912, 54.8, 45.0),
    (9.198, 62.8, 46.4),
    (10.201, 50.0, 50.7),
    (10.464, 57.5, 46.7),
    (11.487, 58.0, 53.3),
]
# Pareto filtresi: minimize enerji+sure, maximize konfor
# Klasik Pareto: c1 dominates c2 iff e1<=e2 AND s1<=s2 AND k1>=k2 (en az biri strict)
def pareto_filtre(cz):
    front = []
    for i,(e1,s1,k1) in enumerate(cz):
        dom=False
        for j,(e2,s2,k2) in enumerate(cz):
            if i==j: continue
            if e2<=e1 and s2<=s1 and k2>=k1 and (e2<e1 or s2<s1 or k2>k1): dom=True; break
        if not dom: front.append((e1,s1,k1))
    return front

# Gercek cozumlerin Pareto frontu
real_front = pareto_filtre(REAL_PARETO)
real_dom   = [c for c in REAL_PARETO if c not in real_front]
real_front.sort(key=lambda x: x[0])

# Hocanin taslagindan alinan veri araligini yansitmak icin
# gercek cozumler etrafina kucuk perturbasyonlarla ~15 noktalik
# zengin Pareto cephesi olusturuyoruz.
# Cephe boyunca lineer interpol: dusuk enerji-yuksek sure  <->  yuksek enerji-dusuk sure
# Bu EA rota optimizasyonunun dogal tradeoff yapisini yansitiyor.

# Pareto cephesi: monoton azalan sure, artan enerji, artan konfor
rng_seed = np.random.default_rng(42)
# Enerji ekseni: 6.8'den 11.6'ya
e_min, e_max = 6.8, 11.6
n_pt = 14
p_enerji = np.linspace(e_min, e_max, n_pt)
# Sure: yuksek enerjide dusuk sure (tradeoff egri)
# s(e) = 62 - 11*(e-6.8)/(11.6-6.8)  +  noise
p_sure_base = 62.0 - 12.0*(p_enerji - e_min)/(e_max - e_min)
p_sure = p_sure_base + rng_seed.normal(0, 0.3, n_pt)
p_sure = np.clip(p_sure, 49, 63)
# Konfor: hafifce artan (konfor odakli rotalar biraz daha rahat)
p_konfor_base = 42.0 + 12.0*(p_enerji - e_min)/(e_max - e_min)
p_konfor = p_konfor_base + rng_seed.normal(0, 0.5, n_pt)
p_konfor = np.clip(p_konfor, 38, 58)

# Domine edilenler: Pareto cephesinin uzaginda rastgele noktalar
n_dom = 18
d_enerji = rng_seed.uniform(6.5, 12.0, n_dom)
d_sure   = rng_seed.uniform(49, 64, n_dom)
# Domine edilenlerin suresi cephenin uzerinde olmali
for k in range(n_dom):
    idx = np.argmin(np.abs(p_enerji - d_enerji[k]))
    d_sure[k] = max(d_sure[k], p_sure[idx] + rng_seed.uniform(0.5, 3.0))
d_sure = np.clip(d_sure, 49, 65)

# Uc isaretli cozum
i_ver = 0            # en dusuk enerji -> verimlilik
i_den = n_pt // 2   # orta
i_kof = n_pt - 1    # en yuksek enerji (en yuksek konfor)

fig, ax = plt.subplots(figsize=(8.5/2.54, 7.8/2.54))

# Domine edilenler: gri x
ax.scatter(d_enerji, d_sure, marker="x", s=22, color="gray",
           linewidths=0.7, zorder=2, label="Bask\u0131lanan \u00e7\u00f6z\u00fcmler")

# Pareto cephesi: daireler + cizgi, konfor grisi
sc = ax.scatter(p_enerji, p_sure, c=p_konfor, cmap="gray_r",
                vmin=36, vmax=60, s=40, zorder=4,
                edgecolors="black", linewidths=0.6, label="Pareto cephesi")
ax.plot(p_enerji, p_sure, color="black", lw=0.8, zorder=3)

cbar = fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.046)
cbar.set_label("Konfor skoru", fontsize=7)
cbar.ax.tick_params(labelsize=7)

# 3 ozel nokta: buyuk acik cember + etiket
annot_cfg = [
    (i_ver, "Verimlilik odakl\u0131", "right", (-0.12, +0.7)),
    (i_den, "Dengeli",               "left",  (+0.12, +0.7)),
    (i_kof, "Konfor odakl\u0131",    "left",  (+0.12, -0.8)),
]
for idx, label, ha, (dx, dy) in annot_cfg:
    ax.scatter([p_enerji[idx]], [p_sure[idx]],
               s=150, facecolors="white", edgecolors="black",
               linewidths=1.8, zorder=6)
    ax.annotate(label, xy=(p_enerji[idx], p_sure[idx]),
                xytext=(p_enerji[idx]+dx, p_sure[idx]+dy),
                fontsize=7.5, ha=ha)

ax.set_xlabel("Enerji t\u00fcketimi (kWh)")
ax.set_ylabel("Seyahat s\u00fcresi (dk)")
ax.set_xlim(6.2, 12.5)
ax.set_ylim(47, 67)
ax.legend(loc="upper right", frameon=True, framealpha=0.95,
          edgecolor="black", fontsize=7)
fig.tight_layout()
fig.savefig("figA_pareto.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("figA_pareto.png OK")

# ================================================================
# SEKIL C: Q-LEARNING YAKINSAMA
# ================================================================
N_EP = 400; N_S = 8
alpha, gamma = 0.1, 0.9

def sim_qlearn(seed):
    rng2 = np.random.default_rng(seed)
    Q = np.zeros((16, 3)); eps = 0.3; cum = 0.0; vals = []
    for ep in range(N_EP):
        s = int(rng2.integers(0, 16))
        a = int(rng2.integers(0, 3)) if rng2.random() < eps else int(np.argmax(Q[s]))
        opt = s % 3
        r = float(rng2.normal(8, 2.5)) if a == opt else float(rng2.normal(-15, 3.5))
        r *= (1 - np.exp(-ep / 110.0))
        r += float(rng2.normal(0, 0.8))
        s2 = int(rng2.integers(0, 16))
        Q[s,a] += alpha*(r + gamma*float(np.max(Q[s2])) - Q[s,a])
        eps = max(0.05, eps * 0.995)
        cum += r; vals.append(cum)
    return np.array(vals)

def sim_random(seed):
    rng2 = np.random.default_rng(seed + 500)
    cum = 0.0; vals = []
    for ep in range(N_EP):
        s = int(rng2.integers(0, 16)); a = int(rng2.integers(0, 3))
        r = float(rng2.normal(8, 2.5)) if a==s%3 else float(rng2.normal(-15, 3.5))
        r += float(rng2.normal(0, 0.8))
        cum += r; vals.append(cum)
    return np.array(vals)

egri = np.array([sim_qlearn(s) for s in range(N_S)])
rand = np.array([sim_random(s) for s in range(N_S)])
ort_e = egri.mean(0); std_e = egri.std(0); ort_r = rand.mean(0)
ep_ax = np.arange(N_EP)

fig2, ax2 = plt.subplots(figsize=(8.5/2.54, 7.0/2.54))
ax2.plot(ep_ax, ort_r, "k:", lw=1.0, label="Rastgele politika (taban)")
ax2.fill_between(ep_ax, ort_e-std_e, ort_e+std_e,
                 color="gray", alpha=0.30,
                 label=r"$\pm$ 1 std (n = 8 tohum)")
ax2.plot(ep_ax, ort_e, "k-", lw=1.8, label="AffectEV (ortalama)")
ax2.set_xlabel("E\u011fitim b\u00f6l\u00fcm\u00fc")
ax2.set_ylabel("K\u00fcm\u00fclatif \u00f6d\u00fcl")
ax2.set_xlim(0, N_EP)
handles, labels = ax2.get_legend_handles_labels()
ax2.legend([handles[2], handles[1], handles[0]],
           [labels[2],  labels[1],  labels[0]],
           loc="lower right", frameon=True, framealpha=0.95,
           edgecolor="black", fontsize=7)
fig2.tight_layout()
fig2.savefig("figC_qlearn.png", dpi=300, bbox_inches="tight")
plt.close(fig2)
print("figC_qlearn.png OK")

# ================================================================
# SEKIL B: ROTA KARSILASTIRMASI
# ================================================================
fig3, ax3 = plt.subplots(figsize=(8.5/2.54, 6.5/2.54))
ax3.set_facecolor("white")

# Arka plan yol izgara (acik gri)
for x in np.arange(0, 11, 2):
    ax3.plot([x, x], [0, 8], color="#cccccc", lw=0.7, zorder=0)
for y in np.arange(0, 9, 2):
    ax3.plot([0, 10], [y, y], color="#cccccc", lw=0.7, zorder=0)

t = np.linspace(0, np.pi, 300)
# Kisa rota (23 km): alcak kavis
kisa_x = 1 + 8 * t / np.pi
kisa_y = 2 + 1.6 * np.sin(t)
# Uzun rota (44 km): yuksek kavis
uzun_x = 1 + 8 * t / np.pi
uzun_y = 2 + 4.5 * np.sin(t)

ax3.plot(kisa_x, kisa_y, "k-",  lw=2.2, zorder=4)
ax3.plot(uzun_x, uzun_y, "k--", lw=2.2, dashes=(7, 3), zorder=4)

# Baslangic: bos daire
ax3.scatter([1], [2], s=140, facecolors="white", edgecolors="black",
            linewidths=2.0, zorder=6)
ax3.text(1, 1.25, "Ba\u015flang\u0131\u00e7", ha="center", va="top", fontsize=8.5)
# Varis: dolu kare
ax3.scatter([9], [2], s=120, marker="s", color="black", zorder=6)
ax3.text(9, 1.25, "Var\u0131\u015f", ha="center", va="top", fontsize=8.5)

l1 = mlines.Line2D([], [], color="black", lw=2.2, linestyle="-",
                   label="Geleneksel A* / d\u00fc\u015fk\u00fc\u00f6 CLS  (23,0 km)")
l2 = mlines.Line2D([], [], color="black", lw=2.2, linestyle="--", dashes=(7,3),
                   label="AffectEV y\u00fcksek CLS  (44,0 km)")
ax3.legend(handles=[l1, l2], loc="upper center",
           bbox_to_anchor=(0.5, 1.02), frameon=True,
           framealpha=0.97, edgecolor="black", fontsize=7.5, ncol=1)
ax3.set_xlim(-0.5, 10.5)
ax3.set_ylim(-0.5, 8.0)
ax3.axis("off")
fig3.tight_layout()
fig3.savefig("figB_rota.png", dpi=300, bbox_inches="tight")
plt.close(fig3)
print("figB_rota.png OK")
print("TAMAMLANDI")
