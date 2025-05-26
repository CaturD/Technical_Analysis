import yfinance as yf
import mysql.connector
import json
import time
import pandas as pd
from datetime import datetime, timedelta

# Daftar ticker saham
tickers = [
    "ACES.JK","ADMR.JK","ADRO.JK","AKRA.JK","AMMN.JK","AMRT.JK","ANTM.JK","ARTO.JK","ASII.JK","BBCA.JK","BBNI.JK","BBRI.JK",
    "BBTN.JK","BMRI.JK","BRIS.JK","BRPT.JK","CPIN.JK","CTRA.JK","ESSA.JK","EXCL.JK","GOTO.JK","ICBP.JK","INCO.JK","INDF.JK",
    "INKP.JK","ISAT.JK","ITMG.JK","JPFA.JK","JSMR.JK","KLBF.JK","MAPA.JK","MAPI.JK","MBMA.JK","MDKA.JK","MEDC.JK","PGAS.JK",
    "PGEO.JK","PTBA.JK","SIDO.JK","SMGR.JK","SMRA.JK","TLKM.JK","TOWR.JK","UNTR.JK","UNVR.JK",
]

def save_stock_data_to_db(ticker, data_json_list):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                ticker VARCHAR(10) PRIMARY KEY,
                data JSON
            )
        """)
        insert_query = """
            INSERT INTO stock_data (ticker, data)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE data = VALUES(data)
        """
        cleaned_data = json.dumps(data_json_list, default=str)
        cursor.execute(insert_query, (ticker, cleaned_data))
        conn.commit()
        print(f"Data {ticker} berhasil disimpan.")
    except Exception as e:
        print(f"Gagal menyimpan data {ticker}: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def fetch_and_store(ticker):
    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=3*365)
        df = yf.download(
            ticker,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1d',
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            print(f"Data kosong untuk {ticker}")
            return

        df.reset_index(inplace=True)
        data_json = []
        for _, row in df.iterrows():
            tanggal = row['Date']
            if isinstance(tanggal, pd.Series):
                tanggal = tanggal.iloc[0]
            tanggal = pd.to_datetime(tanggal)

            open_val = row['Open'] if not isinstance(row['Open'], pd.Series) else row['Open'].iloc[0]
            high_val = row['High'] if not isinstance(row['High'], pd.Series) else row['High'].iloc[0]
            low_val = row['Low'] if not isinstance(row['Low'], pd.Series) else row['Low'].iloc[0]
            close_val = row['Close'] if not isinstance(row['Close'], pd.Series) else row['Close'].iloc[0]
            volume_val = row['Volume'] if not isinstance(row['Volume'], pd.Series) else row['Volume'].iloc[0]

            data_json.append({
                "Date": tanggal.strftime('%Y-%m-%d'),
                "Open": float(open_val) if pd.notna(open_val) else None,
                "High": float(high_val) if pd.notna(high_val) else None,
                "Low": float(low_val) if pd.notna(low_val) else None,
                "Close": float(close_val) if pd.notna(close_val) else None,
                "Volume": int(volume_val) if pd.notna(volume_val) else None,
                "Name": ticker
            })

        save_stock_data_to_db(ticker, data_json)

    except Exception as e:
        print(f"Gagal mengambil atau memproses {ticker}: {e}")

for ticker in tickers:
    print(f"Mengambil data historis {ticker} dari yfinance...")
    fetch_and_store(ticker)
    time.sleep(10)  # jeda antar request
