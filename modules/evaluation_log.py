import mysql.connector
import json
import pandas as pd
import streamlit as st
from itertools import combinations
from modules.indicators import compute_indicators
from modules.analysis import compute_final_signal
from modules.custom_strategies import apply_custom_strategy
from modules.backtesting import run_backtesting_profit


def save_winrate_evaluation_to_db(ticker, interval, strategy, indicators_dict, params_dict, winrate_value, db_config=None):
    if db_config is None:
        db_config = {"host": "localhost", "user": "root", "password": "", "database": "indonesia_stock"}

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_winrate_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(20),
                data_interval VARCHAR(20),
                strategy VARCHAR(50),
                indicators TEXT,
                parameters JSON,
                winrate FLOAT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        indicators_used = ', '.join([k for k, v in indicators_dict.items() if v])
        params_json = json.dumps(params_dict)

        cursor.execute("""
            SELECT COUNT(*) FROM strategy_winrate_log
            WHERE ticker = %s AND data_interval = %s AND strategy = %s AND indicators = %s AND parameters = %s
        """, (ticker, interval, strategy, indicators_used, params_json))

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO strategy_winrate_log
                (ticker, data_interval, strategy, indicators, parameters, winrate)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (ticker, interval, strategy, indicators_used, params_json, winrate_value))
            conn.commit()
            print("Data win rate disimpan.")
        else:
            print("Strategi yang sama sudah disimpan sebelumnya.")
    except Exception as e:
        print(f"Gagal menyimpan ke database: {e}")
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

def evaluate_strategy(ticker, df, indicators_dict, params_dict, interval, money, strategy_name="Final Signal"):
    df_eval = compute_indicators(df.copy(), indicators_dict, params_dict)
    df_eval['Final_Signal'] = compute_final_signal(df_eval, indicators_dict)
    signal_series = apply_custom_strategy(df_eval, strategy_name)
    return run_backtesting_profit(df_eval, money, signal_series, key_prefix=f"{ticker}_{strategy_name}")

# Evaluasi kombinasi indikator (2–5 indikator aktif)
def evaluate_indicator_combinations(ticker, df, params, interval, money=1_000_000):
    indikator_list = ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']
    results = []

    for r in [2, 3, 4, 5]:
        for combo in combinations(indikator_list, r):
            combo_dict = {key: key in combo for key in indikator_list}
            try:
                df_eval = compute_indicators(df.copy(), combo_dict, params)
                df_eval['Final_Signal'] = compute_final_signal(df_eval, combo_dict)
                signal_series = apply_custom_strategy(df_eval, "Final Signal")
                if signal_series.nunique() <= 1:
                    continue
                _, final_value, gain, gain_pct, winrate = run_backtesting_profit(
                    df_eval, money, signal_series, key_prefix=f"{ticker}_{'_'.join(combo)}"
                )
                results.append({
                    'Kombinasi': ', '.join(combo),
                    'Win Rate': round(winrate * 100, 2),
                    'Keuntungan (Rp)': round(gain, 2),
                    'Keuntungan (%)': round(gain_pct, 2)
                })
            except Exception as e:
                results.append({
                    'Kombinasi': ', '.join(combo),
                    'Win Rate': None,
                    'Keuntungan (Rp)': None,
                    'Keuntungan (%)': None,
                    'Error': str(e)
                })

    df_result = pd.DataFrame(results)
    for col in ['Kombinasi', 'Win Rate', 'Keuntungan (Rp)', 'Keuntungan (%)']:
        if col not in df_result.columns:
            df_result[col] = None
    return df_result.sort_values(by='Keuntungan (Rp)', ascending=False).reset_index(drop=True)

def get_all_winrate_logs():
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        query = """
            SELECT ticker, data_interval, strategy, indicators, winrate, timestamp
            FROM strategy_winrate_log
            ORDER BY winrate DESC
        """
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Gagal mengambil log win rate: {e}")
        return pd.DataFrame()
    finally:
        if conn.is_connected(): conn.close()

def get_top_strategies_by_profit(limit=10):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        from modules.backtesting import _ensure_backtesting_table
        _ensure_backtesting_table(cursor)
        conn.commit()
        cursor.close()
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM data_backtesting LIKE 'start_date'")
        has_start = cursor.fetchone() is not None
        cursor.execute("SHOW COLUMNS FROM data_backtesting LIKE 'end_date'")
        has_end = cursor.fetchone() is not None
        cursor.close()
        columns = ["ticker", "profit", "profit_percentage", "winrate"]
        if has_start:
            columns.append("start_date")
        if has_end:
            columns.append("end_date")
        columns.append("timestamp")
        query = f"SELECT {', '.join(columns)} FROM data_backtesting ORDER BY profit DESC"
        df = pd.read_sql(query, conn)
        df = df.sort_values(by="profit", ascending=False).drop_duplicates("ticker")
        return df.head(limit)
    
    except Exception as e:
        print(f"Gagal mengambil data strategi berdasarkan profit: {e}")
        return pd.DataFrame()
    finally:
        if conn.is_connected():
            conn.close()
