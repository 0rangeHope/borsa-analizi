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

# Görseldeki hisseler
if secilen_pazar == "Kişisel ABD Portföyü":
    hisse_havuzu = ["POWL", "QCOM", "IONQ", "RGTI", "APLD", "NVDA", "LUNR", "AMSC", "HALO", "FLY", "UMAC", "ASTS", "ONDS", "NOK", "SOFI", "KTOS", "ORCL", "WMT"]
else:
    hisse_havuzu = ["TKFEN.IS", "KORDS.IS", "TAVHL.IS", "PETKM.IS", "SASA.IS"]

# Varsayılan olarak tümünü seç
hisseler = st.sidebar.multiselect("Analiz Edilecek Hisseler:", hisse_havuzu, default=hisse_havuzu)

def hesapla_rsi(veri, periyot=14):
    delta = veri.diff()
    kazanc = (delta.where(delta > 0, 0)).rolling(window=periyot).mean()
    kayip = (-delta.where(delta < 0, 0)).rolling(window=periyot).mean()
    rs = kazanc / kayip
    return 100 - (100 / (1 + rs))

# --- VERİ ÇEKME VE TEKNİK ANALİZ ---
st.subheader("📊 Günlük Rapor ve Matematiksel Analiz Tablosu")
analiz_metni_icin_veri = ""

if st.button("Anlık Verileri Çek ve Günlük Rapor Oluştur"):
    if not api_anahtari:
        st.warning("İşleme başlamadan önce sol menüden Groq API anahtarınızı girmelisiniz.")
    else:
        with st.spinner('Piyasa verileri işleniyor ve matematiksel modeller hesaplanıyor...'):
            sonuclar = []
            for hisse in hisseler:
                ticker = yf.Ticker(hisse)
                df = ticker.history(period="3mo")
                
                if not df.empty and len(df) > 20:
                    df['SMA_20'] = df['Close'].rolling(window=20).mean()
                    df['RSI_14'] = hesapla_rsi(df['Close'], 14)
                    
                    son_veri = df.iloc[-1]
                    onceki_veri = df.iloc[-2]
                    
                    fiyat = son_veri['Close']
                    gunluk_degisim_yuzde = ((fiyat - onceki_veri['Close']) / onceki_veri['Close']) * 100
                    rsi = son_veri['RSI_14']
                    sma20 = son_veri['SMA_20']
                    
                    sinyal = "NÖTR"
                    if pd.notna(rsi):
                        if rsi < 30:
                            sinyal = "AŞIRI SATIM (Alım Fırsatı)"
                        elif rsi > 70:
                            sinyal = "AŞIRI ALIM (Satış Baskısı)"
                        elif fiyat > sma20:
                            sinyal = "POZİTİF TREND"
                        elif fiyat < sma20:
                            sinyal = "NEGATİF TREND"
                    
                    sonuclar.append({
                        "Varlık": hisse, 
                        "Anlık Fiyat": round(fiyat, 2), 
                        "Günlük Değişim (%)": round(gunluk_degisim_yuzde, 2),
                        "RSI (14)": round(rsi, 2) if pd.notna(rsi) else 0, 
                        "Trend Analizi": sinyal
                    })
                    
                    analiz_metni_icin_veri += f"{hisse} - Fiyat: {fiyat:.2f}, Günlük Değişim: %{gunluk_degisim_yuzde:.2f}, RSI: {rsi:.2f}, Trend: {sinyal}\n"
            
            if sonuclar:
                # Tabloyu oluştur ve yüzdelere göre renklendirme uygulayarak göster
                df_sonuclar = pd.DataFrame(sonuclar)
                
                # Stil fonksiyonu: Negatif değerler kırmızı, pozitif değerler yeşil
                def color_negative_red(val):
                    if isinstance(val, (int, float)):
                        color = 'red' if val < 0 else 'green'
                        return f'color: {color}'
                    return ''
                
                styled_df = df_sonuclar.style.map(color_negative_red, subset=['Günlük Değişim (%)'])
                st.dataframe(styled_df, use_container_width=True)
                
                st.subheader("🧠 Bulut Yapay Zeka Günlük Kapanış Raporu")
                prompt = f"""Sen nicel (quantitative) bir mühendis ve algoritmik finans analistisin. 
                Aşağıdaki anlık borsa verilerine göre:
                1. Portföyün günlük genel durumunu özetle (Hangi hisseler kazandırdı, hangileri kaybettirdi).
                2. Teknik göstergeleri (RSI ve Günlük Değişim) referans alarak alım veya satım için matematiksel olarak en dikkat çeken 3 hisseyi analitik bir dille açıkla.
                Muğlak ifadelerden kaçın, doğrudan veriye dayalı nicel bir rapor sun:
                \n{analiz_metni_icin_veri}"""
                
                try:
                    # Stabil ve hızlı model kullanımı
                    client = Groq(api_key=api_anahtari)
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama3-8b-8192", 
                    )
                    st.success("Anlık günlük rapor başarıyla oluşturuldu.")
                    st.markdown(chat_completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Groq Bağlantı Hatası: {e}")
