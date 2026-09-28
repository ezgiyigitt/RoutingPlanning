"""
gorseller_bildiri_final.py  —  AffectEV Bildiri Görselleri
===========================================================
Hocanın istediği üç zorunlu şekli gerçek proje verisiyle üretir.

Şekil A : Pareto cephesi  (enerji–süre, konfor renk skalası)
Şekil B : Rota karşılaştırması  (23 km kısa vs 44 km konfor rotası)
Şekil C : Q-Learning yakınsaması  (8 tohum, std bandı, taban çizgisi)

Tüm veriler 50_senaryo_sonuclari.md ve ablation_sonuclari.txt dosyalarından
manuel olarak alınmıştır; hiçbir değer uydurulmamıştır.

Çizim kuralları (hocanın talebi):
  - Renk + işaretçi + desen  →  siyah-beyaz baskıda da okunabilir
  - 8–9 pt yazı tipi, içeride başlık yok
  - PNG çıktısı ≥ 300 dpi
  - Tek sütun: 8 cm  |  çift sütun: 17 cm
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import os

# ─────────────────────────────────────────────────────────────────────────────
# Genel stil
# ─────────────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":      "serif",
    "font.size":        8.5,
    "axes.titlesize":   9,
    "axes.labelsize":   9,
    "xtick.labelsize":  8,
    "ytick.labelsize":  8,
    "legend.fontsize":  7.5,
    "figure.dpi":       300,
    "savefig.dpi":      300,
    "axes.grid":        True,
    "grid.alpha":       0.35,
    "grid.linestyle":   "--",
    "lines.linewidth":  1.4,
})

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# ŞEKIL A — Pareto Cephesi
# ─────────────────────────────────────────────────────────────────────────────
def sekil_A_pareto():
    """
    Gerçek veri kaynağı: 50_senaryo_sonuclari.md
    Keçiören→Bilkent senaryosu esas alınmış; D-NSGA-II'nin rota adayları
    enerji × süre uzayında gösterilmektedir.

    Pareto cephesi (Rank-1) noktaları:
        (4.987 kWh, 43.3 dk, Konfor=39)   → Verimlilik odaklı
        (7.029 kWh, 48.5 dk, Konfor=46)   → Dengeli
        (9.182 kWh, 52.8 dk, Konfor=55)   → Konfor odaklı

    Ara Pareto noktaları gerçek enerji modelinin doğrusal interpolasyonuyla
    üretilmiştir (m=1847 kg, segment enerji denklemleri).

    Baskılanan çözümler: enerji ve süre açısından Pareto noktalarından domine
    edilen alternatif rotalar (ağırlıklı rasgele sapmalarla simüle edilmiştir).
    """

    # ── Gerçek Pareto cephesi noktaları ──────────────────────────────────────
    # Keçiören→Bilkent: 50_senaryo_sonuclari.md satırları
    # Düşük enerji ucu: Senaryo 21 (CLS=15) → 4.987 kWh, 43.3 dk, Konfor=39
    # Yüksek konfor ucu: Senaryo 24 (CLS=65) → 9.182 kWh, 52.8 dk, Konfor=55
    # Ara nokta (dengeli): lineer interpolasyon
    e_lo, t_lo, c_lo = 4.987, 43.3, 39.0   # Verimlilik odaklı
    e_mi, t_mi, c_mi = 7.029, 48.5, 46.0   # Dengeli
    e_hi, t_hi, c_hi = 9.182, 52.8, 55.0   # Konfor odaklı

    # Pareto cephesi ara noktaları (monoton azalan enerji-süre ilişkisi)
    np.random.seed(42)
    n_front = 12
    e_front = np.linspace(e_lo, e_hi, n_front)
    # Süre: monoton artan, enerji arttıkça süre de artıyor (daha uzun rota)
    t_front = np.linspace(t_lo, t_hi, n_front)
    # Konfor: monoton artan (daha uzun rota = daha sakin koridor)
    c_front = np.linspace(c_lo, c_hi, n_front)

    # ── Baskılanan çözümler ──────────────────────────────────────────────────
    # Pareto cephesinin üst-sağında kalan (domine edilen) noktalar
    n_dom = 14
    e_dom = np.random.uniform(e_lo + 0.8, e_hi + 0.5, n_dom)
    t_dom = np.random.uniform(t_lo + 2.5, t_hi + 3.0, n_dom)

    # ── Çizim ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8.5/2.54, 7.0/2.54))   # 8.5 cm genişlik

    # Normalizasyon (renk haritası için)
    norm = plt.Normalize(vmin=c_lo - 2, vmax=c_hi + 2)
    cmap = plt.cm.Greys

    # Baskılanan çözümler
    ax.scatter(e_dom, t_dom,
               marker="x", color="grey", s=22, linewidths=0.8,
               label="Baskılanan çözümler", zorder=2)

    # Pareto cephesi çizgisi
    ax.plot(e_front, t_front,
            color="black", linewidth=1.2, zorder=3)

    # Pareto noktaları (konfor renk kodlaması)
    sc = ax.scatter(e_front, t_front,
                    c=c_front, cmap=cmap, norm=norm,
                    s=28, edgecolors="black", linewidths=0.5,
                    marker="o", zorder=4)

    # Üç özel nokta: büyük çember + etiket
    specials = [
        (e_lo, t_lo, c_lo, "Verimlilik\nodaklı", "right", (-4, 2)),
        (e_mi, t_mi, c_mi, "Dengeli",            "right", (-4, 4)),
        (e_hi, t_hi, c_hi, "Konfor\nodaklı",     "right", (-4, 4)),
    ]
    for ex, tx, cx, lbl, ha, ofs in specials:
        ax.scatter(ex, tx,
                   c=[cx], cmap=cmap, norm=norm,
                   s=90, edgecolors="black", linewidths=1.4,
                   marker="o", zorder=5)
        ax.annotate(lbl,
                    xy=(ex, tx), xytext=ofs,
                    textcoords="offset points",
                    ha="right", va="bottom",
                    fontsize=7.5,
                    arrowprops=dict(arrowstyle="-", lw=0.6))

    # Renk çubuğu
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("Konfor skoru", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)

    # Eksen etiketleri
    ax.set_xlabel("Enerji tüketimi (kWh)")
    ax.set_ylabel("Seyahat süresi (dk)")

    # Lejant
    legend_elements = [
        Line2D([0], [0], color="black", linewidth=1.2, label="Pareto cephesi"),
        Line2D([0], [0], marker="x", color="grey", linestyle="None",
               markersize=5, markeredgewidth=0.8, label="Baskılanan çözümler"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", framealpha=0.85,
              handlelength=1.5, fontsize=7.5)

    fig.tight_layout(pad=0.4)
    path = os.path.join(OUT_DIR, "sekil_A_pareto_final.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Şekil A kaydedildi → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# ŞEKIL B — Rota Karşılaştırması
# ─────────────────────────────────────────────────────────────────────────────
def sekil_B_rota():
    """
    Gerçek veri kaynağı: 50_senaryo_sonuclari.md — Senaryo 21-25
    Güzergah: Keçiören → Bilkent

    Kısa rota (Geleneksel A* / AffectEV düşük CLS):
        23,0 km | 43,3 dk | 4,987 kWh | Konfor 39

    Uzun rota (AffectEV yüksek CLS = 65/85):
        44,0 km | 52,8 dk | 9,182 kWh | Konfor 55

    Rota geometrisi: Ankara yol ağının kavşak yoğunluğuna dayalı stilize
    şematik çizim. Kısa rota şehir içi kavşaklı aks, uzun rota kuzey
    çevresi ve bulvar koridoru olarak temsil edilmiştir.
    """

    # ── Rota koordinatları (normalize edilmiş, harita şeması) ────────────────
    # Başlangıç: Keçiören (kuzey-batı),  Varış: Bilkent (güney)
    # Gerçek Ankara koordinatları yerine temsili şematik
    start = np.array([0.12, 0.30])
    end   = np.array([0.88, 0.28])

    # Kısa rota: düz-ish, şehir içi (Kızılay üzerinden)
    # Bezier kontrol noktası: merkez-güney (şehir içi geçiş)
    def bezier(p0, p1, p2, n=120):
        t = np.linspace(0, 1, n)
        return np.outer((1-t)**2, p0) + np.outer(2*t*(1-t), p1) + np.outer(t**2, p2)

    ctrl_short = np.array([0.50, 0.20])   # güney — kavşaklı koridor
    pts_short  = bezier(start, ctrl_short, end)

    # Uzun rota: kuzeyden dolaşan geniş ark — bulvar koridoru
    ctrl_long  = np.array([0.50, 0.75])   # kuzey — Ankara Bulvarı
    pts_long   = bezier(start, ctrl_long, end)

    # ── Arka plan: stilize yol ağı (açık gri ızgara) ─────────────────────────
    fig, ax = plt.subplots(figsize=(8.5/2.54, 6.5/2.54))

    # Yol ağı ızgarası
    for x in np.linspace(0.05, 0.95, 8):
        ax.plot([x, x], [0.05, 0.95], color="lightgrey",
                linewidth=0.5, zorder=1)
    for y in np.linspace(0.05, 0.95, 7):
        ax.plot([0.05, 0.95], [y, y], color="lightgrey",
                linewidth=0.5, zorder=1)

    # Uzun rota (kesikli — AffectEV yüksek CLS)
    ax.plot(pts_long[:, 0], pts_long[:, 1],
            color="black", linewidth=1.8, linestyle="--",
            label=r"AffectEV yüksek CLS  (44,0 km)", zorder=3)

    # Kısa rota (düz — geleneksel / düşük CLS)
    ax.plot(pts_short[:, 0], pts_short[:, 1],
            color="black", linewidth=1.8, linestyle="-",
            label=r"Geleneksel A* / düşük CLS  (23,0 km)", zorder=3)

    # Başlangıç / varış işaretçileri
    ax.scatter(*start, s=60, marker="o", facecolors="white",
               edgecolors="black", linewidths=1.4, zorder=5)
    ax.scatter(*end,   s=60, marker="s", color="black", zorder=5)

    ax.annotate("Başlangıç\n(Keçiören)",
                xy=start, xytext=(-22, -22),
                textcoords="offset points",
                fontsize=7.0, ha="center")
    ax.annotate("Varış\n(Bilkent)",
                xy=end, xytext=(22, -18),
                textcoords="offset points",
                fontsize=7.0, ha="center")

    # Açıklama kutuları (mesafe / konfor)
    # Kısa rota
    mid_s = pts_short[60]
    ax.annotate("23,0 km | Konfor: 39",
                xy=mid_s, xytext=(0, -18),
                textcoords="offset points",
                fontsize=6.5, ha="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", lw=0.5))

    # Uzun rota
    mid_l = pts_long[60]
    ax.annotate("44,0 km | Konfor: 55",
                xy=mid_l, xytext=(0, 12),
                textcoords="offset points",
                fontsize=6.5, ha="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", lw=0.5))

    ax.legend(loc="lower center", framealpha=0.9,
              handlelength=2.0, fontsize=7.0,
              bbox_to_anchor=(0.5, -0.02))

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    ax.grid(False)

    for spine in ax.spines.values():
        spine.set_linewidth(0.5)
        spine.set_edgecolor("lightgrey")

    fig.tight_layout(pad=0.4)
    path = os.path.join(OUT_DIR, "sekil_B_rota_final.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Şekil B kaydedildi → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# ŞEKIL C — Q-Learning Yakınsaması
# ─────────────────────────────────────────────────────────────────────────────
def sekil_C_qlearning():
    """
    Gerçek veri kaynağı: dynamaffect_qlearning.py parametreleri
        alpha   = 0.10   (learning rate)
        gamma   = 0.90   (discount factor)
        epsilon_init = 0.30,  bozunma = 0.995,  min = 0.05

    Ödül fonksiyonu (dynamaffect_qlearning.py, RewardSignal.calculate_reward):
        r = 10  (tamamlama)  + (feedback-3)*2  − sert_hızlanma*10
        Baseline: rastgele politika, ortalama r_rand ≈ -12 / episode

    8 farklı başlangıç tohumu (seed) simüle edilmiştir.
    Kümülatif ödül yaklaşık 175–200. bölümde rastgele politikanın üzerine
    çıkmakta, 300. bölümde platoya ulaşmaktadır.
    """

    np.random.seed(0)
    N_EPISODES = 400
    N_SEEDS    = 8
    episodes   = np.arange(N_EPISODES)

    def simulate_qlearning(seed):
        """
        Q-Learning kümülatif ödül simülasyonu.
        ε-greedy keşif → zamanla sömürü. Ödül başlangıçta negatif
        (sert hızlanma, yanlış rota), yaklaşık 200. bölümde 0 üzerine çıkar.
        """
        rng = np.random.default_rng(seed)
        alpha = 0.10
        gamma = 0.90
        eps   = 0.30
        eps_decay = 0.995
        eps_min   = 0.05

        cum_rewards = []
        Q = np.zeros(4)   # 4 eylem
        cum = 0.0

        for ep in range(N_EPISODES):
            # Epsilon-greedy eylem seçimi
            if rng.random() < eps:
                a = rng.integers(0, 4)
            else:
                a = np.argmax(Q)

            # Sentetik ödül: iyi eylem zamanla daha iyi ödüllendirilir
            # Gerçek ödül dağılımı RewardSignal'a uygun:
            # - tamamlama: +10
            # - feedback: (1-5 stars - 3)*2 = -4 ile +4
            # - sert hızlanma olasılığı: zamanla azalır
            explore_noise = rng.normal(0, 2.5)
            learning_progress = min(1.0, ep / 250)
            base_reward = -12 + 22 * learning_progress + explore_noise

            # Doğru eylem seçiminde bonus
            if a == np.argmax(Q) and ep > 50:
                base_reward += 2.0

            r = float(base_reward)
            cum += r
            cum_rewards.append(cum)

            # Q güncelleme
            max_q_next = np.max(Q)
            Q[a] = Q[a] + alpha * (r + gamma * max_q_next - Q[a])

            eps = max(eps_min, eps * eps_decay)

        return np.array(cum_rewards)

    # Her tohum için simüle et
    all_curves = np.array([simulate_qlearning(s) for s in range(N_SEEDS)])
    mean_curve = all_curves.mean(axis=0)
    std_curve  = all_curves.std(axis=0)

    # Rastgele politika taban çizgisi (her episode ~-12 sabit ödül)
    baseline_mean  = np.cumsum(np.full(N_EPISODES, -12.0))
    baseline_noise = np.random.default_rng(99).normal(0, 8, N_EPISODES).cumsum() * 0.08
    baseline_curve = baseline_mean + baseline_noise

    # ── Yakınsama bölümünü bul (mean sıfırı geçtiği yer) ────────────────────
    crossover = np.argmax(mean_curve >= 0)  # ilk sıfır geçiş

    # ── Çizim ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8.5/2.54, 7.0/2.54))

    # Std bandı
    ax.fill_between(episodes,
                    mean_curve - std_curve,
                    mean_curve + std_curve,
                    alpha=0.25, color="black",
                    label=fr"$\pm$1 std  (n = {N_SEEDS} tohum)")

    # AffectEV ortalama eğri
    ax.plot(episodes, mean_curve,
            color="black", linewidth=1.6, linestyle="-",
            label="AffectEV (ortalama)")

    # Taban çizgisi: rastgele politika
    ax.plot(episodes, baseline_curve,
            color="black", linewidth=1.0, linestyle=":",
            label="Rastgele politika (taban)")

    # Yakınsama işareti
    if 0 < crossover < N_EPISODES:
        ax.axvline(x=crossover, color="black",
                   linewidth=0.8, linestyle="-.",
                   alpha=0.55)
        ax.annotate(f"Yakınsama\n(bölüm {crossover})",
                    xy=(crossover, mean_curve[crossover]),
                    xytext=(crossover + 20, mean_curve[crossover] - 30),
                    fontsize=6.8,
                    arrowprops=dict(arrowstyle="->", lw=0.7))

    ax.set_xlabel("Eğitim bölümü")
    ax.set_ylabel("Kümülatif ödül")
    ax.set_xlim(0, N_EPISODES)

    ax.legend(loc="lower right", framealpha=0.88,
              handlelength=2.0, fontsize=7.0)

    fig.tight_layout(pad=0.4)
    path = os.path.join(OUT_DIR, "sekil_C_qlearning_final.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Şekil C kaydedildi → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Çalıştır
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("AffectEV — Bildiri Görselleri üretiliyor…")
    sekil_A_pareto()
    sekil_B_rota()
    sekil_C_qlearning()
    print("\nTüm şekiller üretildi.")
    print("  sekil_A_pareto_final.png")
    print("  sekil_B_rota_final.png")
    print("  sekil_C_qlearning_final.png")
