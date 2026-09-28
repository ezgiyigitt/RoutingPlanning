"""
ev_rota_planner.py  —  AffectEV  v7  (Sayfa Tabanlı Uygulama)
===============================================================
Ankara Elektrikli Araç Rota Planlayıcı

Kurulum:
    pip install folium requests
    pip install opencv-python opencv-contrib-python numpy   # opsiyonel

Çalıştır:
    python ev_rota_planner.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import folium
import math
import webbrowser
import os
import heapq
import requests
import threading
import random
import time
from datetime import datetime
from typing import List, Tuple, Optional, Dict
# ── DynamAffect Integration
try:
    from dynamaffect_integration import DynamAffectRoutePlanner, create_sample_graph
    DYNAMAFFECT_VAR = True
except ImportError:
    DYNAMAFFECT_VAR = False

KONFOR_HAFIZASI = None
KOGNITIF_VAR = False
GELISMIS_VAR = False

GOOGLE_API_KEY   = ""
TOMTOM_API_KEY   = "9vhNo3evFfz59k6RKFrNwO7oV0Czf3bu"
MIN_BATARYA_ESIK = 10
TARAMA_SURE      = 4   # Gerçekçi duygu analizi için 4 saniye

# ─────────────────────────────────────────────
#  ARAÇ VERİLERİ
# ─────────────────────────────────────────────
ARACLAR = {
    "Tesla Model 3":    {"batarya": 60, "tuketim_baz": 0.145, "max_menzil": 400, "renk": "#E31937",
                         "hiz_tuketim": {30:.130, 50:.145, 90:.175, 120:.220}, "rejen": 0.18},
    "Renault Zoe":      {"batarya": 40, "tuketim_baz": 0.175, "max_menzil": 220, "renk": "#FFCC00",
                         "hiz_tuketim": {30:.155, 50:.175, 90:.210, 120:.270}, "rejen": 0.15},
    "Togg T10X":        {"batarya": 88, "tuketim_baz": 0.165, "max_menzil": 500, "renk": "#C8102E",
                         "hiz_tuketim": {30:.148, 50:.165, 90:.198, 120:.245}, "rejen": 0.20},
    "Volkswagen ID.4":  {"batarya": 77, "tuketim_baz": 0.158, "max_menzil": 480, "renk": "#00B0F0",
                         "hiz_tuketim": {30:.140, 50:.158, 90:.190, 120:.238}, "rejen": 0.17},
    "BMW iX3":          {"batarya": 74, "tuketim_baz": 0.170, "max_menzil": 420, "renk": "#0066CC",
                         "hiz_tuketim": {30:.150, 50:.170, 90:.202, 120:.252}, "rejen": 0.19},
    "Hyundai Ioniq 5":  {"batarya": 72, "tuketim_baz": 0.160, "max_menzil": 430, "renk": "#1DA462",
                         "hiz_tuketim": {30:.142, 50:.160, 90:.192, 120:.240}, "rejen": 0.22},
    "Kia EV6":          {"batarya": 77, "tuketim_baz": 0.158, "max_menzil": 480, "renk": "#BB162B",
                         "hiz_tuketim": {30:.140, 50:.158, 90:.189, 120:.236}, "rejen": 0.21},
}

YOL_TIPLERI = {
    "sehir":  {"hiz": 40,  "trafik_carpan": 1.35},
    "bulvar": {"hiz": 60,  "trafik_carpan": 1.20},
    "otoyol": {"hiz": 90,  "trafik_carpan": 1.05},
    "ulke":   {"hiz": 75,  "trafik_carpan": 1.10},
}

# ─────────────────────────────────────────────
#  ANKARA DÜĞÜM NOKTALARI
# ─────────────────────────────────────────────
ANKARA_DUGUMLER = {
    # Merkez
    "Kızılay":              (39.9208, 32.8541,  861),
    "Ulus":                 (39.9250, 32.8600,  850),
    "Hacettepe":            (39.8950, 32.8650,  940),
    "TBMM":                 (39.9167, 32.8500,  870),
    "Anıtkabir":            (39.9256, 32.8373,  880),
    
    # Ana İlçeler
    "Çankaya":              (39.9036, 32.8597,  930),
    "Keçiören":             (39.9700, 32.8650,  980),
    "Mamak":                (39.9300, 32.7950,  900),
    "Yenimahalle":          (39.9450, 32.8200,  880),
    "Altındağ":             (39.9500, 32.8667,  870),
    "Etimesgut":            (39.9500, 32.6833,  840),
    
    # Alt Bölgeler
    "Ayrancı":              (39.9000, 32.8500,  910),
    "Kavaklıdere":          (39.9050, 32.8600,  920),
    "Küçükesat":            (39.9000, 32.8700,  940),
    "Tunalı Hilmi":         (39.9050, 32.8550,  900),
    "Dikmen":               (39.8833, 32.8833,  960),
    "Balgat":               (39.8833, 32.8167,  900),
    "Söğütözü":             (39.9000, 32.8000,  875),
    "Çayyolu":              (39.8667, 32.7333,  970),
    "Ümitköy":              (39.8667, 32.7000,  990),
    "Yaşamkent":            (39.8583, 32.6833, 1010),
    "Konutkent":            (39.8750, 32.6667, 1020),
    "Bilkent":              (39.8667, 32.7500,  950),
    "ODTÜ":                 (39.8917, 32.7750,  900),
    
    # Keçiören & Yenimahalle Alt-İlçeleri
    "Etlik":                (39.9583, 32.8833,  950),
    "Bağlum":               (40.0500, 32.8167, 1050),
    "Güçlükaya":            (40.0167, 32.8667, 1020),
    "Pınarbaşı":            (40.0000, 32.8833, 1000),
    "Kalaba":               (40.0000, 32.8500, 1000),
    "Şentepe":              (39.9600, 32.8417,  960),
    "Kuşcağız":             (39.9833, 32.8833, 1010),
    "Mamak":                (39.9333, 32.9167,  900),
    "Altındağ":             (39.9500, 32.8667,  920),
    "Hamamönü":             (39.9400, 32.8700,  905),
    "Demirlibahçe":         (39.9333, 32.8833,  910),
    "Karakusunlar":         (39.9250, 32.9333,  895),
    "Gülveren":             (39.9417, 32.9000,  910),
    "Boğaziçi":             (39.9167, 32.9000,  890),
    "Şirintepe":            (39.9550, 32.9100,  920),
    "Yenimahalle":          (39.9667, 32.8000,  900),
    "Ostim":                (39.9667, 32.8333,  930),
    "Demetevler":           (39.9750, 32.8167,  920),
    "Şehitler":             (39.9500, 32.7833,  900),
    "Susuzköy":             (39.9333, 32.7833,  890),
    "Karşıyaka":            (39.9583, 32.7833,  905),
    "Doğukent":             (39.9833, 32.7667,  920),
    "Etimesgut":            (39.9500, 32.6833,  835),
    "Elvankent":            (39.9167, 32.7333,  860),
    "Yapracık":             (39.9333, 32.7167,  845),
    "Ayyıldız":             (39.9500, 32.7500,  860),
    "Bağlıca":              (39.9667, 32.7000,  870),
    "Süvari":               (39.9417, 32.6667,  830),
    "Sincan":               (39.9667, 32.5833,  800),
    "Eryaman":              (39.9833, 32.6333,  820),
    "Fatih":                (39.9583, 32.5500,  795),
    "İstasyon":             (39.9500, 32.5833,  800),
    "Tandoğan (Sincan)":    (39.9750, 32.5333,  790),
    "Yenikent":             (39.9667, 32.5000,  785),
    "Batıkent":             (39.9667, 32.7333,  880),
    "Törekent":             (39.9500, 32.7167,  865),
    "Pursaklar":            (40.0333, 33.0000,  910),
    "Karapürçek":           (40.0167, 32.9667,  930),
    "Gölbaşı":              (39.7833, 32.8167,  985),
    "Tulumtaş":             (39.8000, 32.8000,  970),
    "Mürted":               (39.8167, 32.7667,  960),
    "Akyurt":               (40.1333, 33.0833,  920),
    "Kahramankazan":        (40.2333, 32.6833,  850),
    "Temelli":              (39.9500, 32.4167,  770),
    "Beypazarı":            (40.1667, 31.9167,  640),
    "Nallıhan":             (40.1833, 31.3500,  550),
    "Kalecik":              (40.1000, 33.4000,  650),
    "Şereflikoçhisar":      (38.9333, 33.5333,  900),
    "Esenboğa Havalimanı":  (40.1167, 32.9833,  955),
    "AŞTİ":                 (39.9167, 32.8000,  855),
    "TBMM":                 (39.9167, 32.8500,  855),
    "Anıtkabir":            (39.9256, 32.8373,  905),
    "Ulus":                 (39.9400, 32.8533,  870),
    "A.Ö.Ü Kampüs":         (39.9333, 32.8667,  890),
    "Hacettepe":            (39.9417, 32.8583,  905),
    "Gazi Üniversitesi":    (39.9333, 32.8083,  860),
    "TCDD Gar":             (39.9333, 32.8500,  865),
    "Kızılcahamam":         (40.4833, 32.6500,  710),
    "Çubuk":                (40.2333, 33.0333,  840),
    "Haymana":              (39.4333, 32.5000, 1010),
    "Polatlı":              (39.5833, 32.1500,  830),
    "Bala":                 (39.5500, 33.1167,  820),
    "Elmadağ":              (39.9167, 33.2333,  900),
    "Güdül":                (40.2167, 32.2500,  730),
    "Çamlıdere":            (40.4833, 32.4833,  700),
    "Kızılcahamam Kaplıca": (40.5167, 32.6333,  700),
    "Esenboğa":             (40.0500, 33.0000,  950),
    "Akköprü":              (39.9350, 32.8200,  865),
    "Dikimevi":             (39.9500, 32.8833,  930),
    "Ulucanlar":            (39.9450, 32.8450,  880),
    "Hipodrom":             (39.9350, 32.8450,  865),
    "Maltepe":              (39.9467, 32.8300,  870),
    "Sıhhıye":              (39.9300, 32.8517,  862),
    "Kolej":                (39.9083, 32.8583,  900),
    "Gazi Mahallesi":       (39.9300, 32.8083,  860),
    "Şenlik":               (39.9667, 32.8500,  945),
    "Önder":                (39.9583, 32.9000,  910),
    "Tuzluçayır":           (39.9417, 32.9333,  895),
    "İskitler":             (39.9517, 32.8400,  905),
    "Cebeci":               (39.9333, 32.8833,  910),
    "Hüseyingazi":          (40.0167, 32.8500, 1010),
    "Girişimci":            (39.9667, 32.8083,  920),
}

# ─────────────────────────────────────────────
#  YOL BAĞLANTILARI
# ─────────────────────────────────────────────
YOLLAR = [
    ("Kızılay","Ulus",3,"sehir"),("Kızılay","Çankaya",4,"sehir"),
    ("Kızılay","Bahçelievler",5,"bulvar"),("Kızılay","Tandoğan",3,"sehir"),
    ("Kızılay","Gaziosmanpaşa",2,"sehir"),("Kızılay","A.Ö.Ü Kampüs",2,"sehir"),
    ("Kızılay","Söğütözü",4,"bulvar"),("Kızılay","Sıhhıye",1,"sehir"),
    ("Kızılay","Kolej",3,"sehir"),("Kızılay","Anıtkabir",3,"sehir"),
    ("Kızılay","TCDD Gar",2,"sehir"),("Kızılay","Maltepe",2,"sehir"),
    ("Sıhhıye","Ulus",2,"sehir"),("Sıhhıye","Maltepe",2,"sehir"),
    ("Sıhhıye","Hamamönü",2,"sehir"),
    ("Ulus","Altındağ",3,"sehir"),("Ulus","A.Ö.Ü Kampüs",2,"sehir"),
    ("Ulus","Hacettepe",2,"sehir"),("Ulus","Ulucanlar",2,"sehir"),
    ("Ulus","Hipodrom",2,"sehir"),("Ulus","Maltepe",3,"sehir"),
    ("Ulus","İskitler",2,"sehir"),
    ("Anıtkabir","TBMM",2,"sehir"),("Anıtkabir","Tandoğan",2,"sehir"),
    ("TBMM","Söğütözü",3,"sehir"),("TBMM","Tandoğan",2,"sehir"),
    ("TBMM","Bahçelievler",4,"bulvar"),
    ("AŞTİ","Tandoğan",1,"sehir"),("AŞTİ","Emek",3,"bulvar"),
    ("AŞTİ","Söğütözü",2,"sehir"),
    ("Çankaya","Dikmen",5,"sehir"),("Çankaya","Balgat",6,"bulvar"),
    ("Çankaya","Gaziosmanpaşa",3,"sehir"),("Çankaya","Kavaklıdere",2,"sehir"),
    ("Çankaya","Ayrancı",3,"sehir"),("Çankaya","Küçükesat",2,"sehir"),
    ("Çankaya Merkez","Çankaya",1,"sehir"),
    ("Çankaya Merkez","Dikmen",4,"sehir"),
    ("Çankaya Merkez","Balgat",5,"bulvar"),
    ("Kavaklıdere","Ayrancı",2,"sehir"),
    ("Kavaklıdere","Tunalı Hilmi",1,"sehir"),
    ("Kavaklıdere","Çankaya",2,"sehir"),
    ("Tunalı Hilmi","Kızılay",2,"sehir"),
    ("Tunalı Hilmi","Kolej",2,"sehir"),
    ("Kolej","Küçükesat",2,"sehir"),("Kolej","Ayrancı",3,"sehir"),
    ("Ayrancı","Dikmen",4,"sehir"),
    ("Küçükesat","Dikmen",3,"sehir"),("Küçükesat","Balgat",5,"bulvar"),
    ("Dikmen","Balgat",8,"bulvar"),("Dikmen","Çayyolu",12,"bulvar"),
    ("Balgat","Söğütözü",4,"bulvar"),
    ("Balgat","ODTÜ",8,"bulvar"),("Balgat","Bilkent",10,"bulvar"),
    ("Çayyolu","Bilkent",5,"bulvar"),("Çayyolu","Ümitköy",5,"bulvar"),
    ("Çayyolu","Koru",5,"sehir"),("Çayyolu","Elvankent",10,"bulvar"),
    ("Ümitköy","Yaşamkent",5,"sehir"),("Ümitköy","Konutkent",6,"sehir"),
    ("Yaşamkent","Konutkent",3,"sehir"),
    ("Bilkent","ODTÜ",3,"sehir"),("Bilkent","Emek",8,"bulvar"),
    ("ODTÜ","Emek",6,"bulvar"),("ODTÜ","Söğütözü",7,"bulvar"),
    ("Emek","Gazi Üniversitesi",4,"sehir"),
    ("Emek","Mebusevleri",3,"sehir"),("Emek","Çukurambar",3,"sehir"),
    ("Çukurambar","Söğütözü",2,"sehir"),
    ("Çukurambar","Mebusevleri",2,"sehir"),
    ("Mebusevleri","Bahçelievler",3,"sehir"),
    ("Mebusevleri","Tandoğan",2,"sehir"),
    ("Bahçelievler","Elvankent",5,"bulvar"),
    ("Bahçelievler","Tandoğan",2,"sehir"),
    ("Bahçelievler","Gazi Üniversitesi",3,"sehir"),
    ("Bahçelievler","Gazi Mahallesi",3,"sehir"),
    ("Gazi Mahallesi","Yenimahalle",5,"bulvar"),
    ("Gazi Mahallesi","AŞTİ",4,"sehir"),
    ("Söğütözü","Bilkent",8,"sehir"),  # Eskişehir Yolu - yogun trafik, gerçek mesafe ~8km
    ("Söğütözü","Tandoğan",3,"sehir"),("Söğütözü","Yıldız",3,"sehir"),
    ("Yıldız","Güvenevler",2,"sehir"),("Yıldız","Çetin Emeç",4,"sehir"),
    ("Güvenevler","Gaziosmanpaşa",2,"sehir"),
    ("Gaziosmanpaşa","Çetin Emeç",4,"sehir"),
    ("Çetin Emeç","Balgat",4,"bulvar"),
    ("Altındağ","Hamamönü",2,"sehir"),("Altındağ","Dikimevi",3,"sehir"),
    ("Altındağ","Demirlibahçe",4,"sehir"),("Altındağ","Cebeci",4,"sehir"),
    ("Altındağ","A.Ö.Ü Kampüs",3,"sehir"),("Altındağ","Hacettepe",3,"sehir"),
    ("Hamamönü","Hacettepe",2,"sehir"),("Hamamönü","Ulucanlar",2,"sehir"),
    ("Ulucanlar","İskitler",2,"sehir"),("İskitler","Dikimevi",3,"sehir"),
    ("Dikimevi","Cebeci",2,"sehir"),("Dikimevi","Etlik",3,"sehir"),
    ("Cebeci","Mamak",5,"sehir"),("Cebeci","Demirlibahçe",3,"sehir"),
    ("Cebeci","Boğaziçi",4,"sehir"),
    ("A.Ö.Ü Kampüs","Hacettepe",1,"sehir"),
    ("A.Ö.Ü Kampüs","Altındağ",3,"sehir"),
    ("Keçiören","Pursaklar",15,"bulvar"),("Keçiören","Altındağ",6,"sehir"),
    ("Keçiören","Ostim",8,"bulvar"),("Keçiören","Etlik",5,"sehir"),
    ("Keçiören","Şentepe",4,"sehir"),("Keçiören","Pınarbaşı",8,"sehir"),
    ("Keçiören","Kalaba",6,"sehir"),("Keçiören","Güçlükaya",8,"sehir"),
    ("Keçiören","Şenlik",5,"sehir"),("Keçiören","Hüseyingazi",8,"sehir"),
    ("Keçiören","Bağlum",12,"ulke"),
    ("Etlik","Altındağ",4,"sehir"),("Etlik","Dikimevi",4,"sehir"),
    ("Şentepe","Yenimahalle",5,"sehir"),
    ("Pınarbaşı","Pursaklar",8,"sehir"),("Pınarbaşı","Kalaba",4,"sehir"),
    ("Kalaba","Güçlükaya",4,"sehir"),("Güçlükaya","Kuşcağız",5,"sehir"),
    ("Kuşcağız","Pursaklar",8,"sehir"),
    ("Hüseyingazi","Bağlum",5,"sehir"),
    ("Bağlum","Kahramankazan",20,"ulke"),
    ("Mamak","Altındağ",7,"sehir"),("Mamak","Pursaklar",12,"bulvar"),
    ("Mamak","Ostim",8,"bulvar"),("Mamak","Demirlibahçe",5,"sehir"),
    ("Mamak","Karakusunlar",5,"sehir"),("Mamak","Gülveren",4,"sehir"),
    ("Mamak","Boğaziçi",4,"sehir"),("Mamak","Şirintepe",6,"sehir"),
    ("Mamak","Tuzluçayır",5,"sehir"),("Mamak","Önder",6,"sehir"),
    ("Karakusunlar","Tuzluçayır",4,"sehir"),
    ("Tuzluçayır","Önder",3,"sehir"),("Önder","Pursaklar",10,"sehir"),
    ("Şirintepe","Pursaklar",10,"sehir"),
    ("Gülveren","Demirlibahçe",3,"sehir"),
    ("Boğaziçi","Karakusunlar",3,"sehir"),
    ("Demirlibahçe","Cebeci",3,"sehir"),
    ("Yenimahalle","Ostim",6,"bulvar"),("Yenimahalle","Batıkent",8,"bulvar"),
    ("Yenimahalle","Etimesgut",15,"otoyol"),
    ("Yenimahalle","Demetevler",4,"sehir"),
    ("Yenimahalle","Karşıyaka",5,"sehir"),
    ("Yenimahalle","Şehitler",5,"sehir"),
    ("Yenimahalle","Girişimci",4,"sehir"),
    ("Demetevler","Ostim",4,"sehir"),("Demetevler","Şenlik",4,"sehir"),
    ("Ostim","Pursaklar",12,"bulvar"),("Ostim","Şenlik",4,"sehir"),
    ("Karşıyaka","Şehitler",3,"sehir"),("Karşıyaka","Batıkent",5,"sehir"),
    ("Şehitler","Batıkent",6,"sehir"),
    ("Susuzköy","Şehitler",3,"sehir"),("Susuzköy","Elvankent",5,"sehir"),
    ("Doğukent","Eryaman",5,"sehir"),("Doğukent","Yenimahalle",5,"bulvar"),
    ("Girişimci","Demetevler",4,"sehir"),
    ("Etimesgut","Sincan",15,"otoyol"),("Etimesgut","Batıkent",10,"bulvar"),
    ("Etimesgut","Elvankent",8,"bulvar"),("Etimesgut","Yapracık",5,"sehir"),
    ("Etimesgut","Ayyıldız",7,"sehir"),("Etimesgut","Bağlıca",10,"bulvar"),
    ("Etimesgut","Süvari",8,"sehir"),
    ("Elvankent","Yapracık",4,"sehir"),("Elvankent","Törekent",4,"sehir"),
    ("Elvankent","Batıkent",7,"bulvar"),
    ("Yapracık","Süvari",5,"sehir"),("Ayyıldız","Batıkent",5,"sehir"),
    ("Bağlıca","Sincan",8,"bulvar"),("Süvari","Konutkent",8,"ulke"),
    ("Törekent","Batıkent",3,"sehir"),
    ("Sincan","Eryaman",8,"bulvar"),("Sincan","Fatih",5,"sehir"),
    ("Sincan","İstasyon",3,"sehir"),("Sincan","Yenikent",8,"sehir"),
    ("Eryaman","Doğukent",5,"sehir"),("Eryaman","Batıkent",10,"bulvar"),
    ("Fatih","İstasyon",3,"sehir"),
    ("İstasyon","Tandoğan (Sincan)",4,"sehir"),
    ("Tandoğan (Sincan)","Yenikent",4,"sehir"),
    ("Yenikent","Temelli",18,"ulke"),("Temelli","Polatlı",25,"ulke"),
    ("Batıkent","Eryaman",10,"bulvar"),("Batıkent","Elvankent",7,"bulvar"),
    ("Batıkent","Törekent",3,"sehir"),
    ("Gölbaşı","Çayyolu",18,"ulke"),("Gölbaşı","Balgat",22,"ulke"),
    ("Gölbaşı","Tulumtaş",5,"sehir"),("Gölbaşı","Mürted",8,"ulke"),
    ("Gölbaşı","Haymana",55,"ulke"),
    ("Tulumtaş","Mürted",5,"sehir"),("Mürted","Konutkent",12,"ulke"),
    ("Haymana","Polatlı",35,"ulke"),
    ("Pursaklar","Esenboğa Havalimanı",20,"otoyol"),
    ("Pursaklar","Karapürçek",5,"sehir"),
    ("Pursaklar","Akyurt",20,"ulke"),("Pursaklar","Çubuk",18,"ulke"),
    ("Karapürçek","Esenboğa",8,"sehir"),
    ("Esenboğa Havalimanı","Keçiören",25,"otoyol"),
    ("Esenboğa Havalimanı","Esenboğa",5,"sehir"),
    ("Esenboğa","Karapürçek",5,"sehir"),
    ("Akyurt","Çubuk",15,"ulke"),("Akyurt","Elmadağ",20,"ulke"),
    ("Elmadağ","Bala",45,"ulke"),("Elmadağ","Mamak",25,"ulke"),
    ("Çubuk","Kızılcahamam",50,"ulke"),
    ("Kızılcahamam","Kızılcahamam Kaplıca",5,"sehir"),
    ("Kızılcahamam","Çamlıdere",35,"ulke"),
    ("Kızılcahamam","Kahramankazan",35,"ulke"),
    ("Kahramankazan","Güdül",25,"ulke"),("Güdül","Nallıhan",50,"ulke"),
    ("Nallıhan","Beypazarı",55,"ulke"),("Beypazarı","Kahramankazan",60,"ulke"),
    ("Polatlı","Haymana",35,"ulke"),
    ("Şereflikoçhisar","Bala",40,"ulke"),
    ("Kalecik","Akyurt",35,"ulke"),("Kalecik","Çubuk",30,"ulke"),
    ("Bala","Şereflikoçhisar",40,"ulke"),
]

SARJ_ISTASYONLARI_FALLBACK = [
    {"isim":"Tesla Supercharger - Optimum AVM",   "lat":39.9290,"lon":32.7850,"guc":150,"tip":"DC Hızlı","firma":"Tesla"},
    {"isim":"Tesla Supercharger - Batıkent",       "lat":39.9667,"lon":32.7333,"guc":150,"tip":"DC Hızlı","firma":"Tesla"},
    {"isim":"Tesla Supercharger - Bilkent Center", "lat":39.8700,"lon":32.7500,"guc":250,"tip":"DC Hızlı","firma":"Tesla"},
    {"isim":"Voltrun - Eryaman",                   "lat":39.9833,"lon":32.6333,"guc":100,"tip":"DC Hızlı","firma":"Voltrun"},
    {"isim":"Voltrun - Ostim",                     "lat":39.9667,"lon":32.8333,"guc":100,"tip":"DC Hızlı","firma":"Voltrun"},
    {"isim":"Voltrun - Pursaklar",                 "lat":40.0333,"lon":33.0000,"guc":100,"tip":"DC Hızlı","firma":"Voltrun"},
    {"isim":"Voltrun - Çayyolu",                   "lat":39.8667,"lon":32.7350,"guc":100,"tip":"DC Hızlı","firma":"Voltrun"},
    {"isim":"ZES - Kızılay Merkez",                "lat":39.9208,"lon":32.8541,"guc":50, "tip":"DC",      "firma":"ZES"},
    {"isim":"ZES - Çankaya Çarşı",                 "lat":39.9036,"lon":32.8597,"guc":50, "tip":"DC",      "firma":"ZES"},
    {"isim":"ZES - Esenboğa Havalimanı",            "lat":40.1167,"lon":32.9833,"guc":50, "tip":"DC",      "firma":"ZES"},
    {"isim":"ZES - Keçiören",                      "lat":39.9720,"lon":32.8680,"guc":50, "tip":"DC",      "firma":"ZES"},
    {"isim":"ZES - Ümitköy",                       "lat":39.8680,"lon":32.7020,"guc":50, "tip":"DC",      "firma":"ZES"},
    {"isim":"Eşarj - Ankamall AVM",                "lat":39.9500,"lon":32.8167,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - Armada AVM",                  "lat":39.8900,"lon":32.7600,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - Panora AVM",                  "lat":39.8752,"lon":32.7544,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - Mamak",                       "lat":39.9333,"lon":32.9167,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - Gölbaşı",                     "lat":39.7833,"lon":32.8167,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - Söğütözü",                    "lat":39.9000,"lon":32.8000,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - Dikmen",                      "lat":39.8833,"lon":32.8833,"guc":22, "tip":"AC",      "firma":"Eşarj"},
    {"isim":"Eşarj - TCDD Gar",                    "lat":39.9345,"lon":32.8510,"guc":22, "tip":"AC",      "firma":"Eşarj"},
]


# ─────────────────────────────────────────────
#  ENERJİ HESABI
# ─────────────────────────────────────────────
def _hize_gore_tuketim(arac: Dict, hiz: float) -> float:
    egri = sorted(arac["hiz_tuketim"].items())
    if hiz <= egri[0][0]:   return egri[0][1]
    if hiz >= egri[-1][0]:  return egri[-1][1]
    for i in range(len(egri)-1):
        h1,t1 = egri[i]; h2,t2 = egri[i+1]
        if h1 <= hiz <= h2:
            return t1 + (hiz-h1)/(h2-h1)*(t2-t1)
    return arac["tuketim_baz"]


def segment_enerji(arac_adi: str, km: float, yol_tipi: str, rakım_fark_m: float = 0) -> float:
    arac = ARACLAR[arac_adi]
    tip  = YOL_TIPLERI.get(yol_tipi, YOL_TIPLERI["sehir"])
    tuk  = _hize_gore_tuketim(arac, tip["hiz"]) * tip["trafik_carpan"]
    if rakım_fark_m != 0:
        kwh = (1700 * 9.81 * abs(rakım_fark_m)) / 3_600_000
        if rakım_fark_m > 0:
            tuk += kwh / (km * 0.90)
        else:
            tuk = max(0.05, tuk - kwh * arac["rejen"] / km)
    return max(0.001, round(tuk * km * 1.08, 4))


# ─────────────────────────────────────────────
#  GRAF (DIJKSTRA)
# ─────────────────────────────────────────────
class Graf:
    def __init__(self, arac_adi: str = "Tesla Model 3"):
        self.arac_adi = arac_adi
        self.komsular: Dict[str, list] = {d: [] for d in ANKARA_DUGUMLER}
        self._guncelle(arac_adi)

    def _guncelle(self, arac_adi: str):
        self.arac_adi = arac_adi
        for d in self.komsular: self.komsular[d] = []
        for a, b, km, yol_tipi in YOLLAR:
            if a not in self.komsular or b not in self.komsular: continue
            ra = ANKARA_DUGUMLER[a][2]; rb = ANKARA_DUGUMLER[b][2]
            tip  = YOL_TIPLERI.get(yol_tipi, YOL_TIPLERI["sehir"])
            sure = (km / tip["hiz"]) * 60 * tip["trafik_carpan"]
            eab  = segment_enerji(arac_adi, km, yol_tipi, rb-ra)
            eba  = segment_enerji(arac_adi, km, yol_tipi, ra-rb)
            self.komsular[a].append((b, km, sure, eab, yol_tipi))
            self.komsular[b].append((a, km, sure, eba, yol_tipi))

    def dijkstra(self, bas: str, bit: str, krit: str = "mesafe") -> Tuple[List[str], float]:
        dist = {n: float("inf") for n in self.komsular}
        prev: Dict[str, Optional[str]] = {n: None for n in self.komsular}
        dist[bas] = 0.0
        pq = [(0.0, bas)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == bit: break
            if d > dist[u]: continue
            for v, km, sure, enerji, _yt in self.komsular[u]:
                ag = km if krit=="mesafe" else (sure if krit=="sure" else enerji)
                nd = dist[u] + ag
                if nd < dist[v]:
                    dist[v] = nd; prev[v] = u
                    heapq.heappush(pq, (nd, v))
        yol, n = [], bit
        while n: yol.append(n); n = prev[n]
        yol.reverse()
        if not yol or yol[0] != bas: return [], float("inf")
        return yol, dist[bit]

    def cok_amacli_dijkstra(self, bas: str, bit: str,
                             w_e: float, w_t: float, w_c: float
                             ) -> Tuple[List[str], float]:
        """
        CLS ağırlıklı çok amaçlı Dijkstra algoritması.

        Kenar maliyet fonksiyonu:
            cost(u→v) = w_e · Ê(u,v)  +  w_t · T̂(u,v)  +  w_c · Ĉ(u,v)

            Ê(u,v) = enerji / E_REF          (normalize enerji)
            T̂(u,v) = sure   / T_REF          (normalize süre)
            Ĉ(u,v) = kenar_konfor_maliyeti(yol_tipi, Δrakım, önceki_tip)
        """
        if CokAmacliRotaOptimizatoru is None:
            return [], float("inf")
        E_REF     = CokAmacliRotaOptimizatoru.E_REF
        T_REF     = CokAmacliRotaOptimizatoru.T_REF
        konfor_fn = CokAmacliRotaOptimizatoru.kenar_konfor_maliyeti

        dist: Dict[str, float]           = {n: float("inf") for n in self.komsular}
        prev: Dict[str, Optional[str]]   = {n: None          for n in self.komsular}
        prev_tip: Dict[str, Optional[str]] = {n: None        for n in self.komsular}
        dist[bas] = 0.0
        pq = [(0.0, bas)]

        while pq:
            d, u = heapq.heappop(pq)
            if u == bit: break
            if d > dist[u]: continue
            for v, km, sure, enerji, yol_tipi in self.komsular.get(u, []):
                ra  = ANKARA_DUGUMLER.get(u, (0, 0, 0))[2]
                rb  = ANKARA_DUGUMLER.get(v, (0, 0, 0))[2]
                e_n = min(1.0, enerji / (E_REF + 1e-9))
                t_n = min(1.0, sure   / (T_REF + 1e-9))
                k_n = konfor_fn(yol_tipi, rb - ra, prev_tip.get(u))
                nd  = dist[u] + w_e * e_n + w_t * t_n + w_c * k_n
                if nd < dist[v]:
                    dist[v]    = nd
                    prev[v]    = u
                    prev_tip[v] = yol_tipi
                    heapq.heappush(pq, (nd, v))

        yol, n = [], bit
        while n: yol.append(n); n = prev[n]
        yol.reverse()
        if not yol or yol[0] != bas: return [], float("inf")
        return yol, dist[bit]


# ─────────────────────────────────────────────
#  METRİKLER
# ─────────────────────────────────────────────
def yol_metrikleri(yol: List[str], arac_adi: str) -> Dict:
    mesafe = sure = enerji = 0.0
    seg: Dict = {}
    for a, b, km, yol_tipi in YOLLAR:
        ra = ANKARA_DUGUMLER[a][2]; rb = ANKARA_DUGUMLER[b][2]
        tip = YOL_TIPLERI[yol_tipi]
        s   = (km / tip["hiz"]) * 60 * tip["trafik_carpan"]
        seg[(a,b)] = (km, s, segment_enerji(arac_adi, km, yol_tipi, rb-ra))
        seg[(b,a)] = (km, s, segment_enerji(arac_adi, km, yol_tipi, ra-rb))
    for i in range(len(yol)-1):
        k, s, e = seg.get((yol[i], yol[i+1]), (0, 0, 0))
        mesafe += k; sure += s; enerji += e
    return {"mesafe_km": round(mesafe,1), "sure_dk": round(sure,1),
            "enerji_kwh": round(enerji,3)}


# ─────────────────────────────────────────────
#  ŞARJ PLANI
# ─────────────────────────────────────────────
def _en_yakin_sarj(durum: str, sarj_listesi: List[Dict]) -> Optional[Dict]:
    lat, lon = ANKARA_DUGUMLER[durum][:2]
    en, ed = None, float("inf")
    for ist in sarj_listesi:
        dlat = (ist["lat"]-lat)*111
        dlon = (ist["lon"]-lon)*111*math.cos(math.radians(lat))
        d = math.sqrt(dlat**2+dlon**2)
        if d < ed: ed = d; en = {**ist, "uzaklik_km": round(d,2)}
    return en


def sarj_durak_planla(yol, arac_adi, baslangic_yuzde, sarj_listesi,
                      min_esik=MIN_BATARYA_ESIK, hedef_yuzde=80):
    arac   = ARACLAR[arac_adi]
    toplam = arac["batarya"]
    kwh    = toplam * (baslangic_yuzde/100)
    seg: Dict = {}
    for a, b, km, yol_tipi in YOLLAR:
        ra = ANKARA_DUGUMLER[a][2]; rb = ANKARA_DUGUMLER[b][2]
        seg[(a,b)] = segment_enerji(arac_adi, km, yol_tipi, rb-ra)
        seg[(b,a)] = segment_enerji(arac_adi, km, yol_tipi, ra-rb)
    plan = [{"tip":"baslangic", "durum":yol[0],
             "batarya_yuzde":round(baslangic_yuzde,1),
             "enerji_kwh":round(kwh,2)}]
    sarj_no = 0
    tahmin_modeli = EMAHoltBataryaModeli(alfa=0.6, beta=0.4)
    
    # Ortalama segment mesafesi ve rota bilgiklerinin ön hesabı
    kalan_kms = []
    for j in range(len(yol)-1):
        found_km = 1.0 # Fallback
        for a_, b_, km_, _ in YOLLAR:
            if (a_ == yol[j] and b_ == yol[j+1]) or (b_ == yol[j] and a_ == yol[j+1]):
                found_km = km_
                break
        kalan_kms.append(found_km)
    
    avg_segment_len = sum(kalan_kms) / len(kalan_kms) if kalan_kms else 1.0
    
    for i in range(len(yol)-1):
        harcanan     = seg.get((yol[i], yol[i+1]), 0)
        sonraki_kwh  = kwh - harcanan
        sonraki_pct  = (sonraki_kwh / toplam) * 100
        
        # Modeli YÜZDE üzerinden güncelle
        tahmin_modeli.guncelle(sonraki_pct)
        
        # Ufuk Hesabı
        remaining_distance = sum(kalan_kms[i+1:])
        ufuk_h = (remaining_distance / avg_segment_len) if avg_segment_len > 0 else 0
        
        predicted_battery_pct = tahmin_modeli.tahmin_et(ufuk_h)
        
        if predicted_battery_pct < min_esik:
            ist = _en_yakin_sarj(yol[i], sarj_listesi)
            sarj_no += 1
            kwh = toplam*(hedef_yuzde/100)
            plan.append({"tip":"sarj", "durum":yol[i],
                         "batarya_yuzde":round(hedef_yuzde,1),
                         "enerji_kwh":round(kwh,2),
                         "istasyon":ist, "sarj_no":sarj_no})
            sonraki_kwh = kwh - harcanan
        kwh = max(0.0, sonraki_kwh)
        plan.append({"tip":"durak", "durum":yol[i+1],
                     "batarya_yuzde":round((kwh/toplam)*100,1),
                     "enerji_kwh":round(kwh,2)})
    return plan, sarj_no


# ─────────────────────────────────────────────
#  SÜRE (TomTom / Google / Yerel)
# ─────────────────────────────────────────────
def tomtom_sure_cek(bas, bit, timeout=8):
    """TomTom Routing API ile canlı trafik süresi hesaplar."""
    if not TOMTOM_API_KEY:
        return None
    b = ANKARA_DUGUMLER[bas][:2]
    e = ANKARA_DUGUMLER[bit][:2]
    try:
        url = (
            f"https://api.tomtom.com/routing/1/calculateRoute/"
            f"{b[0]},{b[1]}:{e[0]},{e[1]}/json"
        )
        r = requests.get(url, params={
            "key":             TOMTOM_API_KEY,
            "traffic":         "true",
            "travelMode":      "car",
            "routeType":       "fastest",
            "departAt":        "now",
            "language":        "tr-TR",
        }, timeout=timeout)
        r.raise_for_status()
        data   = r.json()
        summ   = data["routes"][0]["summary"]
        # travelTimeInSeconds: canlı trafik dahil süre
        # noTrafficTravelTimeInSeconds: trafik yok süre
        sure_t = summ.get("travelTimeInSeconds", 0) // 60
        sure_n = summ.get("noTrafficTravelTimeInSeconds", sure_t * 60) // 60
        mesafe = summ.get("lengthInMeters", 0)
        return {
            "sure_normal_dk":  int(sure_n),
            "sure_trafik_dk":  int(sure_t),
            "mesafe_m":        mesafe,
            "kaynak":          "TomTom (Canlı Trafik)",
        }
    except Exception:
        return None


def google_sure_cek(bas, bit, timeout=8):
    if not GOOGLE_API_KEY: return None
    b = ANKARA_DUGUMLER[bas][:2]; e = ANKARA_DUGUMLER[bit][:2]
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params={"origins":f"{b[0]},{b[1]}", "destinations":f"{e[0]},{e[1]}",
                    "mode":"driving", "departure_time":"now",
                    "traffic_model":"best_guess", "language":"tr",
                    "key":GOOGLE_API_KEY}, timeout=timeout)
        el = r.json()["rows"][0]["elements"][0]
        if el["status"] != "OK": return None
        sn = el["duration"]["value"]//60
        st = el.get("duration_in_traffic",{}).get("value", sn*60)//60
        return {"sure_normal_dk":sn, "sure_trafik_dk":st,
                "mesafe_m":el["distance"]["value"],
                "kaynak":"Google Maps (Canlı Trafik)"}
    except Exception: return None


def yerel_sure_tahmin(yol, arac_adi):
    saat   = datetime.now().hour
    carpan = {7:1.6,8:1.9,9:1.7,17:1.8,18:2.0,19:1.7}.get(saat, 1.0)
    m      = yol_metrikleri(yol, arac_adi)
    return {"sure_normal_dk":round(m["sure_dk"]),
            "sure_trafik_dk":round(m["sure_dk"]*carpan),
            "mesafe_m":int(m["mesafe_km"]*1000),
            "kaynak":f"Yerel Tahmin ({saat}:00 trafik ×{carpan})"}


# ─────────────────────────────────────────────
#  DOLULUK SİMÜLASYONU
# ─────────────────────────────────────────────
def doluluk_hesapla(ist):
    saat = datetime.now().hour; gun = datetime.now().weekday()
    tbl  = {0:.08,1:.05,2:.04,3:.04,4:.05,5:.08,6:.15,7:.35,8:.55,9:.60,
            10:.58,11:.55,12:.65,13:.70,14:.68,15:.72,16:.80,17:.85,18:.82,
            19:.75,20:.65,21:.50,22:.35,23:.20}
    baz = tbl.get(saat, 0.5)
    if gun >= 5: baz *= 0.75
    if "AVM" in ist.get("isim","") and gun >= 5: baz *= 1.30
    if ist.get("tip")=="DC Hızlı": baz *= 1.25
    elif ist.get("tip")=="AC":     baz *= 0.80
    random.seed(int(time.time()/300) + hash(ist.get("isim","")))
    d = min(0.98, max(0.0, baz * random.uniform(0.85, 1.15)))
    if d < 0.40:  return {"doluluk_oran":round(d*100,1),"durum":"Müsait",    "renk":"#00FF88","emoji":"🟢"}
    elif d < 0.70:return {"doluluk_oran":round(d*100,1),"durum":"Kısmen Dolu","renk":"#FFB800","emoji":"🟡"}
    else:         return {"doluluk_oran":round(d*100,1),"durum":"Yoğun",     "renk":"#FF4444","emoji":"🔴"}


# ─────────────────────────────────────────────
#  CANLI ŞARJ İSTASYONLARI (TomTom API)
# ─────────────────────────────────────────────
def canli_sarj_istasyonlari_getir(timeout=10):
    if not TOMTOM_API_KEY: return []
    try:
        url = "https://api.tomtom.com/search/2/categorySearch/electric%20vehicle%20station.json"
        params = {
            "key": TOMTOM_API_KEY,
            "lat": 39.9334,
            "lon": 32.8597,
            "radius": 50000,
            "limit": 50,
            "language": "tr-TR"
        }
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        out = []
        for poi in r.json().get("results", []):
            try:
                p = poi.get("poi", {})
                isim = p.get("name", "Şarj İstasyonu")
                firma = p.get("brands", [{"name": "Genel"}])[0].get("name", "Genel")
                
                # Güç ve Tip Analizi
                guc = 22
                tip = "AC"
                cp = poi.get("chargingPark", {})
                connectors = cp.get("connectors", [])
                for c in connectors:
                    kw = c.get("ratedPowerKW", 0)
                    if kw > guc:
                        guc = kw
                        ctype = c.get("currentType", "")
                        if "DC" in ctype or kw > 43:
                            tip = "DC Hızlı"
                
                lat, lon = poi.get("position", {}).get("lat"), poi.get("position", {}).get("lon")
                if lat and lon:
                    out.append({"isim": isim[:60], "lat": float(lat), "lon": float(lon),
                                "guc": guc, "tip": tip, "firma": firma[:20], "kaynak": "TomTom API (Canlı)"})
            except Exception: continue
        return out
    except Exception: return []


# ─────────────────────────────────────────────
#  HARİTA OLUŞTUR
# ─────────────────────────────────────────────
def harita_olustur(bas, bit, arac_adi, bat_pct, rotalar, sarj_ist,
                   aktif, sure_bilgi, sarj_plan, sarj_sayisi,
                   sarj_kaynagi="Yerel Veri", kognitif=None,
                   opt_bilgi=None) -> str:

    merkez = [(ANKARA_DUGUMLER[bas][0]+ANKARA_DUGUMLER[bit][0])/2,
              (ANKARA_DUGUMLER[bas][1]+ANKARA_DUGUMLER[bit][1])/2]
    m = folium.Map(location=merkez, zoom_start=12, tiles="CartoDB dark_matter")

    STIL = {
        "mesafe": {"renk": "#00FF88", "ag": 6, "lbl": "🛣 En Kısa Yol"},
        "sure":   {"renk": "#00CFFF", "ag": 5, "lbl": "⚡ En Hızlı Yol"},
        "enerji": {"renk": "#FFB800", "ag": 5, "lbl": "🔋 En Az Enerji"},
        "mo":     {"renk": "#C77DFF", "ag": 6, "lbl": "⭐ Size Özel Rota"},
    }
    
    # Rotaları aynı yola sahip olanlara göre grupla (üst üste çizilip tooltip karışmasını önler)
    yol_gruplari = {}
    for krit, yol in rotalar.items():
        if not yol: continue
        yol_tup = tuple(yol)
        if yol_tup not in yol_gruplari:
            yol_gruplari[yol_tup] = []
        yol_gruplari[yol_tup].append(krit)

    aktif_yol = rotalar.get(aktif, [])
    aktif_tup = tuple(aktif_yol)

    for yol_tup, krit_listesi in yol_gruplari.items():
        # Bu grupta aktif rota varsa, rengi ve kalınlığı o belirler
        if aktif in krit_listesi:
            ana_krit = aktif
        else:
            # Öncelik sırası: mo > enerji > sure > mesafe
            ana_krit = krit_listesi[0]
            
        stil = STIL[ana_krit]
        lbl_birlesik = " + ".join([STIL[k]["lbl"] for k in krit_listesi])
        coords = [ANKARA_DUGUMLER[d][:2] for d in yol_tup]
        met = yol_metrikleri(list(yol_tup), arac_adi)
        
        is_aktif = (yol_tup == aktif_tup)
        
        folium.PolyLine(
            locations=coords, color=stil["renk"],
            weight=stil["ag"] if is_aktif else 3,
            opacity=1.0 if is_aktif else 0.35,
            tooltip=lbl_birlesik,
            popup=folium.Popup(
                f"<div style='font-family:Arial;font-size:12px'>"
                f"<b style='color:{stil['renk']}'>{lbl_birlesik}</b><br><br>"
                f"📏 {met['mesafe_km']} km<br>"
                f"⏱ {met['sure_dk']:.0f} dk<br>"
                f"⚡ {met['enerji_kwh']} kWh</div>",
                max_width=250)
        ).add_to(m)

    plan_map = {a["durum"]: a for a in sarj_plan}
    def brenk(p): return "#00FF88" if p>40 else ("#FFB800" if p>15 else "#FF4444")

    for d in aktif_yol:
        if d in (bas, bit): continue
        lat, lon = ANKARA_DUGUMLER[d][:2]
        adim = plan_map.get(d, {}); pct = adim.get("batarya_yuzde","?")
        rc   = brenk(pct) if isinstance(pct,(int,float)) else "#888"
        folium.CircleMarker(location=[lat,lon], radius=6,
            color=rc, fill=True, fill_color=rc, fill_opacity=0.85,
            tooltip=f"📍 {d} — 🔋 %{pct}").add_to(m)

    for adim in sarj_plan:
        if adim["tip"] != "sarj": continue
        lat, lon = ANKARA_DUGUMLER[adim["durum"]][:2]
        ist = adim.get("istasyon") or {}
        folium.Marker(
            location=[lat,lon],
            popup=folium.Popup(
                f"<div style='font-family:Arial;min-width:180px'>"
                f"<b style='color:#FF6600'>⚡ ZORUNLU ŞARJ #{adim['sarj_no']}</b><br>"
                f"<hr style='margin:4px 0'>📍 <b>{adim['durum']}</b><br>"
                f"🔋 Şarj sonrası: <b>%{adim['batarya_yuzde']}</b><br>"
                f"🔌 {ist.get('isim','Yakın istasyon')}<br>"
                f"⚡ {ist.get('guc','?')} kW ({ist.get('tip','?')})</div>",
                max_width=240),
            tooltip=f"⚡ Şarj #{adim['sarj_no']} — {adim['durum']}",
            icon=folium.Icon(color="orange", icon="bolt", prefix="fa")
        ).add_to(m)

    b_lat, b_lon = ANKARA_DUGUMLER[bas][:2]
    folium.Marker(location=[b_lat,b_lon],
        popup=folium.Popup(
            f"<b>🚀 {bas}</b><br>🔋 %{bat_pct}<br>"
            f"⏱ Trafik: {sure_bilgi['sure_trafik_dk']} dk | Normal: {sure_bilgi['sure_normal_dk']} dk<br>"
            f"<small>{sure_bilgi['kaynak']}</small>", max_width=270),
        tooltip=f"🟢 {bas} — Başlangıç",
        icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)

    e_lat, e_lon = ANKARA_DUGUMLER[bit][:2]
    son = next((a for a in reversed(sarj_plan) if a["durum"]==bit), {})
    kalan = son.get("batarya_yuzde","?")
    folium.Marker(location=[e_lat,e_lon],
        popup=folium.Popup(f"<b>🏁 {bit}</b><br>🔋 Varışta: %{kalan}", max_width=200),
        tooltip=f"🔴 {bit} — Bitiş (%{kalan})",
        icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(m)

    ts = datetime.now().strftime("%H:%M")
    for ist in sarj_ist:
        dol = doluluk_hesapla(ist)
        rc  = "red"    if ist["guc"]>=100 else ("orange" if ist["guc"]>=43 else "blue")
        ik  = "bolt"   if ist["guc"]>=100 else ("plug"   if ist["guc"]>=43 else "battery-three-quarters")
        sm  = "⚡"     if ist["guc"]>=100 else ("🔌"     if ist["guc"]>=43 else "🔋")
        bar = "█"*int(dol["doluluk_oran"]/10) + "░"*(10-int(dol["doluluk_oran"]/10))
        folium.Marker(location=[ist["lat"],ist["lon"]],
            popup=folium.Popup(
                f"<div style='font-family:Arial;min-width:200px;padding:4px'>"
                f"<b>{sm} {ist['isim']}</b><hr style='margin:4px 0'>"
                f"⚡ {ist['guc']} kW &nbsp; 🔌 {ist['tip']} &nbsp; 🏢 {ist.get('firma','')}"
                f"<hr style='margin:4px 0'>"
                f"<div style='font-family:monospace;color:{dol['renk']}'>{bar}</div>"
                f"<b style='color:{dol['renk']}'>{dol['emoji']} {dol['durum']} — %{dol['doluluk_oran']}</b><br>"
                f"<small style='color:#888'>{ts} | {ist.get('kaynak','Yerel')}</small></div>",
                max_width=260),
            tooltip=f"{dol['emoji']} {ist['isim']} %{dol['doluluk_oran']}",
            icon=folium.Icon(color=rc, icon=ik, prefix="fa")).add_to(m)

    for d, bilgi in ANKARA_DUGUMLER.items():
        if d in (bas,bit) or d in aktif_yol: continue
        folium.CircleMarker(location=bilgi[:2], radius=3,
            color="#777", fill=True, fill_color="#444", fill_opacity=0.5,
            tooltip=f"{d} ({bilgi[2]}m)").add_to(m)

    plan_html = ""
    for adim in sarj_plan:
        if adim["tip"] == "sarj":
            plan_html += (f"<div style='color:#FF6600'>⚡ Şarj #{adim['sarj_no']} @ "
                          f"{adim['durum']} → %{adim['batarya_yuzde']}</div>")
        elif adim["tip"] == "baslangic":
            plan_html += f"<div style='color:#00FF88'>🚀 {adim['durum']}: %{adim['batarya_yuzde']}</div>"
        elif adim["durum"] == bit:
            rc2 = "#00FF88" if isinstance(adim.get("batarya_yuzde"),float) and adim["batarya_yuzde"]>20 else "#FF4444"
            plan_html += f"<div style='color:{rc2}'>🏁 {bit}: %{adim['batarya_yuzde']}</div>"

    sarj_ozet = (f"<b style='color:#FF6600'>⚡ {sarj_sayisi} zorunlu şarj durağı</b>"
                 if sarj_sayisi > 0
                 else "<span style='color:#00FF88'>✅ Şarj gerekmez</span>")
    met_aktif = yol_metrikleri(aktif_yol, arac_adi)

    panel = f"""
    <div style="position:fixed;top:20px;right:20px;z-index:9999;
        background:rgba(13,15,25,0.94);border:1px solid #333;border-radius:12px;
        padding:14px 18px;font-family:Arial;font-size:12px;color:#ddd;
        box-shadow:0 4px 24px rgba(0,0,0,.7);min-width:240px;max-width:290px">
      <b style="font-size:14px;color:#00FF88">⚡ Rota Özeti</b>
      <hr style="margin:6px 0;border-color:#333">
      <div style="color:#999;font-size:11px">🚗 {arac_adi}</div>
      <div style="color:#999;font-size:11px">📍 {bas} → {bit}</div>
      <hr style="margin:6px 0;border-color:#333">
      <div>📏 {met_aktif['mesafe_km']} km &nbsp; ⚡ {met_aktif['enerji_kwh']} kWh</div>
      <div>⏱ Trafik: <b style="color:#00CFFF">{sure_bilgi['sure_trafik_dk']} dk</b>
           &nbsp; Normal: {sure_bilgi['sure_normal_dk']} dk</div>
      <div style="color:#666;font-size:10px">{sure_bilgi['kaynak']}</div>
      <hr style="margin:6px 0;border-color:#333">
      <b>🔋 Batarya Planı:</b><br>{plan_html}
      <hr style="margin:6px 0;border-color:#333">
      {sarj_ozet}
    </div>"""

    legend = f"""
    <div style="position:fixed;bottom:28px;left:28px;z-index:9999;
        background:rgba(13,15,25,0.93);border:1px solid #333;border-radius:12px;
        padding:13px 17px;font-family:Arial;font-size:12px;color:#ddd;
        box-shadow:0 4px 20px rgba(0,0,0,.6);min-width:205px">
      <b style="font-size:13px">🗺 Gösterge</b><br><br>
      <span style="color:#00FF88">━━</span> En Kısa &nbsp;
      <span style="color:#00CFFF">━━</span> En Hızlı &nbsp;
      <span style="color:#FFB800">━━</span> En Az Enerji &nbsp;
      <span style="color:#C77DFF">━━</span> Size Özel<br><br>
      <b>Şarj:</b><br>
      <span style="color:#ff6b6b">⚡</span> DC Hızlı (100kW+) &nbsp;
      <span style="color:#ffa500">🔌</span> DC &nbsp;
      <span style="color:#4fc3f7">🔋</span> AC<br><br>
      <b>Batarya (duraklar):</b><br>
      <span style="color:#00FF88">●</span>&gt;40% &nbsp;
      <span style="color:#FFB800">●</span>15-40% &nbsp;
      <span style="color:#FF4444">●</span>&lt;15%<br><br>
      <span style="color:#666;font-size:10px">{ts} | {sarj_kaynagi}<br>
      {len(ANKARA_DUGUMLER)} nokta | {len(sarj_ist)} ist.</span>
    </div>"""

    m.get_root().html.add_child(folium.Element(panel))
    m.get_root().html.add_child(folium.Element(legend))

    if kognitif:
        ikon = kognitif.get("ikon","😐"); mod  = kognitif.get("mod","notr").title()
        cls  = kognitif.get("cls",0);    renk = kognitif.get("renk","#00CFFF")
        acik = kognitif.get("aciklama","")
        oneriler = kognitif.get("oneriler",[])
        bar_w = int(cls/100*180)
        oneri_html = "".join(f"<div style='margin-top:3px'>{o}</div>" for o in oneriler[:3])
        kog_panel = f"""
        <div style="position:fixed;top:20px;left:20px;z-index:9999;
            background:rgba(13,15,25,0.94);border:1px solid {renk};
            border-radius:12px;padding:12px 16px;
            font-family:Arial;font-size:12px;color:#ddd;
            box-shadow:0 4px 20px rgba(0,0,0,.7);min-width:220px">
          <b style="font-size:13px;color:{renk}">{ikon} AffectEV — Sürücü Durumu</b>
          <hr style="margin:6px 0;border-color:{renk};opacity:.4">
          <div><b>Mod: {mod}</b></div>
          <div style="background:#1a1a2e;border-radius:4px;height:12px;width:180px;margin:4px 0">
            <div style="background:{renk};height:12px;border-radius:4px;width:{bar_w}px"></div>
          </div>
          <div style="color:{renk};font-size:11px">Kognitif Yük: {cls:.0f} / 100</div>
          <div style="color:#888;font-size:10px;margin-top:4px">{acik}</div>
          {oneri_html}
        </div>"""
        m.get_root().html.add_child(folium.Element(kog_panel))

    # ── Çok Amaçlı Optimizasyon ve Baseline Analiz Paneli ─────────
    if opt_bilgi:
        aw  = opt_bilgi.get("agirliklar", {})
        fsk = opt_bilgi.get("f_skorlar", {})
        met = opt_bilgi.get("metrikleri", {})
        cls_v = opt_bilgi.get("cls", "—")
        mod_v = opt_bilgi.get("mod", "—")
        w_e_p = f"{aw.get('w_enerji', 0):.0%}"
        w_t_p = f"{aw.get('w_sure',   0):.0%}"
        w_c_p = f"{aw.get('w_konfor', 0):.0%}"
        MOD_EMOJI = {"yorgun": "😴 Yorgun", "stresli": "😰 Stresli",
                     "notr": "😐 Normal", "enerjik": "😄 Enerjik"}
        mod_goster = MOD_EMOJI.get(mod_v, "😐 Normal")

        KRIT_BASLIK = {
            "mesafe": "🛣 En Kısa Yol",
            "sure":   "⚡ En Hızlı Yol",
            "enerji": "🔋 En Az Enerji",
            "mo":     "⭐ Size Özel Rota",
        }
        en_iyi_krit = min(fsk, key=fsk.get) if fsk else "—"

        # Daha Sade ve Modern Liste Stili
        liste_html = ""
        for k in ["mo", "sure", "enerji", "mesafe"]:
            if k not in fsk: continue
            skor   = fsk[k]
            mm     = met.get(k, {})
            sure_v = round(mm.get("sure_dk", 0))
            en_v   = mm.get("enerji_kwh", 0)
            uygunluk = round((1 - skor) * 100)
            
            if k == "mo":
                renk = "#C77DFF"
                bg_renk = "rgba(199, 125, 255, 0.15)"
                border = "border-left: 3px solid #C77DFF;"
            else:
                renk = "#bbb"
                bg_renk = "rgba(255, 255, 255, 0.03)"
                border = "border-left: 3px solid transparent;"
                
            liste_html += f"""
            <div style="background:{bg_renk}; {border} padding:6px 10px; margin-bottom:6px; border-radius:4px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:{renk}; font-weight:bold; font-size:11px;">{KRIT_BASLIK[k]}</span>
                <span style="color:#00FF88; font-size:10px; font-weight:bold;">%{uygunluk} Uygun</span>
              </div>
              <div style="color:#888; font-size:10px; margin-top:3px;">
                ⏱ {sure_v} dk &nbsp;•&nbsp; ⚡ {en_v} kWh
              </div>
            </div>
            """

        opt_panel = f"""
        <div style="position:fixed;bottom:28px;right:28px;z-index:9999;
            background:rgba(13,15,25,0.96);border:1px solid #7c4dff;
            border-radius:12px;padding:16px;
            font-family:Arial, sans-serif;color:#ddd;
            box-shadow:0 6px 30px rgba(124,77,255,.3);min-width:270px">
            
          <div style="margin-bottom:12px;">
            <b style="color:#C77DFF; font-size:14px;">🧭 Rotanızı Nasıl Seçtik?</b>
          </div>
          
          <div style="background:rgba(255,255,255,0.06); padding:10px; border-radius:8px; margin-bottom:14px;">
            <div style="color:#999; font-size:10px; margin-bottom:4px;">Tespit Edilen Sürücü Durumu:</div>
            <div style="color:#fff; font-size:14px; font-weight:bold;">{mod_goster}</div>
          </div>
          
          <div style="margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid #3a2a5a;">
            <div style="color:#999; font-size:10px; margin-bottom:6px;">Rota belirlenirken önem sırası:</div>
            <div style="display:flex; justify-content:space-between; font-size:11px; font-weight:bold;">
              <span style="color:#FFB800">⚡ Enerji: {w_e_p}</span>
              <span style="color:#00CFFF">⏱ Süre: {w_t_p}</span>
              <span style="color:#C77DFF">😊 Konfor: {w_c_p}</span>
            </div>
          </div>
          
          <b style="font-size:11px; color:#aaa; display:block; margin-bottom:8px;">Alternatif Rotalar:</b>
          {liste_html}
          
        </div>"""
        m.get_root().html.add_child(folium.Element(opt_panel))

    cikti = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "ankara_ev_rota.html")
    m.save(cikti)
    return cikti, m


# ═════════════════════════════════════════════
#  TEMA & RENK PALETİ  —  Apple HIG
# ═════════════════════════════════════════════
BG_ROOT  = "#F5F5F7"   # Apple off-white arka plan
BG_PANEL = "#FFFFFF"   # Saf beyaz panel
BG_CARD  = "#FFFFFF"   # Kart yüzeyi
BG_INPUT = "#F2F2F7"   # Giriş alanı (iOS secondary bg)
FG_MAIN  = "#1C1C1E"   # Apple label (near-black)
FG_SUB   = "#6E6E73"   # Apple secondary label
FG_MUTED = "#C7C7CC"   # Apple tertiary label
ACCENT   = "#34C759"   # iOS Green (başarı / onay)
ACCENT2  = "#007AFF"   # iOS Blue (birincil eylem)
WARN     = "#FF9500"   # iOS Orange
DANGER   = "#FF3B30"   # iOS Red
PURPLE   = "#5856D6"   # iOS Indigo
SEPARATOR= "#E5E5EA"   # Ayırıcı çizgi

FONT_H1  = ("Helvetica Neue", 22, "bold")
FONT_H2  = ("Helvetica Neue", 15, "bold")
FONT_H3  = ("Helvetica Neue", 12, "bold")
FONT_BODY= ("Helvetica Neue", 10)
FONT_SM  = ("Helvetica Neue", 9)
FONT_XS  = ("Helvetica Neue", 8)
FONT_MONO= ("Menlo",          10)

MOD_ISIM  = {"yorgun":"😴 Yorgun", "stresli":"😰 Stresli",
             "notr":"😐 Nötr",    "enerjik":"😄 Enerjik"}
KRIT_ISIM = {"mesafe":"🛣 En Kısa Rota", "sure":"⚡ En Hızlı Rota",
             "enerji":"🔋 En Az Enerjili Rota"}



# ═════════════════════════════════════════════
#  GUI  —  SAYFA TABANLI UYGULAMA
# ═════════════════════════════════════════════
class EVRotaGUI:

    SAYFALAR      = ["surucucler", "analiz", "mod_sonuc", "rota", "harita"]
    SAYFA_ETIKET  = ["Sürücü", "Analiz", "Sonuç", "Rota", "Harita"]

    # ─────────────────────────────────────────
    #  BAŞLANGIÇ
    # ─────────────────────────────────────────
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AffectEV")
        self.root.geometry("800x700")
        self.root.configure(bg=BG_ROOT)
        self.root.resizable(False, False)

        # Backend
        self.graf         = Graf("Tesla Model 3")
        self.sarj_ist     = SARJ_ISTASYONLARI_FALLBACK.copy()
        self.sarj_kaynagi = "Yerel Veri"
        self.kognitif_aktif = KOGNITIF_VAR
        self.pm:  Optional[SurucuProfilYonetici]  = None
        self.klz: Optional[KognitivYukAnalizci]   = None
        self.dro: Optional[DuyguRotaOptimizatoru] = None
        self.aktif_uid  = "U01"
        self.aktif_cls  = 40.0
        self.aktif_mod  = "notr"
        self.cls_params: Dict = {}
        self._son_harita_path = ""

        if self.kognitif_aktif:
            self.pm  = SurucuProfilYonetici()
            profil   = self.pm.profil_al(self.aktif_uid)
            if profil:
                if GELISMIS_VAR:
                    self.klz = MLDestekliKognitivYukAnalizci(profil)
                else:
                    self.klz = KognitivYukAnalizci(profil)
            self.dro = DuyguRotaOptimizatoru(self.pm)
            
        if GELISMIS_VAR:
            self.kaydedici = SurusVeriKaydedici()
            self.duygu_motor = SurekliDuyguMotoru(
                self.pm.profil_al(self.aktif_uid) if self.pm else None
            )

        # Sayfa sistemi
        self.sayfa_frames: Dict[str, tk.Frame] = {}
        self.aktif_sayfa  = ""

        self._gui_olustur()
        threading.Thread(target=self._sarj_guncelle, daemon=True).start()

    # ─────────────────────────────────────────
    #  YARDIMCILAR
    # ─────────────────────────────────────────
    def _durum(self, t: str):
        try: self.root.after(0, lambda: self.durum_lbl.config(text=t))
        except Exception: pass


    def _sayfa_goster(self, sayfa_adi: str):
        for f in self.sayfa_frames.values():
            f.place_forget()
        self.aktif_sayfa = sayfa_adi
        self.sayfa_frames[sayfa_adi].place(x=0, y=0, relwidth=1, relheight=1)
        self._prog_guncelle()

    def _prog_guncelle(self):
        idx = self.SAYFALAR.index(self.aktif_sayfa) if self.aktif_sayfa in self.SAYFALAR else -1
        for i, (dot, lbl) in enumerate(self._prog_lbls):
            if i < idx:
                dot.config(bg=ACCENT, fg="#FFFFFF", text="✓")
                lbl.config(fg=ACCENT)
            elif i == idx:
                dot.config(bg=ACCENT2, fg="#FFFFFF", text=str(i+1))
                lbl.config(fg=ACCENT2)
            else:
                dot.config(bg=FG_MUTED, fg="#FFFFFF", text=str(i+1))
                lbl.config(fg=FG_MUTED)

    def _sarj_guncelle(self):
        self._durum("🔄 Canlı Şarj İstasyonları (TomTom API) yükleniyor...")
        d = canli_sarj_istasyonlari_getir(10)
        if d:
            self.sarj_ist = d
            self.sarj_kaynagi = f"TomTom API ({len(d)} ist.)"
            self._durum(f"✅ {len(d)} canlı şarj istasyonu yüklendi")
        else:
            self._durum(f"⚠️  API yanıt vermedi, {len(self.sarj_ist)} yerel istasyon aktif")

    # ─────────────────────────────────────────
    #  ANA GUI OLUŞTUR
    # ─────────────────────────────────────────
    def _gui_olustur(self):
        # ── Üst şerit (header)
        header = tk.Frame(self.root, bg="#080b14", height=110)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Logo + durum satırı
        logo_row = tk.Frame(header, bg="#080b14")
        logo_row.pack(fill="x", padx=24, pady=(12, 0))

        tk.Label(logo_row, text="⚡", font=("Segoe UI", 24),
                 bg="#080b14", fg=ACCENT).pack(side="left")
        tk.Label(logo_row, text="AffectEV",
                 font=("Segoe UI", 19, "bold"),
                 bg="#080b14", fg=FG_MAIN).pack(side="left", padx=(5, 0))
        tk.Label(logo_row, text=" Duygu-Duyarlı EV Rota Planlayıcı",
                 font=("Segoe UI", 9),
                 bg="#080b14", fg=FG_SUB).pack(side="left", pady=(6, 0))

        self.durum_lbl = tk.Label(logo_row, text="⏳ Yükleniyor...",
                                  font=FONT_XS, bg="#080b14", fg=WARN)
        self.durum_lbl.pack(side="right", pady=(6, 0))

        # İlerleme adımları
        prog_row = tk.Frame(header, bg="#080b14")
        prog_row.pack(fill="x", padx=24, pady=(8, 8))
        self._prog_lbls = []

        for i, et in enumerate(self.SAYFA_ETIKET):
            dot = tk.Label(prog_row, text=str(i+1), width=2, height=1,
                           font=("Segoe UI", 8, "bold"),
                           bg=FG_MUTED, fg=FG_SUB, relief="flat")
            dot.pack(side="left")
            name = tk.Label(prog_row, text=f"  {et}",
                            font=("Segoe UI", 8), bg="#080b14", fg=FG_MUTED)
            name.pack(side="left")
            self._prog_lbls.append((dot, name))
            if i < len(self.SAYFA_ETIKET) - 1:
                tk.Label(prog_row, text="   ——   ",
                         font=("Segoe UI", 7), bg="#080b14", fg="#222").pack(side="left")

        # Çizgi ayırıcı
        tk.Frame(self.root, bg="#1a1d30", height=2).pack(fill="x")

        # Sayfa konteyneri
        self._container = tk.Frame(self.root, bg=BG_ROOT)
        self._container.pack(fill="both", expand=True)

        # Her sayfayı oluştur
        self._olustur_s1_surucucler()
        self._olustur_s2_analiz()
        self._olustur_s3_mod_sonuc()
        self._olustur_s4_rota()
        self._olustur_s5_harita()

        self._sayfa_goster("surucucler")

    # ─── Sayfa çerçevesi yardımcısı
    def _yeni_sayfa(self, sayfa_adi: str) -> tk.Frame:
        f = tk.Frame(self._container, bg=BG_ROOT)
        self.sayfa_frames[sayfa_adi] = f
        return f

    # ─── Kart bileşeni — Apple card stili
    def _kart(self, parent, baslik: str = "", renk: str = ACCENT2,
              pady=(8, 6), padx=24) -> tk.Frame:
        outer = tk.Frame(parent, bg=BG_ROOT)
        outer.pack(fill="x", padx=padx, pady=pady)
        if baslik:
            tk.Label(outer, text=baslik, font=FONT_H3,
                     bg=BG_ROOT, fg=FG_SUB).pack(anchor="w", pady=(0, 4))
        # Beyaz kart + ince gri kenarlık
        border = tk.Frame(outer, bg=SEPARATOR, bd=0)
        border.pack(fill="x")
        card = tk.Frame(border, bg=BG_CARD, padx=18, pady=14)
        card.pack(fill="x", padx=1, pady=1)
        return card

    # ─── Navigasyon butonları — Apple pill buton stili
    def _nav_bar(self, parent, geri_cmd=None, ileri_cmd=None,
                 ileri_text="Devam  →", ileri_renk=ACCENT2,
                 ileri_disabled=False) -> tk.Frame:
        # İnce üst ayırıcı
        tk.Frame(parent, bg=SEPARATOR, height=1).pack(fill="x", side="bottom")
        bar = tk.Frame(parent, bg=BG_PANEL, pady=14)
        bar.pack(fill="x", padx=24, side="bottom")
        if geri_cmd:
            tk.Button(bar, text="←  Geri", command=geri_cmd,
                      bg=BG_INPUT, fg=FG_SUB,
                      font=FONT_BODY, relief="flat",
                      cursor="hand2", padx=18, pady=8
                      ).pack(side="left")
        if ileri_cmd:
            state = "disabled" if ileri_disabled else "normal"
            b = tk.Button(bar, text=ileri_text, command=ileri_cmd,
                          bg=ACCENT2 if not ileri_disabled else FG_MUTED,
                          fg="#FFFFFF",
                          font=FONT_H3, relief="flat",
                          cursor="hand2", padx=22, pady=9,
                          state=state,
                          activebackground="#0056CC")
            b.pack(side="right")
            return b
        return bar

    # ═══════════════════════════════════════════
    #  SAYFA 1 — SÜRÜCÜ SEÇİMİ
    # ═══════════════════════════════════════════
    def _olustur_s1_surucucler(self):
        s = self._yeni_sayfa("surucucler")

        # Başlık
        tk.Label(s, text="Merhaba! 👋",
                 font=FONT_H1, bg=BG_ROOT, fg=FG_MAIN
                 ).pack(anchor="w", padx=24, pady=(24, 2))
        tk.Label(s, text="Başlamak için bu yolculuğu yapacak sürücüyü seçin.",
                 font=FONT_BODY, bg=BG_ROOT, fg=FG_SUB
                 ).pack(anchor="w", padx=24, pady=(0, 8))

        # Sürücü seçim kartı
        kart = self._kart(s, "👤  Sürücü Seçimi", ACCENT2)

        uid_listesi = [f"{p['uid']} — {p['isim']}" for p in self.pm.suruculer] \
            if (self.kognitif_aktif and self.pm) else ["Sürücü bulunamadı"]

        self.uid_var = tk.StringVar(value=uid_listesi[0])

        sel_row = tk.Frame(kart, bg=BG_CARD)
        sel_row.pack(fill="x", pady=(0, 10))
        tk.Label(sel_row, text="Sürücü :", font=FONT_BODY,
                 bg=BG_CARD, fg=FG_SUB, width=10, anchor="w").pack(side="left")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
                         fieldbackground=BG_INPUT, background=BG_CARD,
                         foreground=FG_MAIN, selectbackground=BG_INPUT,
                         arrowcolor=ACCENT2)
        self.uid_cb = ttk.Combobox(sel_row, textvariable=self.uid_var,
                                   values=uid_listesi, width=34,
                                   state="readonly", style="Dark.TCombobox",
                                   font=FONT_BODY)
        self.uid_cb.pack(side="left", padx=(6, 0))
        self.uid_cb.bind("<<ComboboxSelected>>", lambda _: self.profil_bilgi_lbl.config(text=""))

        # Profil yükle butonu
        tk.Button(kart, text="✅  Profili Yükle",
                  command=self._profili_yukle,
                  bg=ACCENT2, fg=BG_ROOT,
                  font=FONT_H3, relief="flat",
                  cursor="hand2", padx=18, pady=7
                  ).pack(anchor="w", pady=(6, 4))

        self.profil_bilgi_lbl = tk.Label(kart, text="",
                                          font=FONT_SM, bg=BG_CARD,
                                          fg=ACCENT, justify="left")
        self.profil_bilgi_lbl.pack(anchor="w")

        # Profil detayı kartı
        self.profil_detay_kart = self._kart(s, "📊  Profil Özeti", FG_SUB)
        self.profil_detay_lbl  = tk.Label(self.profil_detay_kart,
                                           text="Profil yüklendikten sonra bilgiler burada görünür.",
                                           font=FONT_SM, bg=BG_CARD, fg=FG_SUB,
                                           justify="left")
        self.profil_detay_lbl.pack(anchor="w")

        # Kognitif mod yoksa uyarı
        if not self.kognitif_aktif:
            uyari = self._kart(s, "", WARN)
            tk.Label(uyari,
                     text="⚠️  Kognitif motor yüklenemedi.\n"
                          "pip install opencv-python numpy",
                     font=FONT_SM, bg=BG_CARD, fg=WARN).pack(anchor="w")

        # Nav
        self.s1_ileri_btn = self._nav_bar(
            s, geri_cmd=None,
            ileri_cmd=lambda: self._sayfa_goster("analiz"),
            ileri_text="Analize Geç  →",
            ileri_disabled=True)

    def _profili_yukle(self):
        if not (self.kognitif_aktif and self.pm): return
        uid    = self.uid_var.get().split(" — ")[0]
        self.aktif_uid = uid
        profil = self.pm.profil_al(uid)
        if not profil:
            self._durum("⚠️ Profil bulunamadı!"); return

        self.klz = KognitivYukAnalizci(profil)
        isim  = profil["isim"]
        yas   = profil["yas"]
        mes   = profil["meslek"]
        tip   = profil.get("gun_ici_tip","—").title()
        dom   = MOD_ISIM.get(profil.get("dominant_duygu","notr"), "Nötr")

        self.profil_bilgi_lbl.config(text=f"✅  {isim} başarıyla yüklendi.")
        self.profil_detay_lbl.config(
            fg=FG_MAIN,
            text=(f"  👤  {isim}   •   {yas} yaş   •   {mes}\n"
                  f"  🕐  Tip: {tip}   •   Dominant Duygu: {dom}"))

        self._durum(f"✅ Profil yüklendi: {isim}")
        # İleri butonu aç
        self.s1_ileri_btn.config(state="normal")

    # ═══════════════════════════════════════════
    #  SAYFA 2 — DUYGU ANALİZİ
    # ═══════════════════════════════════════════
    def _olustur_s2_analiz(self):
        s = self._yeni_sayfa("analiz")

        tk.Label(s, text="Duygu Analizi 📷",
                 font=FONT_H1, bg=BG_ROOT, fg=FG_MAIN
                 ).pack(anchor="w", padx=24, pady=(24, 2))
        tk.Label(s,
                 text=f"Kameranın önüne geçin. {TARAMA_SURE} saniyelik analiz yapılacak.",
                 font=FONT_BODY, bg=BG_ROOT, fg=FG_SUB
                 ).pack(anchor="w", padx=24, pady=(0, 8))

        # Mod bilgisi kartı
        kart = self._kart(s, "", ACCENT2)

        sim_txt = ("🎥  OpenCV mevcut — gerçek kamera aktif"
                   if (KOGNITIF_VAR and CV2_VAR)
                   else "🔬  Simülasyon modu — biyometrik model kullanılıyor")
        tk.Label(kart, text=sim_txt, font=FONT_SM,
                 bg=BG_CARD, fg=FG_SUB).pack(anchor="w", pady=(0, 8))

        # Büyük geri sayım / durum
        self.analiz_geri_say_lbl = tk.Label(kart,
            text=f"▶  {TARAMA_SURE} Saniyelik Analizi Başlat",
            font=("Segoe UI", 15, "bold"),
            bg=BG_CARD, fg=ACCENT2)
        self.analiz_geri_say_lbl.pack(anchor="w")

        # İlerleme çubuğu
        self.analiz_prog_canvas = tk.Canvas(kart, width=700, height=10,
                                             bg="#1a1d30", highlightthickness=0)
        self.analiz_prog_canvas.pack(fill="x", pady=(8, 4))

        # Anlık CLS gösterge
        cls_row = tk.Frame(kart, bg=BG_CARD)
        cls_row.pack(fill="x", pady=(4, 0))
        tk.Label(cls_row, text="Kognitif Yük :", font=FONT_SM,
                 bg=BG_CARD, fg=FG_SUB).pack(side="left")
        self.analiz_cls_canvas = tk.Canvas(cls_row, width=260, height=14,
                                            bg=BG_ROOT, highlightthickness=0)
        self.analiz_cls_canvas.pack(side="left", padx=8)
        self.analiz_cls_lbl = tk.Label(cls_row, text="—",
                                        font=FONT_MONO, bg=BG_CARD, fg=FG_SUB)
        self.analiz_cls_lbl.pack(side="left")

        # Başlat butonu
        self.tarama_btn = tk.Button(kart,
            text=f"📷   {TARAMA_SURE} Saniyelik Yüz Analizi Başlat",
            command=self._yuz_tara,
            bg="#0d2b1a", fg="#44cc77",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=20, pady=10)
        self.tarama_btn.pack(fill="x", pady=(12, 0))

        # Nav
        self._nav_bar(s,
            geri_cmd=lambda: self._sayfa_goster("surucucler"),
            ileri_cmd=lambda: self._sayfa_goster("mod_sonuc"),
            ileri_text="Sonuca Bak  →",
            ileri_disabled=True)
        # Saklı ileri buton referansı
        self.s2_ileri_btn = s.winfo_children()[-1]

    def _yuz_tara(self):
        if not (self.kognitif_aktif and self.klz): return
        self.tarama_btn.config(state="disabled", text="⏳  Analiz yapılıyor...")
        self.analiz_geri_say_lbl.config(text="Lütfen kameraya bakın...", fg=WARN)

        def analiz():
            kamera_acildi = self.klz.kamera_baslat(display=True)
            cls_ornekler  = []
            # Yorgunluk Eğrisi Tahminleyicisi Başlatıldı
            y_modeli = EMAHoltYorgunlukModeli(alfa=0.6, beta=0.4)

            for saniye in range(TARAMA_SURE, 0, -1):
                # Geri sayım güncelle
                yuzde = int((TARAMA_SURE - saniye + 1) / TARAMA_SURE * 100)
                msg = (f"🎥  {saniye} saniye kameraya bakın..."
                       if kamera_acildi
                       else f"🔬  {saniye} saniye analiz ediliyor...")
                self.root.after(0, lambda m=msg, y=yuzde: self._analiz_prog_guncelle(m, y))
                time.sleep(1)

                # CLS örneği al (simülasyonda biraz daha gerçekçi noise ekle)
                if kamera_acildi:
                    c = self.klz.anlik_cls()
                else:
                    c = self.klz.sim_cls_hesapla()
                    # Gerçekçilik: küçük zaman-bağımlı varyasyon
                    ilerleme_orani = (TARAMA_SURE - saniye) / TARAMA_SURE
                    c = c * (0.90 + 0.10 * ilerleme_orani) + random.gauss(0, 1.8)
                    c = max(0.0, min(100.0, c))

                cls_ornekler.append(c)
                # Trend hesabı için model beslemesi
                y_modeli.guncelle(c)

                # Anlık CLS'yi ekranda göster
                self.root.after(0, lambda cv=c: self._analiz_cls_goster(cv))

            if kamera_acildi:
                self.klz.kamera_durdur()

            # Ağırlıklı ortalama
            if len(cls_ornekler) >= 4:
                w = list(range(1, len(cls_ornekler) + 1))
                mevcut_cls = sum(c*ww for c,ww in zip(cls_ornekler, w)) / sum(w)
            else:
                mevcut_cls = sum(cls_ornekler) / len(cls_ornekler) if cls_ornekler else 40.0

            # --- PREDICTIVE FATIGUE DECISION ---
            # İleriye dönük 20 adımlık (örn: ~45 dk sürüş ufku) yorgunluk simülasyonu
            gelecek_cls = y_modeli.tahmin_et(20)
            
            # Dinamik Rota Sapması (Soft Constraint):
            # Eğer sürücünün trendi hızlı yorulmaya işaret ediyorsa (trend > 0.5) ve gelecek CLS yüksek seviyelere 
            # (stresli bölge > 75.0) ulaşacaksa; sistemi 'şimdiden' aşırı stresli farz et! Böylece optimizasyon 
            # katmanı (%100 Konfor önceliği ile) rotayı hemen baştan güvenliğe uygun esnetecek.
            if y_modeli.t_t and y_modeli.t_t > 0.5 and gelecek_cls > 75.0:
                print(f"[PREDICTIVE FATIGUE ACTIVED] Sürücüde tükenme trendi! Mevcut: {mevcut_cls:.1f} -> Tahmini MolaCL: {gelecek_cls:.1f}")
                cls = round(gelecek_cls, 1)
            else:
                cls = round(mevcut_cls, 1)

            self.aktif_cls = cls
            self.aktif_mod = cls_to_mod(cls)

            if self.dro:
                self.cls_params = self.dro.optimize_parametreler(
                    self.aktif_uid, cls, self.arac_var.get() if hasattr(self, 'arac_var') else "Tesla Model 3")

            self.root.after(0, lambda: self._analiz_bitti(cls, TARAMA_SURE, kamera_acildi))

        threading.Thread(target=analiz, daemon=True).start()

    def _analiz_prog_guncelle(self, msg: str, yuzde: int):
        self.analiz_geri_say_lbl.config(text=msg, fg=WARN)
        w = int(yuzde / 100 * 700)
        self.analiz_prog_canvas.delete("all")
        self.analiz_prog_canvas.create_rectangle(0, 0, 700, 10, fill="#1a1d30", outline="")
        if w:
            self.analiz_prog_canvas.create_rectangle(0, 0, w, 10, fill=ACCENT2, outline="")

    def _analiz_cls_goster(self, cls: float):
        renk = DANGER if cls>=70 else (WARN if cls>=50 else (FG_MAIN if cls>=30 else ACCENT))
        w = int(cls / 100 * 260)
        self.analiz_cls_canvas.delete("all")
        self.analiz_cls_canvas.create_rectangle(0, 0, 260, 14, fill=BG_ROOT, outline="")
        if w:
            self.analiz_cls_canvas.create_rectangle(0, 0, w, 14, fill=renk, outline="")
        self.analiz_cls_lbl.config(text=f"{cls:.0f} / 100", fg=renk)

    def _analiz_bitti(self, cls: float, sure: int, kamera_acildi: bool):
        tarama_t = "kamerayla" if kamera_acildi else "simülasyonla"
        self.analiz_geri_say_lbl.config(
            text=f"✅  {sure} saniyelik analiz tamamlandı ({tarama_t}).",
            fg=ACCENT)
        self.analiz_prog_canvas.delete("all")
        self.analiz_prog_canvas.create_rectangle(0, 0, 700, 10, fill=ACCENT, outline="")
        self._analiz_cls_goster(cls)
        self.tarama_btn.config(state="normal",
                               text=f"🔄   Yeniden Tara ({TARAMA_SURE} sn)")
        # Sonuç sayfasını güncelle
        self._mod_sonuc_guncelle(cls)
        # İleri buton aç
        for widget in self.sayfa_frames["analiz"].winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and "Sonuca" in str(child.cget("text")):
                        child.config(state="normal")
        self._durum(f"✅ Analiz tamamlandı — {MOD_ISIM.get(self.aktif_mod,'?')}  (CLS: {cls:.0f})")
        # Otomatik geç
        self.root.after(800, lambda: self._sayfa_goster("mod_sonuc"))

    # ═══════════════════════════════════════════
    #  SAYFA 3 — MOD & SONUÇ
    # ═══════════════════════════════════════════
    def _olustur_s3_mod_sonuc(self):
        s = self._yeni_sayfa("mod_sonuc")

        tk.Label(s, text="Analiz Sonucu 🧠",
                 font=FONT_H1, bg=BG_ROOT, fg=FG_MAIN
                 ).pack(anchor="w", padx=24, pady=(24, 2))
        tk.Label(s, text="Duygu durumunuza göre rota optimize edildi.",
                 font=FONT_BODY, bg=BG_ROOT, fg=FG_SUB
                 ).pack(anchor="w", padx=24, pady=(0, 8))

        # Duygu kartı
        kart = self._kart(s, "", ACCENT2)

        self.mod_emoji_lbl = tk.Label(kart, text="—",
                                       font=("Segoe UI", 46),
                                       bg=BG_CARD, fg=FG_MAIN)
        self.mod_emoji_lbl.pack()

        self.mod_isim_lbl = tk.Label(kart, text="Analiz bekleniyor",
                                      font=("Segoe UI", 18, "bold"),
                                      bg=BG_CARD, fg=ACCENT2)
        self.mod_isim_lbl.pack(pady=(2, 8))

        # CLS bar
        cls_row = tk.Frame(kart, bg=BG_CARD)
        cls_row.pack(fill="x", pady=(0, 6))
        tk.Label(cls_row, text="Kognitif Yük :", font=FONT_SM,
                 bg=BG_CARD, fg=FG_SUB).pack(side="left")
        self.mod_cls_canvas = tk.Canvas(cls_row, width=280, height=16,
                                         bg=BG_ROOT, highlightthickness=0)
        self.mod_cls_canvas.pack(side="left", padx=8)
        self.mod_cls_lbl = tk.Label(cls_row, text="—",
                                     font=FONT_MONO, bg=BG_CARD, fg=FG_SUB)
        self.mod_cls_lbl.pack(side="left")

        # Açıklama
        self.mod_acik_lbl = tk.Label(kart, text="",
                                      font=FONT_SM, bg=BG_CARD, fg=FG_SUB,
                                      wraplength=700, justify="left")
        self.mod_acik_lbl.pack(anchor="w", pady=(0, 6))

        # Rota önerisi
        self.mod_oneri_lbl = tk.Label(kart, text="",
                                       font=("Segoe UI", 11, "bold"),
                                       bg=BG_CARD, fg=WARN,
                                       wraplength=700, justify="left")
        self.mod_oneri_lbl.pack(anchor="w")

        # Öneriler detay
        self.mod_oneriler_lbl = tk.Label(kart, text="",
                                          font=FONT_SM, bg=BG_CARD, fg=FG_SUB,
                                          wraplength=700, justify="left")
        self.mod_oneriler_lbl.pack(anchor="w", pady=(4, 0))

        # Otomatik uygula
        self.oto_mod_var = tk.BooleanVar(value=True)
        tk.Checkbutton(kart, text="Rota tercihini otomatik uygula",
                       variable=self.oto_mod_var,
                       bg=BG_CARD, fg=FG_SUB,
                       selectcolor=BG_ROOT,
                       font=FONT_SM).pack(anchor="w", pady=(10, 0))

        self._nav_bar(s,
            geri_cmd=lambda: self._sayfa_goster("analiz"),
            ileri_cmd=lambda: self._sayfa_goster("rota"),
            ileri_text="Rotayı Planla  →",
            ileri_renk=ACCENT)

    def _mod_sonuc_guncelle(self, cls: float):
        p   = self.cls_params
        mod = self.aktif_mod
        renk   = p.get("renk", ACCENT2) if p else ACCENT2
        ikon   = p.get("ikon", "😐") if p else "😐"
        isim   = {"yorgun":"YORGUN 😴","stresli":"STRESLİ 😰",
                  "notr":"NÖTR 😐","enerjik":"ENERJİK 😄"}.get(mod, "NÖTR 😐")
        acik   = p.get("aciklama", "") if p else ""
        krit_n = KRIT_ISIM.get(p.get("rota_krit","enerji"), "Enerji Verimli") if p else ""
        oneriler = p.get("oneriler", []) if p else []

        self.mod_emoji_lbl.config(text=ikon, fg=renk)
        self.mod_isim_lbl.config(text=isim, fg=renk)
        self.mod_acik_lbl.config(text=acik)
        self.mod_oneri_lbl.config(text=f"👉  Size  '{krit_n}'  öneriyoruz")
        self.mod_oneriler_lbl.config(text="  •  ".join(oneriler[:3]))

        # CLS bar
        w = int(cls / 100 * 280)
        self.mod_cls_canvas.delete("all")
        self.mod_cls_canvas.create_rectangle(0, 0, 280, 16, fill=BG_ROOT, outline="")
        if w: self.mod_cls_canvas.create_rectangle(0, 0, w, 16, fill=renk, outline="")
        self.mod_cls_canvas.create_text(140, 8,
            text=f"CLS  {cls:.0f} / 100", fill="white",
            font=("Segoe UI", 8, "bold"))
        self.mod_cls_lbl.config(text=f"{cls:.0f}", fg=renk)

        # Rota sayfasına mod uygula
        if self.oto_mod_var.get() and p and hasattr(self, 'rota_var'):
            self.rota_var.set(p.get("rota_krit", "enerji"))

    # ═══════════════════════════════════════════
    #  SAYFA 4 — ROTA PARAMETRELERİ
    # ═══════════════════════════════════════════
    def _olustur_s4_rota(self):
        s = self._yeni_sayfa("rota")
        sl = sorted(ANKARA_DUGUMLER.keys())

        tk.Label(s, text="Rota Ayarları 🗺️",
                 font=FONT_H1, bg=BG_ROOT, fg=FG_MAIN
                 ).pack(anchor="w", padx=24, pady=(20, 2))
        tk.Label(s, text="Başlangıç, bitiş ve araç bilgilerini seçin.",
                 font=FONT_BODY, bg=BG_ROOT, fg=FG_SUB
                 ).pack(anchor="w", padx=24, pady=(0, 4))

        # Rota noktaları
        kart1 = self._kart(s, "📍  Güzergah", ACCENT2, pady=(6, 4))
        grid  = tk.Frame(kart1, bg=BG_CARD)
        grid.pack(fill="x")

        tk.Label(grid, text="Başlangıç :", font=FONT_BODY,
                 bg=BG_CARD, fg=FG_SUB, width=12, anchor="w").grid(row=0, column=0, pady=5, sticky="w")
        self.bas_var = tk.StringVar(value="Kızılay")
        ttk.Combobox(grid, textvariable=self.bas_var, values=sl,
                     width=32, state="readonly", font=FONT_BODY
                     ).grid(row=0, column=1, padx=8)

        tk.Label(grid, text="Bitiş :", font=FONT_BODY,
                 bg=BG_CARD, fg=FG_SUB, width=12, anchor="w").grid(row=1, column=0, pady=5, sticky="w")
        self.bit_var = tk.StringVar(value="Esenboğa Havalimanı")
        ttk.Combobox(grid, textvariable=self.bit_var, values=sl,
                     width=32, state="readonly", font=FONT_BODY
                     ).grid(row=1, column=1, padx=8)

        # Araç bilgileri
        kart2 = self._kart(s, "🚗  Araç & Batarya", ACCENT2, pady=(4, 4))
        grid2 = tk.Frame(kart2, bg=BG_CARD)
        grid2.pack(fill="x")

        tk.Label(grid2, text="Araç :", font=FONT_BODY,
                 bg=BG_CARD, fg=FG_SUB, width=14, anchor="w").grid(row=0, column=0, pady=5, sticky="w")
        self.arac_var = tk.StringVar(value="Tesla Model 3")
        self.arac_cb  = ttk.Combobox(grid2, textvariable=self.arac_var,
                                     values=list(ARACLAR.keys()),
                                     width=30, state="readonly", font=FONT_BODY)
        self.arac_cb.grid(row=0, column=1, padx=8)
        self.arac_cb.bind("<<ComboboxSelected>>", self._arac_degisti)

        tk.Label(grid2, text="Batarya (%) :", font=FONT_BODY,
                 bg=BG_CARD, fg=FG_SUB, width=14, anchor="w").grid(row=1, column=0, pady=5, sticky="w")
        bat_row = tk.Frame(grid2, bg=BG_CARD)
        bat_row.grid(row=1, column=1, padx=8, sticky="w")
        self.bat_var = tk.IntVar(value=80)
        style2 = ttk.Style()
        style2.configure("Bat.Horizontal.TScale", background=BG_CARD)
        tk.Scale(bat_row, from_=5, to=100, orient="horizontal",
                 variable=self.bat_var, bg=BG_CARD, fg=ACCENT,
                 troughcolor=BG_INPUT, highlightbackground=BG_CARD,
                 activebackground=ACCENT, length=220,
                 command=lambda v: self.bat_lbl.config(text=f"%{int(float(v))}")
                 ).pack(side="left")
        self.bat_lbl = tk.Label(bat_row, text="%80",
                                 bg=BG_CARD, fg=WARN,
                                 font=("Segoe UI", 13, "bold"))
        self.bat_lbl.pack(side="left", padx=6)

        self.arac_info_lbl = tk.Label(kart2, text="",
                                       font=FONT_SM, bg=BG_CARD, fg=FG_SUB)
        self.arac_info_lbl.pack(anchor="w", pady=(6, 0))
        self._arac_bilgi_goster()

        # Rota tercihi
        kart3 = self._kart(s, "⚙️  Rota Tercihi", ACCENT2, pady=(4, 4))
        self.rota_var = tk.StringVar(value="enerji")
        rf = tk.Frame(kart3, bg=BG_CARD)
        rf.pack(fill="x")
        for v, etiket, renk in [
            ("mesafe","🛣  En Kısa Yol","#00FF88"),
            ("sure",  "⚡  En Hızlı Yol",ACCENT2),
            ("enerji","🔋  En Az Enerji",WARN)]:
            tk.Radiobutton(rf, text=etiket, variable=self.rota_var, value=v,
                           bg=BG_CARD, fg=renk, selectcolor=BG_ROOT,
                           activebackground=BG_CARD,
                           font=FONT_BODY).pack(side="left", padx=14)

        # Mod varsa uygulandı notu
        self.rota_mod_not_lbl = tk.Label(kart3, text="",
                                          font=FONT_SM, bg=BG_CARD, fg=FG_SUB)
        self.rota_mod_not_lbl.pack(anchor="w", pady=(4, 0))

        # Nav
        self._nav_bar(s,
            geri_cmd=lambda: self._sayfa_goster("mod_sonuc"),
            ileri_cmd=self.rota_ciz,
            ileri_text="🗺   Haritayı Çiz",
            ileri_renk=ACCENT)

    def _arac_degisti(self, _=None):
        self.graf._guncelle(self.arac_var.get())
        self._arac_bilgi_goster()

    def _arac_bilgi_goster(self):
        a = ARACLAR.get(self.arac_var.get(), {})
        if a:
            menzil = int(a["batarya"] / a["tuketim_baz"])
            self.arac_info_lbl.config(
                text=f"  🔋 {a['batarya']} kWh   ⚡ ~{a['tuketim_baz']} kWh/km (şehir)   📏 ~{menzil} km maks.")

    # ═══════════════════════════════════════════
    #  SAYFA 5 — HARİTA SONUCU
    # ═══════════════════════════════════════════
    def _olustur_s5_harita(self):
        s = self._yeni_sayfa("harita")

        tk.Label(s, text="Rota Hazır! ⚡",
                 font=FONT_H1, bg=BG_ROOT, fg=ACCENT
                 ).pack(anchor="w", padx=24, pady=(24, 2))
        tk.Label(s, text="Harita tarayıcınızda açıldı.",
                 font=FONT_BODY, bg=BG_ROOT, fg=FG_SUB
                 ).pack(anchor="w", padx=24, pady=(0, 8))

        # Sonuç kartı
        self.sonuc_kart = self._kart(s, "📊  Özet", ACCENT)
        self.sonuc_lbl  = tk.Label(self.sonuc_kart,
                                    text="Rota henüz hesaplanmadı.",
                                    font=FONT_BODY, bg=BG_CARD,
                                    fg=FG_MAIN, justify="left",
                                    wraplength=680)
        self.sonuc_lbl.pack(anchor="w")

        # Butonlar
        btn_kart = self._kart(s, "", ACCENT, pady=(4, 4))
        btn_row  = tk.Frame(btn_kart, bg=BG_CARD)
        btn_row.pack(fill="x")

        self.harita_ac_btn = tk.Button(btn_row,
            text="🌐  Haritayı Tarayıcıda Aç",
            command=self._harita_ac,
            bg=ACCENT2, fg=BG_ROOT,
            font=FONT_H3, relief="flat",
            cursor="hand2", padx=18, pady=8)
        self.harita_ac_btn.pack(side="left", padx=(0, 10))

        tk.Button(btn_row,
            text="🔄  Yeni Rota",
            command=lambda: self._sayfa_goster("surucucler"),
            bg=BG_CARD, fg=FG_SUB,
            font=FONT_BODY, relief="flat",
            cursor="hand2", padx=14, pady=8
            ).pack(side="left")

        # Trafik API notu
        if TOMTOM_API_KEY:
            api_txt = "✅ TomTom Canlı Trafik API aktif"
            api_renk = ACCENT
        elif GOOGLE_API_KEY:
            api_txt  = "✅ Google Maps API aktif"
            api_renk = ACCENT
        else:
            api_txt  = "ⓘ  Trafik API Key yok — yerel trafik tahmini kullanılıyor"
            api_renk = FG_SUB
        tk.Label(s, text=api_txt, bg=BG_ROOT, fg=api_renk, font=FONT_XS
                 ).pack(anchor="w", padx=24, pady=(4, 0))

        # Nav
        self._nav_bar(s,
            geri_cmd=lambda: self._sayfa_goster("rota"),
            ileri_cmd=None)

    def _harita_ac(self):
        if self._son_harita_path:
            webbrowser.open(f"file://{os.path.abspath(self._son_harita_path)}")

    # ─────────────────────────────────────────
    #  DUYGU ONAY PENCERESİ
    # ─────────────────────────────────────────
    def _duygu_onayla(self) -> bool:
        if not (self.kognitif_aktif and self.cls_params):
            return True

        p     = self.cls_params
        mod   = p.get("mod","notr")
        ikon  = p.get("ikon","😐")
        renk  = p.get("renk","#00CFFF")
        acik  = p.get("aciklama","")
        cls_d = p.get("cls", self.aktif_cls)

        krit_isim = KRIT_ISIM.get(p.get("rota_krit","enerji"), "?")
        sarj_info = (f"Şarj uyarısı: %{p.get('sarj_esik',10)} altına düşünce → "
                     f"%{p.get('sarj_hedef',80)}'e dolduracak")

        onay_var = tk.BooleanVar(value=False)
        win = tk.Toplevel(self.root)
        win.title("Duygu Durumu Analizi — Onay")
        win.geometry("480x440")
        win.configure(bg=BG_CARD)
        win.resizable(False, False)
        win.grab_set()
        win.attributes("-topmost", True)

        # Başlık şeridi
        hdr = tk.Frame(win, bg=renk, height=4)
        hdr.pack(fill="x")
        tk.Label(win, text=f"{ikon}  Duygu Durumu Tespit Edildi",
                 font=FONT_H2, bg=BG_CARD, fg=renk).pack(pady=(18, 4))

        ic = tk.Frame(win, bg=BG_CARD, padx=28, pady=6)
        ic.pack(fill="both", expand=True)

        mod_isim = {"yorgun":"😴  YORGUN","stresli":"😰  STRESLİ",
                    "notr":"😐  NÖTR","enerjik":"😄  ENERJİK"}.get(mod,"😐  NÖTR")
        tk.Label(ic, text=mod_isim, font=("Segoe UI", 26, "bold"),
                 bg=BG_CARD, fg=renk).pack(pady=(4, 2))

        cf = tk.Frame(ic, bg=BG_CARD); cf.pack(fill="x", pady=4)
        tk.Label(cf, text="Kognitif Yük:", bg=BG_CARD, fg=FG_SUB,
                 font=FONT_SM).pack(side="left")
        cv = tk.Canvas(cf, width=200, height=18, bg=BG_ROOT, highlightthickness=0)
        cv.pack(side="left", padx=8)
        dolu = int(cls_d/100*200)
        cv.create_rectangle(0,0,200,18,fill=BG_ROOT,outline="")
        if dolu: cv.create_rectangle(0,0,dolu,18,fill=renk,outline="")
        cv.create_text(100,9,text=f"{cls_d:.0f} / 100",fill="white",font=("Segoe UI",8,"bold"))

        tk.Label(ic, text=acik, bg=BG_CARD, fg="#aaa",
                 font=FONT_SM, wraplength=420, justify="center").pack(pady=(2,8))
        tk.Frame(ic, bg="#222", height=1).pack(fill="x", pady=4)
        tk.Label(ic, text="Bu duruma göre rota planlanacak:",
                 bg=BG_CARD, fg=FG_SUB, font=FONT_XS).pack(anchor="w")

        pf = tk.Frame(ic, bg=BG_ROOT, padx=12, pady=8); pf.pack(fill="x", pady=4)
        tk.Label(pf, text=f"🗺  Rota türü: {krit_isim}",
                 bg=BG_ROOT, fg=FG_MAIN, font=FONT_BODY, anchor="w").pack(anchor="w")
        tk.Label(pf, text=sarj_info, bg=BG_ROOT, fg="#aaa",
                 font=FONT_SM, anchor="w").pack(anchor="w", pady=(2,0))
        for o in p.get("oneriler",[])[:2]:
            tk.Label(pf, text=o, bg=BG_ROOT, fg=WARN,
                     font=FONT_XS, anchor="w", wraplength=400).pack(anchor="w")

        bf = tk.Frame(win, bg=BG_CARD, pady=12); bf.pack(fill="x", padx=28)

        def onayla(): onay_var.set(True); win.destroy()
        def iptal():  onay_var.set(False); win.destroy()

        tk.Button(bf, text="✅  Bu Rotayı Çiz", command=onayla,
                  bg=renk, fg=BG_ROOT, font=FONT_H3,
                  relief="flat", cursor="hand2", padx=16, pady=7
                  ).pack(side="left", fill="x", expand=True, padx=(0,6))
        tk.Button(bf, text="✕  İptal", command=iptal,
                  bg="#1e2035", fg="#ccc", font=FONT_BODY,
                  relief="flat", cursor="hand2", padx=12, pady=7
                  ).pack(side="left")

        self.root.wait_window(win)
        return onay_var.get()

    # ─────────────────────────────────────────
    #  PROFİL PENCERESİ
    # ─────────────────────────────────────────
    def _profil_penceresi(self):
        if not (self.pm and self.kognitif_aktif): return
        uid    = self.uid_var.get().split(" — ")[0]
        istat  = self.pm.istatistik_ozet(uid)
        profil = self.pm.profil_al(uid)
        if not profil: return

        win = tk.Toplevel(self.root)
        win.title(f"📊 Profil — {profil['isim']}")
        win.geometry("460x560")
        win.configure(bg=BG_CARD)

        # FIX: None değerleri için güvenli .title() çağrısı
        gun_ici_tip   = str(profil.get("gun_ici_tip") or "—").title()
        son_mod       = str(profil.get("son_mod") or "—").title()
        dominant_duygu= str(profil.get("dominant_duygu") or "—").title()

        tk.Label(win, text=f"👤 {profil['isim']}",
                 font=FONT_H2, bg=BG_CARD, fg=ACCENT2).pack(pady=(14,2))
        tk.Label(win, text=(f"{profil['yas']} yaş  •  {profil['meslek']}  •  "
                            f"{gun_ici_tip} tipi"),
                 font=FONT_SM, bg=BG_CARD, fg=FG_SUB).pack()
        tk.Frame(win, bg=ACCENT2, height=1).pack(fill="x", padx=20, pady=8)

        def satir(k, v, vc=FG_MAIN):
            f = tk.Frame(win, bg=BG_CARD); f.pack(fill="x", padx=20, pady=2)
            tk.Label(f, text=k, bg=BG_CARD, fg=FG_SUB,
                     font=FONT_SM, width=24, anchor="w").pack(side="left")
            tk.Label(f, text=str(v), bg=BG_CARD, fg=vc,
                     font=("Segoe UI", 9, "bold")).pack(side="left")

        satir("🔬 Tanıma Doğruluğu",
              f"%{round(profil.get('taninma_dogrulugu',0)*100,1)}", ACCENT)
        satir("📱 Kullanım Sayısı", profil.get("kullanim_sayisi",0))
        satir("🧠 Son CLS",
              f"{profil.get('son_cls','—')} / 100",
              DANGER if (profil.get("son_cls") or 0)>60 else ACCENT)
        satir("🎭 Son Mod",   son_mod)        # FIX: None güvenceli
        satir("💨 Dom. Duygu", dominant_duygu)  # FIX: None güvenceli
        satir("🔄 Göz Kırp Baz",
              f"{profil['biyometrik']['blink_baz_dk']} / dk")
        satir("👁 Göz Açıklık Baz",
              f"{profil['biyometrik']['goz_acikligi_baz']:.3f}")

        if istat.get("toplam_sefer"):
            tk.Frame(win, bg="#333", height=1).pack(fill="x", padx=20, pady=8)
            tk.Label(win, text="📈 30 Günlük İstatistikler",
                     font=("Segoe UI", 10, "bold"), bg=BG_CARD, fg=ACCENT2).pack()
            satir("Toplam Sefer",   istat["toplam_sefer"])
            satir("Toplam km",      f"{istat['toplam_km']} km")
            satir("Ortalama CLS",   f"{istat['cls_ort']} / 100",
                  WARN if istat["cls_ort"]>50 else ACCENT)
            satir("Maks CLS",       f"{istat['cls_max']}", DANGER)
            satir("Min CLS",        f"{istat['cls_min']}", ACCENT)
            satir("Ort. Tüketim ×", f"×{istat['tuk_carpan_ort']}")
            satir("Dominant Mod",   str(istat["dominant_mod"]).title())

        tk.Button(win, text="Kapat", command=win.destroy,
                  bg="#1e2035", fg="#ccc", font=FONT_SM,
                  relief="flat").pack(pady=10)

    # ─────────────────────────────────────────
    #  ROTA ÇİZ
    # ─────────────────────────────────────────
    def rota_ciz(self):
        bas  = self.bas_var.get()
        bit  = self.bit_var.get()
        arac = self.arac_var.get()
        bat  = self.bat_var.get()
        krit = self.rota_var.get()

        if bas == bit:
            messagebox.showwarning("Uyarı", "Başlangıç ve bitiş aynı olamaz!")
            return

        if not self._duygu_onayla():
            self._durum("ℹ️ Rota çizimi iptal edildi.")
            return

        sarj_esik     = MIN_BATARYA_ESIK
        sarj_hedef    = 80
        tuk_carpan_ek = 1.0
        mod_bilgi     = {}

        if self.kognitif_aktif and self.cls_params:
            p = self.cls_params
            mod_bilgi = p
            if self.oto_mod_var.get():
                sarj_esik     = p.get("sarj_esik",  sarj_esik)
                sarj_hedef    = p.get("sarj_hedef", sarj_hedef)
                tuk_carpan_ek = p.get("tuk_carpan", 1.0)
                # Kullanıcı seçimi burada KORUNUYOR.
                # Sistem önerisi aşağıda F(r) analizi sonrası uygulanacak.

        if self.graf.arac_adi != arac:
            self.graf._guncelle(arac)

        # ── Standart 3 Dijkstra rotası
        rotalar = {}
        for k in ["mesafe", "sure", "enerji"]:
            yol, _ = self.graf.dijkstra(bas, bit, k)
            rotalar[k] = yol

        # ── Çok Amaçlı Optimizasyon Pipeline ──────────────────────
        mo_detay: Dict = {}
        if KOGNITIF_VAR and CokAmacliRotaOptimizatoru is not None:
            # 1) CLS → ağırlıklar
            if GELISMIS_VAR and hasattr(self, 'duygu_motor'):
                w_e, w_t, w_c = self.duygu_motor.rota_agirliklari(self.aktif_cls)
                duygu = self.duygu_motor.duygu_tahmin(self.aktif_cls)
            else:
                w_e, w_t, w_c = CokAmacliRotaOptimizatoru.agirlik_hesapla(self.aktif_cls)

            # 2) Ağırlıklı Dijkstra ile 4. aday rota (SADECE görsel karşılaştırma içindir)
            mo_yol, _ = self.graf.cok_amacli_dijkstra(bas, bit, w_e, w_t, w_c)
            if mo_yol:
                # Mesafe kısıtı: çok amaçlı rota en kısa rotadan 1.5× daha uzun olamaz
                mo_met  = yol_metrikleri(mo_yol, arac)
                ref_met = yol_metrikleri(rotalar.get("mesafe", mo_yol), arac)
                if ref_met["mesafe_km"] > 0 and mo_met["mesafe_km"] <= ref_met["mesafe_km"] * 1.5:
                    rotalar["mo"] = mo_yol
                # 1.5×'i aşıyorsa "mo" eklenmez → haritada görünmez

            # 3) Her rota için metrik + konfor skoru
            met_tum   = {k: yol_metrikleri(v, arac) for k, v in rotalar.items() if v}
            konfor_sk = {
                k: CokAmacliRotaOptimizatoru.rota_konfor_skoru(v, ANKARA_DUGUMLER, YOLLAR)
                for k, v in rotalar.items() if v
            }

            # 4) Objective function: F(r) skoru hesapla
            mo_krit, mo_f, mo_detay = CokAmacliRotaOptimizatoru.en_iyi_rota_sec(
                rotalar, met_tum, konfor_sk, self.aktif_cls,
                komsular        = self.graf.komsular,
                ankara_dugumler = ANKARA_DUGUMLER,
                baslangic       = bas,
                bitis           = bit,
            )

            # 5) NSGA-II rotalar["mo"]'yu kendi değeriyle ezmiş olabilir → tekrar doğrula
            if "mo" in rotalar:
                mo_recheck  = yol_metrikleri(rotalar["mo"], arac)
                ref_recheck = yol_metrikleri(rotalar.get("mesafe", []), arac)
                
                gecerli = True
                if ref_recheck["mesafe_km"] > 0:
                    oran = mo_recheck["mesafe_km"] / ref_recheck["mesafe_km"]
                    if oran < 0.9 or oran > 1.5:
                        gecerli = False
                
                if not gecerli or mo_recheck["mesafe_km"] == 0:
                    # Aşırı uzun veya geçersiz/kopuk rota (0 km) → haritadan ve tablodan kaldır
                    del rotalar["mo"]
                    mo_detay.get("f_skorlar", {}).pop("mo", None)
                    mo_detay.get("metrikleri", {}).pop("mo", None)
                else:
                    # Geçerli → met_tum ve mo_detay'ı gerçek metriklerle güncelle
                    met_tum["mo"] = mo_recheck
                    mo_detay.setdefault("metrikleri", {})["mo"] = mo_recheck
                    konfor_sk["mo"] = CokAmacliRotaOptimizatoru.rota_konfor_skoru(
                        rotalar["mo"], ANKARA_DUGUMLER, YOLLAR)

            # 6) Oto modda aktif rotayı belirle
            # DÜZELTME: Artık "mo" rotası ana (aktif) rota olarak seçilebilir.
            if self.oto_mod_var.get():
                krit = mo_krit
                self.rota_var.set(krit)

        # ── Aktif rota ──────────────────────────────────────────────
        aktif_yol = rotalar.get(krit, []) or rotalar.get("enerji", [])
        if not aktif_yol:
            messagebox.showerror("Hata", "Rota bulunamadı!")
            return

        met        = yol_metrikleri(aktif_yol, arac)
        sure_bilgi = (tomtom_sure_cek(bas, bit)
                       or google_sure_cek(bas, bit)
                       or yerel_sure_tahmin(aktif_yol, arac))
        met["enerji_kwh"] = round(met["enerji_kwh"] * tuk_carpan_ek, 3)

        sarj_plan, sarj_sayisi = sarj_durak_planla(
            aktif_yol, arac, bat, self.sarj_ist,
            min_esik=sarj_esik, hedef_yuzde=sarj_hedef)

        html_path, m_obj = harita_olustur(
            bas, bit, arac, bat, rotalar, self.sarj_ist, krit,
            sure_bilgi, sarj_plan, sarj_sayisi,
            self.sarj_kaynagi, kognitif=mod_bilgi, opt_bilgi=mo_detay)
        self._son_harita_path = html_path

        if self.kognitif_aktif and self.pm:
            self.pm.profil_guncelle(
                self.aktif_uid, self.aktif_cls,
                met["mesafe_km"], tuk_carpan_ek)

        # ── Özet metni
        krit_etiket = {
            "mesafe": "En Kısa", "sure": "En Hızlı",
            "enerji": "En Az Enerji", "mo": "Çok Amaçlı Optimal",
        }
        son    = next((a for a in reversed(sarj_plan) if a["durum"] == bit), {})
        kalan  = son.get("batarya_yuzde", "?")
        yeterli = isinstance(kalan, (int, float)) and kalan >= sarj_esik
        tf      = sure_bilgi["sure_trafik_dk"] - sure_bilgi["sure_normal_dk"]
        tf_str  = f"+{tf} dk trafik" if tf > 0 else "trafik az"
        sarj_msg = (f"✅ Şarj gerekmez — varışta ~%{kalan}"
                    if sarj_sayisi == 0
                    else f"⚡ {sarj_sayisi} şarj durağı — varışta ~%{kalan}")
        mod_str = ""
        if mod_bilgi:
            mod_str = (f"\n{mod_bilgi.get('ikon','')} Mod: "
                       f"{str(mod_bilgi.get('mod','')).title()} "
                       f"(CLS: {mod_bilgi.get('cls','—')}) — "
                       f"{mod_bilgi.get('aciklama','')}")

        opt_str = ""
        if mo_detay:
            aw   = mo_detay.get("agirliklar", {})
            fsk  = mo_detay.get("f_skorlar", {})
            nsga2_aktif = mo_detay.get("nsga2_aktif", False)
            nsga2_bilgi = mo_detay.get("nsga2_detay", {})
            nsga2_etiket = ""
            if nsga2_aktif and nsga2_bilgi:
                pb = nsga2_bilgi.get('pareto_boyutu', 0)
                nsga2_etiket = f"  🧬 NSGA-II (Pareto:{pb})"
            opt_str = (
                f"\n🎯 Objective F={min(fsk.values(), default=0):.4f}  "
                f"[⚡{aw.get('w_enerji',0):.0%} "
                f"⏱{aw.get('w_sure',0):.0%} "
                f"😊{aw.get('w_konfor',0):.0%}]{nsga2_etiket}"
            )

        ozet_text = (
            f"✅  {krit_etiket.get(krit, krit)} Rota\n"
            f"📍  {bas}  →  {bit}\n"
            f"📏  {met['mesafe_km']} km   "
            f"⏱  {sure_bilgi['sure_trafik_dk']} dk ({tf_str})   "
            f"⚡  {met['enerji_kwh']} kWh\n"
            f"{sarj_msg}{mod_str}{opt_str}\n"
            f"📡  {sure_bilgi['kaynak']}"
        )
        self.sonuc_lbl.config(
            fg=ACCENT if yeterli else DANGER,
            text=ozet_text)

        self._durum(f"✅ Harita oluşturuldu — {bas} → {bit}")
        self._sayfa_goster("harita")
        webbrowser.open(f"file://{os.path.abspath(html_path)}")

        if GELISMIS_VAR and hasattr(self, 'kaydedici'):
            self.kaydedici.sefer_baslat(self.aktif_uid)
            for nokta in GpsSimulatoru(ANKARA_DUGUMLER).rota_sim_noktalari(aktif_yol):
                self.kaydedici.nokta_ekle(nokta["lat"], nokta["lon"], nokta["hiz_kmsa"])
            self.kaydedici.sefer_bitir(
                cls_gecmis=self.klz._cls_gecmis if hasattr(self.klz, '_cls_gecmis') else [self.aktif_cls],
                rota_dugum_listesi=aktif_yol,
                arac_adi=arac,
                mod=self.aktif_mod
            )

        # ── Geri Bildirim Anketi: AI'nin konfor hafizasini besle
        self.root.after(1500, lambda: self._geri_bildirim_anketi_goster(aktif_yol))

    def _geri_bildirim_anketi_goster(self, yol: list):
        """
        Rota haritasi actiktan sonra kullaniciya 1-5 konfor puani sorar
        ve bu bilgiyi NSGA-II'nin kullandigi konfor hafizasina yazar.
        """
        if KONFOR_HAFIZASI is None or len(yol) < 2:
            return

        pencere = tk.Toplevel(self.root)
        pencere.title("Rota Geri Bildirimi")
        pencere.geometry("390x230")
        pencere.resizable(False, False)
        pencere.grab_set()

        try:
            pencere.configure(bg="#1a1a2e")
        except Exception:
            pass

        tk.Label(
            pencere,
            text="Bu rotayi nasil buldunuz?",
            font=("Segoe UI", 13, "bold"),
            bg="#1a1a2e", fg="#e0e0e0"
        ).pack(pady=(18, 4))

        tk.Label(
            pencere,
            text="Konfor puaniniz gelecek rotayi iyilestirir (NSGA-II ogrenir).",
            font=("Segoe UI", 9),
            bg="#1a1a2e", fg="#9e9eb8"
        ).pack(pady=(0, 10))

        puan_var = tk.IntVar(value=3)

        cerceve = tk.Frame(pencere, bg="#1a1a2e")
        cerceve.pack()

        yildiz_butonlar = []

        def yildiz_guncelle(deger):
            for i, btn in enumerate(yildiz_butonlar):
                btn.config(fg="#FFD700" if (i + 1) <= deger else "#555577")

        for i in range(1, 6):
            val = i
            btn = tk.Button(
                cerceve,
                text="★",
                font=("Segoe UI", 24),
                bg="#1a1a2e",
                fg="#FFD700" if i <= 3 else "#555577",
                relief="flat",
                activebackground="#1a1a2e",
                cursor="hand2",
                command=lambda v=val: [puan_var.set(v), yildiz_guncelle(v)]
            )
            btn.pack(side="left", padx=4)
            yildiz_butonlar.append(btn)

        def kaydet_ve_kapat():
            puan = puan_var.get()
            try:
                KONFOR_HAFIZASI.guncelle(yol, puan)
                print(f"[KonforHafiza] Rota puanlandi: {puan}/5 ")
            except Exception as e:
                print(f"[KonforHafiza] Kaydedilemedi: {e}")
            pencere.destroy()

        btn_cerceve = tk.Frame(pencere, bg="#1a1a2e")
        btn_cerceve.pack(pady=14)

        tk.Button(
            btn_cerceve, text="Kaydet",
            font=("Segoe UI", 10, "bold"),
            bg="#4CAF50", fg="white",
            relief="flat", padx=14, pady=6,
            cursor="hand2", command=kaydet_ve_kapat
        ).pack(side="left", padx=8)

        tk.Button(
            btn_cerceve, text="Atla",
            font=("Segoe UI", 10),
            bg="#333355", fg="#9e9eb8",
            relief="flat", padx=14, pady=6,
            cursor="hand2", command=pencere.destroy
        ).pack(side="left", padx=4)

    def calistir(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = EVRotaGUI()
    app.calistir()