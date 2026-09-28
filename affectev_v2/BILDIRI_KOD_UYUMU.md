# Bildiri (187.pdf) ↔ kod uyumu — v3 (28 Eylül 2026)

Bu dosya üç şeyi anlatır: bildiri ile kod arasındaki farklar, v3'te yapılan düzeltmeler ve kodun
bildiride raporlanan sayılara ne kadar yaklaştığı. Güncel sayısal karşılaştırmayı
`python experiments/run_all.py` üretir ve `results/bildiri_karsilastirma.md` dosyasına yazar.

## 1. Eski kod (kök klasör) ile bildiri arasındaki farklar

Eski kod bildirideki sayıları birebir veriyor, ancak bu sayıları bildiride anlatılan yöntemle üretmiyor:

| Bildiri | Eski kod |
|---|---|
| D-NSGA-II (100/50, p_c 0,8, p_m 0,1) | AffectEV satırı ağırlıklı toplam Dijkstra (`cok_amacli_dijkstra`); NSGA-II çalışmıyor |
| 50 rastgele senaryo × 10 tohum | 10 sabit güzergâh × 5 CLS; deterministik, tohum yok |
| OSM tabanlı Ankara ağı | 98 düğümlük elle yazılmış graf (`ANKARA_DUGUMLER/YOLLAR`) |
| Dn. 2 konfor (kavşak, durak, trafik) | Yol tipi ortalama maliyeti: (1 − ort. maliyet) × 100 |
| Dn. 3 enerji, Tablo 1 araç parametreleri | Tablo tabanlı kWh/km × trafik çarpanı × 1,08 |
| Dn. 4–5, SoC_min %20 | SoC hesaplanmıyor; eşik 10 |
| Tablo 2 "Ortalama Kavşak" | Hiçbir scriptte hesaplanmıyor |
| Şekil 1 Pareto cephesi | 2 noktalı tarama; "Dengeli" noktası iki noktanın ortalaması olarak ekleniyor |
| Şekil 2 Q-Learning (1000 bölüm, 10 tohum) | Ödül N(8,3)/N(−15,4) × (1 − e^(−ep/120)) formülüyle çiziliyor |
| Dn. 6 durum / eylem uzayı | Farklı durum (origin, dest, ASI, saat…) ve eylemler (fast/economic/scenic…) |
| Tablo 4 "Geleneksel (A*)" | Aslında Dijkstra-mesafe rotası |
| Şekil 3 harita | Elle koordinat + Bezier eğrisi |

## 2. affectev_v2 ile bildiri arasındaki farklar ve v3'teki düzeltmeler

| # | Konu | Bildiri | v2 | v3 |
|---|---|---|---|---|
| 1 | CLS'nin rotayı seçmesi | Cephe üç seçenek sunar (Konfor, Dengeli, Verimlilik); CLS bunlardan birini etkinleştirir (Bölüm 3, Şekil 1) | Tüm cepheden ağırlıklı seçim | **Üç seçenekten biri etkinleşir** (`nsga2.activate`). Tablo 3 rejim sütunu doğrudan bu seçenektir |
| 2 | Ağırlıkların hedef fonksiyonundaki yeri | "hedef fonksiyonunda … ağırlıklarla birleştirilir" | Yalnızca karar aşaması | F = w_e·ê + w_t·t̂ + w_c·ĉ karar fonksiyonu. Pozitif ağırlıkla ölçeklenen amaçlar Pareto baskınlığını değiştirmediği için cephe CLS'den bağımsızdır; bu durum kodda belgelendi |
| 3 | N_intersection (Dn. 2) | Rotadaki sinyalize kavşak sayısı | Yalnızca OSM `traffic_signals` etiketi → rota başına 3–10 | **Ana yolların eş düzey kavşakları + OSM sinyalleri, 50 m'de kümelenmiş** → 19–36 (bildiri 22,6–32,4) |
| 4 | N_stop (Dn. 2) | Rotadaki durak sayısı | Otobüs durağı | **Beklenen araç duruş sayısı**: kavşakta durma + tıkanıklıkta dur-kalk |
| 5 | Dn. 3c ivme terimi | E_accel = m·a·d | a·d = kalkış başına ½v² | **a = ortalama pozitif ivme (RPA)**, ortalama hıza bağlı. Enerji 0,13 → 0,22 kWh/km (bildiri Tablo 4: 0,217) |
| 6 | Kavşak gecikmesi | — | Yalnızca etiketli sinyallerde | Her kavşak kümesinde |
| 7 | Tablo 3 rejim | V / K | En yakın kategoriye atama | Etkinleşen seçenek |
| 8 | Şekil 1 senaryosu | Belirtilmemiş | Keçiören–Bilkent | Sincan → Ulus (eski koddaki Şekil 1 senaryosu). Keçiören–Bilkent cephesi `case_study.json`'da |

## 3. Bildiride sayısal değeri olmayan parametreler

Aşağıdaki değerler bildiride verilmemiştir. **Kalibrasyon** sütunu, değerin bildirideki bir sayıya
bakılarak seçilip seçilmediğini gösterir. Hiçbir sonuç koda sabit yazılmamıştır. Tüm tablo ve
şekiller gerçek hesaplamadan üretilir.

| Parametre | Değer | Gerekçe | Kalibrasyon |
|---|---|---|---|
| C_batt | 60 kWh | Tablo 4: %75 → %66,7 düşüşü 4,99 kWh'e karşılık gelir | Bildiriden türetildi |
| P_aux | 2,0 kW | Klima/ısıtma açıkken tipik ortalama | Evet: Keçiören–Bilkent A* enerji yoğunluğu Tablo 4'e (0,217 kWh/km) yakın olsun diye 1,5 → 2,0 |
| a(v̄) (Dn. 3c) | max(0,04; 0,30 − 0,0028·v̄) m/s² | Sürüş çevrimlerinde RPA: kent içi ~0,15–0,30, otoyol ~0,05 | Hayır |
| α (eğim) | 0 | OSM'de yükseklik yok. Dn. 3b'de α yalnızca cos α ile girer (%5 eğimde 0,9988) | — |
| Kavşak kümeleme | 50 m | Bölünmüş yolda aynı kavşak bir kez sayılır | Hayır |
| Senaryo mesafesi | Kuş uçuşu 8–25 km | Temsili vaka Keçiören–Bilkent (~17 km) aralığın ortasında | Hayır (v2: 5–20 km) |
| Başlangıç SoC | U(30, 90) | v2 ile aynı | Hayır |
| Sentetik trafik | v2 ile aynı (`config.TrafficParams`) | — | Hayır |
| Sentetik kullanıcı (Q-Learning) | v2 ile aynı | — | Hayır |
| ρ, g, P_charge, SoC_target | 1,2 · 9,81 · 50 kW · %80 | Standart değerler | Hayır |

## 4. Sonuç: kod bildiriye ne kadar yakın?

Tüm değerler 50 senaryo × 10 tohumdan elde edildi (`results/bildiri_karsilastirma.md`).

**Yakın veya bildiriyle aynı yönde olanlar:**
* Seyahat süreleri bildiriden en fazla %12 sapıyor (39–49 dk; bildiri 42–45 dk).
* Dijkstra kavşak sayısı 35,5 (bildiri 32,4). En az kavşak AffectEV'de (18,8), bildiride de öyle.
* Sıralamalar bildiriyle aynı: en düşük enerji Dijkstra'da, en hızlı rota A*'ta.
* Tablo 3: CLS arttıkça konfor ve enerji artıyor, süre yüksek CLS'de uzuyor (bildiride de öyle). Rejim CLS 50 ile 65
  arasında değişiyor (bildiride de öyle). CLS ≤ 50'de baskın seçenek bildiride V, kodda D.
* Tablo 4'ün A* satırı: 21,0 km / 42,4 dk / 4,54 kWh / SoC %67,4 (bildiri 23,0 / 43,3 / 4,99 / 66,7).
  Düşük CLS rotası A* rotasıyla aynı (bildiride de öyle).
* Q-Learning rastgele politikayı açıkça geçiyor ve yaklaşık 300.–400. bölümde platoya ulaşıyor.

**Tutmayanlar ve nedenleri:**
1. **Konfor düzeyi.** Kodda 62,6–76,8, bildiride 46,8–52,5. Tablo 1 ağırlıklarıyla Dn. 2, 20–25 km'lik
   bir rotada gerçekçi sayımlarla (≈20–35 kavşak, ≈20–35 duruş, D ≈ 50) 60–75 arası bir değer
   verir. 39–55 bandına inmek için bu sayımların yaklaşık iki katı gerekir. Bildirideki
   değerler eski koddaki yol tipi ölçeğinden gelir; o ölçek Dn. 2 değildir.
2. **Tablo 4, yüksek CLS satırı** (44 km, konfor +%41). Dn. 2'deki N_int ve N_stop rota üzerindeki
   toplam sayımlardır, bu yüzden uzun bir rota daha fazla kavşak ve duruş toplar. Gerçek Ankara
   ağında Keçiören–Bilkent için çevre yolu üzerinden giden 35–46 km'lik alternatifler denendi.
   Bunlarda 27–63 kavşak vardı ve konforları 39–62 çıktı. Hepsi A* rotasından (22 kavşak,
   konfor 67,7) daha az konforlu. En konforlu çözüm A* rotasıyla neredeyse aynı olduğundan,
   Dn. 2'ye sadık bir kod bu satırı üretemez.
3. **Tablo 2 enerji düzeyi.** Kodda 4,6–5,1 kWh, bildiride 7,1–8,0 kWh. Bildirinin kendi verileri
   de birbirini tutmuyor: Tablo 4'te 43 dakikada 4,99 kWh harcanıyor, Tablo 2'de ise 42–45
   dakikada 7,1–8,0 kWh. Tek bir fiziksel model ikisini birden veremez. Kod Tablo 4 ölçeğine uyuyor.
4. **Şekil 2 ölçeği.** Kodda rastgele politika ≈ 4,5 ve plato ≈ 9, bildiride −7,5 ve 7,5. Bildirideki
   eğri formülle çizilmişti. Dn. 8'deki θ katsayıları ve konfor terimiyle, sentetik kullanıcı
   tanımına bağlı olarak başka bir ölçek çıkıyor.
5. **Tablo 3 rejim etiketi.** Düşük CLS'de kod çoğunlukla "Dengeli" seçeneğini etkinleştiriyor,
   bildiri ise "Verimlilik" diyor. Yapısal bulgu (iki rejim, 50–65 arası geçiş) iki tarafta da aynı.
