Tablo 4: Keçiören–Bilkent Senaryosu Rota Üretimi Karşılaştırması (başlangıç SoC %75, tohum 0)

| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor (0-100) | Kavşak | Duruş | Seçenek |
|---|---|---|---|---|---|---|---|---|
| Geleneksel (A*) | 21.0 | 42.4 | 4.54 | 67.4 | 67.7 | 22 | 29.9 | — |
| AffectEV / Düşük CLS (15) | 21.0 | 42.4 | 4.54 | 67.4 | 67.7 | 22 | 29.9 | Verimlilik |
| AffectEV / Yüksek CLS (85) | 21.1 | 42.9 | 4.57 | 67.4 | 67.8 | 22 | 29.8 | Konfor |

Yüksek CLS rotasının A*'a göre değişimi: konfor +0.1%, enerji +0.8%, mesafe +0.5%, süre +1.0%.
Düşük CLS rotası A* ile aynı mı: evet.
Cephe büyüklüğü: 4 çözüm; etkinleşen seçenekler — düşük CLS: Verimlilik, yüksek CLS: Konfor.

10 trafik tohumu ortalaması:

| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor |
|---|---|---|---|---|---|
| Geleneksel (A*) | 21.0 | 40.5 | 4.44 | 67.6 | 69.7 |
| AffectEV / Düşük CLS (15) | 21.0 | 40.5 | 4.44 | 67.6 | 69.7 |
| AffectEV / Yüksek CLS (85) | 21.1 | 41.4 | 4.51 | 67.5 | 69.8 |
