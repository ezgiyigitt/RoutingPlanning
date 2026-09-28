Tablo 2: 50 Şehir İçi Senaryosunda Performans Karşılaştırması (Ablasyon)

| Yöntem | Seyahat Süresi (dk) | Enerji Tüketimi (kWh) | Konfor Skoru (0-100) | Ortalama Kavşak | Mesafe (km) | Şarj durağı |
|---|---|---|---|---|---|---|
| Dijkstra (mesafe) | 48.7 ± 13.3 | 4.60 ± 1.16 | 62.6 ± 11.4 | 35.5 | 20.7 ± 5.3 | 0/500 |
| A* (süre) | 39.2 ± 9.5 | 4.87 ± 1.48 | 74.3 ± 7.5 | 19.7 | 24.9 ± 9.6 | 0/500 |
| NSGA-II (CLS yok) | 39.5 ± 9.8 | 4.84 ± 1.46 | 74.2 ± 7.6 | 19.8 | 24.4 ± 9.3 | 0/500 |
| AffectEV (CLS uyarlamalı) | 40.4 ± 10.3 | 5.05 ± 1.56 | 75.0 ± 7.3 | 18.8 | 25.6 ± 9.8 | 0/2500 |

Not: Değerler 50 senaryo × 10 tohum üzerinden ortalama ± standart sapmadır. AffectEV satırı beş CLS düzeyinin (15, 30, 50, 65, 85) tamamını kapsar (2500 çalıştırma). Ortalama Kavşak: rotadaki kavşak kümesi sayısı (N_intersection; tanım için affectev/network.py).
