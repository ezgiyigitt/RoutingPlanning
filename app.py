import streamlit as st
import folium
from streamlit_folium import st_folium
import time
import os
import cv2

from ev_rota_planner import (
    Graf, ANKARA_DUGUMLER, ARACLAR, 
    canli_sarj_istasyonlari_getir, 
    tomtom_sure_cek, google_sure_cek, yerel_sure_tahmin, 
    yol_metrikleri, sarj_durak_planla,
    harita_olustur, KOGNITIF_VAR, MOD_PARAMETRELERI
)

if KOGNITIF_VAR:
    from kognitif_motor import (
        SurucuProfilYonetici, CokAmacliRotaOptimizatoru,
        KognitivYukAnalizci, MLDestekliKognitivYukAnalizci
    )
    try:
        from duygu_regresyonu import SurekliDuyguMotoru
        GELISMIS_VAR = True
    except ImportError:
        GELISMIS_VAR = False

try:
    from surucu_konfor_hafizasi import get_konfor_hafizasi
    KONFOR_HAFIZASI = get_konfor_hafizasi()
except ImportError:
    KONFOR_HAFIZASI = None

# ────────────────────────────────────────────────────────
#  SAYFA YAPILANDIRMASI VE STİL (APP GÖRÜNÜMÜ)
# ────────────────────────────────────────────────────────
st.set_page_config(page_title="AffectEV", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Modern, Apple esintili iOS tarzı CSS */
    [data-testid="stSidebar"] {
        background-color: #0f111a;
    }
    .stButton>button {
        border-radius: 8px;
        background-color: #007aff;
        color: white;
        border: none;
        font-weight: 600;
        width: 100%;
        transition: 0.2s;
    }
    .stButton>button:hover {
        background-color: #005bb5;
        border-color: transparent;
        color: white;
    }
    .main-title {
        font-size: 28px;
        font-weight: 800;
        color: #1c1c1e;
        margin-bottom: -15px;
    }
    .sub-title {
        font-size: 14px;
        color: #8e8e93;
        margin-bottom: 20px;
    }
    .stSelectbox label, .stSlider label {
        font-weight: 600 !important;
        color: #1c1c1e !important;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────
#  SİSTEM DEĞİŞKENLERİ (STATE)
# ────────────────────────────────────────────────────────
if "graf" not in st.session_state:
    st.session_state.graf = Graf("Tesla Model 3")
if "sarj_ist" not in st.session_state:
    st.session_state.sarj_ist = canli_sarj_istasyonlari_getir(10) or []
if "kognitif_aktif" not in st.session_state:
    st.session_state.kognitif_aktif = KOGNITIF_VAR
if "pm" not in st.session_state and KOGNITIF_VAR:
    st.session_state.pm = SurucuProfilYonetici()
if "cls" not in st.session_state:
    st.session_state.cls = 40.0
if "hesapla_btn" not in st.session_state:
    st.session_state.hesapla_btn = False
if "rota_cizildi" not in st.session_state:
    st.session_state.rota_cizildi = False
if "son_rota" not in st.session_state:
    st.session_state.son_rota = []

# ────────────────────────────────────────────────────────
#  SOL MENÜ (SİDEBAR) - AYARLAR VE ANALİZ
# ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='color:white'>⚡ AffectEV</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#a1a1a6; font-size:12px; margin-top:-10px;'>Duygu-Duyarlı EV Routing</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # 1. Sürücü Seçimi
    st.markdown("<b style='color:#ddd'>👤 Sürücü Profili</b>", unsafe_allow_html=True)
    uid_list = ["U01 — Ahmet Y.", "U02 — Ayşe K.", "U03 — Mehmet T.", "U04 — Zeynep B.", "M01 — Misafir"]
    secilen_uid = st.selectbox("Sürücü:", uid_list, label_visibility="collapsed")
    uid_kodu = secilen_uid.split(" — ")[0]
    
    # Profil detayları
    if st.session_state.kognitif_aktif:
        profil = st.session_state.pm.profil_al(uid_kodu)
        if profil:
            st.success(f"Giriş yapıldı: {profil['isim']}")
    
    st.divider()
    
    # 2. Duygu & Kamera Simülasyonu
    st.markdown("<b style='color:#ddd'>📷 Kognitif Yük (CLS) Durumu</b>", unsafe_allow_html=True)
    
    veri_kaynagi = st.radio("Veri Kaynağı:", ["Simülasyon (Manuel)", "Gerçek Zamanlı Kamera (OpenCV)"], 
                            label_visibility="collapsed")
    
    if veri_kaynagi == "Gerçek Zamanlı Kamera (OpenCV)":
        if st.button("📷 5 Saniyelik Yüz Analizini Başlat"):
            if 'profil' in locals() and profil:
                if GELISMIS_VAR:
                    klz = MLDestekliKognitivYukAnalizci(profil)
                else:
                    klz = KognitivYukAnalizci(profil)
                kamera_basarili = klz.kamera_baslat()
                
                if kamera_basarili:
                    durum_metni = st.empty()
                    prog = st.progress(0)
                    kamera_penceresi = st.empty()  # Kamera feed'i için placeholder
                    cls_degerleri = []
                    
                    # Profesyonel Analiz: İlk 2 saniye 'ısınma', son 3 saniye 'gerçek örnekleme'
                    for s in range(50): # 0.1 saniyelik 50 adım = 5 saniye
                        if s % 10 == 0:
                            sn_kalan = 5 - (s // 10)
                            durum_metni.info(f"Kameraya bakın... Analiz yapılıyor: {sn_kalan} saniye")
                            prog.progress((s // 10 + 1) / 5)
                        
                        # Kamera görüntüsünü al ve göster
                        frame = klz.get_latest_frame()
                        if frame is not None:
                            # OpenCV BGR -> RGB çevrimi
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            kamera_penceresi.image(frame_rgb, channels="RGB", width="stretch")
                        
                        # Her saniyede bir CLS kaydı al
                        if s % 10 == 0:
                            c = klz.anlik_cls()
                            if s >= 20: # ilk 2 saniyeden sonra
                                cls_degerleri.append(c)
                        
                        time.sleep(0.1)
                        
                    kamera_penceresi.empty() # Analiz bitince kamerayı temizle
                    klz.kamera_durdur()
                    
                    if cls_degerleri:
                        # Ortalama yerine en yüksek yorgunluk belirtisini veya kararlı son değeri baz al
                        st.session_state.cls = max(cls_degerleri) 
                        durum_metni.success(f"Analiz tamamlandı! Algılanan Kognitif Yük: %{int(st.session_state.cls)}")
                else:
                    st.error("Kamera başlatılamadı. Lütfen kamera erişiminizi kontrol edin.")
            else:
                st.error("Önce bir profil yüklemelisiniz.")
    else:
        st.session_state.cls = st.slider("CLS (Yorgunluk/Stres) Skoru", 0.0, 100.0, st.session_state.cls, 1.0)
    
    aktif_cls = st.session_state.cls
    if aktif_cls < 30: mod, renk, emoji = "Enerjik", "#00CFFF", "😄"
    elif aktif_cls < 60: mod, renk, emoji = "Normal", "#00FF88", "😐"
    elif aktif_cls < 80: mod, renk, emoji = "Yorgun", "#FFB800", "😴"
    else: mod, renk, emoji = "Stresli", "#FF4444", "😰"
        
    st.markdown(f"<div style='background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; border-left:4px solid {renk}; color:white'>"
                f"<b>Sürücü Modu:</b> {emoji} {mod} <br><small>Güncel CLS Skoru: %{int(aktif_cls)}</small></div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────
#  ANA EKRAN (HARİTA VE ROTA PLANLAMA)
# ────────────────────────────────────────────────────────
st.markdown("<div class='main-title'>Rotanızı Planlayın</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Batarya, Canlı Trafik ve Duygu Durumuna göre en optimum rotalar</div>", unsafe_allow_html=True)

# Seçim Kutuları (Yan Yana)
col1, col2, col3, col4 = st.columns(4)
with col1:
    baslangic = st.selectbox("Nereden", list(ANKARA_DUGUMLER.keys()), index=0)
with col2:
    bitis = st.selectbox("Nereye", list(ANKARA_DUGUMLER.keys()), index=8) # Çayyolu falan
with col3:
    arac_adi = st.selectbox("Aracınız", list(ARACLAR.keys()), index=0)
with col4:
    batarya = st.number_input("Batarya Seviyesi (%)", min_value=5, max_value=100, value=80, step=5)

oto_mod = st.toggle("✨ Otonom Sürüş Desteği (Duruma Göre Kendisi Seçsin)", value=True)

manuel_secim = None
if not oto_mod:
    manuel_secim_str = st.radio("Lütfen Tercihinizi Yapın:", ["Mesafe (En Kısa)", "Süre (En Hızlı)", "Enerji (En Az Yakan)", "Size Özel (Duygu Odaklı)"], horizontal=True)
    if manuel_secim_str == "Mesafe (En Kısa)":
        manuel_secim = "mesafe"
    elif manuel_secim_str == "Süre (En Hızlı)":
        manuel_secim = "sure"
    elif manuel_secim_str == "Enerji (En Az Yakan)":
        manuel_secim = "enerji"
    else:
        manuel_secim = "mo"

hesapla = st.button("🚀 Haritayı ve Rotaları Hesapla", type="primary", width="stretch")

if hesapla:
    st.session_state.graf._guncelle(arac_adi) # Graf ağırlıklarını araca göre güncelle
    
    with st.spinner('Harita, canlı trafik ve NSGA-II rotaları hesaplanıyor...'):
        graf = st.session_state.graf
        rotalar = {}
        
        # Temel 3 Rota hesapla (Dijkstra)
        rotalar["mesafe"], _ = graf.dijkstra(baslangic, bitis, "mesafe")
        rotalar["sure"], _   = graf.dijkstra(baslangic, bitis, "sure")
        rotalar["enerji"], _ = graf.dijkstra(baslangic, bitis, "enerji")
        
        mo_detay = {}
        krit = "mesafe"
        mod_bilgi = None
        
        # Kognitif Motor (AffectEV NSGA-II)
        if st.session_state.kognitif_aktif and rotalar["mesafe"]:
            # Ağırlıkları çek
            if GELISMIS_VAR:
                duygu_motor = SurekliDuyguMotoru(profil if 'profil' in locals() else None)
                w_e, w_t, w_c = duygu_motor.rota_agirliklari(st.session_state.cls)
            else:
                w_e, w_t, w_c = CokAmacliRotaOptimizatoru.agirlik_hesapla(st.session_state.cls)
            # Size Özel (mo) rota çiz
            mo_yol, _ = graf.cok_amacli_dijkstra(baslangic, bitis, w_e, w_t, w_c)
            
            if mo_yol:
                # Mesafe Kısıtı (1.5x kontrolü)
                mo_met  = yol_metrikleri(mo_yol, arac_adi)
                ref_met = yol_metrikleri(rotalar.get("mesafe", mo_yol), arac_adi)
                if ref_met["mesafe_km"] > 0 and mo_met["mesafe_km"] <= ref_met["mesafe_km"] * 1.5:
                    rotalar["mo"] = mo_yol
            
            # Objektif skorlama ve konfor hesabı
            met_tum   = {k: yol_metrikleri(v, arac_adi) for k, v in rotalar.items() if v}
            
            from ev_rota_planner import YOLLAR
            konfor_sk = {
                k: CokAmacliRotaOptimizatoru.rota_konfor_skoru(v, ANKARA_DUGUMLER, YOLLAR)
                for k, v in rotalar.items() if v
            }

            mo_krit, mo_f, mo_detay = CokAmacliRotaOptimizatoru.en_iyi_rota_sec(
                rotalar, met_tum, konfor_sk, st.session_state.cls,
                komsular        = graf.komsular,
                ankara_dugumler = ANKARA_DUGUMLER,
                baslangic       = baslangic,
                bitis           = bitis,
            )
            
            if oto_mod:
                krit = mo_krit
            else:
                krit = manuel_secim if manuel_secim else "mesafe"

            mod_bilgi = {
                "mod": mod.lower(),
                "cls": st.session_state.cls,
                "renk": renk,
                "ikon": emoji,
                "aciklama": "Streamlit üzerinden entegre test modülü çalışıyor.",
                "oneriler": ["Klima seviyesi artırıldı.", "Müzik listesi sakinleştirildi."] if st.session_state.cls > 60 else []
            }

        aktif_yol = rotalar.get(krit, []) or rotalar.get("enerji", [])
        if not aktif_yol:
            st.error("Seçilen hedefler arasında rota bulunamadı!")
            st.stop()
            
        # Trafik çekimi
        sure_bilgi = tomtom_sure_cek(baslangic, bitis) or google_sure_cek(baslangic, bitis) or yerel_sure_tahmin(aktif_yol, arac_adi)
        
        # Batarya planlama
        sarj_plan, sarj_sayisi = sarj_durak_planla(aktif_yol, arac_adi, batarya, st.session_state.sarj_ist, min_esik=10, hedef_yuzde=80)
        
        # Harita oluştur
        html_path, m = harita_olustur(
            baslangic, bitis, arac_adi, batarya, rotalar, st.session_state.sarj_ist,
            krit, sure_bilgi, sarj_plan, sarj_sayisi,
            sarj_kaynagi="TomTom API (Canlı)", kognitif=mod_bilgi, opt_bilgi=mo_detay
        )
        
        # Haritayı ekrana bas
        st_folium(m, width="stretch", height=800, returned_objects=[])
        
        st.success(f"Rota çizildi! Toplam {sarj_sayisi} şarj noktasına uğranacak. Aktif Rota: {krit.upper()}")
        
        st.session_state.son_rota = aktif_yol
        st.session_state.rota_cizildi = True

if st.session_state.rota_cizildi:
    st.markdown("---")
    st.markdown("### 📝 Rota Geri Bildirimi")
    st.write("Sistemimizin öğrenebilmesi için lütfen bu rotaya bir konfor puanı verin:")
    with st.form("feedback_form"):
        puan = st.slider("Konfor Puanınız (1=Çok Kötü, 5=Mükemmel)", 1, 5, 3)
        gonder = st.form_submit_button("Puanı Gönder")
        if gonder:
            if KONFOR_HAFIZASI:
                KONFOR_HAFIZASI.guncelle(st.session_state.son_rota, puan)
                st.success(f"Teşekkürler! Puanınız ({puan}/5) kaydedildi. Sistem bir sonraki rotayı buna göre iyileştirecek (Q-Learning).")
            else:
                st.error("Konfor hafızası modülü bulunamadı.")