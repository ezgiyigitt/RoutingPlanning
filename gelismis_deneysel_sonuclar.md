# Geliştirilmiş Deneysel Sonuçlar — ML + Sürekli Duygu

Bu rapor; Random Forest tabanlı CLS tahmini ve sürekli duygu regresyonu ile elde edilen rota optimizasyon sonuçlarını klasik ÇAMD ile karşılaştırır.

## Senaryo: Kızılay ➔ Çayyolu (Orta Mesafe - Şehir İçi)
### Enerjik   (CLS=15)
**ML Tahmini CLS:** 14.1  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=39.45% Süre=56.64% Konfor=3.91%
**ML+Duygu Ağırlıkları:** Enerji=42.73% Süre=27.72% Konfor=29.54%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 19.0 km | 25.3 dk | 4.37 kWh | 0.680 | 0.1911 | 0.3224 |
| B2: Hızlı Yol | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.1853 | 0.2938 |
| B3: Eko Rota | 19.0 km | 25.3 dk | 4.37 kWh | 0.680 | 0.1911 | 0.3224 |
| ÇAMD (Heuristik) | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.1853 | 0.2938 |
| **ML+Duygu (Önerilen)** | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.1853 | 0.2938 |

### Nötr      (CLS=45)
**ML Tahmini CLS:** 32.8  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=56.78% Süre=23.04% Konfor=20.18%
**ML+Duygu Ağırlıkları:** Enerji=42.69% Süre=27.62% Konfor=29.69%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 19.0 km | 25.3 dk | 4.37 kWh | 0.680 | 0.2754 | 0.3232 |
| B2: Hızlı Yol | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.2576 | 0.2944 |
| B3: Eko Rota | 19.0 km | 25.3 dk | 4.37 kWh | 0.680 | 0.2754 | 0.3232 |
| ÇAMD (Heuristik) | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.2576 | 0.2944 |
| **ML+Duygu (Önerilen)** | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.2576 | 0.2944 |

### Yorgun    (CLS=75)
**ML Tahmini CLS:** 51.0  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=29.78% Süre=7.63% Konfor=62.59%
**ML+Duygu Ağırlıkları:** Enerji=42.66% Süre=27.62% Konfor=29.72%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 19.0 km | 25.3 dk | 4.37 kWh | 0.680 | 0.4908 | 0.3234 |
| B2: Hızlı Yol | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.4299 | 0.2945 |
| B3: Eko Rota | 19.0 km | 25.3 dk | 4.37 kWh | 0.680 | 0.4908 | 0.3234 |
| ÇAMD (Heuristik) | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.4299 | 0.2945 |
| **ML+Duygu (Önerilen)** | 20.0 km | 24.0 dk | 4.559 kWh | 0.581 | 0.4299 | 0.2945 |

## Senaryo: Ulus ➔ Gölbaşı (Orta-Uzun Mesafe - Çevre Yolu)
### Enerjik   (CLS=15)
**ML Tahmini CLS:** 14.1  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=39.45% Süre=56.64% Konfor=3.91%
**ML+Duygu Ağırlıkları:** Enerji=42.73% Süre=27.72% Konfor=29.54%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.2697 | 0.3745 |
| B2: Hızlı Yol | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.2697 | 0.3745 |
| B3: Eko Rota | 33.0 km | 35.0 dk | 7.143 kWh | 0.664 | 0.2709 | 0.3830 |
| ÇAMD (Heuristik) | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.2697 | 0.3745 |
| **ML+Duygu (Önerilen)** | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.2697 | 0.3745 |

### Nötr      (CLS=45)
**ML Tahmini CLS:** 32.8  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=56.78% Süre=23.04% Konfor=20.18%
**ML+Duygu Ağırlıkları:** Enerji=42.69% Süre=27.62% Konfor=29.69%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.3442 | 0.3751 |
| B2: Hızlı Yol | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.3442 | 0.3751 |
| B3: Eko Rota | 33.0 km | 35.0 dk | 7.143 kWh | 0.664 | 0.3500 | 0.3837 |
| ÇAMD (Heuristik) | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.3442 | 0.3751 |
| **ML+Duygu (Önerilen)** | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.3442 | 0.3751 |

### Yorgun    (CLS=75)
**ML Tahmini CLS:** 51.0  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=29.78% Süre=7.63% Konfor=62.59%
**ML+Duygu Ağırlıkları:** Enerji=42.66% Süre=27.62% Konfor=29.72%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.5006 | 0.3752 |
| B2: Hızlı Yol | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.5006 | 0.3752 |
| B3: Eko Rota | 33.0 km | 35.0 dk | 7.143 kWh | 0.664 | 0.5187 | 0.3838 |
| ÇAMD (Heuristik) | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.5006 | 0.3752 |
| **ML+Duygu (Önerilen)** | 33.0 km | 35.0 dk | 7.143 kWh | 0.635 | 0.5006 | 0.3752 |

## Senaryo: Bilkent ➔ Esenboğa Havalimanı (Uzun Mesafe - Karma Yol)
### Enerjik   (CLS=15)
**ML Tahmini CLS:** 14.1  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=39.45% Süre=56.64% Konfor=3.91%
**ML+Duygu Ağırlıkları:** Enerji=42.73% Süre=27.72% Konfor=29.54%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.4168 | 0.4996 |
| B2: Hızlı Yol | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.4168 | 0.4996 |
| B3: Eko Rota | 50.0 km | 59.1 dk | 10.501 kWh | 0.722 | 0.4171 | 0.5021 |
| ÇAMD (Heuristik) | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.4168 | 0.4996 |
| **ML+Duygu (Önerilen)** | 76.0 km | 73.7 dk | 15.799 kWh | 0.532 | 0.5484 | 0.5634 |

### Nötr      (CLS=45)
**ML Tahmini CLS:** 32.8  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=56.78% Süre=23.04% Konfor=20.18%
**ML+Duygu Ağırlıkları:** Enerji=42.69% Süre=27.62% Konfor=29.69%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.4734 | 0.5001 |
| B2: Hızlı Yol | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.4734 | 0.5001 |
| B3: Eko Rota | 50.0 km | 59.1 dk | 10.501 kWh | 0.722 | 0.4750 | 0.5026 |
| ÇAMD (Heuristik) | 68.0 km | 71.6 dk | 14.089 kWh | 0.544 | 0.5398 | 0.5341 |
| **ML+Duygu (Önerilen)** | 76.0 km | 73.7 dk | 15.799 kWh | 0.532 | 0.5794 | 0.5635 |

### Yorgun    (CLS=75)
**ML Tahmini CLS:** 51.0  |  Duygu: yor=0.25 str=0.25 sak=0.25 ene=0.25

**ÇAMD Ağırlıkları:**  Enerji=29.78% Süre=7.63% Konfor=62.59%
**ML+Duygu Ağırlıkları:** Enerji=42.66% Süre=27.62% Konfor=29.72%

| Yöntem | Mesafe | Süre | Enerji | Konfor | F_ÇAMD | F_ML |
|--------|--------|------|--------|--------|--------|------|
| B1: Kısa Yol | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.6020 | 0.5002 |
| B2: Hızlı Yol | 50.0 km | 59.1 dk | 10.501 kWh | 0.714 | 0.6020 | 0.5002 |
| B3: Eko Rota | 50.0 km | 59.1 dk | 10.501 kWh | 0.722 | 0.6072 | 0.5027 |
| ÇAMD (Heuristik) | 76.0 km | 73.7 dk | 15.799 kWh | 0.532 | 0.5587 | 0.5634 |
| **ML+Duygu (Önerilen)** | 76.0 km | 73.7 dk | 15.799 kWh | 0.532 | 0.5587 | 0.5634 |


## Anonim Veri Kayıt İstatistikleri

- **toplam_sefer**: 1
- **toplam_km**: 15.2
- **ort_mesafe_km**: 15.16
- **ort_cls**: 16.9
- **ort_hiz_kmsa**: 50.1
- **mod_dagilimi**: {'enerjik': 1}
- **ilk_sefer**: 2026-04-15
- **son_sefer**: 2026-04-15

## Özellik Önemleri (CLS ML Modeli)

- `ear_norm                      ` 0.7951  ███████████████████████████████████████
- `kas_norm                      ` 0.0854  ████
- `blink_norm                    ` 0.0797  ███
- `stres_egilimi                 ` 0.0079  
- `bugun_km_norm                 ` 0.0058  
- `yorgunluk_esigi_inv           ` 0.0055  
- `son_cls_ort                   ` 0.0053  

## ML Model Performansı (5-fold CV)

- **rmse_ort**: 4.75
- **rmse_std**: 0.27
- **n_ornek**: 300
- **mod**: Sentetik
