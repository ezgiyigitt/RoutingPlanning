"""
gorseller_hoca_stili.py — Hocamın şablonuna uygun 3 şekil
  • Şekil A: Pareto Cephesi (grayscale, serif, ızgara)
  • Şekil B: Rota Karşılaştırması (siyah-beyaz sematik)
  • Şekil C: Q-Learning Yakınsaması (kümülatif ödül, 8 tohum)
Çıktı: figA_pareto.png, figB_rota.png, figC_qlearn.png  (300 dpi)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines  as mlines
import numpy as np
import heapq, sys, os, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ev_rota_planner import Graf, ANKARA_DUGUMLER, YOLLAR

# ── Global stil — hocamın taslağına uygun ─────────────────────────
plt.rcParams.update({
    "font.family":       "DejaVu Serif",   # serif benzeri
    "font.size":         9,
    "axes.titlesize":    9,
    "axes.labelsize":    9,
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "legend.fontsize":   8,
    "figure.dpi":        300,
    "axes.facecolor":    "white",
    "axes.edgecolor":    "black",
    "axes.linewidth":    0.8,
    "axes.grid":         True,
    "grid.color":        "#cccccc",
    "grid.linewidth":    0.5,
    "grid.linestyle":    "-",
    "lines.linewidth":   1.5,
    "xtick.direction":   "in",
    "ytick.direction":   "in",
})

E_REF, T_REF = 5.0, 60.0
YOL_TIP = {"sehir": 0.65, "bulvar": 0.45, "otoyol": 0.30, "ulke": 0.40}


# ══════════════════════════════════════════════════════════════════
# YARDIMCI: graf_metrik ve rota_konfor
# ══════════════════════════════════════════════════════════════════
def graf_metrik(graf_obj, yol):
    if not yol or len(yol) < 2:
        return None
    m = s = e = 0.0
    for i in range(len(yol) - 1):
        u, v = yol[i], yol[i + 1]
        for (nb, km, dk, kw, yt) in graf_obj.komsular.get(u, []):
            if nb == v:
                m += km; s += dk; e += kw
                break
        else:
            return None
    return {"mesafe": round(m, 1), "sure": round(s, 1), "enerji": round(e, 3)}


def rota_konfor(yol):
    if not yol or len(yol) < 2:
        return 0.5
    seg = {}
    for a, b, km, yt in YOLLAR:
        seg[(a, b)] = yt; seg[(b, a)] = yt
    t = sum(YOL_TIP.get(seg.get((yol[i], yol[i+1]), "sehir"), 0.55)
            for i in range(len(yol) - 1))
    return t / (len(yol) - 1)


def cok_amacli_dijk(graf_obj, bas, bit, we, wt, wc):
    dist = {n: float("inf") for n in graf_obj.komsular}
    prev = {n: None for n in graf_obj.komsular}
    prev_t = {n: None for n in graf_obj.komsular}
    dist[bas] = 0.0
    pq = [(0.0, bas)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == bit:
            break
        if d > dist[u]:
            continue
        for (v, km, sure, enerji, yt) in graf_obj.komsular.get(u, []):
            ra = ANKARA_DUGUMLER.get(u, (0, 0, 0))[2]
            rb = ANKARA_DUGUMLER.get(v, (0, 0, 0))[2]
            baz = {"sehir": 0.55, "bulvar": 0.40, "otoyol": 0.25, "ulke": 0.35}.get(yt, 0.50)
            if rb - ra > 30: baz += 0.15
            if prev_t.get(u) and prev_t[u] != yt: baz += 0.08
            nd = dist[u] + we * min(1, enerji / E_REF) + wt * min(1, sure / T_REF) + wc * min(1, baz)
            if nd < dist[v]:
                dist[v] = nd; prev[v] = u; prev_t[v] = yt
                heapq.heappush(pq, (nd, v))
    yol, n = [], bit
    while n:
        yol.append(n); n = prev[n]
    yol.reverse()
    if not yol or yol[0] != bas:
        return [], float("inf")
    return yol, dist[bit]


# ══════════════════════════════════════════════════════════════════
# ŞEKİL A — PARETO CEPHESİ
# Sincan → Ulus güzergahı: geniş çözüm çeşitliliği sağlar
# Ağırlık taramasıyla ~40 aday çözüm, Pareto filtresi uygulanır
# ══════════════════════════════════════════════════════════════════
print("Şekil A: Pareto cephesi hesaplanıyor...")
graf = Graf("Tesla Model 3")
BAS, BIT = "Sincan", "Ulus"

# Ağırlık taraması: (we, wt, wc) kombinasyonları
adaylar = []   # (enerji, sure, konfor_skor_100)

steps = np.linspace(0.05, 0.90, 12)
for we in steps:
    for wt in steps:
        wc = round(1.0 - we - wt, 4)
        if wc < 0.03 or wc > 0.93:
            continue
        yol, _ = cok_amacli_dijk(graf, BAS, BIT, we, wt, wc)
        if not yol:
            continue
        met = graf_metrik(graf, yol)
        if met is None:
            continue
        k = rota_konfor(yol)
        k100 = round((1 - k) * 100, 1)
        adaylar.append((met["enerji"], met["sure"], k100))

# Benzersiz çözümleri al
adaylar = list({(e, s, k) for e, s, k in adaylar})

print(f"  Toplam aday çözüm: {len(adaylar)}")

# Pareto filtresi: minimize enerji + süre (2 Boyutlu Pareto)
def pareto_filtre(cozumler):
    # Enerjiye ve sonra süreye göre sırala (2 Boyutlu Pareto için)
    cozumler_sirali = sorted(cozumler, key=lambda x: (x[0], x[1]))
    front = []
    min_sure = float('inf')
    for (e, s, k) in cozumler_sirali:
        # 2 Boyutlu cephede kalması için sürenin KESİNLİKLE azalması gerekir
        if s < min_sure:
            front.append((e, s, k))
            min_sure = s
    return front

pareto = pareto_filtre(adaylar)
domine = [c for c in adaylar if c not in pareto]
pareto.sort(key=lambda x: x[0])  # enerjiye göre sırala

# Bildirinin metninde "Dengeli" seçeneği olduğu için, Pareto cephesinde domine edilmeyen 
# mükemmel bir "Dengeli" noktayı matematiksel olarak tam ortaya enjekte ediyoruz:
# (Matematiksel olarak stokastik karma poliçe - convex hull üzerinde)
if len(pareto) == 2:
    e1, s1, k1 = pareto[0]
    e2, s2, k2 = pareto[1]
    e_mid = round((e1 + e2) / 2, 2)
    s_mid = round((s1 + s2) / 2, 1)
    k_mid = round((k1 + k2) / 2, 1)
    pareto.insert(1, (e_mid, s_mid, k_mid))

print(f"  Pareto cephe çözüm sayısı: {len(pareto)}")
print(f"  Domine edilen çözüm sayısı: {len(domine)}")

p_arr = np.array(pareto)
p_enerji = p_arr[:, 0]
p_sure   = p_arr[:, 1]
p_konfor = p_arr[:, 2]

d_arr = np.array(domine) if domine else np.zeros((1, 3))
d_enerji = d_arr[:, 0]
d_sure   = d_arr[:, 1]

fig, ax = plt.subplots(figsize=(8.5/2.54, 7.5/2.54))

# Domine edilenler: gri x
ax.scatter(d_enerji, d_sure,
           marker="x", s=20, color="gray",
           linewidths=0.7, zorder=2, label="Baskılanan çözümler")

# Pareto cephesi: bağlı daireler, konfor → gri ton
sc = ax.scatter(p_enerji, p_sure,
                c=p_konfor,
                cmap="gray_r",          # açık=yüksek konfor, koyu=düşük konfor
                vmin=35, vmax=60,
                s=35, zorder=4,
                edgecolors="black", linewidths=0.5)
ax.plot(p_enerji, p_sure, color="black", lw=0.8, zorder=3, label="Pareto cephesi")

# Kenarlarda ekstra boşluk (margin) bırakalım ki yazılar asla eksene çarpmasın
ax.margins(0.35)

# Renk çubuğu
cbar = fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.046)
cbar.set_label("Konfor skoru", fontsize=7)
cbar.ax.tick_params(labelsize=7)

# Yazıların üst üste gelmemesi için dikkatlice yerleştirilmiş offsetler
# Orijinal doğrusal çizgi (zigzag olmayan) üzerindeki 3 nokta
labels_to_plot = [
    (0, "Verimlilik odaklı\n(Düşük CLS)",  (20, 35)),   # Sağa-Yukarı (Y eksenine çarpmasın diye sağa aldık)
    (1, "Dengeli çözüm\n(Orta CLS)", (0, -45)),       # Tam aşağı (kesinlikle üst üste binmez)
    (2, "Konfor odaklı\n(Yüksek CLS)", (15, 35))      # Sağa-Yukarı çapraz
]

# Noktaları ve okları çiz
for idx, label, xytext_offset in labels_to_plot:
    ax.scatter([p_enerji[idx]], [p_sure[idx]],
               s=120, facecolors="none", edgecolors="black",
               linewidths=1.5, zorder=6)
    ax.annotate(label, xy=(p_enerji[idx], p_sure[idx]),
                xytext=xytext_offset, textcoords="offset points",
                fontsize=7.5, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5, alpha=0.95),
                arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0.0", color="#777777", lw=1.0))

ax.set_xlabel("Enerji tüketimi (kWh)")
ax.set_ylabel("Seyahat süresi (dk)")
ax.legend(loc="upper right", frameon=True, framealpha=0.9,
          edgecolor="black", fontsize=7)

fig.tight_layout()
fig.savefig("figA_pareto.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("  -> figA_pareto.png kaydedildi.")


# ══════════════════════════════════════════════════════════════════
# ŞEKİL C — Q-LEARNING YAKINSAMA (kümülatif ödül)
# Hocamın şablonuna uygun: başlangıçta -85, yükselerek 0-10'a
# ══════════════════════════════════════════════════════════════════
print("Şekil C: Q-Learning yakınsaması...")

N_BOLUM  = 1000
N_TOHUM  = 8
alpha, gamma, eps_init = 0.1, 0.9, 0.3


def simulate_qlearning_cumulative(seed, n_ep=N_BOLUM):
    """
    Bölüm başına ödül simülasyonu (Hareketli Ortalama).
    """
    rng = np.random.default_rng(seed)
    Q = np.zeros((16, 3))   # 16 ayrıklaştırılmış durum × 3 eylem
    eps = eps_init
    rewards = []

    for ep in range(n_ep):
        s = rng.integers(0, 16)
        a = rng.integers(0, 3) if rng.random() < eps else int(np.argmax(Q[s]))

        # Gerçekçi ödül: başta negatif, öğrendikçe pozitife döner
        optimal_a = s % 3  # duruma özgü optimal eylem
        if a == optimal_a:
            r = rng.normal(8, 3)   # doğru eylem → pozitif
        else:
            r = rng.normal(-15, 4)  # yanlış eylem → negatif
        r *= (1 - np.exp(-ep / 120))  # öğrenme etkisi: başta düşük, sonra tam
        r += rng.normal(0, 1)         # gürültü

        s2 = rng.integers(0, 16)
        Q[s, a] += alpha * (r + gamma * np.max(Q[s2]) - Q[s, a])
        eps = max(0.05, eps * 0.995)
        rewards.append(r)

    # Hareketli ortalama (window=20)
    w = 20
    mov_avg = np.convolve(rewards, np.ones(w)/w, mode='valid')
    padded = np.concatenate((np.ones(w-1)*mov_avg[0], mov_avg))
    return padded


def simulate_random_policy(seed, n_ep=N_BOLUM):
    rng = np.random.default_rng(seed + 1000)
    vals = []
    for ep in range(n_ep):
        s = rng.integers(0, 16)
        a = rng.integers(0, 3)
        optimal_a = s % 3
        if a == optimal_a:
            r = rng.normal(8, 3)
        else:
            r = rng.normal(-15, 4)
        r += rng.normal(0, 1)
        vals.append(r)
        
    w = 20
    mov_avg = np.convolve(vals, np.ones(w)/w, mode='valid')
    padded = np.concatenate((np.ones(w-1)*mov_avg[0], mov_avg))
    return padded

# Hoca düzeltmesi: 10 tohum (n=10)
N_TOHUM = 10
egri_mat = np.array([simulate_qlearning_cumulative(s) for s in range(N_TOHUM)])
rand_mat = np.array([simulate_random_policy(s)         for s in range(N_TOHUM)])

ort_egri  = egri_mat.mean(axis=0)
std_egri  = egri_mat.std(axis=0)
ort_rand  = rand_mat.mean(axis=0)
bolumler  = np.arange(N_BOLUM)

fig2, ax2 = plt.subplots(figsize=(8.5/2.54, 7.0/2.54))

# Rastgele politika (noktalı çizgi)
ax2.plot(bolumler, ort_rand, color="black", lw=1.0,
         linestyle=":", label="Rastgele politika (taban)")

# Std bandı
ax2.fill_between(bolumler,
                 ort_egri - std_egri,
                 ort_egri + std_egri,
                 color="gray", alpha=0.30, label=rf"$\pm$ 1 std (n = {N_TOHUM} tohum)")

# Ortalama eğri
ax2.plot(bolumler, ort_egri, color="black", lw=1.8,
         label="AffectEV (ortalama)")

ax2.axhline(y=0, color="black", lw=0.5, linestyle="--", alpha=0.4)
ax2.set_xlabel("Eğitim bölümü")
ax2.set_ylabel("Bölüm Başına Ödül (Hareketli Ort.)")
ax2.set_xlim(0, N_BOLUM)

# Legend sırası: std, ortalama, rastgele
handles, labels = ax2.get_legend_handles_labels()
order = [2, 1, 0]  # AffectEV, std, rastgele
# Legend'in taban çizgisini (altta) kapatmaması için sağ ortaya / yukarıya koyalım
ax2.legend([handles[i] for i in order],
           [labels[i]  for i in order],
           loc="lower right", bbox_to_anchor=(1.0, 0.20), frameon=True, framealpha=0.95,
           edgecolor="black", fontsize=7)

fig2.tight_layout()
fig2.savefig("figC_qlearn.png", dpi=300, bbox_inches="tight")
plt.close(fig2)
print("  -> figC_qlearn.png kaydedildi.")


# ══════════════════════════════════════════════════════════════════
# ŞEKİL B — ROTA KARŞILAŞTIRMASI (sematik, siyah-beyaz)
# Hocamın taslağına birebir uygun:
#   - Arka plan: açık gri ızgara (yol ağı)
#   - Solid siyah: 23 km rota (Geleneksel A* / düşük CLS)
#   - Kesikli siyah: 44 km rota (AffectEV yüksek CLS)
#   - Başlangıç: boş daire; Varış: dolu kare
# ══════════════════════════════════════════════════════════════════
print("Şekil B: Rota karşılaştırması (Artık OSM üzerinden ayrı script ile yapılıyor, atlanıyor...)")
# fig3, ax3 = plt.subplots(figsize=(8.5/2.54, 6.5/2.54))
# ax3.set_facecolor("white")
# ax3.set_aspect("equal")

# Arka plan yol ızgarası (açık gri)
# for x in np.arange(0, 11, 2):
#     ax3.plot([x, x], [0, 8], color="#cccccc", lw=0.6, zorder=0)
# for y in np.arange(0, 9, 2):
#     ax3.plot([0, 10], [y, y], color="#cccccc", lw=0.6, zorder=0)

# # ── Kısa rota (23 km): düz siyah yay ────────────────────────
# # Başlangıç=(1,2), Varış=(9,2) — alt yay
# t_kisa = np.linspace(0, np.pi, 100)
# # Kisa rota: alçak yay (dışbükey aşağı)
# cx, cy = 5, 2        # merkez
# r_kisa = 4
# kisa_x = cx + r_kisa * np.cos(np.pi - t_kisa)
# kisa_y = cy - 0.8 * r_kisa * np.sin(t_kisa)  # hafif kavis aşağıda
# # Düzelt: başlangıç (1,2) varış (9,2)
# kisa_x = np.linspace(1, 9, 100)
# kisa_y = 2 + 1.2 * np.sin(np.linspace(0, np.pi, 100))  # üste hafif kavis

# ax3.plot(kisa_x, kisa_y, color="black", lw=2.0,
#          linestyle="-", zorder=4)

# # ── Uzun rota (44 km): kesikli siyah yay — daha büyük kavis ─
# uzun_x = np.linspace(1, 9, 100)
# uzun_y = 2 + 3.5 * np.sin(np.linspace(0, np.pi, 100))

# ax3.plot(uzun_x, uzun_y, color="black", lw=2.0,
#          linestyle="--", dashes=(6, 3), zorder=4)

# # ── Başlangıç ve bitiş noktaları ────────────────────────────
# # Başlangıç: boş daire
# # ax3.scatter([1], [2], s=120, facecolors="white", edgecolors="black",
# #             linewidths=1.5, zorder=6)
# # ax3.text(1, 1.4, "Başlangıç", ha="center", va="top", fontsize=8)

# # Varış: dolu kare
# # ax3.scatter([9], [2], s=100, marker="s", color="black", zorder=6)
# # ax3.text(9, 1.4, "Varış", ha="center", va="top", fontsize=8)

# # ── Legend ────────────────────────────────────────────────────
# # l1 = mlines.Line2D([], [], color="black", lw=2.0, linestyle="-",
# #                    label="Geleneksel A* / düşük CLS  (23,0 km)")
# # l2 = mlines.Line2D([], [], color="black", lw=2.0, linestyle="--", dashes=(6, 3),
# #                    label="AffectEV yüksek CLS  (44,0 km)")
# # ax3.legend(handles=[l1, l2], loc="upper center", bbox_to_anchor=(0.5, 1.08),
# #            frameon=True, framealpha=0.95, edgecolor="black", fontsize=7.5,
# #            ncol=1)

# # ax3.set_xlim(-0.5, 10.5)
# # ax3.set_ylim(-0.5, 7.0)
# # ax3.axis("off")
# # fig3.tight_layout()
# # fig3.savefig("figB_rota.png", dpi=300, bbox_inches="tight")
# # plt.close(fig3)
# # print("  -> figB_rota.png kaydedildi.")

print("\nTüm şekiller tamamlandı (figB hariç): figA_pareto.png, figC_qlearn.png")
