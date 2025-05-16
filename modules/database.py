import mysql.connector
import pandas as pd
import json
import streamlit as st

def get_data_from_db(ticker, interval='1 day'):
    table_map = {
        '1 minute': 'stock_data_1m',
        '2 minutes': 'stock_data_2m',
        '3 minutes': 'stock_data_3m',
        '5 minutes': 'stock_data_5m',
        '10 minutes': 'stock_data_10m',
        '15 minutes': 'stock_data_15m',
        '30 minutes': 'stock_data_30m',
        '45 minutes': 'stock_data_45m',
        '1 hour': 'stock_data_1h',
        '2 hours': 'stock_data_2h',
        '3 hours': 'stock_data_3h',
        '4 hours': 'stock_data_4h',
        '1 day': 'stock_data',
        '1 week': 'stock_data_weekly',
        '1 month': 'stock_data_monthly',
        '3 months': 'stock_data_3mo',
        '6 months': 'stock_data_6mo',
        '12 months': 'stock_data_12mo'
    }

    table_name = table_map.get(interval, 'stock_data')

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor(dictionary=True)

        query = f"SELECT data FROM {table_name} WHERE ticker = %s"
        cursor.execute(query, (ticker,))
        result = cursor.fetchone()

        if result:
            data_json = json.loads(result["data"])
            df = pd.DataFrame(data_json)

            if 'Date' not in df.columns:
                st.error("Kolom 'Date' tidak ditemukan dalam data.")
                return pd.DataFrame()

            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_cols:
                if col not in df.columns:
                    st.error(f"Kolom '{col}' tidak ditemukan dalam data.")
                    return pd.DataFrame()

            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df

        else:
            st.warning(f"Data untuk ticker {ticker} tidak ditemukan di tabel '{table_name}'.")
            return pd.DataFrame()

    except mysql.connector.Error as err:
        st.error(f"Kesalahan koneksi database: {err}")
        return pd.DataFrame()

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def save_stock_data_to_db(ticker, data_json_list, interval='1d'):
    table_map = {
        '1m': 'stock_data_1m',
        '2m': 'stock_data_2m',
        '3m': 'stock_data_3m',
        '5m': 'stock_data_5m',
        '10m': 'stock_data_10m',
        '15m': 'stock_data_15m',
        '30m': 'stock_data_30m',
        '45m': 'stock_data_45m',
        '60m': 'stock_data_1h',
        '1h': 'stock_data_1h',
        '1d': 'stock_data',
        '1wk': 'stock_data_weekly',
        '1mo': 'stock_data_monthly'
    }
    table_name = table_map.get(interval, 'stock_data')

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor()

        create_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            ticker VARCHAR(10) PRIMARY KEY,
            data JSON
        )
        """
        cursor.execute(create_query)

        insert_query = f"""
        INSERT INTO {table_name} (ticker, data)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE data = VALUES(data)
        """
        json_data = json.dumps(data_json_list)
        cursor.execute(insert_query, (ticker, json_data))
        conn.commit()
        print(f"Data {ticker} berhasil disimpan ke tabel {table_name}")
    except mysql.connector.Error as err:
        print(f"Gagal menyimpan data: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_ticker_list():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor()
        query = "SELECT DISTINCT ticker FROM stock_data"
        cursor.execute(query)
        tickers = [row[0] for row in cursor.fetchall()]
        return tickers
    except mysql.connector.Error as err:
        st.error(f"Kesalahan koneksi database: {err}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Data REALTIME
def get_realtime_data_from_db(ticker):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor(dictionary=True)

        query = "SELECT data FROM stock_data_realtime WHERE ticker = %s"
        cursor.execute(query, (ticker,))
        result = cursor.fetchone()

        if result:
            data_json = json.loads(result["data"])
            df = pd.DataFrame(data_json)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df
        else:
            st.warning(f"Data realtime tidak ditemukan untuk {ticker}.")
            return pd.DataFrame()

    except mysql.connector.Error as err:
        st.error(f"Kesalahan koneksi database realtime: {err}")
        return pd.DataFrame()

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()