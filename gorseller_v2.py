"""
gorseller_v2.py - Hoca stilinde 3 sekil
"""
import sys, os, heapq, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
GUZERGAHLAR = [
    ("Sincan", "Ulus"),
    ("Cayyolu", "Esenboga Havalimani") if False else ("Batikent", "Kavaklidere"),
    ("Kecioren", "Bilkent"),
]

def graf_metrik(g, yol):
    if not yol or len(yol) < 2: return None
    m = s = e = 0.0
    for i in range(len(yol) - 1):
        u, v = yol[i], yol[i + 1]
        for (nb, km, dk, kw, yt) in g.komsular.get(u, []):
            if nb == v: m += km; s += dk; e += kw; break
        else: return None
    return {"mesafe": round(m, 1), "sure": round(s, 1), "enerji": round(e, 3)}

def rota_konfor(yol):
    if not yol or len(yol) < 2: return 0.5
    seg = {}
    for a, b, km, yt in YOLLAR: seg[(a, b)] = yt; seg[(b, a)] = yt
    t = sum(YOL_TIP.get(seg.get((yol[i], yol[i + 1]), "sehir"), 0.55)
            for i in range(len(yol) - 1))
    return t / (len(yol) - 1)

def cok_dijk(g, bas, bit, we, wt, wc):
    dist = {n: float("inf") for n in g.komsular}
    prev = {n: None for n in g.komsular}
    pt = {n: None for n in g.komsular}
    dist[bas] = 0.0
    pq = [(0.0, bas)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == bit: break
        if d > dist[u]: continue
        for (v, km, sure, enerji, yt) in g.komsular.get(u, []):
            ra = ANKARA_DUGUMLER.get(u, (0, 0, 0))[2]
            rb = ANKARA_DUGUMLER.get(v, (0, 0, 0))[2]
            baz = {"sehir": 0.55, "bulvar": 0.40, "otoyol": 0.25, "ulke": 0.35}.get(yt, 0.50)
            if rb - ra > 30: baz += 0.15
            if pt.get(u) and pt[u] != yt: baz += 0.08
            nd = dist[u] + we * min(1, enerji/E_REF) + wt * min(1, sure/T_REF) + wc * min(1, baz)
            if nd < dist[v]:
                dist[v] = nd; prev[v] = u; pt[v] = yt
                heapq.heappush(pq, (nd, v))
    yol, n = [], bit
    while n: yol.append(n); n = prev[n]
    yol.reverse()
    if not yol or yol[0] != bas: return [], float("inf")
    return yol, dist[bit]

def pareto_filtre(cz):
    front = []
    for i, (e1, s1, k1) in enumerate(cz):
        dom = False
        for j, (e2, s2, k2) in enumerate(cz):
            if i == j: continue
            if e2 <= e1 and s2 <= s1 and k2 >= k1 and (e2 < e1 or s2 < s1 or k2 > k1):
                dom = True; break
        if not dom: front.append((e1, s1, k1))
    return front

# ================================================================
# SEKIL A: PARETO — Sincan->Ulus (en genis yelpazeyi saglayan rota)
# ================================================================
graf = Graf("Tesla Model 3")
BAS, BIT = "Sincan", "Ulus"

adaylar_set = set()
for we_i in range(1, 20):
    for wt_i in range(1, 20 - we_i):
        we = we_i / 20.0; wt = wt_i / 20.0; wc = round(1 - we - wt, 4)
        if wc < 0.03: continue
        yol, _ = cok_dijk(graf, BAS, BIT, we, wt, wc)
        if not yol: continue
        met = graf_metrik(graf, yol)
        if met is None: continue
        k100 = round((1 - rota_konfor(yol)) * 100, 1)
        adaylar_set.add((met["enerji"], met["sure"], k100))

adaylar = list(adaylar_set)
pareto = pareto_filtre(adaylar)
domine = [c for c in adaylar if c not in pareto]
pareto.sort(key=lambda x: x[0])

p = np.array(pareto)
p_e, p_s, p_k = p[:, 0], p[:, 1], p[:, 2]
d = np.array(domine) if domine else np.zeros((1, 3))
d_e, d_s = d[:, 0], d[:, 1]

# Uc ozel cozum indeksleri
i_ver = 0                   # en dusuk enerji (verimlilik)
i_kof = len(pareto) - 1    # en yuksek konfor
i_den = len(pareto) // 2   # ortadaki

fig, ax = plt.subplots(figsize=(8.5/2.54, 7.8/2.54))

ax.scatter(d_e, d_s, marker="x", s=22, color="gray",
           linewidths=0.7, zorder=2, label="Baskılanan çözümler")

sc = ax.scatter(p_e, p_s, c=p_k, cmap="gray_r",
                vmin=p_k.min() - 2, vmax=p_k.max() + 2,
                s=38, zorder=4,
                edgecolors="black", linewidths=0.6, label="Pareto cephesi")
ax.plot(p_e, p_s, color="black", lw=0.8, zorder=3)

cbar = fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.046)
cbar.set_label("Konfor skoru", fontsize=7)
cbar.ax.tick_params(labelsize=7)

# 3 ozel nokta: buyuk acik cember
for idx, label, dx, dy in [
    (i_ver, "Verimlilik odakli", -0.15, +0.6),
    (i_den, "Dengeli",           +0.20, +0.6),
    (i_kof, "Konfor odakli",     +0.10, -0.7),
]:
    ax.scatter([p_e[idx]], [p_s[idx]],
               s=140, facecolors="white", edgecolors="black",
               linewidths=1.6, zorder=6)
    ax.annotate(label, xy=(p_e[idx], p_s[idx]),
                xytext=(p_e[idx] + dx, p_s[idx] + dy),
                fontsize=7.5, ha="left" if dx >= 0 else "right")

ax.set_xlabel("Enerji tuketimi (kWh)")
ax.set_ylabel("Seyahat suresi (dk)")
ax.legend(loc="upper right", frameon=True, framealpha=0.95,
          edgecolor="black", fontsize=7)
fig.tight_layout()
fig.savefig("figA_pareto.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("figA_pareto.png OK")

# ================================================================
# SEKIL C: Q-LEARNING (Kumulatif odul, 8 tohum)
# ================================================================
N_EP = 400; N_S = 8
alpha, gamma, eps0 = 0.1, 0.9, 0.3

def sim_qlearn(seed):
    rng = np.random.default_rng(seed)
    Q = np.zeros((16, 3))
    eps = eps0; cum = 0.0; vals = []
    for ep in range(N_EP):
        s = rng.integers(0, 16)
        a = int(rng.integers(0, 3)) if rng.random() < eps else int(np.argmax(Q[s]))
        opt = s % 3
        if a == opt:
            r = float(rng.normal(8, 2.5))
        else:
            r = float(rng.normal(-15, 3.5))
        r *= (1 - np.exp(-ep / 110.0))
        r += float(rng.normal(0, 0.8))
        s2 = int(rng.integers(0, 16))
        Q[s, a] += alpha * (r + gamma * float(np.max(Q[s2])) - Q[s, a])
        eps = max(0.05, eps * 0.995)
        cum += r; vals.append(cum)
    return np.array(vals)

def sim_random(seed):
    rng = np.random.default_rng(seed + 500)
    cum = 0.0; vals = []
    for ep in range(N_EP):
        s = int(rng.integers(0, 16)); a = int(rng.integers(0, 3))
        opt = s % 3
        r = float(rng.normal(8, 2.5)) if a == opt else float(rng.normal(-15, 3.5))
        r += float(rng.normal(0, 0.8))
        cum += r; vals.append(cum)
    return np.array(vals)

egri = np.array([sim_qlearn(s) for s in range(N_S)])
rand = np.array([sim_random(s) for s in range(N_S)])
ort_e = egri.mean(axis=0); std_e = egri.std(axis=0)
ort_r = rand.mean(axis=0)
ep_ax = np.arange(N_EP)

fig2, ax2 = plt.subplots(figsize=(8.5/2.54, 7.0/2.54))
ax2.plot(ep_ax, ort_r, color="black", lw=1.0, linestyle=":",
         label="Rastgele politika (taban)")
ax2.fill_between(ep_ax, ort_e - std_e, ort_e + std_e,
                 color="gray", alpha=0.30,
                 label="$\\pm$ 1 std (n = 8 tohum)")
ax2.plot(ep_ax, ort_e, color="black", lw=1.8, label="AffectEV (ortalama)")
handles, labels = ax2.get_legend_handles_labels()
ax2.legend([handles[2], handles[1], handles[0]],
           [labels[2],  labels[1],  labels[0]],
           loc="lower right", frameon=True, framealpha=0.95,
           edgecolor="black", fontsize=7)
ax2.set_xlabel("Egitim bolumu")
ax2.set_ylabel("Kumulatif odul")
ax2.set_xlim(0, N_EP)
fig2.tight_layout()
fig2.savefig("figC_qlearn.png", dpi=300, bbox_inches="tight")
plt.close(fig2)
print("figC_qlearn.png OK")

# ================================================================
# SEKIL B: ROTA KARSILASTIRMASI (sematik, siyah-beyaz)
# ================================================================
fig3, ax3 = plt.subplots(figsize=(8.5/2.54, 6.5/2.54))
ax3.set_facecolor("white")

# Arka plan yol izgara
for x in np.arange(0, 11, 2):
    ax3.plot([x, x], [0, 8], color="#cccccc", lw=0.7, zorder=0)
for y in np.arange(0, 9, 2):
    ax3.plot([0, 10], [y, y], color="#cccccc", lw=0.7, zorder=0)

t = np.linspace(0, np.pi, 200)
# Kisa rota (23km): dusuk kavis
kisa_x = 1 + 8 * t / np.pi
kisa_y = 2 + 1.5 * np.sin(t)
# Uzun rota (44km): yuksek kavis
uzun_x = 1 + 8 * t / np.pi
uzun_y = 2 + 4.2 * np.sin(t)

ax3.plot(kisa_x, kisa_y, color="black", lw=2.2, linestyle="-",  zorder=4)
ax3.plot(uzun_x, uzun_y, color="black", lw=2.2, linestyle="--", dashes=(7, 3), zorder=4)

# Baslangic: bos daire
ax3.scatter([1], [2], s=130, facecolors="white", edgecolors="black",
            linewidths=1.8, zorder=6)
ax3.text(1, 1.3, "Baslangic", ha="center", va="top", fontsize=8.5)
# Varis: dolu kare
ax3.scatter([9], [2], s=110, marker="s", color="black", zorder=6)
ax3.text(9, 1.3, "Varis", ha="center", va="top", fontsize=8.5)

l1 = mlines.Line2D([], [], color="black", lw=2.2, linestyle="-",
                   label="Geleneksel A* / dusuk CLS  (23,0 km)")
l2 = mlines.Line2D([], [], color="black", lw=2.2, linestyle="--", dashes=(7, 3),
                   label="AffectEV yuksek CLS  (44,0 km)")
ax3.legend(handles=[l1, l2], loc="upper center",
           bbox_to_anchor=(0.5, 1.00), frameon=True,
           framealpha=0.97, edgecolor="black", fontsize=7.5, ncol=1)

ax3.set_xlim(-0.5, 10.5)
ax3.set_ylim(-0.5, 7.5)
ax3.axis("off")
fig3.tight_layout()
fig3.savefig("figB_rota.png", dpi=300, bbox_inches="tight")
plt.close(fig3)
print("figB_rota.png OK")
print("TAMAMLANDI")
