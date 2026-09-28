# Kod sonuçları ↔ bildiri (187.pdf)

Her satırda solda bildirideki değer, sağda bu kodun ürettiği değer ve göreli fark vardır.
Kod değerleri `python experiments/run_all.py` ile üretilir; bu dosya da otomatik yazılır.

## Tablo 2 — 50 senaryo × 10 tohum

| Yöntem | Süre bildiri | Süre kod | Enerji bildiri | Enerji kod | Konfor bildiri | Konfor kod | Kavşak bildiri | Kavşak kod |
|---|---|---|---|---|---|---|---|---|
| Dijkstra | 44.2 ± 13.4 | 48.7 ± 13.3 (+10%) | 7.1 ± 2.2 | 4.6 ± 1.2 (-35%) | 46.8 ± 6.9 | 62.6 ± 11.4 (+34%) | 32.4 | 35.5 (+10%) |
| A* | 42.0 ± 11.7 | 39.2 ± 9.5 (-7%) | 7.7 ± 2.7 | 4.9 ± 1.5 (-37%) | 50.5 ± 5.8 | 74.3 ± 7.5 (+47%) | 30.1 | 19.7 (-35%) |
| NSGA-II | 44.7 ± 13.0 | 39.5 ± 9.8 (-12%) | 7.8 ± 2.9 | 4.8 ± 1.5 (-38%) | 49.6 ± 7.5 | 74.2 ± 7.6 (+50%) | 28.5 | 19.8 (-31%) |
| AffectEV | 45.3 ± 13.3 | 40.4 ± 10.3 (-11%) | 8.0 ± 2.9 | 5.0 ± 1.6 (-37%) | 50.3 ± 6.9 | 75.0 ± 7.3 (+49%) | 22.6 | 18.8 (-17%) |

## Tablo 3 — CLS düzeyleri

| CLS | Konfor bildiri | Konfor kod | Enerji bildiri | Enerji kod | Süre bildiri | Süre kod | Rejim bildiri | Rejim kod |
|---|---|---|---|---|---|---|---|---|
| 15 | 47.3 | 72.7 | 7.1 | 4.68 | 43.5 | 40.0 | V | D (%65) |
| 30 | 49.6 | 73.9 | 7.8 | 4.80 | 44.7 | 39.5 | V | D (%84) |
| 50 | 49.6 | 75.0 | 7.8 | 4.96 | 44.7 | 39.6 | V | D (%82) |
| 65 | 52.5 | 76.7 | 8.6 | 5.38 | 46.7 | 41.3 | K | K (%56) |
| 85 | 52.5 | 76.8 | 8.6 | 5.42 | 46.7 | 41.7 | K | K (%66) |

Göreli değişim CLS 15 → 85:

| | Bildiri | Kod |
|---|---|---|
| Konfor | +11% | +6% |
| Enerji | +21% | +16% |
| Süre | +7% | +4% |

## Tablo 4 — Keçiören → Bilkent (SoC %75, tohum 0)

| Satır | Bildiri (km / dk / kWh / SoC / konfor) | Kod (km / dk / kWh / SoC / konfor) |
|---|---|---|
| A* | 23.0 / 43.3 / 4.99 / 66.7 / 39.0 | 21.0 / 42.4 / 4.54 / 67.4 / 67.7 |
| Düşük CLS | 23.0 / 43.3 / 4.99 / 66.7 / 39.0 | 21.0 / 42.4 / 4.54 / 67.4 / 67.7 |
| Yüksek CLS | 44.0 / 52.8 / 9.18 / 59.7 / 55.0 | 21.1 / 42.9 / 4.57 / 67.4 / 67.8 |

Yüksek CLS / A*: bildiri konfor +41%, enerji +84%, mesafe +91% — kod konfor +0.1%, enerji +0.8%, mesafe +0.5%.
Düşük CLS = A* rotası: bildiri evet — kod evet.

## Şekil 2 — Q-Learning

| | Bildiri | Kod |
|---|---|---|
| Son 200 bölüm ortalama ödül | ≈7.5 | 9.03 |
| Rastgele politika | ≈-7.5 | 4.47 |
| Q-Learning − rastgele (son 200) | ≈15.0 | 4.61 |
| İlk 100 bölüm ortalaması | negatif | 5.52 |
