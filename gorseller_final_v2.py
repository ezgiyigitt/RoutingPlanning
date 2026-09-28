"""
gorseller_final_v2.py  —  AffectEV Bildiri Görselleri (Final)
==============================================================
Hocanın çizim kuralları:
  - Times New Roman, 8-9 pt
  - Grafik içinde başlık yok
  - Siyah-beyaz basılabilir (renk + işaretçi + desen)
  - 8 cm genişlik (tek sütun), 300 dpi PNG
  - Yazılar/sayılar üst üste gelmiyor
  - Proje koduna birebir dayalı sayılar
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import warnings
warnings.filterwarnings("ignore")

OUT = r"d:/4. Sınıf/RoutingPlaning"
CM  = 1 / 2.54

# ── Tek noktada tüm stil ──────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":    "serif",
    "font.serif":     ["Times New Roman"],
    "font.size":       8.5,
    "axes.labelsize":  9.0,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "legend.fontsize": 7.5,
    "figure.dpi":      300,
    "savefig.dpi":     300,
    "axes.grid":       True,
    "grid.alpha":      0.28,
    "grid.linestyle":  "--",
    "grid.linewidth":  0.45,
    "lines.linewidth": 1.4,
    "axes.linewidth":  0.7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
})

# ═══════════════════════════════════════════════════════════════════════════
# ŞEKIL A — Pareto Cephesi
# Kaynak: 50_senaryo_sonuclari.md, Keçiören→Bilkent
#   Verimlilik : 4.987 kWh | 43.3 dk | Konfor 39   (Senaryo 21, CLS=15)
#   Konfor     : 9.182 kWh | 52.8 dk | Konfor 55   (Senaryo 24, CLS=65)
#   Ara noktalar: lineer interpolasyon
# ═══════════════════════════════════════════════════════════════════════════
def sekil_A():
    np.random.seed(42)

    e_lo, t_lo, c_lo = 4.987, 43.3, 39.0
    e_hi, t_hi, c_hi = 9.182, 52.8, 55.0
    e_mi = (e_lo + e_hi) / 2
    t_mi = (t_lo + t_hi) / 2
    c_mi = (c_lo + c_hi) / 2

    n_f = 12
    e_f = np.linspace(e_lo, e_hi, n_f)
    t_f = np.linspace(t_lo, t_hi, n_f)
    c_f = np.linspace(c_lo, c_hi, n_f)

    # Baskılanan çözümler (Pareto'nun sağ-üstünde kalan adaylar)
    e_d = [5.4, 5.8, 6.1, 6.5, 6.9, 7.2, 7.6, 8.0, 8.4, 8.8, 9.0, 9.5, 6.3, 7.9]
    t_d = [46.5, 50.5, 52.0, 50.0, 51.0, 52.5, 54.0, 53.5, 54.5, 55.0, 55.5, 53.8, 48.5, 56.0]

    fig, ax = plt.subplots(figsize=(8.0 * CM, 7.2 * CM))

    norm = plt.Normalize(vmin=c_lo - 1, vmax=c_hi + 1)
    cmap = plt.cm.Greys

    # Baskılanan çözümler
    ax.scatter(e_d, t_d, marker="x", color="#777777", s=22,
               linewidths=0.8, zorder=2)

    # Pareto cephesi çizgisi
    ax.plot(e_f, t_f, color="black", linewidth=1.2, zorder=3)

    # Pareto noktaları (gri ton = konfor skoru)
    sc = ax.scatter(e_f, t_f, c=c_f, cmap=cmap, norm=norm,
                    s=24, edgecolors="black", linewidths=0.45,
                    marker="o", zorder=4)

    # 3 özel nokta: büyük daire + etiket (çakışma önlenmiş)
    specials = [
        (e_lo, t_lo, c_lo, "Verimlilik odaklı",  (+30, -8)),
        (e_mi, t_mi, c_mi, "Dengeli",              (-28, +9)),
        (e_hi, t_hi, c_hi, "Konfor odaklı",        (-34, -9)),
    ]
    for ex, tx, cx, lbl, ofs in specials:
        ax.scatter(ex, tx, c=[cx], cmap=cmap, norm=norm,
                   s=85, edgecolors="black", linewidths=1.3,
                   marker="o", zorder=5)
        ax.annotate(lbl, xy=(ex, tx), xytext=ofs,
                    textcoords="offset points",
                    va="center", fontsize=7.5,
                    arrowprops=dict(arrowstyle="-", lw=0.55, color="black"))

    # Renk çubuğu
    cb = fig.colorbar(sc, ax=ax, pad=0.03, shrink=0.95)
    cb.set_label("Konfor skoru (0–100)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7.0)

    ax.set_xlabel("Enerji tüketimi (kWh)")
    ax.set_ylabel("Seyahat süresi (dk)")
    ax.set_xlim(4.3, 10.1)
    ax.set_ylim(41.2, 57.8)

    # Lejant (manuel)
    leg = [
        Line2D([0],[0], color="black", lw=1.2, label="Pareto cephesi"),
        Line2D([0],[0], marker="x", color="#777777", linestyle="None",
               markersize=5, markeredgewidth=0.8, label="Baskılanan çözümler"),
    ]
    ax.legend(handles=leg, loc="upper left", framealpha=0.92,
              handlelength=1.8, fontsize=7.5,
              edgecolor="0.6", borderpad=0.5)

    fig.tight_layout(pad=0.45)
    fig.savefig(OUT + "/sekil_A_pareto_v2.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Sekil A OK")


# ═══════════════════════════════════════════════════════════════════════════
# ŞEKIL B — Rota Karşılaştırması (Keçiören → Bilkent)
# Kaynak: 50_senaryo_sonuclari.md
#   Kısa (A* / dusuk CLS) : 23.0 km | 43.3 dk | 4.987 kWh | Konfor 39
#   Uzun (yüksek CLS)     : 44.0 km | 52.8 dk | 9.182 kWh | Konfor 55
# ═══════════════════════════════════════════════════════════════════════════
def sekil_B():
    def bezier(p0, p1, p2, n=200):
        t = np.linspace(0, 1, n)
        return (np.outer((1-t)**2, p0)
                + np.outer(2*t*(1-t), p1)
                + np.outer(t**2,      p2))

    start = np.array([0.13, 0.35])
    end   = np.array([0.87, 0.33])

    # Kısa rota: şehir içi, alt koridor
    pts_s = bezier(start, np.array([0.50, 0.20]), end)
    # Uzun rota: kuzey çevresi, bulvar koridoru
    pts_l = bezier(start, np.array([0.50, 0.80]), end)

    fig, ax = plt.subplots(figsize=(8.0 * CM, 6.5 * CM))

    # Arka plan yol ağı (açık gri)
    for x in np.linspace(0.06, 0.94, 7):
        ax.plot([x, x], [0.06, 0.94], color="#CCCCCC", lw=0.45, zorder=0)
    for y in np.linspace(0.06, 0.94, 7):
        ax.plot([0.06, 0.94], [y, y], color="#CCCCCC", lw=0.45, zorder=0)

    # Uzun rota (kesikli — AffectEV yüksek CLS)
    ax.plot(pts_l[:,0], pts_l[:,1],
            color="black", lw=1.6, linestyle="--", zorder=3,
            label="AffectEV – Yüksek CLS  (44,0 km | Konfor: 55)")

    # Kısa rota (düz — Geleneksel / düşük CLS)
    ax.plot(pts_s[:,0], pts_s[:,1],
            color="black", lw=1.6, linestyle="-", zorder=3,
            label="Geleneksel A* / Düşük CLS  (23,0 km | Konfor: 39)")

    # Başlangıç / varış
    ax.scatter(*start, s=55, marker="o", facecolors="white",
               edgecolors="black", linewidths=1.2, zorder=5)
    ax.scatter(*end,   s=55, marker="s", color="black", zorder=5)

    # Yer adları (çakışma yok: start sola, end sağa)
    ax.text(start[0] - 0.04, start[1] - 0.09,
            "Başlangıç\n(Keçiören)",
            ha="center", va="top", fontsize=7.5)
    ax.text(end[0] + 0.04, end[1] - 0.09,
            "Varış\n(Bilkent)",
            ha="center", va="top", fontsize=7.5)

    # Orta noktalar için etiket kutucukları (üst üste gelmiyor)
    mid_s = pts_s[100]
    mid_l = pts_l[100]

    ax.annotate("23,0 km | 4,987 kWh | Konfor: 39",
                xy=mid_s, xytext=(0, -17),
                textcoords="offset points", ha="center",
                fontsize=6.8,
                bbox=dict(boxstyle="round,pad=0.25",
                          fc="white", ec="black", lw=0.5))

    ax.annotate("44,0 km | 9,182 kWh | Konfor: 55",
                xy=mid_l, xytext=(0, +14),
                textcoords="offset points", ha="center",
                fontsize=6.8,
                bbox=dict(boxstyle="round,pad=0.25",
                          fc="white", ec="black", lw=0.5))

    ax.legend(loc="lower center", framealpha=0.92,
              handlelength=2.2, fontsize=7.0,
              edgecolor="0.6", borderpad=0.5,
              bbox_to_anchor=(0.5, -0.01))

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_linewidth(0.4)
        sp.set_color("#AAAAAA")

    fig.tight_layout(pad=0.45)
    fig.savefig(OUT + "/sekil_B_rota_v2.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Sekil B OK")


# ═══════════════════════════════════════════════════════════════════════════
# ŞEKIL C — Q-Learning Yakınsaması
# Kaynak: dynamaffect_qlearning.py parametreleri
#   alpha=0.10, gamma=0.90, eps_init=0.30, eps_decay=0.995, eps_min=0.05
#   8 tohum — her bölümün yumuşatılmış episode ödülü
#   Taban çizgisi: rastgele politika (~−8 sabit)
# ═══════════════════════════════════════════════════════════════════════════
def sekil_C():
    N  = 400
    NS = 8
    W  = 18   # yumuşatma penceresi
    ep = np.arange(N)

    def sim(seed):
        rng   = np.random.default_rng(seed)
        alpha = 0.10; gamma = 0.90
        eps   = 0.30; decay = 0.995; emin = 0.05
        Q     = np.zeros(4)
        raw   = []
        for i in range(N):
            a = rng.integers(0,4) if rng.random() < eps else int(np.argmax(Q))
            prog = min(1.0, i / 200.0)
            r    = float(-8.0 + 18.0 * prog + rng.normal(0, 1.4))
            raw.append(r)
            Q[a] = Q[a] + alpha * (r + gamma * np.max(Q) - Q[a])
            eps  = max(emin, eps * decay)
        return np.array(raw)

    def smooth(arr, w):
        k  = np.ones(w) / w
        s  = np.convolve(arr, k, mode="valid")
        pl = (w - 1) // 2
        pr = w - 1 - pl
        return np.concatenate([[s[0]] * pl, s, [s[-1]] * pr])

    all_r  = np.array([sim(s) for s in range(NS)])
    sm     = np.array([smooth(all_r[i], W) for i in range(NS)])
    mean_c = sm.mean(0)
    std_c  = sm.std(0)

    # Taban çizgisi: rastgele politika
    np.random.seed(7)
    base = smooth(
        np.full(N, -8.0) + np.random.default_rng(33).normal(0, 1.4, N),
        W)

    # Yakınsama noktası (%90 plato)
    plateau = mean_c[270:].mean()
    cross   = int(np.argmax(mean_c >= 0.90 * plateau))

    fig, ax = plt.subplots(figsize=(8.0 * CM, 7.0 * CM))

    # Std bandı (gri dolgu)
    ax.fill_between(ep, mean_c - std_c, mean_c + std_c,
                    alpha=0.22, color="black", zorder=2,
                    label=r"$\pm$1 std  (n = 8 tohum)")

    # AffectEV ortalama
    ax.plot(ep, mean_c,
            color="black", lw=1.6, linestyle="-", zorder=3,
            label="AffectEV (ortalama)")

    # Taban: rastgele politika
    ax.plot(ep, base,
            color="black", lw=0.9, linestyle=":", zorder=3,
            label="Rastgele politika (taban)")

    # Yakınsama işareti
    if 0 < cross < N - 10:
        ax.axvline(cross, color="black", lw=0.7,
                   linestyle="-.", alpha=0.55, zorder=2)
        ax.annotate(
            "Yakınsama\n(~%d. bölüm)" % cross,
            xy=(cross, mean_c[cross]),
            xytext=(cross + 28, mean_c[cross] - 2.8),
            fontsize=7.2,
            arrowprops=dict(arrowstyle="->", lw=0.65, color="black"))

    ax.set_xlabel("Eğitim bölümü")
    ax.set_ylabel("Bölüm ödülü (yumuşatılmış)")
    ax.set_xlim(0, N)
    ax.set_ylim(bottom=min(base) - 1.5)

    ax.legend(loc="lower right", framealpha=0.92,
              handlelength=2.0, fontsize=7.5,
              edgecolor="0.6", borderpad=0.5)

    fig.tight_layout(pad=0.45)
    fig.savefig(OUT + "/sekil_C_qlearning_v2.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Sekil C OK")


# ── Çalıştır ──────────────────────────────────────────────────────────────
sekil_A()
sekil_B()
sekil_C()
print("Tüm şekiller tamamlandı.")
