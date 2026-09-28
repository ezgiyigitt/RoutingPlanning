# AffectEV v3 (klasör adı: affectev_v2)

**Elektrikli Araçlarda Sürücü Bilişsel Yükünü Dikkate Alan Çok Amaçlı Rota Planlaması**
Ezgi Yiğit, Özlem Feyza Erkan · Beykoz Üniversitesi

Bu klasör, bildiride anlatılan yöntemin uygulamasıdır. Bildirideki her tablo ve şekil
`experiments/` altındaki scriptlerle **gerçekten koşularak** üretilir. Hiçbir sonuç elle girilmez.

Bildiri ile kod arasındaki farklar, v3 düzeltmeleri ve bildiride değeri verilmeyen parametrelerin
nasıl seçildiği `BILDIRI_KOD_UYUMU.md` dosyasında anlatılır. Sayısal karşılaştırma
`results/bildiri_karsilastirma.md` dosyasındadır. Önceki (v2) kaynak dosyaları ve sonuçları
`_yedek_v2/` klasöründe saklanır.

## Hızlı başlangıç (yerel)

```bash
cd affectev_v2
pip install -r requirements.txt
python run.py
```

(Windows'ta `AffectEV_Baslat.bat` dosyasına çift tıklamak da yeterli.) Tarayıcıda
`http://127.0.0.1:8000` açılır.

Arayüz adım adım ilerler:

1. **Sürücü** seçimi. Her sürücünün Q-Learning tablosu ayrı tutulur (`data/q_tables/`); yeni sürücü eklenebilir.
2. **Araç** seçimi ve şarj durumu. Tesla Model 3 bildirideki referans araçtır. Togg T10X, IONIQ 5 ve Zoe
   için üretici verileri kullanılır; Togg için Cd yayımlanmadığından 0,30 varsayılmıştır.
3. **Hava durumu**: Açık, Yağmurlu, Karlı/Soğuk veya Sıcak. Hız, yuvarlanma direnci, klima/ısıtma
   gücü ve hava yoğunluğu değişir (`config.WEATHER`; model varsayımıdır). Bildiri deneyleri "Açık"
   koşulunu kullanır.
4. **Sürücü analizi**: 3 saniyelik yüz okumayla F ve V ölçülür, C elle girilir, CLS (Dn. 1)
   hesaplanıp gösterilir. Ardından otomatik olarak sonraki adıma geçilir.
5. **Güzergâh**: başlangıç ve varış seçilir.
6. **Rotalar**: Üç seçenek (Verimlilik, Dengeli, Konfor) yan yana kartlarda gösterilir; her kartta
   süre yazar. Altta OpenStreetMap canlı haritası yer alır. CLS'ye göre önerilen rota seçili gelir.
   Seçenekler birbirinden farklı güzergâhlardır (ortak uzunluk ≤ %70, süre ≤ en hızlının 1,5 katı;
   `affectev/options.py`). Seçilen rota puanlanabilir; puanlar Q-Learning'i günceller.

Deney sonuçları arayüzde gösterilmez; bunlar `experiments/` scriptleriyle üretilir. Arayüz
`frontend/dist` içinde derlenmiş olarak gelir, Node.js gerekmez.

Arayüzde geliştirme yapmak için:

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173 (API: python run.py)
```

## Sorun giderme: OpenCV

"module 'cv2' has no attribute 'CascadeClassifier'" hatası, aynı anda birden fazla OpenCV paketi
kurulu olduğunda görülür (ör. MediaPipe'ın getirdiği opencv-contrib-python ile opencv-python
çakışması). `AffectEV_Baslat.bat` bunu açılışta kontrol edip kendisi onarır. Elle onarmak için
tüm AffectEV pencerelerini kapatıp `OpenCV_Onar.bat` dosyasını çalıştırın.

OpenCV 5 paketleri Haar sınıflandırıcı XML dosyalarını içermediği için bu dosyalar projeyle birlikte
`data/haarcascades/` klasöründe gelir (Intel lisansı dosyaların içindedir).

## Yüz okuma (deneysel)

"Sürücü durumu" kartındaki **Kamerayla yüz oku** düğmesi 3 saniyelik bir kamera analizi yapar
(OpenCV Haar yüz/göz/gülümseme; TensorFlow kuruluysa `../modeller/raf_db_emotion_model.keras`
RAF-DB duygu modeli de kullanılır). Dn. 1'in girdilerini önerir:

* F = gözlerin kapalı olduğu kare oranı × 100 (PERCLOS benzeri)
* V = olumsuz duygu olasılığı × 100 (model yoksa 50 × (1 − gülümseme oranı))
* C kameradan ölçülmez; kaydırıcıdan girilir.

Bildiride biyometrik kestirim kapsam dışı olduğundan bu modül deney sonuçlarında kullanılmaz ve
doğrulanmamıştır. Görüntüler kaydedilmez, yalnızca yerel sunucuda işlenir.

## Bildirideki sonuçları yeniden üretme

```bash
python experiments/run_all.py      # 2 çekirdekte ~25 dk
python tests/test_affectev.py      # denklem/parametre testleri
```

| Bildiri öğesi | Script | Çıktı (`results/`) |
|---|---|---|
| Tablo 2 (ablasyon, 50 senaryo × 10 tohum) | `run_experiments.py` + `make_tables.py` | `tablo2.md`, `summary.json`, `raw_runs.csv` |
| Tablo 3 (CLS düzeyleri, rejimler) | `make_tables.py` | `tablo3.md` |
| Tablo 4 (Keçiören → Bilkent, SoC %75) | `case_study.py` | `tablo4.md`, `case_study.json` |
| Şekil 1 (Pareto cephesi) | `case_study.py` | `sekil1_pareto.png` |
| Şekil 2 (Q-Learning, 1000 bölüm, 10 tohum) | `qlearning_experiment.py` | `sekil2_qlearning.png`, `qlearning_summary.json` |
| Şekil 3 (OSM harita) | `case_study.py` | `sekil3_harita.png` |
| Bildiri sayılarıyla karşılaştırma | `compare_with_paper.py` | `bildiri_karsilastirma.md` |

## Bildiri ↔ kod eşlemesi

| Bildiri | Kod |
|---|---|
| Dn. 1 CLS | `affectev/models.py: cognitive_load_score` |
| Dn. 2 Konfor | `affectev/models.py: comfort_score, route_metrics` |
| Dn. 3, 3a–3d Enerji | `affectev/models.py: energy_components_j` |
| Dn. 4 SoC, Dn. 5 şarj süresi | `affectev/models.py: soc_final, charge_time_min`, `affectev/planner.py: apply_soc` |
| Tablo 1 parametreleri | `affectev/config.py` |
| Tablo 3 ağırlıkları | `affectev/config.py: CLS_WEIGHT_TABLE`, `models.cls_weights` |
| Dijkstra (mesafe) / A* (süre) | `affectev/routing.py` |
| D-NSGA-II | `affectev/nsga2.py` |
| Dn. 6–9 Q-Learning | `affectev/qlearning.py` |
| OSM Ankara yol ağı | `affectev/network.py`, `data/ankara_osm.json.gz` |

## Yöntem ayrıntıları (bildiride netleştirilmesi önerilenler)

* **Yol ağı:** Overpass API'den alınan OSM verisi (39,75–40,14 K; 32,55–33,05 D). Kapsanan yol sınıfları
  motorway…unclassified ve bağlantı yolları. Kavşaklar arasında sadeleştirilmiş, en büyük güçlü bağlı
  bileşen alınmıştır: 17.037 düğüm, 31.614 yönlü kenar.
* **N_intersection:** Rotadaki kavşak kümesi sayısı. Ağ yalnızca ana yollardan oluşur (tertiary ve
  üstü). Bu yüzden rampa olmayan en az 3 farklı komşusu olan her eş düzey düğüm kontrollü kavşak
  sayılır; OSM `traffic_signals` düğümleri de eklenir. Yalnızca otoyolların buluştuğu düğümler
  (farklı seviyeli) sayılmaz. Birbirine 50 m'den yakın noktalar tek kavşaktır.
  **N_stop:** Beklenen araç duruş sayısı. Her kavşakta durma olasılığı (0,3 + 0,6·D) ve
  tıkanıklıkta km başına 2·D² dur-kalk olayı.
  **D_traffic:** Uzunluk ağırlıklı ortalama trafik yoğunluğu (0–100).
* **Sentetik trafik:** Her tohum için yol sınıfı taban yoğunluğu, Kızılay merkezli yoğunluk artışı,
  8 rastgele trafik sıcak noktası ve gürültüden oluşan bir alan üretilir. Hız
  v = v_serbest·(1 − 0,6·D) ile hesaplanır. Her kavşakta beklenen bekleme (10 + 30·D) sn'dir
  (`config.TrafficParams`).
* **Dn. 3c:** a, segmentin ortalama pozitif ivmesidir (RPA). Bekleme dahil ortalama hıza bağlıdır:
  a = max(0,04; 0,30 − 0,0028·v̄[km/sa]) m/s². Dn. 3'te rejeneratif frenleme terimi yoktur.
  OSM'de yükseklik bulunmadığından α = 0 alınır; Dn. 3b'de α yalnızca cos α ile girdiğinden etkisi
  ihmal edilebilir düzeydedir.
* **D-NSGA-II:**
  * Amaçlar: enerji, süre ve (100 − konfor).
  * Başlangıç popülasyonu: 3 tek-amaç uç rota ile gürültülü rastgele ağırlıklı en kısa yollar.
  * Çaprazlama: ortak düğüm üzerinden. Mutasyon: bir alt rotanın yeniden yönlendirilmesi.
  * Optimizasyon Pareto cephesini üretir. Cepheden üç seçenek çıkarılır: Verimlilik (en düşük
    enerji), Dengeli (eşit ağırlıklı normalize skor en iyi) ve Konfor (en yüksek konfor).
  * CLS bu üç seçenekten birini etkinleştirir. Seçilen, cephe içinde min-max normalize edilmiş
    F = w_e·ê + w_t·t̂ + w_c·ĉ değerini en küçük yapan seçenektir (`nsga2.activate`). Ağırlıklar
    Tablo 3'ten gelir. Pozitif ölçekleme baskınlığı değiştirmediği için cephe CLS'den bağımsızdır.
  * "NSGA-II (CLS yok)" aynı üç seçenekten eşit ağırlıkla (1/3) seçim yapar. Böylece ablasyon
    yalnızca CLS uyarlamasının etkisini ölçer.
* **Senaryolar:** Master tohum 2026 ile rastgele seçilmiş 50 başlangıç–varış çifti kullanılır
  (kuş uçuşu 8–25 km). Başlangıç SoC'si U(30, 90) aralığındadır. Her senaryo 10 trafik tohumu
  ile koşulur. Tablo 2'deki AffectEV satırı 5 CLS düzeyinin tamamının ortalamasıdır.
* **Q-Learning:**
  * Durum: 5 CLS düzeyi × 3 SoC düzeyi × 3 trafik düzeyi × 4 önceki rota tipi.
  * Eylemler: Konfor, Dengeli ve Verimlilik.
  * Sentetik kullanıcının gizli tercihi: β(CLS) = sigmoid((CLS−50)/10); SoC < 40 iken menzil
    kaygısı eklenir.
  * Memnuniyet sinyali [−1, 1] aralığındadır ve N(0; 0,2) gürültü içerir.
  * Seyahat havuzu, ana deneyin gerçek D-NSGA-II çıktılarıdır.
* **Tablo 1 dışı parametreler:** ρ = 1,2 kg/m³; P_aux = 2,0 kW; C_batt = 60 kWh (Tablo 4'ten
  türetilir); P_charge = 50 kW; SoC_target = %80. Hangi değerin neye göre seçildiği
  `BILDIRI_KOD_UYUMU.md` dosyasında listelenmiştir.

## Klasör yapısı

```
affectev/      çekirdek model (config, network, models, routing, nsga2, qlearning, planner)
backend/       FastAPI (api.py)
frontend/      React + Vite arayüz (dist/ derlenmiş)
experiments/   bildiri tablolarını/şekillerini üreten scriptler
results/       üretilmiş tablolar, şekiller, ham sonuçlar
data/          OSM verisi (ODbL, © OpenStreetMap katkıcıları)
tests/         birim testleri
```
