# Elektrikli Araçlarda Sürücü Bilişsel Yükünü Dikkate Alan Çok Amaçlı Rota Planlaması
## Multi-Objective Route Planning Considering Driver Cognitive Load in Electric Vehicles

**Ezgi Yiğit 1, Özlem Feyza Erkan 2**
1 Bilgisayar Mühendisliği Bölümü Beykoz Üniversitesi, 34810, İstanbul
{ezgiyigit}@ogrenci.beykoz.edu.tr, {feyzaerkan}@beykoz.edu.tr

### Özetçe
Elektrikli araç (EA) ekosisteminin hızla yaygınlaşmasıyla birlikte, seyir esnasında enerji verimliliği, batarya yönetimi ve rota optimizasyonu kritik bir araştırma problemi haline gelmiştir. Mevcut navigasyon sistemleri çoğunlukla yalnızca süre, mesafe veya enerji minimizasyonuna odaklanmakta; sürücünün anlık bilişsel ve psikolojik durumunu karar mekanizmalarına dahil etmemektedir. Bu çalışmada, sürücünün bilişsel durumunu da dikkate alan çok amaçlı bir rota planlama ve optimizasyon çerçevesi (AffectEV) önerilmektedir. Sistem, Bilişsel Yük Skoru (CLS) parametresini kontrollü bir girdi olarak alıp rota tercihlerini dinamik olarak uyarlamaktadır. Rota üretim aşamasında, enerji tüketimi, seyahat süresi ve sürüş konforu kriterleri Pareto-optimal tabanlı Dinamik NSGA-II yaklaşımı ile eşzamanlı olarak optimize edilmektedir. Ayrıca sistem, sürücü tercihlerine uyum sağlayabilmek adına sentetik bir kullanıcı modeli üzerinden Q-Learning tabanlı pekiştirmeli öğrenme mekanizması ile desteklenmiştir. Ankara şehir içi ulaşım ağı üzerinde yapılan benzetim sonuçları, önerilen yaklaşımın yüksek bilişsel yük altındaki sürücüler için %84 daha fazla enerji tüketimi ve uzayan mesafe ödünleşimi pahasına, sürüş konforunu %41 oranında artırabildiğini göstermektedir.

### Abstract
With the rapid expansion of the electric vehicle (EV) ecosystem, energy efficiency, battery management, and route optimization during driving have become critical research challenges. Existing navigation systems primarily focus on minimizing travel time, distance, or energy consumption, while largely ignoring the driver’s instantaneous cognitive and psychological state in decision-making processes. This study proposes AffectEV, a multi-objective route planning and optimization framework that incorporates the driver’s cognitive state into the decision mechanism. The system takes the Cognitive Load Score (CLS) as a controlled input to dynamically adapt route preferences. During the route generation stage, energy consumption, travel time, and driving comfort are simultaneously optimized using a Pareto-optimal Dynamic NSGA-II approach. In addition, a Q-Learning-based reinforcement learning module operating on a synthetic user model is integrated to continuously adapt to driver preferences. Simulation experiments conducted on the Ankara urban transportation network demonstrate that the proposed framework can improve driving comfort by 41% for drivers under high cognitive load, at the cost of 84% increased energy consumption and extended travel distance.

---

### 1. Giriş
Küresel ulaşım paradigmasının elektrikli araçlara (EA) doğru evrilmesi, güzergah belirleme algoritmalarında köklü bir revizyonu zorunlu kılmıştır. İçten yanmalı motora sahip geleneksel araçların aksine, EA'lar katı batarya kısıtlarına ve şarj istasyonlarının homojen olmayan mekansal dağılımına tabidir [1], [2]. Güncel literatürdeki ticari ve akademik navigasyon çözümleri; trafik yoğunluğu, topografik eğim ve seyir hızını analiz ederek enerji tüketimini minimize etmeye odaklanmaktadır. Ancak bu tek boyutlu yaklaşım, sürüş eyleminin temel aktörü olan insanın duygu durumunu ve zihinsel kapasitesini denklem dışında bırakmaktadır. 

Sürüş, mekanik bir taşıma eyleminden ziyade; sürekli dikkat, anlık karar alma ve çevresel uyarıcılara karşı reaksiyon gerektiren dinamik bir zihinsel süreçtir [3], [4]. Özellikle yorgunluk emareleri gösteren veya yüksek bilişsel yüke maruz kalan bir sürücü için, trafik yoğunluğunun yüksek olduğu karmaşık bir kavşak ağı, rotayı teorik olarak kısaltmasına rağmen kaza riskini ve stresi dramatik biçimde artırabilmektedir. Günümüzde literatürde duygu farkındalıklı rota üreten (örn. HappyRouting [9]) veya kişiselleştirilmiş EA rota planlaması yapan (örn. Houalef vd. [5]) çeşitli çalışmalar bulunmaktadır. Ancak mevcut sistemler, araç batarya dinamiklerini, şarj kısıtlarını ve insan merkezli sürüş deneyimini çok amaçlı bir optimizasyon çerçevesinde aynı potada eritmeme eğilimindedir. AffectEV sistemi, bu iki boyutu birleştirerek literatürdeki eksikliği gidermeyi amaçlamaktadır.

Bu çalışmada, "AffectEV" adı verilen akıllı bir rota planlama çatısı tanıtılmaktadır. Geliştirilen sistem; sürücünün anlık bilişsel yük durumuna (CLS) göre enerji kısıtlarını hesaplayan dinamik tüketim modeli, çelişen hedefleri dengeleyen D-NSGA-II çok amaçlı optimizasyon motoru [6], [7] ve sentetik kullanıcı tercihlerine zamanla adapte olan Q-Learning algoritmasını [8] tek bir platformda birleştirmektedir.

### 2. Sistem Modeli ve Bilişsel Çerçeve
Geliştirilen AffectEV prototipi; sürücü bilişsel yük durumunun entegrasyonu ve enerji tüketiminin modellenmesi olmak üzere iki ana bileşenden oluşur.

#### 2.1. Bilişsel Yük ve Sürüş Konforu Modellemesi
Araç içerisindeki bireyin anlık profili; duygusal değerlik (V), yorgunluk katsayısı (F) ve ölçümlenen bilişsel yük (C) verilerinden oluşan bir vektör olarak tanımlanır. Bu değişkenlerin sentezlenmesi neticesinde, sürücünün o anki durumunu tekil bir skora indirgeyen ve tüm sistemi süren **Bilişsel Yük Skoru (CLS)** formüle edilmiştir:

$$CLS = \lambda_f \cdot F + \lambda_c \cdot C + \lambda_v \cdot V \quad (1)$$

Burada $\lambda_f$, $\lambda_c$ ve $\lambda_v$ katsayıları ağırlıkları ifade etmektedir. Bu çalışmada algoritmik karar mekanizmasını test etmek amacıyla CLS değerleri kontrollü senaryo parametresi olarak (0-100 aralığında) atanmıştır; biyometrik sensörlerden gerçek zamanlı çıkarım yapan kestirim modülünün eğitimi ve doğrulanması kapsam dışı bırakılmıştır.

Dairesel ölçümleri önlemek adına, güzergahın sürücüye sunacağı *nesnel* sürüş konforu skoru ($Comfort_{route}$), bağımsız trafik metrikleri üzerinden aşağıdaki matematiksel bağıntı ile sayısallaştırılmaktadır:

$$Comfort_{route} = 100 - (w_{kavsak} \times N_{kavsak} + w_{durak} \times N_{durak} + w_{trafik} \times D_{trafik}) \quad (2)$$

Burada $N_{kavsak}$ ve $N_{durak}$ rotadaki sinyalize kavşak ve durak sayılarını, $D_{trafik}$ ise normalize edilmiş trafik yoğunluğunu ifade etmektedir. 

#### 2.2. Kinetik Enerji ve Şarj Dinamikleri
Rota adaylarının fizibilitesi test edilirken Batarya Şarj Durumu (SoC) aşılmaz bir kısıt olarak işleme alınmaktadır. Seyahat edilecek bir yol segmentinin toplam tahmini enerji sarfiyatı ($E_{toplam}$), aerodinamik sürüklenme, zeminden kaynaklı yuvarlanma direnci, anlık ivmelenme ve yardımcı sistemlerin harcadığı gücün toplanmasıyla elde edilir [10], [11]:

$$E_{toplam} = \sum_{i=1}^{n} (E_{drag,i} + E_{roll,i} + E_{accel,i} + E_{aux,i}) \quad (3)$$

Burada $n$ rota üzerindeki toplam segment sayısını ifade etmektedir. Kinetik alt bileşenler, standart fiziksel modellere göre aşağıdaki şekilde formüle edilmiştir:
- Aerodinamik sürüklenme: $E_{drag,i} = \frac{1}{2} \rho C_d A v_i^2 d_i$
- Yuvarlanma direnci: $E_{roll,i} = C_r m g \cos(\alpha_i) d_i$
- İvmelenme enerjisi: $E_{accel,i} = m a_i d_i$
- Yardımcı sistemler: $E_{aux,i} = P_{aux} \frac{d_i}{v_i}$

Eğer algoritma, seçilen rota dizilimi sonunda batarya seviyesinin güvenlik eşiğinin ($SoC_{min}$) altına düşeceğini öngörürse, sistem otomatik bir müdahale ile güzergah üzerindeki uygun şarj istasyonlarını rotaya dahil eder:

$$SoC_{final} = SoC_{initial} - \frac{\sum_{j=1}^{k} E_j}{C_{batt}} + \sum_{c \in C_{stops}} \Delta SoC_c \quad (4)$$

Burada $SoC_{initial}$ başlangıç şarj seviyesini, $C_{batt}$ batarya kapasitesini, $C_{stops}$ şarj duraklarının kümesini ve $\Delta SoC_c$ c. durakta kazanılan şarj miktarını ifade etmektedir. İstasyonlarda geçirilecek gecikme süresi ($\Delta t_{charge}$) ise hedef şarj seviyesine ($SoC_{target}$) ulaşmak için gereken enerjiye bağlıdır:

$$\Delta t_{charge} = \frac{(SoC_{target} - SoC_{current}) \times C_{batt}}{P_{charge}} \quad (5)$$

Kullanılan sistem ve araç parametreleri Tablo 1'de sunulmuştur.

**Tablo 1: Simülasyon ve Sistem Parametreleri**

| Parametre | Değer / Açıklama |
| :--- | :--- |
| Araç Tipi | Tesla Model 3 Standart Range |
| Sürüklenme Katsayısı ($C_d$) | 0.23 |
| Araç Kütlesi ($m$) | 1847 kg |
| Ön Kesit Alanı ($A$) | 2.22 m² |
| Yuvarlanma Direnci ($C_r$) | 0.01 |
| Minimum SoC Eşiği ($SoC_{min}$) | %20 |
| NSGA-II Popülasyon/Nesil | 100 / 50 |
| NSGA-II Çaprazlama/Mutasyon | 0.8 / 0.1 |
| Q-Learning ($\alpha$, $\gamma$, $\epsilon$) | 0.1, 0.9, 0.1 |

### 3. D-NSGA-II İle Rota Optimizasyonu ve Q-Learning Adaptasyonu
Taşıt yönlendirmede kullanılan standart algoritmalar genellikle ağırlıklandırılmış tek bir parametreyi minimize etmeye programlıdır (Dijkstra - mesafe maliyetli [12], A* - süre maliyetli [13]). Ancak elektrikli araç seyir koşullarında süre, enerji ve konfor birbiriyle çelişen hedeflerdir.

Bu çelişkiyi çözümlemek adına Dinamik NSGA-II tercih edilmiştir [6], [14]. Optimizasyon süreci, kullanıcıya "mutlak tek bir rota" dayatmak yerine; Konfor Odaklı, Dengeli ve Verimlilik Odaklı olmak üzere Pareto-optimal cephesinde yer alan bir çözüm kümesi sunmaktadır (Şekil 1).

**Şekil 1:** Enerji ve Seyahat Süresi Düzleminde Pareto-Optimal Çözüm Cephesi ve Seçenek Dağılımları

Kullanıcıya sunulan bu alternatifler arasından yapılan nihai seçimler ve seyir sonrasındaki sentetik memnuniyet oranları, Markov Karar Süreci modeline dayalı bir Q-Learning altyapısını beslemektedir [8]. Algoritmanın karar mekanizmasını şekillendiren anlık durum uzayı (state space) $s$, sürücü ve araç dinamiklerini bütüncül temsil edecek biçimde formüle edilmiştir:

$$s = (CLS, SoC_{level}, Traffic_{level}, Route_{type}) \quad (6)$$

Bu durum uzayına karşılık gelen eylem kümesi (action space) ise D-NSGA-II tarafından üretilen rota kategorileridir ($a \in \{Konfor, Dengeli, Verimlilik\}$). Modelin zaman içindeki adaptasyonunu sağlayan standart Q-değeri güncelleme kuralı Denklem 7'de, bu güncellemeyi besleyen ödül (reward) fonksiyonu ise Denklem 8'de tanımlanmıştır:

$$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right] \quad (7)$$

$$r = \theta_1 \cdot feedback + \theta_2 \cdot Comfort_{route} - \theta_3 \cdot Delay \quad (8)$$

Burada $\alpha \in (0, 1]$ öğrenme oranını, $\gamma \in [0, 1]$ indirim faktörünü (discount factor), $r$ anlık ödülü ve $s'$ sistemin geçeceği sonraki durumu ifade etmektedir. Ödül fonksiyonunda yer alan $feedback$ seyahat sonrasında kullanıcı modelinden alınan memnuniyet sinyalidir.

Öğrenme sürecinde keşif ve sömürü (exploration-exploitation) dengesini optimize etmek amacıyla $\epsilon$-greedy eylem seçim stratejisi kullanılmıştır:

$$a = \begin{cases} \arg\max_{a} Q(s, a) & \text{olasılık } 1-\epsilon \\ \text{rastgele eylem} & \text{olasılık } \epsilon \end{cases} \quad (9)$$

### 4. Simülasyon Sonuçları ve Performans Değerlendirmesi
Sistemin doğrulanması amacıyla, Ankara şehrine ait OpenStreetMap tabanlı yol ağı üzerinde, rastgele belirlenmiş 50 farklı şehir içi başlangıç-varış senaryosu koşturulmuştur. Sentetik trafik yoğunluğu ve hız profilleri tanımlanmış olup, güvenilirlik açısından her senaryo 10 farklı rastgele tohum (seed) değeri ile tekrarlanmıştır. 

Sistemin Q-Learning modülünün uzun dönemli öğrenme performansı, Şekil 2'de görselleştirilmiştir. Standart sapma bantlarıyla desteklenen grafik, modelin rastgele politikaya (taban çizgisi) kıyasla yaklaşık 250. döngüden itibaren başarılı bir şekilde yakınsadığını doğrulamaktadır.

**Şekil 2:** Q-Learning Modeli Kümülatif Ödül Yakınsama Eğrisi (10 tohum ortalaması, $\pm1$ standart sapma bandı ile)

Çok amaçlı optimizasyon (NSGA-II) ve CLS adaptasyonunun katkılarını adil biçimde değerlendirebilmek için hazırlanan ablasyon çalışması ve performans karşılaştırması Tablo 2'de sunulmuştur. Kavşak sayısı, nesnel bir konfor göstergesi olarak tabloya dâhil edilmiştir.

**Tablo 2: 50 Şehir İçi Senaryosunda Performans Karşılaştırması (Ablasyon)**

| Yöntem | Hedef Fonksiyonu | Süre (dk) | Enerji (kWh) | Konfor (0-100) | Ortalama Kavşak |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Dijkstra | Mesafe maliyetli | 44.2 | **7.1** | 46.8 | 32.4 |
| A* | Süre maliyetli | **42.0** | 7.7 | 50.5 | 30.1 |
| NSGA-II (Sabit Ağırlık) | Çok amaçlı, CLS yok | 44.5 | 7.5 | 50.0 | 28.5 |
| **AffectEV (D-NSGA-II)** | Çok amaçlı, CLS uyarlamalı | 45.3 | 8.0 | **50.3** | **22.6** |

Tablo 2'den görüleceği üzere, AffectEV genel ortalama metriklerde standart tek amaçlı algoritmalarla (veya sabit ağırlıklı NSGA-II ile) eşdeğer bir çizgide yer almaktadır. Sistemin asıl fark yaratan özelliği ve kazancı, yüksek bilişsel yük koşullarında devreye giren adaptif davranışıdır. CLS düzeyine göre bu davranışın nasıl değiştiği Tablo 3'te özetlenmektedir.

**Tablo 3: CLS Düzeyine Göre AffectEV Adaptasyon Performansı ve Rejimler**

| Sürücü Durumu | CLS Değeri | Ağırlıklar ($w_e$ / $w_t$ / $w_c$) | Konfor | Enerji (kWh) | Süre (dk) | Rejim |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Çok Enerjik | 15 | 0.50 / 0.40 / 0.10 | 47.3 | 7.1 | 43.5 | **V** |
| Enerjik | 30 | 0.40 / 0.35 / 0.25 | 49.6 | 7.8 | 44.7 | **V** |
| Nötr | 50 | 0.28 / 0.22 / 0.50 | 49.6 | 7.8 | 44.7 | **V** |
| Yorgun | 65 | 0.13 / 0.10 / 0.77 | **52.5** | 8.6 | 46.7 | **K** |
| Stresli | 85 | 0.08 / 0.07 / 0.85 | **52.5** | 8.6 | 46.7 | **K** |
*(V: Verimlilik Rejimi, K: Konfor Rejimi)*

Tablo 3, beş kademeli ağırlık şemasının pratikte iki ana davranışsal rejimde (Verimlilik ve Konfor) çalıştığını göstermektedir. Sistem, fiilen CLS≈50 civarında bir eşikle çalışarak, enerjik durumlarda verimliliği önceliklendirirken yorgun ve stresli durumlarda doğrudan konfor rejimine geçiş yapmaktadır. 

Bu davranışın harita üzerindeki somut yansıması Şekil 3'te ve verileri Tablo 4'te (Keçiören → Bilkent, Başlangıç SoC: %75 senaryosu) verilmiştir.

**Şekil 3:** Geleneksel A* Rotası (Düz Çizgi) ile Yüksek CLS AffectEV Rotasının (Kesikli Çizgi) Harita Üzerinde Karşılaştırması

**Tablo 4: Keçiören - Bilkent Senaryosu Rota Üretimi Karşılaştırması**

| Algoritma / Durum | Mesafe (km) | Süre (dk) | Enerji (kWh) | Nihai SoC (%) | Konfor (0-100) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Geleneksel (A*) / Düşük CLS | **23.0** | **43.3** | **4.99** | **%66.7** | 39 |
| AffectEV / Yüksek CLS (Yorgun) | 44.0 | 52.8 | 9.18 | %59.7 | **55** |

Geleneksel A* algoritması, sürücü durumundan bağımsız olarak her koşulda 23 km'lik kısa-süre-odaklı rotayı seçmektedir. AffectEV ise, düşük CLS'li sürücü için bu verimli rotayı korurken; yüksek CLS'li sürücü için daha az kesintili bulvar koridorlarını kullanarak 44 km'lik alternatif bir rota üretmektedir. Bu tercih %84 daha fazla enerji tüketimi ve mesafenin neredeyse iki katına çıkması ödünleşimi ile sonuçlansa da, sistemin asli amacı olan sürüş konforunu 39'dan 55 puana (%41) çıkartmayı başarmaktadır.

### 5. Sonuçlar ve Tartışma
Bu çalışmada, elektrikli araçlar için batarya SoC limitlerini, kinematik yol dinamiklerini ve sürücünün anlık bilişsel profilini entegre bir biçimde işleyen bütüncül bir rota planlama mimarisi ortaya konmuştur. Deneysel sonuçlar, geleneksel algoritmaların sürücünün durumundan bağımsız stresli rotalar üretebildiğini, AffectEV modelinin ise yüksek bilişsel yüke maruz kalan yorgun bir sürücü için artan mesafe ve enerji tüketimi ödünleşimlerini göze alarak sürüş konforunu artırabildiğini işaret etmektedir.

#### Sınırlılıklar
Bu çalışma kapsamında gerçekleştirilen testler, Ankara yol ağında tek tip bir araç profili (Tesla Model 3) ve sentetik kullanıcı/trafik verileri kullanılarak simüle edilmiştir. Biyometrik sensörlerden gerçek zamanlı çıkarım yapan kestirim modülünün eğitimi ve doğrulanması kapsam dışı bırakılmıştır; bu nedenle CLS değerleri kontrollü senaryo parametresi olarak atanmıştır. Gelecek çalışmalarda sistemin gerçek sürücü telemetrisi, canlı trafik API'leri ve daha geniş araç segmentleriyle desteklenerek otonom bir seyir asistanına entegre edilmesi hedeflenmektedir.

### 6. Kaynakça
[1] M. Abid, M. Tabaa, A. Chakir, and H. Hachimi, “Routing and charging of electric vehicles: A literature review,” Energy Reports, Vol. 8, Suppl. 9, pp. 556-578, 2022.
[2] C. Ye, W. He, and H. Chen, “Electric vehicle routing models and solution algorithms in logistics distribution: A systematic review,” Environmental Science and Pollution Research, Vol. 29, pp. 57067-57090, 2022.
[3] P. A. Hancock, G. M. Hancock, and C. M. Janelle, “The impact of emotions and emotion regulation on driving performance,” Work, Vol. 41, Suppl. 1, pp. 3608-3611, 2012.
[4] G. Underwood, P. Chapman, S. Wright, and D. Crundall, “Vehicular traffic and visual attention,” Perception, Vol. 31, No. 3, pp. 233-246, 2002.
[5] A.-R. Houalef, F. Delavernhe, S.-M. Senouci, and E. Aglzim, “Data-driven, personalized route planning for connected electric vehicles: Optimizing time, energy, and charging stops,” Applied Energy, Vol. 402, p. 126887, 2025.
[6] K. Deb, A. Pratap, S. Agarwal, and T. Meyarivan, “A fast and elitist multiobjective genetic algorithm: NSGA-II,” IEEE Transactions on Evolutionary Computation, Vol. 6, No. 2, pp. 182-197, 2002.
[7] R. Gutiérrez-Moreno, Á. Llamazares, P. Revenga, and M. Ocaña, “Electric vehicle route optimization: An end-to-end learning approach with multi-objective planning,” World Electric Vehicle Journal, Vol. 17, No. 1, p. 41, 2026.
[8] C. J. C. H. Watkins and P. Dayan, “Q-learning,” Machine Learning, Vol. 8, pp. 279-292, 1992.
[9] D. Bethge, D. Bulanda, A. Kozlowski, T. Kosch, A. Schmidt, and T. Grosse-Puppendahl, “HappyRouting: Learning emotion-aware route trajectories for scalable in-the-wild navigation,” Proceedings of MobileHCI 2024, 2024.
[10] A. Snoeck, A. Bhargava, D. Merchan, J. Davis, and J. Pachon, “Energy estimation of last-mile electric vehicle routes,” Proceedings of the ACM International Conference on Artificial Intelligence, 2024.
[11] H. S. Zhang, H. K. Fathy, and J. L. Stein, “Energy management and battery optimization in electric vehicles: A review,” Applied Energy, Vol. 262, p. 114660, 2020.
[12] E. W. Dijkstra, "A note on two problems in connexion with graphs," Numerische Mathematik, Vol. 1, pp. 269-271, 1959.
[13] P. E. Hart, N. J. Nilsson, and B. Raphael, "A Formal Basis for the Heuristic Determination of Minimum Cost Paths," IEEE Transactions on Systems Science and Cybernetics, Vol. 4, No. 2, pp. 100-107, 1968.
[14] A. Haddad, T. Tlili, N. Dahmani, and S. Krichen, “Integrating NSGA-II and Q-learning for solving the multi-objective electric vehicle routing problem with battery swapping stations,” International Journal of Intelligent Transportation Systems Research, Vol. 23, pp. 840-856, 2025.
