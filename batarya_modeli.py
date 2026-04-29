class EMAHoltBataryaModeli:
    """
    Kullanıcının belirlediği EMA + Holt's Trend temelli Hybrid Batarya Öngörü Modeli.
    Bu analiz, bataryanın tüketiminden çok, doğrudan *Mevcut Batarya Seviyesi (B_t)* üzerinden izleme yapar.
    Ayrıca kalan mesafe / ortalama segment üzerinden "Horizon (h)" süresini dinamiğe bağlar.
    """
    def __init__(self, alfa: float = 0.5, beta: float = 0.3):
        self.alfa = alfa
        self.beta = beta
        self.b_t = None  # Level (EMA)
        self.t_t = None  # Trend (Holt)

    def guncelle(self, x_t: float):
        """
        Her segment (düğüm) geçildiğinde yeni batarya seviyesini modele yükler.
        Oluşan değişimi (Trend) hesaplar. x_t: Mevcut Batarya (Yüzde veya KWh).
        """
        if self.b_t is None:
            self.b_t = x_t
            self.t_t = 0.0
        else:
            onceki_b = self.b_t
            onceki_t = self.t_t
            
            # Level (EMA): B_t = alfa * x_t + (1 - alfa) * B_t-1
            # (Genel Holt literatüründe (B_t-1 + T_t-1) alınır ancak kullanıcının "Final Hybrid Model"'inde doğrudan geçmiş batarya değeri baz alınmıştır)
            self.b_t = self.alfa * x_t + (1 - self.alfa) * onceki_b
            
            # Trend (Holt): T_t = beta * (B_t - B_t-1) + (1 - beta) * T_t-1
            self.t_t = self.beta * (self.b_t - onceki_b) + (1 - self.beta) * onceki_t

    def tahmin_et(self, ufuk_h: float) -> float:
        """
        Gelecekteki 'h' adımı için batarya seviyesini tahmin eder.
        Forecast: B_{t+h} = B_t + h * T_t
        (Düzenli tüketimde T_t negatif olacağı için Batarya düşecektir)
        """
        if self.b_t is None:
            return 100.0 # Güvenli değer
        return self.b_t + ufuk_h * self.t_t
