import yfinance as yf
import mysql.connector
import json
import time
import pandas as pd
from datetime import datetime, timedelta

tickers = [
    "BBCA.JK",
    # Tambahkan lainnya
]

def get_existing_data(ticker):
    """Ambil data yang sudah ada dari database (JSON)."""
    conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM stock_data WHERE ticker = %s", (ticker,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return json.loads(result[0]) if result else None

def save_stock_data_to_db(ticker, data_json):
    """Simpan data baru ke dalam DB dengan struktur JSON."""
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                ticker VARCHAR(10) PRIMARY KEY,
                data JSON
            )
        """)
        query = """
            INSERT INTO stock_data (ticker, data)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE data = VALUES(data)
        """
        cursor.execute(query, (ticker, json.dumps(data_json, default=str)))
        conn.commit()
        print(f"{ticker}: Data berhasil disimpan.")
    except Exception as e:
        print(f"{ticker}: Gagal menyimpan data: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def fetch_and_update(ticker):
    existing_data = get_existing_data(ticker)

    if existing_data and len(existing_data) > 0:
        last_date_str = max(entry['Date'] for entry in existing_data)
        start_date = datetime.strptime(last_date_str, '%Y-%m-%d') + timedelta(days=1)
    else:
        start_date = datetime.today() - timedelta(days=3*365)

    end_date = datetime.today()

    if start_date > end_date:
        print(f"[{ticker}] Tidak ada data baru.")
        return

    df = yf.download(
        ticker,
        start=start_date.strftime('%Y-%m-%d'),
        end=end_date.strftime('%Y-%m-%d'),
        interval='1d',
        progress=False,
        auto_adjust=False
    )

    if df.empty:
        print(f"[{ticker}] Data kosong.")
        return

    df = df.reset_index()  # pastikan 'Date' jadi kolom biasa

    if 'Date' not in df.columns:
        print(f"[{ticker}] Kolom 'Date' tidak ditemukan.")
        return

    new_data = []
    for i in range(len(df)):
        try:
            tanggal_str = pd.to_datetime(df['Date'].iloc[i]).strftime('%Y-%m-%d')  # AMAN
            new_data.append({
                "Date": tanggal_str,
                "Open": float(df['Open'].iloc[i]) if pd.notna(df['Open'].iloc[i]) else None,
                "High": float(df['High'].iloc[i]) if pd.notna(df['High'].iloc[i]) else None,
                "Low": float(df['Low'].iloc[i]) if pd.notna(df['Low'].iloc[i]) else None,
                "Close": float(df['Close'].iloc[i]) if pd.notna(df['Close'].iloc[i]) else None,
                "Volume": int(df['Volume'].iloc[i]) if pd.notna(df['Volume'].iloc[i]) else None,
                "Name": ticker
            })
        except Exception as e:
            print(f"[{ticker}] Gagal parsing baris ke-{i}: {e}")
            continue

    if existing_data:
        existing_dates = set(entry['Date'] for entry in existing_data)
        new_data = [d for d in new_data if d['Date'] not in existing_dates]
        all_data = existing_data + new_data
    else:
        all_data = new_data

    if not new_data:
        print(f"[{ticker}] Tidak ada data baru untuk ditambahkan.")
        return

    save_stock_data_to_db(ticker, all_data)

# Run per ticker
for ticker in tickers:
    print(f"Memproses: {ticker}")
    fetch_and_update(ticker)
    time.sleep(5)
