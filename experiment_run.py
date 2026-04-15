import os
import sys

# Proje dizinini yola ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ev_rota_planner import Graf, yol_metrikleri, ANKARA_DUGUMLER, YOLLAR
from kognitif_motor import CokAmacliRotaOptimizatoru

def run_experiment():
    with open("deneysel_sonuclar.md", "w", encoding="utf-8") as f:
        def w(text=""):
            f.write(text + "\n")
            
        w("# Deneysel Optimizasyon Sonuçları\n")
        w("Bu rapor, önerilen *ÇAMD (Çok Amaçlı Karar Verme)* yönteminin klasik Dijkstra algoritmalarıyla "
          "enerji, seyahat süresi ve sürücü konforu/CLS alanında kıyaslamalı sonuçlarını içermektedir.\n")
        
        graf = Graf()
        arac = "Tesla Model 3"
        
        # Test Senaryoları (Kalkış -> Varış)
        senaryolar = [
            ("Kızılay", "Çayyolu", "Orta Mesafe - Şehir İçi"),
            ("Ulus", "Gölbaşı", "Orta-Uzun Mesafe - Çevre Yolu"),
            ("Bilkent", "Esenboğa Havalimanı", "Uzun Mesafe - Karma Yol")
        ]
        
        # Kognitif Yük Senaryoları
        cls_durumlari = [
            (20.0, "Enerjik (CLS=20)"),
            (45.0, "Nötr (CLS=45)"),
            (80.0, "Yorgun (CLS=80)")
        ]

        for (bas, bit, aciklama) in senaryolar:
            w(f"## Senaryo: {bas} ➔ {bit} ({aciklama})")
            
            # 1. Klasik (Baseline) Algoritmalar
            baselines = ["mesafe", "sure", "enerji"]
            baseline_results = {}
            for b in baselines:
                yol_b, _ = graf.dijkstra(bas, bit, b)
                if not yol_b: continue
                met = yol_metrikleri(yol_b, arac)
                konf = CokAmacliRotaOptimizatoru.rota_konfor_skoru(yol_b, ANKARA_DUGUMLER, YOLLAR)
                baseline_results[b] = {
                    "sure_dk": round(met["sure_dk"]),
                    "enerji_kwh": round(met["enerji_kwh"], 2),
                    "konfor": round(konf, 3),
                    "mesafe_km": round(met["mesafe_km"], 1)
                }
            
            # 2. Önerilen (ÇAMD) Algoritma
            for cls_val, cls_isim in cls_durumlari:
                w_e, w_t, w_c = CokAmacliRotaOptimizatoru.agirlik_hesapla(cls_val)
                yol_mo, _ = graf.cok_amacli_dijkstra(bas, bit, w_e, w_t, w_c)
                if not yol_mo: continue
                met_mo = yol_metrikleri(yol_mo, arac)
                konf_mo = CokAmacliRotaOptimizatoru.rota_konfor_skoru(yol_mo, ANKARA_DUGUMLER, YOLLAR)
                f_skor = CokAmacliRotaOptimizatoru.f_objective(
                    met_mo["enerji_kwh"], met_mo["sure_dk"], konf_mo, w_e, w_t, w_c
                )
                
                w(f"### Sürücü Durumu: {cls_isim}")
                w(f"**Atanan Ağırlıklar:** Zaman=`%{int(w_t*100)}`, Enerji=`%{int(w_e*100)}`, Konfor=`%{int(w_c*100)}`\n")
                w("| Yöntem | Mesafe | Süre | Enerji Tük. | Konfor Skoru (C) | F(r) |")
                w("|--------|--------|------|-------------|------------------|------|")
                
                isimler = {
                    "mesafe": "B1: Kısa Yol",
                    "sure": "B2: Hızlı Yol",
                    "enerji": "B3: Eko Rota"
                }
                
                for b in baselines:
                    r = baseline_results[b]
                    b_f = CokAmacliRotaOptimizatoru.f_objective(r["enerji_kwh"], r["sure_dk"], r["konfor"], w_e, w_t, w_c)
                    w(f"| {isimler[b]} | {r['mesafe_km']} km | {r['sure_dk']} dk | {r['enerji_kwh']} kWh | {r['konfor']} | {b_f:.3f} |")
                
                w(f"| **Önerilen (MO)** | **{round(met_mo['mesafe_km'],1)} km** | **{round(met_mo['sure_dk'])} dk** | **{round(met_mo['enerji_kwh'],2)} kWh** | **{round(konf_mo,3)}** | **{f_skor:.3f}** |")
                w("\n")
    print("Deneysel sonuçlar deneysel_sonuclar.md dosyasına başarıyla kaydedildi.")

if __name__ == "__main__":
    run_experiment()
