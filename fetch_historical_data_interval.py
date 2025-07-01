import argparse
import json
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
import mysql.connector


def reset_table(stock_data_interval: str) -> None:
    """Drop the table so a fresh one is created each run."""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="indonesia_stock",
    )
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {stock_data_interval}")
    conn.commit()
    cursor.close()
    conn.close()

# ---------- Fungsi penyimpanan ----------
# def save_stock_data_to_db(ticker, data_json, interval):
def save_to_stock_data_interval(stock_data_interval, ticker, interval, data_json):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # ganti sesuai password kamu
        database="indonesia_stock"
    )
    cursor = conn.cursor()

    # Buat tabel jika belum ada
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {stock_data_interval} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        interval VARCHAR(10) NOT NULL,
        data JSON NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_ticker_interval (ticker, interval)
    );
    """
    cursor.execute(create_table_query)

    # Simpan atau update data
    insert_query = f"""
        INSERT INTO {stock_data_interval} (ticker, interval, data)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE data = VALUES(data), updated_at = CURRENT_TIMESTAMP;
    """
    cursor.execute(insert_query, (ticker, interval, json.dumps(data_json)))
    conn.commit()
    cursor.close()
    conn.close()

# ---------- Fungsi pengambilan & konversi ----------
def fetch_and_store(ticker, interval, period):
    try:
        print(f"[{ticker}] Mengambil data ({interval})...")

        if interval.endswith("m") or interval.endswith("h"):
            df = yf.download(
                ticker,
                interval=interval,
                period=period,
                progress=False,
                auto_adjust=False,
            )
        else:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=5 * 365)
            df = yf.download(
                ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval,
                progress=False,
                auto_adjust=False
            )

        if df.empty:
            print(f"[{ticker}] Data kosong.")
            return

        df.reset_index(inplace=True)
        date_col = "Datetime" if "Datetime" in df.columns else "Date"

        data_json = []
        for _, row in df.iterrows():
            try:
                tanggal = row[date_col]
                if not isinstance(tanggal, pd.Timestamp):
                    tanggal = pd.to_datetime(tanggal)

                date_fmt = "%Y-%m-%d %H:%M:%S" if interval.endswith("m") or interval.endswith("h") else "%Y-%m-%d"
                data_json.append({
                    "Date": tanggal.strftime(date_fmt),
                    "Open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                    "High": float(row["High"]) if pd.notna(row["High"]) else None,
                    "Low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                    "Close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                    "Volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                    "Name": ticker
                })
            except Exception as e_row:
                print(f"[{ticker}] Gagal memproses baris: {e_row}")

        save_to_stock_data_interval(TABLE_NAME, ticker, interval, data_json)
        print(f"[{ticker}] Data berhasil disimpan.\n")

    except Exception as e:
        print(f"[{ticker}] Gagal: {e}")


# ---------- Main program ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch historical stock data")
    parser.add_argument("--interval", default="1d", help="Interval (e.g. 1d, 1h, 5m)")
    parser.add_argument(
        "--period",
        default="7d",
        help="Period for minute/hour interval (e.g. 7d, 60d)",
    )

    args = parser.parse_args()
    INTERVAL = args.interval
    PERIOD = args.period
    TABLE_NAME = f"stock_data_interval_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Data akan disimpan di tabel: {TABLE_NAME}")
    
    TICKERS = [
"AALI.JK", "ABBA.JK", 
] # ganti sesuai kebutuhan

    for ticker in TICKERS:
        fetch_and_store(ticker, INTERVAL, PERIOD)
        time.sleep(3)  # hindari rate-limit dari yfinance
