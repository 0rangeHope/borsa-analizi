import streamlit as st
import yfinance as yf
import pandas as pd
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bulut Borsa Analiz Terminali", layout="wide")
st.title("📈 Bulut Yapay Zeka Destekli Portföy Analiz Terminali")

# --- GÜVENLİK VE API YAPILANDIRMASI ---
st.sidebar.header("Sistem Bağlantısı")
api_anahtari = st.sidebar.text_input("Groq API Anahtarı:", type="password", help="console.groq.com adresinden aldığınız anahtarı buraya girin.")

# --- KİŞİSEL PORTFÖY HAVUZU ---
st.sidebar.header("Portföy Ayarları")
secilen_pazar = st.sidebar.radio("Pazar Seçin:", ("Kişisel ABD Portföyü", "Kişisel BIST Portföyü"))

if secilen_pazar == "Kişisel ABD Portföyü":
    hisse_havuzu = ["POWL", "QCOM", "IONQ", "RGTI", "APLD", "NVDA", "LUNR", "AMSC", "HALO", "FLY", "UMAC", "ASTS", "ONDS", "NOK", "SOFI", "KTOS", "ORCL", "WMT"]
else:
    hisse_havuzu = ["TKFEN.IS", "KORDS.IS", "TAVHL.IS", "PETKM.IS", "SASA.IS"]

hisseler = st.sidebar.multiselect("Analiz Edilecek Hisseler:", hisse_havuzu, default=hisse_havuzu[:5])

# --- YARDIMCI FONKSİYONLAR ---
def hesapla_rsi(veri, periyot=14):
    delta = veri.diff()
    kazanc = (delta.where(delta > 0, 0)).rolling(window=periyot).mean()
    kayip = (-delta.where(delta < 0, 0)).rolling(window=periyot).mean()
    rs = kazanc / kayip
    return 100 - (100 / (1 + rs))

# Veri eksikliklerinde sistemin çökmesini engelleyen güvenli çekim fonksiyonu
def guvenli_veri(info_dict, anahtar, carpan=1, format_tipi="float"):
    try:
        deger = info_dict.get(anahtar)
        if deger is None or str(deger).lower() == "infinity":
            return "Veri Yok"
        
        hesaplanmis = float(deger) * carpan
        if format_tipi == "yuzde":
            return f"%{hesaplanmis:.2f}"
        return round(hesaplanmis, 2)
    except:
        return "Veri Yok"

# --- ARAYÜZ SEKMELERİ (TABS) ---
tab1, tab2 = st.tabs(["📊 Günlük Teknik Analiz", "🏢 4 Sütunlu Temel Bilanço Analizi"])

# ==========================================
# 1. SEKME: TEKNİK ANALİZ (Kısa Vadeli Yön)
# ==========================================
with tab1:
    st.subheader("Anlık Fiyat, Momentum ve Trend Analizi")
    if st.button("Teknik Analizi Çalıştır"):
        if not api_anahtari:
            st.warning("Lütfen sol menüden Groq API anahtarınızı girin.")
        else:
            with st.spinner('Piyasa verileri işleniyor...'):
                teknik_sonuclar = []
                analiz_metni = ""
                
                for hisse in hisseler:
                    try:
                        ticker = yf.Ticker(hisse)
                        df = ticker.history(period="3mo")
                        
                        if not df.empty and len(df) > 20:
                            df['SMA_20'] = df['Close'].rolling(window=20).mean()
                            df['RSI_14'] = hesapla_rsi(df['Close'], 14)
                            
                            son_veri = df.iloc[-1]
                            onceki_veri = df.iloc[-2]
                            
                            fiyat = son_veri['Close']
                            gunluk_degisim = ((fiyat - onceki_veri['Close']) / onceki_veri['Close']) * 100
                            rsi = son_veri['RSI_14']
                            sma20 = son_veri['SMA_20']
                            
                            sinyal = "NÖTR"
                            if pd.notna(rsi):
                                if rsi < 30: sinyal = "AŞIRI SATIM"
                                elif rsi > 70: sinyal = "AŞIRI ALIM"
                                elif fiyat > sma20: sinyal = "POZİTİF TREND"
                                elif fiyat < sma20: sinyal = "NEGATİF TREND"
                            
                            teknik_sonuclar.append({
                                "Varlık": hisse, 
                                "Fiyat": round(fiyat, 2), 
                                "Günlük Değişim (%)": round(gunluk_degisim, 2),
                                "RSI (14)": round(rsi, 2) if pd.notna(rsi) else 0, 
                                "Trend": sinyal
                            })
                            analiz_metni += f"{hisse} - Fiyat: {fiyat:.2f}, Değişim: %{gunluk_degisim:.2f}, RSI: {rsi:.2f}\n"
                    except:
                        continue
                
                if teknik_sonuclar:
                    df_teknik = pd.DataFrame(teknik_sonuclar)
                    def renk_fonksiyonu(val):
                        if isinstance(val, (int, float)):
                            return 'color: green' if val > 0 else ('color: red' if val < 0 else '')
                        return ''
                    
                    st.dataframe(df_teknik.style.map(renk_fonksiyonu, subset=['Günlük Değişim (%)']), use_container_width=True)
                    
                    st.subheader("🧠 Teknik Yorum")
                    prompt_teknik = f"Nicel analist olarak şu teknik verileri kısaca yorumla, en iyi alım fırsatı veren 1 hisseyi seç:\n{analiz_metni}"
                    try:
                        client = Groq(api_key=api_anahtari)
                        cevap = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt_teknik}],
                            model="lama-3.3-70b"
                        )
                        st.markdown(cevap.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Yapay Zeka Hatası: {e}")

# ==========================================
# 2. SEKME: TEMEL ANALİZ (İçsel Değer & 4 Sütun)
# ==========================================
with tab2:
    st.subheader("Şirketlerin Operasyonel, Değerleme, Büyüme ve Bilanço Analizi")
    st.info("Not: Temel analiz verilerinin (bilanço) Yahoo Finance sunucularından çekilmesi, veri boyutundan dolayı teknik analize göre biraz daha uzun sürebilir.")
    
    if st.button("4 Sütunlu Temel Analizi Çalıştır"):
        if not api_anahtari:
            st.warning("Lütfen sol menüden Groq API anahtarınızı girin.")
        else:
            with st.spinner('Uluslararası bilanço verileri çekiliyor ve modelleniyor...'):
                temel_sonuclar = []
                temel_metin = ""
                
                for hisse in hisseler:
                    try:
                        ticker = yf.Ticker(hisse)
                        info = ticker.info
                        
                        # 1. Para Kazanıyor mu? (Operasyonel Verimlilik)
                        roe = guvenli_veri(info, "returnOnEquity", carpan=100, format_tipi="yuzde")
                        op_marj = guvenli_veri(info, "operatingMargins", carpan=100, format_tipi="yuzde")
                        
                        # 2. Ucuz mu? (Değerleme Çarpanları)
                        f_k = guvenli_veri(info, "forwardPE")
                        ev_ebitda = guvenli_veri(info, "enterpriseToEbitda")
                        
                        # 3. Ne Kadar Büyüyebilir? (Büyüme)
                        ciro_buyume = guvenli_veri(info, "revenueGrowth", carpan=100, format_tipi="yuzde")
                        kar_buyume = guvenli_veri(info, "earningsGrowth", carpan=100, format_tipi="yuzde")
                        
                        # 4. Bilanço Sağlam mı? (Risk Analizi)
                        cari_oran = guvenli_veri(info, "currentRatio")
                        borc_ozkaynak = guvenli_veri(info, "debtToEquity") # Sektöre göre değişir, düşük iyidir
                        
                        temel_sonuclar.append({
                            "Hisse": hisse,
                            "ROE": roe,
                            "Faaliyet Marjı": op_marj,
                            "İleri F/K": f_k,
                            "EV/EBITDA": ev_ebitda,
                            "Ciro Büyümesi": ciro_buyume,
                            "Cari Oran": cari_oran,
                            "Borç/Özkaynak": borc_ozkaynak
                        })
                        
                        temel_metin += f"""{hisse} -> Operasyonel (ROE:{roe}, Marj:{op_marj}) | Değerleme (F/K:{f_k}, EV/EBITDA:{ev_ebitda}) | Büyüme (Ciro Büyüme:{ciro_buyume}, Kar Büyüme:{kar_buyume}) | Bilanço (Cari Oran:{cari_oran}, Borç/Özkaynak:{borc_ozkaynak})\n"""
                        
                    except Exception as e:
                        # Bir hissede veri çekilemezse döngüyü kırma, diğer hisseye geç
                        continue
                
                if temel_sonuclar:
                    df_temel = pd.DataFrame(temel_sonuclar)
                    st.dataframe(df_temel, use_container_width=True)
                    
                    st.subheader("🧠 Bulut Yapay Zeka Bilanço Değerlemesi")
                    prompt_temel = f"""Sen nicel bir değerleme uzmanısın. Aşağıda portföydeki hisselerin "Para Kazanıyor mu?", "Ucuz mu?", "Büyüyebilir mi?" ve "Bilanço Sağlıklı mı?" prensiplerine göre çekilmiş güncel temel analiz verileri var.
                    Verisi eksik ('Veri Yok') olan parametreleri yoksay. 
                    Mevcut verilere göre matematiksel bir mantıkla en iyi 2 yatırımı (değer/büyüme açısından) detaylıca argüman sunarak listele:
                    \n{temel_metin}"""
                    
                    try:
                        client = Groq(api_key=api_anahtari)
                        cevap_temel = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt_temel}],
                            model="lama-3.3-70b"
                        )
                        st.success("Temel analiz hesaplamaları tamamlandı.")
                        st.markdown(cevap_temel.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Yapay Zeka Hatası: {e}")
