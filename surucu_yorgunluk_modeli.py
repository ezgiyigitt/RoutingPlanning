class EMAHoltYorgunlukModeli:
    """
    Sürücünün Kısa-Dönemli (Micro-Trend) yorgunluk ve stres eğilimini
    zaman serisi (Holt's Linear) ile hesaplayıp gelecekteki uzun yolculukta
    nerelere tırmanacağını kestiren İnsan-Yorgunluk Tahmin Katmanı.
    """
    def __init__(self, alfa: float = 0.6, beta: float = 0.4):
        self.alfa = alfa
        self.beta = beta
        self.c_t = None  # Level (EMA)
        self.t_t = None  # Trend (Holt)

    def guncelle(self, cls_mevcut: float):
        """
        Saniyede (veya belli periyotlarla) bir gelen güncel CLS verisini modele işler.
        """
        if self.c_t is None:
            self.c_t = cls_mevcut
            self.t_t = 0.0
        else:
            onceki_c = self.c_t
            onceki_t = self.t_t
            
            # Level: C_t = alfa * x_t + (1 - alfa) * C_t-1
            self.c_t = self.alfa * cls_mevcut + (1 - self.alfa) * onceki_c
            
            # Trend: T_t = beta * (C_t - C_t-1) + (1 - beta) * T_t-1
            # Trend pozitifse sürücü giderek strese giriyor demektir.
            self.t_t = self.beta * (self.c_t - onceki_c) + (1 - self.beta) * onceki_t

    def tahmin_et(self, ufuk_h: float) -> float:
        """
        Önümüzdeki rotadaki 'h' ufuk süresi boyunca beklenen tahmini CLS yorgunluğunu döner.
        C_{t+h} = C_t + h * T_t
        """
        if self.c_t is None:
            return 40.0 # Nötr başlangıç referansı
        return min(100.0, max(0.0, self.c_t + ufuk_h * self.t_t))
