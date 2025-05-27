import mysql.connector
from datetime import datetime

def save_multi_ticker_evaluation_to_db(
    tickers,
    interval,
    indicators_dict,
    strategy,
    start_date,
    end_date,
    total_accuracy,
    total_profit,
    total_money,
    final_money,
    db_config={"host": "localhost", "user": "root", "password": "", "database": "indonesia_stock"}
):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS multi_ticker_evaluation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tickers_combination TEXT,
                interval VARCHAR(20),
                indicators TEXT,
                strategy VARCHAR(50),
                start_date DATE,
                end_date DATE,
                total_accuracy FLOAT,
                total_profit FLOAT,
                total_money FLOAT,
                final_money FLOAT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        tickers_combination = ', '.join(sorted(tickers))
        indicators_used = ', '.join([key for key, val in indicators_dict.items() if val])

        cursor.execute("""
            SELECT COUNT(*) FROM multi_ticker_evaluation
            WHERE tickers_combination = %s AND interval = %s AND strategy = %s
              AND indicators = %s AND start_date = %s AND end_date = %s
        """, (
            tickers_combination, interval, strategy,
            indicators_used, start_date, end_date
        ))

        if cursor.fetchone()[0] > 0:
            return False, "Hasil kombinasi ini sudah tersimpan sebelumnya."

        cursor.execute("""
            INSERT INTO multi_ticker_evaluation
            (tickers_combination, interval, indicators, strategy, start_date, end_date,
             total_accuracy, total_profit, total_money, final_money)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            tickers_combination, interval, indicators_used, strategy,
            start_date, end_date,
            total_accuracy, total_profit, total_money, final_money
        ))
        conn.commit()
        return True, "Berhasil disimpan ke database."

    except Exception as e:
        return False, f"Kesalahan: {e}"

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()