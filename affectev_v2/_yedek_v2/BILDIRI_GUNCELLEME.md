# Bildiri güncelleme listesi (kod ↔ bildiri tutarlılığı)

Aşağıdaki "Yeni değer"ler `python experiments/run_all.py` ile üretilmiştir (`results/`).
Kod deterministiktir: aynı komut her çalıştırmada aynı sayıları verir. Bildiri bu değerlerle
güncellendiğinde kod ve metin birebir tutarlı olur.

## 1. Özet / Abstract

| Yer | Bildirideki | Yeni değer |
|---|---|---|
| Genel ortalama konfor (AffectEV) | 50,3/100 | **86,2/100** |
| Keçiören–Bilkent, yüksek CLS konfor artışı | %41 | **%1,4** (82,4 → 83,5) |
| Enerji artışı | %84 | **%6,2** (2,72 → 2,89 kWh) |
| Mesafe artışı | %91 | **%9,6** (21,0 → 23,0 km) |

Önerilen Özet cümlesi:
> "...AffectEV'in 50 senaryo × 10 tohumda karşılaştırma algoritmalarından daha yüksek ortalama
> konfor (86,2/100) ve daha az sinyalize kavşak (2,7) sağladığını göstermektedir. Kazanç yüksek
> bilişsel yükte belirginleşmektedir. CLS=85'te konfor, A*'a göre eşleştirilmiş senaryolarda
> ortalama 3,1 puan artmıştır (Wilcoxon p < 10⁻⁸⁰). Buna karşılık enerji tüketimi 0,28 kWh
> artmıştır."

## 2. Tablo 1'e eklenmesi gereken parametreler

ρ = 1,2 kg/m³ · g = 9,81 m/s² · P_aux = 1,5 kW · C_batt = 60 kWh · P_charge = 50 kW · SoC_target = %80

## 3. Tablo 2 (yeni)

| Yöntem | Süre (dk) | Enerji (kWh) | Konfor (0-100) | Ort. Kavşak |
|---|---|---|---|---|
| Dijkstra (mesafe) | 32,6 ± 11,0 | **2,21 ± 0,73** | 79,4 ± 7,5 | 10,6 |
| A* (süre) | **28,1 ± 8,5** | 2,44 ± 0,93 | 84,8 ± 5,1 | 3,2 |
| NSGA-II (CLS yok) | 29,1 ± 8,8 | 2,28 ± 0,76 | 85,2 ± 4,6 | 3,1 |
| AffectEV (CLS uyarlamalı) | 30,6 ± 9,3 | 2,45 ± 0,91 | **86,2 ± 4,4** | **2,7** |

Not satırına eklenmeli: "AffectEV satırı beş CLS düzeyinin tamamını kapsar (2500 çalıştırma)."

Metin değişikliği: Bildiride "A* en yüksek konforu verir, AffectEV eşdeğer çizgidedir" deniyor.
Yeni sonuçlarda **AffectEV en yüksek ortalama konforu ve en az kavşak sayısını** veriyor. Bu bir
kazanç ama bedeli ~2,5 dk ek süre (A*'a göre). Enerjide AffectEV ile A* neredeyse aynı.

## 4. Tablo 3 (yeni)

| Sürücü | CLS | w_e / w_t / w_c | Konfor | Enerji (kWh) | Süre (dk) | Rejim |
|---|---|---|---|---|---|---|
| Çok Enerjik | 15 | 0,50 / 0,40 / 0,10 | 83,9 | 2,20 | 29,4 | D (%63; V %37) |
| Enerjik | 30 | 0,40 / 0,35 / 0,25 | 84,9 | 2,24 | 29,1 | D (%84) |
| Nötr | 50 | 0,28 / 0,22 / 0,50 | 86,5 | 2,41 | 29,9 | D (%78) |
| Yorgun | 65 | 0,13 / 0,10 / 0,77 | 87,7 | 2,66 | 32,0 | K (%69) |
| Stresli | 85 | 0,08 / 0,07 / 0,85 | 87,9 | 2,72 | 32,6 | K (%84) |

Metin değişikliği:
* Bildiride "beş kademe pratikte iki rejime (V/K) iner" deniyor. Yeni sonuçlarda konfor, enerji
  ve süre CLS ile **monoton ve kademeli** değişiyor: 83,9 → 84,9 → 86,5 → 87,7 → 87,9.
* Baskın rejim düşük/orta CLS'de **Dengeli**, yüksek CLS'de **Konfor**. Rejim geçişi CLS 50 ile 65
  arasında; bu bildirideki "50–65 aralığı" gözlemiyle tutarlı.
* "Bildirideki V rejimi" yerine V/D/K üçlüsü ve yüzde dağılımı raporlanmalı.
* Sonuçlar bölümündeki "beş kademeli şema tasarımın öngördüğü kadar kademeli uyarlama
  sağlayamamıştır" cümlesi artık geçerli değil; kaldırılmalı veya ters yönde düzeltilmeli.

## 5. Tablo 4 (yeni, Keçiören → Bilkent, SoC %75, tohum 0)

| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor |
|---|---|---|---|---|---|
| Geleneksel (A*) | 21,0 | 34,9 | 2,72 | 70,5 | 82,4 |
| AffectEV / Düşük CLS (A* ile aynı rota) | 21,0 | 34,9 | 2,72 | 70,5 | 82,4 |
| AffectEV / Yüksek CLS | 23,0 | 40,9 | 2,89 | 70,2 | 83,5 |

Metindeki değerler bunlarla değiştirilmeli: "23 km → 44 km", "4,99 → 9,18 kWh" ve "39 → 55 (%41)".
Düşük CLS'nin A* ile aynı rotayı seçmesi bildiriyle **tutarlı**.

## 6. Şekiller

* **Şekil 1:** `results/sekil1_pareto.png` — gerçek D-NSGA-II çalıştırmasının cephesi. Gri ×
  işaretleri o çalıştırmada değerlendirilen ve baskılanan çözümlerdir.
* **Şekil 2:** `results/sekil2_qlearning.png` — 1000 bölüm, 10 tohum.
  * Metin: "Ödül ilk 100 bölümde negatif değerlerden yükselmekte, ~400. bölümden itibaren
    7,5 düzeyinde plato; rastgele politika −7,5" ifadesi tutmuyor.
  * Yeni ifade: "Hareketli ortalama ödül ~200. bölümde ≈9 düzeyine yükselmekte ve son 200 bölümde
    9,97 ± 0,57 (tohumlar arası) ortalamaya ulaşmaktadır. Rastgele politika ≈4,8'de kalmaktadır.
    Q-Learning 64. bölümden itibaren rastgele politikanın 1 std üzerindedir."
  * Ödül Dn. 8'deki konfor terimi nedeniyle pozitif tabanlıdır.
* **Şekil 3:** `results/sekil3_harita.png` — rotalar artık gerçek OSM yol ağı üzerindeki gerçek
  rotalardır. Başlık "şematik karşılaştırma" yerine "OSM yol ağı üzerinde rota karşılaştırması"
  olabilir.

## 7. Yöntem bölümüne eklenecek netleştirmeler

1. **Konfor bileşenleri (Dn. 2):**
   * N_intersection: OSM `highway=traffic_signals` düğümleri.
   * N_stop: rota üzerindeki (≤25 m) `highway=bus_stop`.
   * D_traffic: uzunluk ağırlıklı ortalama yoğunluk (0–100).
2. **Dn. 3c:** a·d = ½v² her kalkış için. OSM'de yükseklik yok, α = 0 alındı.
3. **D-NSGA-II:**
   * Amaçlar enerji, süre ve (100 − konfor).
   * Operatörler ortak düğüm çaprazlaması ve alt rota yeniden yönlendirme mutasyonudur.
   * CLS ağırlıkları optimizasyonda değil, **Pareto cephesinden karar aşamasında** kullanılır
     (min-max normalize ağırlıklı toplam).
   * "NSGA-II (CLS yok)" aynı cepheden eşit ağırlıkla seçim yapar.
4. **Senaryo üretimi:**
   * Master tohum 2026 ile rastgele 50 başlangıç–varış çifti (kuş uçuşu 5–20 km).
   * Başlangıç SoC'si U(30, 90).
   * 10 sentetik trafik tohumu, aynı tohum bütün senaryolarda aynı şehir trafiğini temsil eder.
5. **Q-Learning:**
   * Durum ayrıklaştırması: 5 CLS × 3 SoC × 3 trafik × 4 önceki rota tipi.
   * Sentetik kullanıcı: β(CLS) = sigmoid((CLS−50)/10), SoC < 40'ta menzil kaygısı, N(0; 0,2) gürültü.
   * delay = (t_a − t_min)/t_min.
6. **Yol ağı:** OSM (25.09.2026), 17.037 düğüm, 31.614 yönlü kenar. "Rastgele belirlenmiş 50
   senaryo" ifadesi artık doğru.

## 8. Dürüstçe belirtilmesi önerilen sınırlılıklar

* 3000 çalıştırmanın hiçbirinde SoC %20'nin altına düşmedi (şehir içi 5–20 km). Şarj durağı
  mekanizması kodda var ve test edildi, ancak deneylerde tetiklenmedi. "Menzil kısıtları güvenli
  yönetildi" ifadesi, "şehir içi senaryolarda menzil kısıtı bağlayıcı olmamıştır" şeklinde
  yumuşatılmalı.
* OSM'de Ankara sinyalize kavşak etiketlemesi seyrek (bbox'ta 1.791 düğüm). Bu yüzden konfor
  skorları yüksek (80–88) ve farklar görece küçük.
* Trafik ve kullanıcı modeli sentetik. CLS kontrollü parametre (bildiride zaten belirtilmiş).
