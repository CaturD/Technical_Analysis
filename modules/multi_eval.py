import pandas as pd
from sqlalchemy import create_engine

def save_multi_ticker_evaluation_to_db(
    tickers,
    interval,
    indicators_dict,
    strategy,
    start_date,
    end_date,
    total_winrate,
    total_profit,
    total_money,
    final_money,
    db_url="mysql+mysqlconnector://root:@localhost/indonesia_stock",
    table_name="multi_ticker_evaluation_log"
):
    try:
        df = pd.DataFrame([{
            "tickers": ', '.join(tickers),
            "data_interval": interval,
            "strategy": strategy,
            "start_date": pd.to_datetime(start_date).date(),
            "end_date": pd.to_datetime(end_date).date(),
            "total_winrate": round(total_winrate, 2),
            "total_profit": round(total_profit, 2),
            "total_money": round(total_money, 2),
            "final_money": round(final_money, 2),
        }])

        engine = create_engine(db_url)
        df.to_sql(table_name, con=engine, if_exists="append", index=False)

        return True, "Data evaluasi gabungan berhasil disimpan ke database."
    except Exception as e:
        return False, f"Gagal menyimpan evaluasi gabungan: {e}"

