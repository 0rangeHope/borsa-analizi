import streamlit as st
import yfinance as yf
import pandas as pd
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bulut Borsa Analiz Terminali", layout="wide")
st.title("📈 Bulut Yapay Zeka Destekli Borsa Analiz Uygulaması")

# --- GÜVENLİK VE API YAPILANDIRMASI ---
st.sidebar.header("Sistem Bağlantısı")
api_anahtari = st.sidebar.text_input("Groq API Anahtarı:", type="password", help="console.groq.com adresinden aldığınız anahtarı buraya girin.")

# --- HİSSE HAVUZU ---
st.sidebar.header("Portföy Ayarları")
secilen_pazar = st.sidebar.radio("Pazar Seçin:", ("ABD Borsaları (Teknoloji)", "Borsa İstanbul (BIST30)"))

if secilen_pazar == "ABD Borsaları (Teknoloji)":
    hisse_havuzu = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
else:
    hisse_havuzu = ["THYAO.IS", "ASELS.IS", "TUPRS.IS", "GARAN.IS", "KCHOL.IS"]

hisseler = st.sidebar.multiselect("Analiz Edilecek Hisseler:", hisse_havuzu, default=hisse_havuzu[:3])

def hesapla_rsi(veri, periyot=14):
    delta = veri.diff()
    kazanc = (delta.where(delta > 0, 0)).rolling(window=periyot).mean()
    kayip = (-delta.where(delta < 0, 0)).rolling(window=periyot).mean()
    rs = kazanc / kayip
    return 100 - (100 / (1 + rs))

# --- VERİ ÇEKME VE TEKNİK ANALİZ ---
st.subheader("📊 Teknik Göstergeler ve Matematiksel Analiz")
analiz_metni_icin_veri = ""

if st.button("Verileri Çek ve Analiz Et"):
    if not api_anahtari:
        st.warning("İşleme başlamadan önce sol menüden Groq API anahtarınızı girmelisiniz.")
    else:
        with st.spinner('Piyasa verileri işleniyor...'):
            sonuclar = []
            for hisse in hisseler:
                ticker = yf.Ticker(hisse)
                df = ticker.history(period="3mo")
                
                if not df.empty and len(df) > 20:
                    df['SMA_20'] = df['Close'].rolling(window=20).mean()
                    df['RSI_14'] = hesapla_rsi(df['Close'], 14)
                    
                    son_veri = df.iloc[-1]
                    fiyat = son_veri['Close']
                    rsi = son_veri['RSI_14']
                    sma20 = son_veri['SMA_20']
                    
                    sinyal = "NÖTR"
                    if pd.notna(rsi):
                        if rsi < 30:
                            sinyal = "AŞIRI SATIM (Alım Bölgesi)"
                        elif rsi > 70:
                            sinyal = "AŞIRI ALIM (Satış Baskısı)"
                        elif fiyat > sma20:
                            sinyal = "POZİTİF TREND"
                    
                    sonuclar.append({"Hisse": hisse, "Fiyat": round(fiyat, 2), "RSI (14)": round(rsi, 2) if pd.notna(rsi) else 0, "Durum": sinyal})
                    analiz_metni_icin_veri += f"{hisse} - Fiyat: {fiyat:.2f}, RSI: {rsi:.2f}, Durum: {sinyal}\n"
            
            if sonuclar:
                df_sonuclar = pd.DataFrame(sonuclar)
                st.dataframe(df_sonuclar, use_container_width=True)
                
                st.subheader("🧠 Bulut Yapay Zeka (Llama 3.3) Analiz Raporu")
                prompt = f"""Sen nicel (quantitative) bir mühendis ve finans analistisin. 
                Aşağıdaki teknik analiz verilerine göre hangi hissenin alım için matematiksel olarak en doğru zamanda olduğunu net ve analitik bir dille açıkla:
                \n{analiz_metni_icin_veri}"""
                
                try:
                    # En güncel ve stabil model buraya entegre edildi
                    client = Groq(api_key=api_anahtari)
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="openai/gpt-oss-20b",
                    )
                    st.success("Bulut analizi başarıyla tamamlandı!")
                    st.markdown(chat_completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Groq Bağlantı Hatası: {e}")