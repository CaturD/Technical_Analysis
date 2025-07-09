# import mysql.connector
# from datetime import datetime

# def save_multi_ticker_evaluation_to_db(
#     tickers,
#     interval,
#     indicators_dict,
#     strategy,
#     start_date,
#     end_date,
#     total_winrate,
#     total_profit,
#     total_money,
#     final_money,
#     db_config={"host": "localhost", "user": "root", "password": "", "database": "indonesia_stock"}
# ):
#     try:
#         conn = mysql.connector.connect(**db_config)
#         cursor = conn.cursor()

#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS multi_ticker_evaluation (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 tickers_combination TEXT,
#                 interval VARCHAR(20),
#                 indicators TEXT,
#                 strategy VARCHAR(50),
#                 start_date DATE,
#                 end_date DATE,
#                 total_winrate FLOAT,
#                 total_profit FLOAT,
#                 total_money FLOAT,
#                 final_money FLOAT,
#                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#             )
#         """)

#         tickers_combination = ', '.join(sorted(tickers))
#         indicators_used = ', '.join([key for key, val in indicators_dict.items() if val])

#         cursor.execute("""
#             SELECT COUNT(*) FROM multi_ticker_evaluation
#             WHERE tickers_combination = %s AND interval = %s AND strategy = %s
#               AND indicators = %s AND start_date = %s AND end_date = %s
#         """, (
#             tickers_combination, interval, strategy,
#             indicators_used, start_date, end_date
#         ))

#         if cursor.fetchone()[0] > 0:
#             return False, "Hasil kombinasi ini sudah tersimpan sebelumnya."

#         cursor.execute("""
#             INSERT INTO multi_ticker_evaluation
#             (tickers_combination, interval, indicators, strategy, start_date, end_date,
#              total_winrate, total_profit, total_money, final_money)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """, (
#             tickers_combination, interval, indicators_used, strategy,
#             start_date, end_date,
#             total_winrate, total_profit, total_money, final_money
#         ))
#         conn.commit()
#         return True, "Berhasil disimpan ke database."

#     except Exception as e:
#         return False, f"Kesalahan: {e}"

#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()

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

        return True, "✅ Data evaluasi gabungan berhasil disimpan ke database."
    except Exception as e:
        return False, f"❌ Gagal menyimpan evaluasi gabungan: {e}"

