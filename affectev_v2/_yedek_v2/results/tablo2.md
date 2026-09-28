Tablo 2: 50 Şehir İçi Senaryosunda Performans Karşılaştırması (Ablasyon)

| Yöntem | Seyahat Süresi (dk) | Enerji Tüketimi (kWh) | Konfor Skoru (0-100) | Ortalama Kavşak | Mesafe (km) | Şarj durağı |
|---|---|---|---|---|---|---|
| Dijkstra (mesafe) | 32.6 ± 11.0 | 2.21 ± 0.73 | 79.4 ± 7.5 | 10.6 | 17.0 ± 5.4 | 0/500 |
| A* (süre) | 28.1 ± 8.5 | 2.44 ± 0.93 | 84.8 ± 5.1 | 3.2 | 19.1 ± 6.7 | 0/500 |
| NSGA-II (CLS yok) | 29.1 ± 8.8 | 2.28 ± 0.76 | 85.2 ± 4.6 | 3.1 | 18.3 ± 5.9 | 0/500 |
| AffectEV (CLS uyarlamalı) | 30.6 ± 9.3 | 2.45 ± 0.91 | 86.2 ± 4.4 | 2.7 | 19.6 ± 6.8 | 0/2500 |

Not: Değerler 50 senaryo × 10 tohum üzerinden ortalama ± standart sapmadır. AffectEV satırı beş CLS düzeyinin (15, 30, 50, 65, 85) tamamını kapsar (2500 çalıştırma). Ortalama Kavşak: rotadaki sinyalize kavşak sayısı (N_intersection).
