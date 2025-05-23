import pandas as pd
import streamlit as st
import mysql.connector
import json
from datetime import datetime, timedelta
from sklearn.metrics import accuracy_score
import yfinance as yf
import time
import requests

def compute_final_signal(data, indicators):
    def majority_vote(row):
        signals = []
        if indicators.get('MA'):
            signals.append(row.get('Signal_MA', 'Hold'))
        if indicators.get('MACD'):
            signals.append(row.get('Signal_MACD', 'Hold'))
        if indicators.get('Ichimoku'):
            signals.append(row.get('Signal_Ichimoku', 'Hold'))
        if indicators.get('SO'):
            signals.append(row.get('Signal_SO', 'Hold'))
        if indicators.get('Volume'):
            vol_signal = row.get('Signal_Volume', 'Hold')
            if vol_signal == 'High Volume':
                signals.append('Buy')
            elif vol_signal == 'Low Volume':
                signals.append('Sell')
            else:
                signals.append('Hold')

        buy = signals.count('Buy')
        sell = signals.count('Sell')
        if buy > sell:
            return 'Buy'
        elif sell > buy:
            return 'Sell'
        return 'Hold'

    return data.apply(majority_vote, axis=1)

def display_analysis_table_with_summary(data, indicators, signal_filter=['Buy', 'Sell', 'Hold']):
    columns_to_display = []
    if indicators.get('MA'):
        columns_to_display += ['MA20', 'MA50', 'Signal_MA']
    if indicators.get('MACD'):
        columns_to_display += ['MACD', 'MACD_signal', 'MACD_hist', 'Signal_MACD']
    if indicators.get('Ichimoku'):
        columns_to_display += ['Tenkan_sen', 'Kijun_sen', 'Senkou_span_A', 'Senkou_span_B', 'Chikou_span', 'Signal_Ichimoku']
    if indicators.get('SO'):
        columns_to_display += ['SlowK', 'SlowD', 'Signal_SO']
    if indicators.get('Volume'):
        columns_to_display += ['Volume', 'Volume_MA20', 'Signal_Volume']

    display_cols = list(dict.fromkeys(columns_to_display + ['Final_Signal', 'Close']))

    data_copy = data.copy().reset_index()
    data_copy.insert(0, 'No', data_copy.index + 1)

    # Filter sinyal jika diberikan
    data_filtered = data_copy[data_copy['Final_Signal'].isin(signal_filter)]

    st.subheader('Tabel Hasil Analisis')
    st.dataframe(data_filtered[display_cols], use_container_width=True)


def save_analysis_to_json_db(ticker, data, indicators):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor()

        cursor.execute("SHOW COLUMNS FROM analisis_indikator LIKE 'title'")
        title_exists = cursor.fetchone()

        if not title_exists:
            alter_query = """
            ALTER TABLE analisis_indikator
            ADD COLUMN title VARCHAR(255),
            ADD COLUMN datetime DATETIME,
            ADD COLUMN indikator TEXT
            """
            cursor.execute(alter_query)

        data = data.reset_index()
        data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
        json_data = data.to_json(orient='records')
        indikator_terpilih = ', '.join([key for key, val in indicators.items() if val])
        title = f"Analisis {ticker} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Cek apakah kombinasi ini sudah ada
        check_query = """
        SELECT COUNT(*) FROM analisis_indikator
        WHERE ticker = %s AND hasil_analisis = %s AND indikator = %s
        """
        cursor.execute(check_query, (ticker, json_data, indikator_terpilih))
        if cursor.fetchone()[0] > 0:
            st.warning("Hasil analisis sudah ada dan tidak disimpan ulang.")
            return

        insert_query = """
        INSERT INTO analisis_indikator (ticker, title, datetime, hasil_analisis, indikator)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (ticker, title, datetime.now(), json_data, indikator_terpilih)
        cursor.execute(insert_query, values)
        conn.commit()
        st.success("Hasil analisis berhasil disimpan ke database.")

    except mysql.connector.Error as err:
        st.error(f"Gagal menyimpan hasil analisis: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def fetch_saved_titles(ticker):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor()
        query = "SELECT title FROM analisis_indikator WHERE ticker = %s ORDER BY datetime DESC"
        cursor.execute(query, (ticker,))
        results = [row[0] for row in cursor.fetchall()]
        return results
    except mysql.connector.Error as err:
        st.error(f"Gagal mengambil judul analisis: {err}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def load_analysis_by_title(ticker, title):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor()
        query = "SELECT hasil_analisis FROM analisis_indikator WHERE ticker = %s AND title = %s"
        cursor.execute(query, (ticker, title))
        result = cursor.fetchone()
        if result:
            data_json = json.loads(result[0])
            df = pd.DataFrame(data_json)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df
        else:
            st.warning("Data tidak ditemukan.")
            return pd.DataFrame()
    except mysql.connector.Error as err:
        st.error(f"Gagal memuat data analisis: {err}")
        return pd.DataFrame()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def show_signal_recap(data, indicators, title='Rekapitulasi Sinyal'):
    st.subheader(title)
    rows = []

    if indicators.get('MA'):
        counts = data['Signal_MA'].value_counts()
        for signal in ['Buy', 'Sell', 'Hold']:
            rows.append({'Indikator': 'Moving Average', 'Sinyal': signal, 'Jumlah': counts.get(signal, 0)})

    if indicators.get('MACD'):
        counts = data['Signal_MACD'].value_counts()
        for signal in ['Buy', 'Sell', 'Hold']:
            rows.append({'Indikator': 'MACD', 'Sinyal': signal, 'Jumlah': counts.get(signal, 0)})

    if indicators.get('Ichimoku'):
        counts = data['Signal_Ichimoku'].value_counts()
        for signal in ['Buy', 'Sell', 'Hold']:
            rows.append({'Indikator': 'Ichimoku', 'Sinyal': signal, 'Jumlah': counts.get(signal, 0)})

    if indicators.get('SO'):
        counts = data['Signal_SO'].value_counts()
        for signal in ['Buy', 'Sell', 'Hold']:
            rows.append({'Indikator': 'Stochastic Oscillator', 'Sinyal': signal, 'Jumlah': counts.get(signal, 0)})

    if indicators.get('Volume'):
        counts = data['Signal_Volume'].value_counts()
        for signal in ['High Volume', 'Low Volume', 'Hold']:
            rows.append({'Indikator': 'Volume', 'Sinyal': signal, 'Jumlah': counts.get(signal, 0)})

    df_recap = pd.DataFrame(rows)
    st.dataframe(df_recap, use_container_width=True)

# EVALUASI AKURASI
def evaluate_strategy_accuracy(df):
    """
    Menghitung akurasi strategi berdasarkan sinyal dan pergerakan harga berikutnya.
    Membandingkan kolom 'Final_Signal' vs 'Actual_Signal' berdasarkan Future_Close.
    """
    if 'Close' not in df.columns or 'Final_Signal' not in df.columns:
        print("Data tidak memiliki kolom yang dibutuhkan.")
        return None

    df = df.copy()
    df['Future_Close'] = df['Close'].shift(-1)
    df.dropna(subset=['Future_Close', 'Final_Signal'], inplace=True)

    df['Actual_Trend'] = df['Future_Close'] > df['Close']
    df['Actual_Signal'] = df['Actual_Trend'].map({True: 'Buy', False: 'Sell'})

    # Hanya bandingkan baris dengan sinyal Buy atau Sell
    mask = df['Final_Signal'].isin(['Buy', 'Sell'])
    accuracy = accuracy_score(df.loc[mask, 'Final_Signal'], df.loc[mask, 'Actual_Signal'])

    # Rekap jumlah sinyal
    signal_count = df['Final_Signal'].value_counts().to_dict()
    correct_predictions = (df['Final_Signal'] == df['Actual_Signal']).sum()

    result = {
        "accuracy": accuracy,
        "total_signals": len(df),
        "correct_predictions": correct_predictions,
        "signal_distribution": signal_count
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
