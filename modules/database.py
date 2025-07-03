import mysql.connector
import pandas as pd
import json
import streamlit as st

def get_data_from_db(ticker, interval='1 day'):
    table_map = {
        '1 minute': 'stock_data_minute',
        '5 minutes': 'stock_data_minute',
        '15 minutes': 'stock_data_minute',
        '30 minutes': 'stock_data_minute',
        '45 minutes': 'stock_data_minute',
        '1 hour': 'stock_data_hourly',
        '2 hours': 'stock_data_hourly',
        '3 hours': 'stock_data_hourly',
        '4 hours': 'stock_data_hourly',
        '1 day': 'stock_data',
        '1 week': 'stock_data_weekly',
        '1 month': 'stock_data_monthly',
        '3 months': 'stock_data_3mo',
        '6 months': 'stock_data_6mo',
        '12 months': 'stock_data_12mo'

        # '1 minute': 'stock_data_1m', '2 minutes': 'stock_data_2m', '3 minutes': 'stock_data_3m',
        # '5 minutes': 'stock_data_5m', '10 minutes': 'stock_data_10m', '15 minutes': 'stock_data_15m',
        # '30 minutes': 'stock_data_30m', '45 minutes': 'stock_data_45m', '1 hour': 'stock_data_1h',
        # '2 hours': 'stock_data_2h', '3 hours': 'stock_data_3h', '4 hours': 'stock_data_4h',
        # '1 day': 'stock_data', '1 week': 'stock_data_weekly', '1 month': 'stock_data_monthly',
        # '3 months': 'stock_data_3mo', '6 months': 'stock_data_6mo', '12 months': 'stock_data_12mo'
    }
    table_name = table_map.get(interval, 'stock_data')

    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT data FROM {table_name} WHERE ticker = %s", (ticker,))
        result = cursor.fetchone()
        if result:
            df = pd.DataFrame(json.loads(result["data"]))
            # Coba kenali dan gunakan kolom waktu yang valid
            time_column = None
            for col in ['Date', 'Datetime', 'date', 'datetime', 'timestamp']:
                if col in df.columns:
                    time_column = col
                    break
            if time_column is None:
                return pd.DataFrame()
            # Konversi kolom waktu dan jadikan index
            df[time_column] = pd.to_datetime(df[time_column])
            df.set_index(time_column, inplace=True)
            df.sort_index(inplace=True)
            return df
        else:
            return pd.DataFrame()
    except mysql.connector.Error:
        return pd.DataFrame()
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

def get_ticker_list():
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM stock_data")
        return [row[0] for row in cursor.fetchall()]
    except:
        return []
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

def save_stock_data_to_db(ticker, data_json_list, interval='1d'):
    table_map = {
        '1 minute': 'stock_data_minute',
        '5 minutes': 'stock_data_minute',
        '15 minutes': 'stock_data_minute',
        '30 minutes': 'stock_data_minute',
        '45 minutes': 'stock_data_minute',
        '1 hour': 'stock_data_hourly',
        '2 hours': 'stock_data_hourly',
        '3 hours': 'stock_data_hourly',
        '4 hours': 'stock_data_hourly',
        '1 day': 'stock_data',
        '1 week': 'stock_data_weekly',
        '1 month': 'stock_data_monthly',
        '3 months': 'stock_data_3mo',
        '6 months': 'stock_data_6mo',
        '12 months': 'stock_data_12mo'
        # '1m': 'stock_data_1m', '2m': 'stock_data_2m', '3m': 'stock_data_3m', '5m': 'stock_data_5m',
        # '10m': 'stock_data_10m', '15m': 'stock_data_15m', '30m': 'stock_data_30m', '45m': 'stock_data_45m',
        # '60m': 'stock_data_1h', '1h': 'stock_data_1h', '1d': 'stock_data', '1wk': 'stock_data_weekly',
        # '1mo': 'stock_data_monthly'
    }
    table_name = table_map.get(interval, 'stock_data')
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ticker VARCHAR(10) PRIMARY KEY,
                data JSON
            )
        """)
        json_data = json.dumps(data_json_list)
        cursor.execute(f"""
            INSERT INTO {table_name} (ticker, data)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE data = VALUES(data)
        """, (ticker, json_data))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Gagal menyimpan data: {err}")
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

from sqlalchemy import create_engine

# Tambahkan ini di akhir database.py
engine = create_engine('mysql+mysqlconnector://root:@localhost/indonesia_stock')
