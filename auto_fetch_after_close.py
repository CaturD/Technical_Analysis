import yfinance as yf
import json
import time
import logging
from datetime import datetime
from modules.database import save_stock_data_to_db

LOG_FILE = "log_fetch_saham.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def fetch_after_market_close(ticker, interval='1d'):
    now = datetime.now()
    closing_time = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if now < closing_time:
        wait_sec = (closing_time - now).seconds
        logging.info(f"Menunggu sampai jam pasar tutup selama {wait_sec} detik...")
        time.sleep(wait_sec + 60)

    if interval in ['1m', '2m', '5m', '15m', '30m', '60m']:
        period = '7d'
    else:
        period = '5y'

    logging.info(f"Mengambil data {interval} untuk {ticker}...")
    df = yf.download(ticker, interval=interval, period=period, progress=False)

    if df.empty:
        logging.warning(f"Data kosong untuk {ticker}.")
        return

    df = df.reset_index()
    data_json = []
    for _, row in df.iterrows():
        date_val = row.get('Datetime') or row.get('Date')
        data_json.append({
            "Date": str(date_val),
            "Open": row['Open'],
            "High": row['High'],
            "Low": row['Low'],
            "Close": row['Close'],
            "Volume": row['Volume'],
            "Name": ticker
        })

    save_stock_data_to_db(ticker, data_json, interval=interval)

tickers = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "AALI.JK", "TLKM.JK"]
intervals = ["1d", "1wk", "1mo"]

for ticker in tickers:
    for interval in intervals:
        try:
            fetch_after_market_close(ticker, interval=interval)
        except Exception as e:
            logging.exception(f"Gagal mengambil data {ticker} ({interval}): {e}")
