from tvDatafeed import TvDatafeed, Interval
import pandas as pd

# Inisialisasi tvDatafeed (tanpa login)
tv = TvDatafeed()  # kamu bisa juga login dengan TvDatafeed(username, password)

# Daftar saham dan konfigurasi
tickers = [
    ("BBCA", "IDX"),
    ("BMRI", "IDX"),
    ("BBRI", "IDX"),
    ("TLKM", "IDX"),
    ("ASII", "IDX")
]
interval = Interval.in_daily  # bisa diganti ke in_1_minute, in_weekly, etc
jumlah_data = 100  # jumlah bar (hari, menit, dsb)

# Fungsi untuk menyimpan ke file atau proses lainnya
def save_to_csv(symbol, df):
    filename = f"data_{symbol}.csv"
    df.to_csv(filename)
    print(f"Data {symbol} berhasil disimpan ke {filename}")

# Proses scraping
for symbol, exchange in tickers:
    print(f"Mengambil data {symbol} dari TradingView...")
    try:
        data = tv.get_hist(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            n_bars=jumlah_data
        )
        if not data.empty:
            print(data.head())
            save_to_csv(symbol, data)
        else:
            print(f"Data kosong untuk {symbol}")
    except Exception as e:
        print(f"Gagal mengambil {symbol}: {e}")
