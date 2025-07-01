import pandas as pd
import streamlit as st
import mysql.connector
from mysql.connector import errorcode
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
        required_columns = {
            "title": "VARCHAR(255)",
            "datetime": "DATETIME",
            "indikator": "TEXT",
        }
        for col, ctype in required_columns.items():
            try:
                cursor.execute(
                    f"ALTER TABLE analisis_indikator ADD COLUMN {col} {ctype}"
                )
            except mysql.connector.Error as err:
                if err.errno != errorcode.ER_DUP_FIELDNAME:
                    raise
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

# Evaluasi win rate strategi berdasarkan arah harga
def evaluate_strategy_winrate(df):
    if 'Close' not in df.columns or 'Final_Signal' not in df.columns:
        return None
    df = df.copy()
    df['Future_Close'] = df['Close'].shift(-1)
    df.dropna(subset=['Future_Close', 'Final_Signal'], inplace=True)
    df['Actual_Trend'] = df['Future_Close'] > df['Close']
    df['Actual_Signal'] = df['Actual_Trend'].map({True: 'Buy', False: 'Sell'})
    mask = df['Final_Signal'].isin(['Buy', 'Sell'])
    winrate = accuracy_score(df.loc[mask, 'Final_Signal'], df.loc[mask, 'Actual_Signal'])
    result = {
        "winrate": winrate,  # ← sebelumnya 'winrate'
        "total_signals": len(df),
        "correct_predictions": (df['Final_Signal'] == df['Actual_Signal']).sum(),
        "signal_distribution": df['Final_Signal'].value_counts().to_dict()
    }
    return result

def save_date_filtered_trend_to_db(ticker, indikator, trend, start_date, end_date):
    try:
        conn = mysql.connector.connect(
            host="localhost", user="root", password="", database="indonesia_stock"
        )
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_filtered (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                indikator VARCHAR(50),
                start_date DATE,
                end_date DATE,
                trend_result VARCHAR(20),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            SELECT COUNT(*) FROM trend_filtered
            WHERE ticker=%s AND indikator=%s AND start_date=%s AND end_date=%s
        """, (ticker, indikator, start_date, end_date))

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO trend_filtered (ticker, indikator, start_date, end_date, trend_result)
                VALUES (%s, %s, %s, %s, %s)
            """, (ticker, indikator, start_date, end_date, trend))
            conn.commit()
        else:
            print(f"Data tren {indikator} untuk {ticker} periode {start_date} s.d. {end_date} sudah ada.")

    except Exception as e:
        print(f"Error menyimpan tren ke DB: {e}")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
