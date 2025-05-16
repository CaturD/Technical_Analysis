import requests
import mysql.connector
import json
import time
from datetime import datetime

# API Key Marketstack
API_KEY = "5ffdc569c36a2679a97c3483add9e005"

# Ticker Indonesia (gunakan kode internasional misalnya IDX:BBCA)
tickers = [ "BBCA.XIDX", "BBRI.XIDX", "BYAN.XIDX", "BMRI.XIDX", "TLKM.XIDX", "ASII.XIDX", "TPIA.XIDX", "BBNI.XIDX", "UNVR.XIDX", "HMSP.XIDX", 
            "GOTO.XIDX", "AMRT.XIDX", "ICBP.XIDX", "UNTR.XIDX", "MDKA.XIDX", "KLBF.XIDX", "ADRO.XIDX", "DCII.XIDX", "CPIN.XIDX", "SMMA.XIDX"]

# Simpan ke MySQL
def save_marketstack_data(ticker, data_json):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data_realtime (
                ticker VARCHAR(20) PRIMARY KEY,
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
        print(f"Data Marketstack {ticker} berhasil disimpan.")
    except Exception as e:
        print(f"Gagal menyimpan {ticker}: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Ambil data real-time dari Marketstack
def fetch_marketstack_realtime(ticker):
    url = "http://api.marketstack.com/v1/eod"
    params = {
        "access_key": API_KEY,
        "symbols": ticker,
        "limit": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()

        data = result.get("data", [])
        if not data:
            print(f"Tidak ada data untuk {ticker}. Respon: {result}")
            return None

        formatted_data = []
        for row in data:
            formatted_data.append({
                "Date": row['date'],
                "Open": row['open'],
                "High": row['high'],
                "Low": row['low'],
                "Close": row['close'],
                "Volume": row['volume'],
                "Name": row['symbol']
            })

        return formatted_data

    except Exception as e:
        print(f"Gagal mengambil data {ticker}: {e}")
        return None

# Eksekusi utama
for ticker in tickers:
    print(f"Mengambil data {ticker} dari Marketstack")
    data = fetch_marketstack_realtime(ticker)
    if data:
        save_marketstack_data(ticker, data)
    time.sleep(5)  # Hindari limit API
