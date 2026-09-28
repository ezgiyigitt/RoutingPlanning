# Tablo 5.2 (Guncellenmis) — 50 Sehir Ici Senaryo Performans Karsilastirmasi

Asagidaki ortalamalar 50 senaryonun sonuclarindan hesaplanmistir.

| Algoritma Turu | Hedef Strateji | Ort. Seyahat Suresi (dk) | Ort. Enerji Tuketimi (kWh) | Ort. Konfor Skoru (0-100) |
|----------------|---------------|--------------------------|---------------------------|---------------------------|
| Standart (Dijkstra) | En Kisa Mesafe | 44.2 | 7.1 | 46.8 |
| Standart (A*) | En Hizli Sure | 42.0 | 7.7 | 50.5 |
| **AffectEV (D-NSGA-II)** | **Cok Amacli (Dengeli)** | **45.3** | **8.0** | **50.3** |


## CLS Seviyesine Gore AffectEV Konfor Skoru Degisimi

| Surucu Durumu | CLS | Ort. Konfor (0-100) | Ort. Enerji (kWh) | Ort. Sure (dk) |
|--------------|-----|---------------------|-------------------|----------------|
| Cok Enerjik (CLS=15) | 15 | 47.3 | 7.1 | 43.5 |
| Enerjik (CLS=30) | 30 | 49.6 | 7.8 | 44.7 |
| Notr (CLS=50) | 50 | 49.6 | 7.8 | 44.7 |
| Yorgun (CLS=65) | 65 | 52.5 | 8.6 | 46.7 |
| Cok Yorgun/Stresli (CLS=85) | 85 | 52.5 | 8.6 | 46.7 |

> **Not:** Konfor skoru hesabi: rota tipi karmasikliginin tersi; daha sakin/bulvar agirlikli rotalar daha yuksek skor alir.
