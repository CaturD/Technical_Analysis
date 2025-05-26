import pandas as pd
import streamlit as st
import mysql.connector
from sqlalchemy import create_engine, text
from io import BytesIO
import json
import logging
from sklearn.metrics import accuracy_score
import plotly.graph_objects as go


# Setup database engine
engine = create_engine('mysql+mysqlconnector://root:@localhost/indonesia_stock')

def fetch_backtesting_data(ticker, start_date, end_date):
    query = text("""
        SELECT hasil_analisis FROM analisis_indikator
        WHERE ticker = :ticker
        ORDER BY datetime DESC
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'ticker': ticker}).fetchall()
            if not result:
                logging.warning("Tidak ada data ditemukan untuk ticker yang dipilih.")
                return pd.DataFrame()

            data_list = [json.loads(row[0]) for row in result]
            df = pd.DataFrame([entry for sublist in data_list for entry in sublist])
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))]
            return df
    except Exception as e:
        logging.error(f"Gagal mengambil data backtesting: {e}")
        return pd.DataFrame()

# def apply_strategy(df, strategy):
#     if strategy == "Final Signal":
#         return df['Final_Signal']
#     elif strategy == "Buy & Hold":
#         signals = ['Hold'] * len(df)
#         signals[0] = 'Buy'
#         signals[-1] = 'Sell'
#         return pd.Series(signals, index=df.index)
#     elif strategy == "MACD Only" and 'Signal_MACD' in df.columns:
#         return df['Signal_MACD']
#     elif strategy == "MA Crossover" and 'Signal_MA' in df.columns:
#         return df['Signal_MA']
#     elif strategy == "Volume Entry" and 'Signal_Volume' in df.columns:
#         # Treat High Volume as Buy, Low Volume as Sell
#         return df['Signal_Volume'].replace({
#             'High Volume': 'Buy',
#             'Low Volume': 'Sell',
#             'Hold': 'Hold'
#         })
#     else:
#         return pd.Series(['Hold'] * len(df), index=df.index)

# custom_strategies.py

def apply_custom_strategy(df, strategy):
    import pandas as pd

    if strategy == "Final Signal":
        return df['Final_Signal']

    elif strategy == "Buy & Hold":
        signals = ['Hold'] * len(df)
        if len(df) > 1:
            signals[0] = 'Buy'
            signals[-1] = 'Sell'
        return pd.Series(signals, index=df.index)

    # === STRATEGI BERDASARKAN MASING-MASING INDIKATOR ===
    elif strategy == "MA Only":
        return df.get('Signal_MA', pd.Series(['Hold'] * len(df), index=df.index))

    elif strategy == "MACD Only":
        return df.get('Signal_MACD', pd.Series(['Hold'] * len(df), index=df.index))

    elif strategy == "Ichimoku Only":
        return df.get('Signal_Ichimoku', pd.Series(['Hold'] * len(df), index=df.index))

    elif strategy == "SO Only":
        return df.get('Signal_SO', pd.Series(['Hold'] * len(df), index=df.index))

    elif strategy == "Volume Only":
        vol_sig = df.get('Signal_Volume', pd.Series(['Hold'] * len(df), index=df.index))
        return vol_sig.replace({
            'High Volume': 'Buy',
            'Low Volume': 'Sell'
        })

    # === STRATEGI KOMBINASI LOGIKA ===
    elif strategy == "Ichimoku + MA Only":
        result = []
        for i in range(len(df)):
            ich = df.iloc[i].get('Signal_Ichimoku')
            ma = df.iloc[i].get('Signal_MA')
            result.append(ich if ich == ma and ich in ['Buy', 'Sell'] else 'Hold')
        return pd.Series(result, index=df.index)

    elif strategy == "All Agree":
        result = []
        for i in range(len(df)):
            signals = [
                df.iloc[i].get('Signal_MA'),
                df.iloc[i].get('Signal_MACD'),
                df.iloc[i].get('Signal_Ichimoku'),
                df.iloc[i].get('Signal_SO'),
                df.iloc[i].get('Signal_Volume')
            ]
            if all(s == 'Buy' for s in signals):
                result.append('Buy')
            elif all(s == 'Sell' for s in signals):
                result.append('Sell')
            else:
                result.append('Hold')
        return pd.Series(result, index=df.index)

    elif strategy == "3 of 5 Majority":
        result = []
        for i in range(len(df)):
            signals = [
                df.iloc[i].get('Signal_MA'),
                df.iloc[i].get('Signal_MACD'),
                df.iloc[i].get('Signal_Ichimoku'),
                df.iloc[i].get('Signal_SO'),
                df.iloc[i].get('Signal_Volume')
            ]
            buy_count = signals.count('Buy')
            sell_count = signals.count('Sell')
            result.append('Buy' if buy_count >= 3 else 'Sell' if sell_count >= 3 else 'Hold')
        return pd.Series(result, index=df.index)

    elif strategy == "MACD + Volume Confirm":
        result = []
        for i in range(len(df)):
            macd = df.iloc[i].get('Signal_MACD')
            vol = df.iloc[i].get('Signal_Volume')
            if macd == 'Buy' and vol == 'High Volume':
                result.append('Buy')
            elif macd == 'Sell' and vol == 'Low Volume':
                result.append('Sell')
            else:
                result.append('Hold')
        return pd.Series(result, index=df.index)

    elif strategy == "Ichimoku + MA Trend":
        result = []
        for i in range(len(df)):
            ich = df.iloc[i].get('Signal_Ichimoku')
            ma20 = df.iloc[i].get('MA20')
            ma50 = df.iloc[i].get('MA50')
            if ich == 'Buy' and ma20 > ma50:
                result.append('Buy')
            elif ich == 'Sell' and ma20 < ma50:
                result.append('Sell')
            else:
                result.append('Hold')
        return pd.Series(result, index=df.index)

    elif strategy == "SO + MACD":
        result = []
        for i in range(len(df)):
            so = df.iloc[i].get('Signal_SO')
            macd = df.iloc[i].get('Signal_MACD')
            if so == 'Buy' and macd == 'Buy':
                result.append('Buy')
            elif so == 'Sell' and macd == 'Sell':
                result.append('Sell')
            else:
                result.append('Hold')
        return pd.Series(result, index=df.index)

    else:
        return pd.Series(['Hold'] * len(df), index=df.index)


def run_backtesting_analysis(df, money, key_prefix="default"):
    st.subheader("Backtesting Analisis")
    if 'Final_Signal' not in df.columns:
        st.warning("Data tidak memiliki kolom Final_Signal.")
        return

    signal_counts = df['Final_Signal'].value_counts().to_frame().reset_index()
    signal_counts.columns = ['Sinyal', 'Jumlah']
    st.dataframe(signal_counts, use_container_width=True)

    # Ekspor ke Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        signal_counts.to_excel(writer, index=False, sheet_name='Sinyal')

    st.download_button(
        label="⬇ Unduh Rekap Sinyal (Excel)",
        data=buffer.getvalue(),
        file_name=f"rekap_sinyal_{key_prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_button_{key_prefix}_rekap"
    )

def run_backtesting_profit(df, money, signal_series, key_prefix="default"):
    st.subheader("Simulasi Keuntungan Trading Per Indikator")
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

        close_value = df.loc[date, 'Close']
        future_value = df.loc[date, 'Future_Close']
        price = float(close_value) if not isinstance(close_value, pd.Series) else float(close_value.iloc[0])
        future_price = float(future_value) if not isinstance(future_value, pd.Series) else float(future_value.iloc[0])

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

    # Ekspor
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name='Backtesting')
    st.download_button(
        label="⬇ Unduh Hasil Backtesting (Excel)",
        data=buffer.getvalue(),
        file_name=f"hasil_backtesting_{key_prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_button_{key_prefix}_profit"
    )

    # Akurasi
    accuracy = accuracy_score(actuals, predictions)
    st.info(f"Akurasi sinyal: **{accuracy * 100:.2f}%**")

    return df_result, final_value, gain, gain_pct, accuracy

def save_backtesting_to_db(ticker, money, final_value, gain, gain_pct, accuracy):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_backtesting (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                money DOUBLE,
                final_money DOUBLE,
                profit DOUBLE,
                profit_percentage DOUBLE,
                accuracy DOUBLE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        check_query = """
        SELECT COUNT(*) FROM data_backtesting
        WHERE ticker = %s AND money = %s AND final_money = %s AND profit_percentage = %s
        """
        cursor.execute(check_query, (ticker, money, final_value, gain_pct))
        if cursor.fetchone()[0] > 0:
            st.warning("Hasil backtesting ini sudah pernah disimpan.")
            return

        query = """
            INSERT INTO data_backtesting (ticker, money, final_money, profit, profit_percentage, accuracy)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (ticker, money, final_value, gain, gain_pct, accuracy)
        cursor.execute(query, values)
        conn.commit()
        st.success("Hasil backtesting berhasil disimpan ke database.")
    except mysql.connector.Error as err:
        st.error(f"Gagal menyimpan hasil backtesting: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def plot_accuracy_history(ticker):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="indonesia_stock"
        )
        df = pd.read_sql(f"""
            SELECT timestamp, accuracy FROM data_backtesting
            WHERE ticker = '{ticker}' AND accuracy IS NOT NULL
            ORDER BY timestamp
        """, conn)
        conn.close()

        if df.empty:
            st.warning("Belum ada data akurasi yang disimpan untuk ticker ini.")
            return

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['accuracy'],
            mode='lines+markers',
            name='Akurasi (%)',
            line=dict(color='blue')
        ))
        fig.update_layout(
            title=f"Riwayat Akurasi Sinyal untuk {ticker}",
            xaxis_title='Tanggal',
            yaxis_title='Akurasi',
            yaxis_tickformat='.0%',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal menampilkan grafik akurasi: {e}")

def evaluate_signal_pairs(df, signal_series):
    pairs = []
    holding = False
    buy_price = None
    buy_date = None

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
            pairs.append({
                'Buy Date': buy_date.strftime('%Y-%m-%d'),
                'Buy Price': round(buy_price, 2),
                'Sell Date': sell_date.strftime('%Y-%m-%d'),
                'Sell Price': round(sell_price, 2),
                'Profit': round(profit, 2)
            })
            holding = False  # Reset for next Buy-Sell pair

    df_pairs = pd.DataFrame(pairs)
    if not df_pairs.empty:
        df_pairs = df_pairs.sort_values(by='Profit', ascending=False).reset_index(drop=True)
    return df_pairs

def evaluate_individual_indicators(ticker, df, params, interval, money=1_000_000):
    from modules.analysis import compute_final_signal
    from modules.indicators import compute_indicators
    from modules.backtesting import apply_custom_strategy, run_backtesting_profit

    results = []
    indikator_list = ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']

    for ind in indikator_list:
        single_indicator = {key: (key == ind) for key in indikator_list}
        df_ind = compute_indicators(df.copy(), single_indicator, params)
        df_ind['Final_Signal'] = compute_final_signal(df_ind, single_indicator)
        signal_series = apply_custom_strategy(df_ind, "Final Signal")

        # Run backtesting profit simulation
        try:
            _, final_value, gain, gain_pct, accuracy = run_backtesting_profit(df_ind, money, signal_series, key_prefix=f"{ticker}_{ind}_auto_eval")
            results.append({
                'Indikator': ind,
                'Akurasi': round(accuracy * 100, 2),
                'Keuntungan (Rp)': round(gain, 2),
                'Keuntungan (%)': round(gain_pct, 2)
            })
        except Exception as e:
            results.append({
                'Indikator': ind,
                'Akurasi': None,
                'Keuntungan (Rp)': None,
                'Keuntungan (%)': None,
                'Error': str(e)
            })

    return pd.DataFrame(results).sort_values(by='Keuntungan (%)', ascending=False).reset_index(drop=True)


# def run_backtesting_analysis(df, money):
#     st.subheader("Total Sinyal")
#     if 'Final_Signal' not in df.columns:
#         st.warning("Data tidak memiliki kolom Final_Signal.")
#         return

#     signal_counts = df['Final_Signal'].value_counts().to_frame().reset_index()
#     signal_counts.columns = ['Sinyal', 'Jumlah']
#     st.dataframe(signal_counts, use_container_width=True)

#     # Ekspor ke Excel
#     buffer = BytesIO()
#     with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
#         signal_counts.to_excel(writer, index=False, sheet_name='Sinyal')
#     st.download_button(
#         label="⬇ Unduh Rekap Sinyal (Excel)",
#         data=buffer.getvalue(),
#         file_name="rekap.xlsx",
#         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         key=f"download_rekap_{ticker}_{interval}"
#     )


# def run_backtesting_profit(df, money, signal_series):
#     st.subheader("Profit Trading")
#     cash = money
#     stock = 0
#     history = []
#     predictions = []
#     actuals = []

#     df['Future_Close'] = df['Close'].shift(-1)

#     for date in df.index[:-1]:
#         # Ambil satu nilai aman meskipun ada index duplikat
#         signal = signal_series.loc[date]
#         if isinstance(signal, pd.Series):
#             signal = signal.iloc[0]

#         price = df.loc[date, 'Close']
#         future_price = df.loc[date, 'Future_Close']
#         if isinstance(price, pd.Series):
#             price = price.iloc[0]
#         if isinstance(future_price, pd.Series):
#             future_price = future_price.iloc[0]

#         # Hitung tren aktual
#         actual_trend = 'Buy' if future_price > price else 'Sell'
#         predictions.append(signal)
#         actuals.append(actual_trend)

#         # Simulasi trading
#         if signal == 'Buy' and cash >= price:
#             qty = cash // price
#             stock += qty
#             cash -= qty * price
#         elif signal == 'Sell' and stock > 0:
#             cash += stock * price
#             stock = 0

#         value = cash + stock * price
#         profit = value - money
#         history.append([date.strftime("%Y-%m-%d"), signal, f"{value:,.0f}", f"{profit:,.0f}"])

#     # Hitung hasil akhir
#     final_price = df['Close'].iloc[-1]
#     final_value = cash + stock * final_price
#     gain = final_value - money
#     gain_pct = (gain / money) * 100

#     st.write(f"Nilai akhir portofolio: **Rp{final_value:,.0f}**")
#     st.write(f"Keuntungan: **Rp{gain:,.0f} ({gain_pct:.2f}%)**")

#     df_result = pd.DataFrame(history, columns=['Tanggal', 'Sinyal', 'Nilai Portofolio', 'Profit'])
#     st.dataframe(df_result, use_container_width=True)

#     # Hitung akurasi
#     accuracy = accuracy_score(actuals, predictions)
#     st.info(f"Akurasi sinyal (berdasarkan harga besok): **{accuracy * 100:.2f}%**")

#     return df_result, final_value, gain, gain_pct, accuracy


# def evaluate_signal_pairs(df, signal_series):
#     pairs = []
#     holding = False
#     buy_price = 0
#     buy_date = None

#     # Pastikan urutan tanggal benar
#     df = df.sort_index()
#     signal_series = signal_series.sort_index()

#     for date in df.index:
#         signal = signal_series.loc[date]
#         if isinstance(signal, pd.Series):
#             signal = signal.iloc[0]
#         price = df.loc[date, 'Close']
#         if isinstance(price, pd.Series):
#             price = price.iloc[0]

#         if signal == 'Buy' and not holding:
#             holding = True
#             buy_price = price
#             buy_date = date

#         elif signal == 'Sell' and holding:
#             sell_price = price
#             sell_date = date
#             profit = sell_price - buy_price
#             pairs.append({
#                 'Buy Date': buy_date.strftime('%Y-%m-%d'),
#                 'Buy Price': buy_price,
#                 'Sell Date': sell_date.strftime('%Y-%m-%d'),
#                 'Sell Price': sell_price,
#                 'Profit': profit
#             })
#             holding = False

#     if not pairs:
#         return pd.DataFrame(columns=['Buy Date', 'Buy Price', 'Sell Date', 'Sell Price', 'Profit'])

#     df_pairs = pd.DataFrame(pairs)
#     return df_pairs.sort_values(by='Profit', ascending=False).reset_index(drop=True)



# # save ke sql dan excel
# from io import BytesIO

# def export_evaluation_to_excel(df_result, df_pairs, ticker, interval):
#     buffer = BytesIO()
#     with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
#         df_result.to_excel(writer, sheet_name='Backtesting Summary', index=False)
#         df_pairs.to_excel(writer, sheet_name='Signal Pairs', index=False)
#     return buffer.getvalue()
