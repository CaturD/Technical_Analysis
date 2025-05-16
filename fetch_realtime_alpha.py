import requests
import mysql.connector
import json
import time
from datetime import datetime

# API key Alpha Vantage
API_KEY = "5ZJPSTK6RUQZMZ6L"

# Daftar ticker real-time (maksimal 5 per menit untuk Alpha Vantage free tier)
tickers = [
    "BBCA", "BBRI", "BYAN", "BMRI", "TLKM", "ASII", "TPIA", "BBNI", "UNVR", "HMSP", 
    "GOTO", "AMRT", "ICBP", "UNTR", "MDKA", "KLBF", "ADRO", "DCII", "CPIN", "SMMA"
]

# Fungsi untuk simpan ke MySQL
def save_realtime_data_to_db(ticker, data_json):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data_realtime (
                ticker VARCHAR(10) PRIMARY KEY,
                data JSON
            )
        """)
        insert_query = """
            INSERT INTO stock_data_realtime (ticker, data)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE data = VALUES(data)
        """
        cursor.execute(insert_query, (ticker, json.dumps(data_json, default=str)))
        conn.commit()
        print(f"Real-time data {ticker} berhasil disimpan.")
    except Exception as e:
        print(f"Gagal menyimpan {ticker}: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Fungsi untuk ambil data realtime dari Alpha Vantage
def fetch_realtime_from_alpha(ticker, interval="5min"):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": ticker,
        "interval": interval,
        "apikey": API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()

        if f"Time Series ({interval})" not in result:
            print(f"Tidak ada data untuk {ticker}. Pesan: {result.get('Note') or result}")
            return None

        time_series = result[f"Time Series ({interval})"]
        formatted_data = []

        for time_str, values in time_series.items():
            formatted_data.append({
                "Date": time_str,
                "Open": float(values["1. open"]),
                "High": float(values["2. high"]),
                "Low": float(values["3. low"]),
                "Close": float(values["4. close"]),
                "Volume": int(float(values["5. volume"])),
                "Name": ticker
            })

        return formatted_data

    except Exception as e:
        print(f"Gagal mengambil {ticker}: {e}")
        return None

# Eksekusi utama
for ticker in tickers:
    print(f"Mengambil real-time data {ticker} dari Alpha Vantage...")
    data = fetch_realtime_from_alpha(ticker)
    if data:
        save_realtime_data_to_db(ticker, data)
    time.sleep(15)  # jeda antar ticker untuk menghindari rate limit
