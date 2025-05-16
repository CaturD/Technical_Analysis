import mysql.connector
import json

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

        insert_query = """
            INSERT INTO strategy_accuracy_log
            (ticker, data_interval, strategy, indicators, parameters, accuracy)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        indicators_enabled = ', '.join([k for k, v in indicators_dict.items() if v])
        params_json = json.dumps(params_dict)

        values = (
            ticker,
            interval,
            strategy,
            indicators_enabled,
            params_json,
            accuracy_value
        )

        cursor.execute(insert_query, values)
        conn.commit()
        print(f"Akurasi strategi untuk {ticker} berhasil disimpan ke database.")

    except Exception as e:
        print(f"Gagal menyimpan akurasi ke database: {e}")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
