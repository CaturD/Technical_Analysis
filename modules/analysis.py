import pandas as pd
import streamlit as st
import mysql.connector
import json
from datetime import datetime
from sklearn.metrics import accuracy_score

# Hitung sinyal akhir berdasarkan mayoritas indikator
def compute_final_signal(data, indicators):
    def majority_vote(row):
        signals = []
        if indicators.get('MA'): signals.append(row.get('Signal_MA', 'Hold'))
        if indicators.get('MACD'): signals.append(row.get('Signal_MACD', 'Hold'))
        if indicators.get('Ichimoku'): signals.append(row.get('Signal_Ichimoku', 'Hold'))
        if indicators.get('SO'): signals.append(row.get('Signal_SO', 'Hold'))
        if indicators.get('Volume'):
            vol_signal = row.get('Signal_Volume', 'Hold')
            signals.append('Buy' if vol_signal == 'High Volume' else 'Sell' if vol_signal == 'Low Volume' else 'Hold')
        buy, sell = signals.count('Buy'), signals.count('Sell')
        return 'Buy' if buy > sell else 'Sell' if sell > buy else 'Hold'
    return data.apply(majority_vote, axis=1)

# Tampilkan tabel analisis dengan filter sinyal dan penomoran
def display_analysis_table_with_summary(df, indicators, signal_filter):
    cols = []
    if indicators.get('MA'):
        cols += ['MA5', 'MA10', 'MA20', 'Signal_MA']
    if indicators.get('MACD'):
        cols += ['MACD', 'MACD_signal', 'MACD_hist', 'Signal_MACD']
    if indicators.get('Ichimoku'):
        cols += ['Tenkan_sen', 'Kijun_sen', 'Senkou_span_A', 'Senkou_span_B', 'Chikou_span', 'Signal_Ichimoku']
    if indicators.get('SO'):
        cols += ['SlowK', 'SlowD', 'Signal_SO']
    if indicators.get('Volume'):
        cols += ['Volume', 'Volume_MA20', 'Signal_Volume']
    
    # Pastikan hanya kolom yang tersedia di df yang dipilih
    existing_cols = [col for col in cols if col in df.columns]
    
    # Tambahkan kolom sinyal akhir
    if 'Final_Signal' in df.columns:
        existing_cols.append('Final_Signal')

    # Filter jika pengguna memilih filter sinyal tertentu
    if signal_filter:
        df_filtered = df[df['Final_Signal'].isin(signal_filter)]
    else:
        df_filtered = df

    st.dataframe(df_filtered[existing_cols], use_container_width=True)


# Simpan hasil analisis ke database (jika belum ada)
def save_analysis_to_json_db(ticker, data, indicators):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("""
            ALTER TABLE analisis_indikator
            ADD COLUMN IF NOT EXISTS title VARCHAR(255),
            ADD COLUMN IF NOT EXISTS datetime DATETIME,
            ADD COLUMN IF NOT EXISTS indikator TEXT
        """)
        data = data.reset_index()
        data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
        json_data = data.to_json(orient='records')
        indikator_aktif = ', '.join([k for k, v in indicators.items() if v])
        title = f"Analisis {ticker} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cursor.execute("""
            SELECT COUNT(*) FROM analisis_indikator
            WHERE ticker = %s AND hasil_analisis = %s AND indikator = %s
        """, (ticker, json_data, indikator_aktif))
        if cursor.fetchone()[0] > 0:
            st.warning("Hasil analisis sudah ada dan tidak disimpan ulang.")
            return
        cursor.execute("""
            INSERT INTO analisis_indikator (ticker, title, datetime, hasil_analisis, indikator)
            VALUES (%s, %s, %s, %s, %s)
        """, (ticker, title, datetime.now(), json_data, indikator_aktif))
        conn.commit()
        st.success("Hasil analisis berhasil disimpan ke database.")
    except mysql.connector.Error as err:
        st.error(f"Gagal menyimpan hasil analisis: {err}")
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# Ambil daftar judul analisis sebelumnya dari DB
def fetch_saved_titles(ticker):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM analisis_indikator WHERE ticker = %s ORDER BY datetime DESC", (ticker,))
        return [r[0] for r in cursor.fetchall()]
    except: return []
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# Load analisis dari DB berdasarkan title
def load_analysis_by_title(ticker, title):
    try:
        conn = mysql.connector.connect(
            host="localhost", user="root", password="", database="indonesia_stock"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT hasil_analisis FROM analisis_indikator WHERE ticker = %s AND title = %s", (ticker, title))
        result = cursor.fetchone()  # ← ini penting, harus dieksekusi sebelum close
        if result:
            df = pd.DataFrame(json.loads(result[0]))
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error saat memuat analisis: {e}")
        return pd.DataFrame()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except: pass  # jika koneksi gagal dibuat


# Tampilkan jumlah sinyal per indikator
def show_signal_recap(data, indicators, title='Rekapitulasi Sinyal'):
    st.subheader(title)
    rows = []
    for key, label in zip(['MA', 'MACD', 'Ichimoku', 'SO', 'Volume'], ['Moving Average', 'MACD', 'Ichimoku', 'Stochastic Oscillator', 'Volume']):
        if indicators.get(key):
            col = f"Signal_{key}" if key != 'Volume' else 'Signal_Volume'
            values = data[col].value_counts()
            for s in ['Buy', 'Sell', 'Hold']:
                label_sinyal = s if key != 'Volume' else 'High Volume' if s == 'Buy' else 'Low Volume' if s == 'Sell' else 'Hold'
                rows.append({'Indikator': label, 'Sinyal': label_sinyal, 'Jumlah': values.get(label_sinyal, 0)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# Evaluasi akurasi strategi berdasarkan arah harga
def evaluate_strategy_accuracy(df):
    if 'Close' not in df.columns or 'Final_Signal' not in df.columns: return None
    df = df.copy()
    df['Future_Close'] = df['Close'].shift(-1)
    df.dropna(subset=['Future_Close', 'Final_Signal'], inplace=True)
    df['Actual_Trend'] = df['Future_Close'] > df['Close']
    df['Actual_Signal'] = df['Actual_Trend'].map({True: 'Buy', False: 'Sell'})
    mask = df['Final_Signal'].isin(['Buy', 'Sell'])
    accuracy = accuracy_score(df.loc[mask, 'Final_Signal'], df.loc[mask, 'Actual_Signal'])
    result = {
        "accuracy": accuracy,
        "total_signals": len(df),
        "correct_predictions": (df['Final_Signal'] == df['Actual_Signal']).sum(),
        "signal_distribution": df['Final_Signal'].value_counts().to_dict()
    }
    return result


# #EVALUASI GABUNG
# # API Key Marketstack
# MARKETSTACK_API_KEY = "5ffdc569c36a2679a97c3483add9e005"

# # Daftar ticker saham
# realtime_tickers = [
#     "BBCA.XIDX"
# ]

# # # Simpan data realtime Marketstack ke MySQL, "BBRI.XIDX", "BYAN.XIDX", "BMRI.XIDX", "TLKM.XIDX", "ASII.XIDX",
# #     "TPIA.XIDX", "BBNI.XIDX", "UNVR.XIDX", "HMSP.XIDX", "GOTO.XIDX", "AMRT.XIDX",
# #     "ICBP.XIDX", "UNTR.XIDX", "MDKA.XIDX", "KLBF.XIDX", "ADRO.XIDX", "DCII.XIDX",
# #     "CPIN.XIDX", "SMMA.XIDX"
# def save_marketstack_data(ticker, data_json):
#     try:
#         conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS stock_data_realtime (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 ticker VARCHAR(20) UNIQUE,
#                 data LONGTEXT
#             )
#         """)
#         insert_query = """
#             INSERT INTO stock_data_realtime (ticker, data)
#             VALUES (%s, %s)
#             ON DUPLICATE KEY UPDATE data = VALUES(data)
#         """
#         cleaned_data = json.dumps([{str(k): v for k, v in entry.items()} for entry in data_json], default=str)
#         cursor.execute(insert_query, (ticker, cleaned_data))
#         conn.commit()
#         print(f"Data Marketstack {ticker} berhasil disimpan.")
#     except Exception as e:
#         print(f"Gagal menyimpan {ticker}: {e}")
#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()

# # Ambil data real-time dari Marketstack
# def fetch_marketstack_realtime(ticker):
#     url = "http://api.marketstack.com/v1/eod"
#     params = {
#         "access_key": MARKETSTACK_API_KEY,
#         "symbols": ticker,
#         "limit": 1
#     }
#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         result = response.json()

#         data = result.get("data", [])
#         if not data:
#             print(f"Tidak ada data untuk {ticker}. Respon: {result}")
#             return None

#         formatted_data = []
#         for row in data:
#             formatted_data.append({
#                 "Date": row['date'],
#                 "Open": row['open'],
#                 "High": row['high'],
#                 "Low": row['low'],
#                 "Close": row['close'],
#                 "Volume": row['volume'],
#                 "Name": row['symbol']
#             })

#         return formatted_data

#     except Exception as e:
#         print(f"Gagal mengambil data {ticker}: {e}")
#         return None

# # Fungsi ambil satu ticker realtime (untuk dashboard)
# def get_realtime_data_from_db(ticker):
#     try:
#         if not ticker:
#             print("Ticker bernilai None")
#             return pd.DataFrame()

#         conn = mysql.connector.connect(
#             host="localhost",
#             user="root",
#             password="",
#             database="indonesia_stock"
#         )
#         cursor = conn.cursor(dictionary=True)
#         query = "SELECT data FROM stock_data_realtime WHERE ticker = %s"
#         cursor.execute(query, (ticker,))
#         result = cursor.fetchone()

#         print(f"[DEBUG] Query result for {ticker}: {result}")

#         if result and result["data"]:
#             try:
#                 print("[DEBUG] Raw JSON data:", result["data"][:150])
#                 data_json = json.loads(result["data"])
#                 print("[DEBUG] JSON decoded successfully.")
#                 df = pd.DataFrame(data_json)
#                 if not df.empty:
#                     df['Date'] = pd.to_datetime(df['Date'])
#                     df.set_index('Date', inplace=True)
#                     print(f"[DEBUG] Dataframe loaded with shape: {df.shape}")
#                 return df
#             except Exception as decode_error:
#                 print(f"Gagal parsing JSON untuk {ticker}: {decode_error}")
#                 return pd.DataFrame()
#         else:
#             print(f"Tidak ada data ditemukan untuk ticker: {ticker}")
#             return pd.DataFrame()

#     except Exception as e:
#         print(f"Gagal membaca data realtime dari database: {e}")
#         return pd.DataFrame()

#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()

# # Eksekusi utama Marketstack real-time
# if __name__ == "__main__":
#     for ticker in realtime_tickers:
#         print(f"Mengambil data {ticker} dari Marketstack...")
#         data = fetch_marketstack_realtime(ticker)
#         if data:
#             save_marketstack_data(ticker, data)
#         time.sleep(5)  # Hindari rate limit
