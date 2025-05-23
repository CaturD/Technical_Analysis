import mysql.connector
import json
import pandas as pd
import streamlit as st

def save_accuracy_evaluation_to_db(
    ticker,
    interval,
    strategy,
    indicators_dict,
    params_dict,
    accuracy_value,
    db_config={"host": "localhost", "user": "root", "password": "", "database": "indonesia_stock"}
):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Buat tabel jika belum ada
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_accuracy_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(20),
                data_interval VARCHAR(20),
                strategy VARCHAR(50),
                indicators TEXT,
                parameters JSON,
                accuracy FLOAT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        indicators_enabled = ', '.join([k for k, v in indicators_dict.items() if v])
        params_json = json.dumps(params_dict)

    #     # Cek apakah data sudah ada (berdasarkan kombinasi unik)
    #     check_query = """
    #         SELECT COUNT(*) FROM strategy_accuracy_log
    #         WHERE ticker = %s AND data_interval = %s AND strategy = %s AND indicators = %s
    #     """
    #     cursor.execute(check_query, (ticker, interval, strategy, indicators_enabled))
    #     count = cursor.fetchone()[0]

    #     # check_query = """
    #     # SELECT COUNT(*) FROM strategy_accuracy_log
    #     # WHERE ticker = %s AND data_interval = %s AND strategy = %s AND indicators = %s AND parameters = %s
    #     # """
    #     # cursor.execute(check_query, (ticker, interval, strategy, indicators_enabled, params_json))
    #     # if cursor.fetchone()[0] > 0:
    #     #     print("Data strategi ini sudah ada.")
    #     #     return

    #     if count == 0:
    #         insert_query = """
    #             INSERT INTO strategy_accuracy_log
    #             (ticker, data_interval, strategy, indicators, parameters, accuracy)
    #             VALUES (%s, %s, %s, %s, %s, %s)
    #         """
    #         values = (ticker, interval, strategy, indicators_enabled, params_json, accuracy_value)
    #         cursor.execute(insert_query, values)
    #         conn.commit()
    #         print(f"Akurasi strategi untuk {ticker} berhasil disimpan ke database.")
    #     else:
    #         print(f"Data akurasi untuk {ticker} dan strategi yang sama sudah ada. Tidak disimpan ulang.")

    # except Exception as e:
    #     print(f"Gagal menyimpan akurasi ke database: {e}")

    # finally:
    #     if conn.is_connected():
    #         cursor.close()
    #         conn.close()

    # Cek apakah data sudah ada (berdasarkan kombinasi unik)
        check_query = """
            SELECT COUNT(*) FROM strategy_accuracy_log
            WHERE ticker = %s AND data_interval = %s AND strategy = %s AND indicators = %s AND parameters = %s
        """
        cursor.execute(check_query, (ticker, interval, strategy, indicators_enabled, params_json))
        count = cursor.fetchone()[0]

        if count == 0:
            insert_query = """
                INSERT INTO strategy_accuracy_log
                (ticker, data_interval, strategy, indicators, parameters, accuracy)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (ticker, interval, strategy, indicators_enabled, params_json, accuracy_value)
            cursor.execute(insert_query, values)
            conn.commit()
            print(f"Akurasi strategi untuk {ticker} berhasil disimpan ke database.")
        else:
            print(f"Data akurasi untuk {ticker} dan strategi yang sama sudah ada. Tidak disimpan ulang.")

    except Exception as e:
        print(f"Gagal menyimpan akurasi ke database: {e}")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def evaluate_strategy(ticker, df, indicators_dict, params_dict, interval, money, strategy_name="Final Signal"):
    from modules.indicators import compute_indicators
    from modules.analysis import compute_final_signal
    from modules.backtesting import apply_strategy, run_backtesting_profit

    df_eval = compute_indicators(df.copy(), indicators_dict, params_dict)
    df_eval['Final_Signal'] = compute_final_signal(df_eval, indicators_dict)
    signal_series = apply_strategy(df_eval, strategy_name)

    return run_backtesting_profit(df_eval, money, signal_series, key_prefix=f"{ticker}_{strategy_name}")

from itertools import combinations

def evaluate_indicator_combinations(ticker, df, params, interval, money=1_000_000):
    from modules.indicators import compute_indicators
    from modules.analysis import compute_final_signal
    from modules.backtesting import apply_strategy, run_backtesting_profit

    indikator_list = ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']
    results = []

    for r in [2, 3]:
        for combo in combinations(indikator_list, r):
            combo_dict = {key: key in combo for key in indikator_list}
            df_eval = compute_indicators(df.copy(), combo_dict, params)
            df_eval['Final_Signal'] = compute_final_signal(df_eval, combo_dict)
            signal_series = apply_strategy(df_eval, "Final Signal")
            try:
                _, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
                    df_eval, money, signal_series, key_prefix=f"{ticker}_{'_'.join(combo)}"
                )
                results.append({
                    'Kombinasi': ', '.join(combo),
                    'Akurasi': round(accuracy * 100, 2),
                    'Keuntungan (Rp)': round(gain),
                    'Keuntungan (%)': round(gain_pct, 2)
                })
            except:
                continue

    return pd.DataFrame(results).sort_values(by='Keuntungan (%)', ascending=False)

def get_all_accuracy_logs():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        query = """
            SELECT ticker, data_interval, strategy, indicators, accuracy, timestamp
            FROM strategy_accuracy_log
            ORDER BY accuracy DESC
        """
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data akurasi: {e}")
        return pd.DataFrame()
    finally:
        if conn.is_connected():
            conn.close()
