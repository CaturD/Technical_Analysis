import argparse
import pandas as pd

from modules.database import get_data_from_db
from modules.best_indicator import get_best_indicator

DEFAULT_PARAMS = {
    'ma5': 5,
    'ma10': 10,
    'ma20': 20,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'so_k': 14,
    'so_d': 3,
    'volume_ma': 20,
    'tenkan': 9,
    'kijun': 26,
    'senkou_b': 52,
    'shift': 26
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cari indikator tunggal terbaik untuk suatu saham"
    )
    parser.add_argument("ticker", help="Kode saham, contoh: BBRI.JK")
    parser.add_argument("--interval", default="1 day", help="Interval data")
    parser.add_argument("--start", help="Tanggal mulai YYYY-MM-DD")
    parser.add_argument("--end", help="Tanggal akhir YYYY-MM-DD")
    parser.add_argument("--money", type=float, default=1_000_000, help="Modal awal")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = get_data_from_db(args.ticker, args.interval)
    if df.empty:
        print("Data tidak ditemukan.")
        return

    if args.start:
        df = df[df.index >= pd.to_datetime(args.start)]
    if args.end:
        df = df[df.index <= pd.to_datetime(args.end)]

    best, result_df = get_best_indicator(
        args.ticker, df, DEFAULT_PARAMS, args.interval, args.money
    )

    if result_df.empty:
        print("Evaluasi gagal.")
        return

    print(result_df)
    if best:
        metric = 'Keuntungan (%)' if 'Keuntungan (%)' in result_df.columns else 'Winrate'
        print(
            f"Indikator terbaik: {best['Indikator']} - {metric} {best.get(metric)}"
        )
    else:
        print("Tidak ada hasil terbaik yang dapat ditentukan.")


if __name__ == "__main__":
    main()