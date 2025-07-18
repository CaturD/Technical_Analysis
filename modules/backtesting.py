import pandas as pd
import streamlit as st
import mysql.connector
from sqlalchemy import create_engine, text
import json
import logging
from sklearn.metrics import accuracy_score
import plotly.graph_objects as go
from modules.custom_strategies import apply_custom_strategy

engine = create_engine('mysql+mysqlconnector://root:@localhost/indonesia_stock')

def _ensure_backtesting_table(cursor):
    """Create table and new columns if they don't exist."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS data_backtesting (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticker VARCHAR(10),
            money DOUBLE,
            final_money DOUBLE,
            profit DOUBLE,
            profit_percentage DOUBLE,
            winrate DOUBLE,
            start_date DATE,
            end_date DATE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("SHOW COLUMNS FROM data_backtesting LIKE 'start_date'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE data_backtesting ADD COLUMN start_date DATE")
    cursor.execute("SHOW COLUMNS FROM data_backtesting LIKE 'end_date'")
    if cursor.fetchone() is None:
        cursor.execute("ALTER TABLE data_backtesting ADD COLUMN end_date DATE")
    try:
        cursor.connection.commit()
    except Exception:
        pass

def fetch_backtesting_data(ticker, start_date, end_date):
    query = text("""
        SELECT hasil_analisis FROM analisis_indikator
        WHERE ticker = :ticker
        ORDER BY id DESC
        LIMIT 1
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'ticker': ticker}).fetchone()
            if not result:
                logging.warning("Tidak ada data ditemukan untuk ticker.")
                return pd.DataFrame()

            data = json.loads(result[0])
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))]
            return df
    except Exception as e:
        logging.error(f"Gagal mengambil data backtesting: {e}")
        return pd.DataFrame()


def run_backtesting_profit(df, money, signal_series, key_prefix="default"):
    st.subheader("Evaluasi Indikator Individu dan Kombinasi")
    if df.empty or signal_series.empty:
        st.warning("Data atau sinyal kosong.")
        return pd.DataFrame(), money, 0, 0, 0

    cash = money
    stock = 0
    history = []
    predictions = []
    actuals = []

    df['Future_Close'] = df['Close'].shift(-1)

    for date in df.index[:-1]:
        signal = signal_series.loc[date]
        if isinstance(signal, pd.Series):
            signal = signal.iloc[0]

        price = df.loc[date, 'Close']
        future_price = df.loc[date, 'Future_Close']

        if isinstance(price, pd.Series):
            price = price.iloc[0]
        if isinstance(future_price, pd.Series):
            future_price = future_price.iloc[0]

        if pd.isna(price) or pd.isna(future_price):
            continue

        actual_trend = 'Buy' if future_price > price else 'Sell'
        predictions.append(signal)
        actuals.append(actual_trend)

        if signal == 'Buy' and cash >= price:
            qty = cash // price
            stock += qty
            cash -= qty * price
        elif signal == 'Sell' and stock > 0:
            cash += stock * price
            stock = 0

        value = cash + stock * price
        profit = value - money
        history.append([date.strftime("%Y-%m-%d"), signal, f"{value:,.0f}", f"{profit:,.0f}"])

    final_price = df['Close'].iloc[-1]
    final_value = cash + stock * final_price
    gain = final_value - money
    gain_pct = (gain / money) * 100

    st.write(f"Nilai akhir portofolio: **Rp{final_value:,.0f}**")
    st.write(f"Keuntungan: **Rp{gain:,.0f} ({gain_pct:.2f}%)**")

    df_result = pd.DataFrame(history, columns=['Tanggal', 'Sinyal', 'Nilai Portofolio', 'Profit'])
    st.dataframe(df_result, use_container_width=True)

    winrate = accuracy_score(actuals, predictions)
    st.info(f"Win Rate sinyal: **{winrate * 100:.2f}%**")

    return df_result, final_value, gain, gain_pct, winrate

# Simpan hasil backtesting ke database
def save_backtesting_to_db(ticker, money, final_value, gain, gain_pct, winrate,
                           start_date, end_date):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        cursor = conn.cursor()
        _ensure_backtesting_table(cursor)
        cursor.execute("""
            SELECT COUNT(*) FROM data_backtesting
            WHERE ticker = %s AND money = %s AND final_money = %s AND
                  profit_percentage = %s AND start_date = %s AND end_date = %s
        """, (ticker, money, final_value, gain_pct, start_date, end_date))
        if cursor.fetchone()[0] > 0:
            st.warning("Hasil backtesting ini sudah pernah disimpan.")
            return
        cursor.execute("""
            INSERT INTO data_backtesting
            (ticker, money, final_money, profit, profit_percentage, winrate,
             start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (ticker, money, final_value, gain, gain_pct, winrate,
                start_date, end_date))
        conn.commit()
        st.success("Hasil backtesting berhasil disimpan ke database.")
    except mysql.connector.Error as err:
        st.error(f"Gagal menyimpan hasil backtesting: {err}")
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# Tampilkan grafik riwayat winrate
def plot_winrate_history(ticker):
    try:
        conn = mysql.connector.connect(host="localhost", user="root", password="", database="indonesia_stock")
        df = pd.read_sql(f"""
            SELECT timestamp, winrate FROM data_backtesting
            WHERE ticker = '{ticker}' AND winrate IS NOT NULL ORDER BY timestamp
        """, conn)
        conn.close()
        if df.empty:
            st.warning("Belum ada data win rate disimpan untuk ticker ini.")
            return
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['winrate'], mode='lines+markers', name='Win Rate'))
        fig.update_layout(title=f"Riwayat Win Rate {ticker}", xaxis_title='Tanggal', yaxis_title='Win Rate', yaxis_tickformat='.0%')
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal menampilkan grafik win rate: {e}")

def evaluate_signal_pairs(df, signal_series):
    """Evaluate buy/sell pairs and return detail DataFrame and total profit."""
    pairs = []
    holding = False
    buy_price = 0
    buy_date = None

    # Pastikan index tersortir
    df = df.sort_index()
    signal_series = signal_series.sort_index()

    for date in df.index:
        signal = signal_series.loc[date]
        if isinstance(signal, pd.Series):
            signal = signal.iloc[0]

        price = df.loc[date, 'Close']
        if isinstance(price, pd.Series):
            price = price.iloc[0]

        if signal == 'Buy' and not holding:
            holding = True
            buy_price = price
            buy_date = date

        elif signal == 'Sell' and holding:
            sell_price = price
            sell_date = date
            profit = sell_price - buy_price
            profit_pct = ((sell_price - buy_price) / buy_price) * 100
            hold_days = (sell_date - buy_date).days
            pairs.append({
                'Buy Date': buy_date.strftime('%Y-%m-%d'),
                'Buy Price': round(buy_price, 2),
                'Sell Date': sell_date.strftime('%Y-%m-%d'),
                'Sell Price': round(sell_price, 2),
                'Profit': round(profit, 2),
                'Profit (%)': round(profit_pct, 4),
                'Hold Days': hold_days,
                'Trend': 'Uptrend' if profit > 0 else 'Downtrend'
            })
            holding = False  # Ini penting: hentikan posisi setelah Sell

    df_pairs = pd.DataFrame(pairs)
    if df_pairs.empty:
        return df_pairs, 0.0

    df_pairs = df_pairs.sort_values(by='Profit', ascending=False).reset_index(drop=True)
    total_profit_pct = df_pairs['Profit (%)'].sum()
    return df_pairs, total_profit_pct

def experiment_buy_sell_combinations(df, signal_series):
    """Generate profit results pairing each Buy with multiple subsequent Sells."""
    df = df.sort_index()
    signal_series = signal_series.sort_index()

    buy_dates = []
    sell_dates = []

    for d in df.index:
        val = signal_series.loc[d]
        if isinstance(val, pd.Series):
            if (val == 'Buy').any():
                buy_dates.append(d)
            if (val == 'Sell').any():
                sell_dates.append(d)
        else:
            if val == 'Buy':
                buy_dates.append(d)
            if val == 'Sell':
                sell_dates.append(d)

    combos = []
    for i, buy_date in enumerate(buy_dates, start=1):
        buy_price = df.loc[buy_date, 'Close']
        if isinstance(buy_price, pd.Series):
            buy_price = buy_price.iloc[0]

        for j, sell_date in enumerate([s for s in sell_dates if s > buy_date], start=1):
            sell_price = df.loc[sell_date, 'Close']
            if isinstance(sell_price, pd.Series):
                sell_price = sell_price.iloc[0]

            profit = sell_price - buy_price
            profit_pct = ((sell_price - buy_price) / buy_price) * 100
            hold_days = (sell_date - buy_date).days

            combos.append({
                'Buy': i,
                'Sell After Buy': j,
                'Buy Date': buy_date.strftime('%Y-%m-%d %H:%M'),
                'Sell Date': sell_date.strftime('%Y-%m-%d %H:%M'),
                'Buy Price': round(buy_price, 2),
                'Sell Price': round(sell_price, 2),
                'Hold Days': hold_days,
                'Profit': round(profit, 2),
                'Profit (%)': round(profit_pct, 4),
                'Trend': 'Uptrend' if profit > 0 else 'Downtrend',
            })

    return pd.DataFrame(combos)

# Evaluasi winrate tiap indikator satu per satu
def evaluate_individual_indicators(ticker, df, params, interval, money):
    from modules.indicators import compute_indicators
    from modules.analysis import compute_final_signal

    results, indikator_list = [], ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']
    for ind in indikator_list:
        active_indicators = {key: (key == ind) for key in indikator_list}
        df_ind = compute_indicators(df.copy(), active_indicators, params)
        df_ind['Final_Signal'] = compute_final_signal(df_ind, active_indicators)
        signal_series = apply_custom_strategy(df_ind, "Final Signal")
        try:
            _, final_value, gain, gain_pct, winrate = run_backtesting_profit(df_ind, money, signal_series, key_prefix=f"{ticker}_{ind}_auto")
            results.append({
                'Indikator': ind,
                'Win Rate': round(winrate * 100, 2),
                'Keuntungan (Rp)': round(gain, 2),
                'Keuntungan (%)': round(gain_pct, 2)
            })
        except Exception as e:
            results.append({'Indikator': ind, 'Win Rate': None, 'Keuntungan (Rp)': None, 'Keuntungan (%)': None, 'Error': str(e)})
    return pd.DataFrame(results).sort_values(by='Keuntungan (%)', ascending=False).reset_index(drop=True)
