# Deneysel Optimizasyon Sonuçları

Bu rapor, önerilen *ÇAMD (Çok Amaçlı Karar Verme)* yönteminin klasik Dijkstra algoritmalarıyla enerji, seyahat süresi ve sürücü konforu/CLS alanında kıyaslamalı sonuçlarını içermektedir.

## Senaryo: Kızılay ➔ Çayyolu (Orta Mesafe - Şehir İçi)
### Sürücü Durumu: Enerjik (CLS=20)
**Atanan Ağırlıklar:** Zaman=`%48`, Enerji=`%45`, Konfor=`%5`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 19.0 km | 25 dk | 4.37 kWh | 0.68 | 0.201 |
| B2: Hızlı Yol | 20.0 km | 24 dk | 4.56 kWh | 0.581 | 0.195 |
| B3: Eko Rota | 19.0 km | 25 dk | 4.37 kWh | 0.68 | 0.201 |
| **Önerilen (MO)** | **20.0 km** | **24 dk** | **4.56 kWh** | **0.581** | **0.195** |


### Sürücü Durumu: Nötr (CLS=45)
**Atanan Ağırlıklar:** Zaman=`%23`, Enerji=`%56`, Konfor=`%20`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 19.0 km | 25 dk | 4.37 kWh | 0.68 | 0.275 |
| B2: Hızlı Yol | 20.0 km | 24 dk | 4.56 kWh | 0.581 | 0.258 |
| B3: Eko Rota | 19.0 km | 25 dk | 4.37 kWh | 0.68 | 0.275 |
| **Önerilen (MO)** | **20.0 km** | **24 dk** | **4.56 kWh** | **0.581** | **0.258** |


### Sürücü Durumu: Yorgun (CLS=80)
**Atanan Ağırlıklar:** Zaman=`%5`, Enerji=`%22`, Konfor=`%71`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 19.0 km | 25 dk | 4.37 kWh | 0.68 | 0.537 |
| B2: Hızlı Yol | 20.0 km | 24 dk | 4.56 kWh | 0.581 | 0.468 |
| B3: Eko Rota | 19.0 km | 25 dk | 4.37 kWh | 0.68 | 0.537 |
| **Önerilen (MO)** | **20.0 km** | **24 dk** | **4.56 kWh** | **0.581** | **0.467** |


## Senaryo: Ulus ➔ Gölbaşı (Orta-Uzun Mesafe - Çevre Yolu)
### Sürücü Durumu: Enerjik (CLS=20)
**Atanan Ağırlıklar:** Zaman=`%48`, Enerji=`%45`, Konfor=`%5`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 33.0 km | 35 dk | 7.14 kWh | 0.635 | 0.281 |
| B2: Hızlı Yol | 33.0 km | 35 dk | 7.14 kWh | 0.635 | 0.281 |
| B3: Eko Rota | 33.0 km | 35 dk | 7.14 kWh | 0.664 | 0.283 |
| **Önerilen (MO)** | **33.0 km** | **35 dk** | **7.14 kWh** | **0.635** | **0.281** |


### Sürücü Durumu: Nötr (CLS=45)
**Atanan Ağırlıklar:** Zaman=`%23`, Enerji=`%56`, Konfor=`%20`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 33.0 km | 35 dk | 7.14 kWh | 0.635 | 0.344 |
| B2: Hızlı Yol | 33.0 km | 35 dk | 7.14 kWh | 0.635 | 0.344 |
| B3: Eko Rota | 33.0 km | 35 dk | 7.14 kWh | 0.664 | 0.350 |
| **Önerilen (MO)** | **33.0 km** | **35 dk** | **7.14 kWh** | **0.635** | **0.344** |


### Sürücü Durumu: Yorgun (CLS=80)
**Atanan Ağırlıklar:** Zaman=`%5`, Enerji=`%22`, Konfor=`%71`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 33.0 km | 35 dk | 7.14 kWh | 0.635 | 0.534 |
| B2: Hızlı Yol | 33.0 km | 35 dk | 7.14 kWh | 0.635 | 0.534 |
| B3: Eko Rota | 33.0 km | 35 dk | 7.14 kWh | 0.664 | 0.555 |
| **Önerilen (MO)** | **33.0 km** | **35 dk** | **7.14 kWh** | **0.635** | **0.534** |


## Senaryo: Bilkent ➔ Esenboğa Havalimanı (Uzun Mesafe - Karma Yol)
### Sürücü Durumu: Enerjik (CLS=20)
**Atanan Ağırlıklar:** Zaman=`%48`, Enerji=`%45`, Konfor=`%5`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 50.0 km | 59 dk | 10.5 kWh | 0.714 | 0.424 |
| B2: Hızlı Yol | 50.0 km | 59 dk | 10.5 kWh | 0.714 | 0.424 |
| B3: Eko Rota | 50.0 km | 59 dk | 10.5 kWh | 0.722 | 0.425 |
| **Önerilen (MO)** | **58.0 km** | **63 dk** | **12.05 kWh** | **0.603** | **0.459** |


### Sürücü Durumu: Nötr (CLS=45)
**Atanan Ağırlıklar:** Zaman=`%23`, Enerji=`%56`, Konfor=`%20`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 50.0 km | 59 dk | 10.5 kWh | 0.714 | 0.473 |
| B2: Hızlı Yol | 50.0 km | 59 dk | 10.5 kWh | 0.714 | 0.473 |
| B3: Eko Rota | 50.0 km | 59 dk | 10.5 kWh | 0.722 | 0.475 |
| **Önerilen (MO)** | **68.0 km** | **72 dk** | **14.09 kWh** | **0.544** | **0.540** |


### Sürücü Durumu: Yorgun (CLS=80)
**Atanan Ağırlıklar:** Zaman=`%5`, Enerji=`%22`, Konfor=`%71`

| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |
|--------|--------|------|-------------|------------------|------|
| B1: Kısa Yol | 50.0 km | 59 dk | 10.5 kWh | 0.714 | 0.630 |
| B2: Hızlı Yol | 50.0 km | 59 dk | 10.5 kWh | 0.714 | 0.630 |
| B3: Eko Rota | 50.0 km | 59 dk | 10.5 kWh | 0.722 | 0.636 |
| **Önerilen (MO)** | **76.0 km** | **74 dk** | **15.8 kWh** | **0.532** | **0.553** |


