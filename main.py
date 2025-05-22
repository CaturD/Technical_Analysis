import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import get_ticker_list, get_data_from_db
from modules.indicators import compute_indicators
from modules.visuals import plot_indicators
from modules.database import get_realtime_data_from_db
from modules.analysis import evaluate_strategy_accuracy
from modules.analysis import (
    compute_final_signal,
    display_analysis_table_with_summary,
    save_analysis_to_json_db,
    fetch_saved_titles,
    load_analysis_by_title,
    show_signal_recap
)
from modules.backtesting import (
    fetch_backtesting_data,
    run_backtesting_analysis,
    run_backtesting_profit,
    save_backtesting_to_db,
    plot_accuracy_history,
    apply_strategy,
    evaluate_signal_pairs,
    evaluate_individual_indicators
)
from modules.evaluation_log import (
    evaluate_indicator_combinations
)

def display_accuracy_result(result, label="Akurasi Historis"):
    if result:
        st.metric(label, f"{result['accuracy']*100:.2f}%")
        with st.expander("Distribusi Sinyal"):
            df = pd.DataFrame(
                [{'Sinyal': k, 'Jumlah': v} for k, v in result['signal_distribution'].items()]
            )
            st.dataframe(df, use_container_width=True)

st.set_page_config(layout="wide")
st.title("DASHBOARD TREND HARGA SAHAM")

# from modules.evaluation_log import get_all_accuracy_logs

# # Ambil data strategi dari database
# df_logs = get_all_accuracy_logs()
# top5 = df_logs.sort_values(by=['accuracy', 'timestamp'], ascending=[False, False]).head(5)

# if not top5.empty:
#     st.markdown("### Top 5 Strategi Saham (Akurasi & Profit Tertinggi)")
#     cols = st.columns(len(top5))
#     for i, row in top5.iterrows():
#         color = "green" if row['accuracy'] >= 0.5 else "red"
#         with cols[i]:
#             st.markdown(f"""
#                 <div style='padding: 10px; border-radius: 10px; background-color: #f9f9f9; border: 1px solid #ddd;'>
#                     <strong>{row['ticker']}</strong><br>
#                     <span style='color: {color}; font-size: 18px; font-weight: bold;'>{row['accuracy']*100:.2f}%</span><br>
#                     <span style='font-size: 14px;'>{row['indicators']}</span><br>
#                     <span style='font-size: 13px;'>({row['strategy']})</span>
#                 </div>
#             """, unsafe_allow_html=True)

from modules.evaluation_log import get_all_accuracy_logs

# Load data
df_logs = get_all_accuracy_logs()
df_sorted = df_logs.sort_values(by='accuracy', ascending=False).reset_index(drop=True)

st.markdown("#### Top Strategi Saham Berdasarkan Akurasi")

# Setup slider
total = len(df_sorted)
per_page = 5
max_slide = max(0, total - per_page)
if "slide_index" not in st.session_state:
    st.session_state.slide_index = 0

slide_index = st.session_state.slide_index

# Invisible button styling with centered alignment
st.markdown("""
<style>
.arrow-button {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    margin-top: 60px;
}
.invisible-button {
    border: none;
    background: transparent;
    font-size: 32px;
    color: transparent;
    cursor: pointer;
}
.invisible-button:hover {
    color: #888;
    transition: 0.3s ease;
}
.visible-button {
    border: none;
    background: transparent;
    font-size: 28px;
    color: #888;
    cursor: pointer;
    margin-top: 60px;
    padding: 0 4px;
}
</style>
""", unsafe_allow_html=True)

# Layout
cols = st.columns([0.3, 9.4, 0.3])

# Left button
with cols[0]:
    st.markdown("<div class='arrow-button'>", unsafe_allow_html=True)
    if slide_index > 0:
        if st.button("<", key="prev_btn", help="Sebelumnya"):
            st.session_state.slide_index = max(0, slide_index - per_page)
    else:
        st.markdown("<button class='invisible-button'> </button>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Cards
with cols[1]:
    df_show = df_sorted.iloc[slide_index:slide_index + per_page]
    card_cols = st.columns(len(df_show))
    for i, (_, row) in enumerate(df_show.iterrows()):
        color = "green" if row['accuracy'] >= 0.5 else "red"
        with card_cols[i]:
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 10px; background-color: #f9f9f9; border: 1px solid #ddd; text-align:center;'>
                    <strong>{row['ticker']}</strong><br>
                    <span style='color: {color}; font-size: 18px; font-weight: bold;'>{row['accuracy']*100:.2f}%</span><br>
                    <span style='font-size: 14px;'>{row['indicators']}</span><br>
                    <span style='font-size: 13px;'>({row['strategy']})</span>
                </div>
            """, unsafe_allow_html=True)

# Right button
with cols[2]:
    st.markdown("<div class='arrow-button'>", unsafe_allow_html=True)
    if slide_index + per_page < total:
        if st.button(">", key="next_btn", help="Berikutnya"):
            st.session_state.slide_index = min(max_slide, slide_index + per_page)
    else:
        st.markdown("<button class='invisible-button'> </button>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
ticker_list = get_ticker_list()
tickers = st.sidebar.multiselect("Pilih Ticker", ticker_list, default=[ticker_list[0]])
interval = st.sidebar.selectbox("Pilih Interval", [
    "1 minute", "2 minutes", "3 minutes", "5 minutes", "10 minutes", "15 minutes", "30 minutes", "45 minutes",
    "1 hour", "2 hours", "3 hours", "4 hours",
    "1 day", "1 week", "1 month", "3 months", "6 months", "12 months"
],
index=12
)
st.sidebar.markdown(f"**Interval terpilih:** {interval}")
start_date = st.sidebar.date_input("Tanggal Mulai", datetime(2025, 4, 12))
end_date = st.sidebar.date_input("Tanggal Selesai", datetime(2025, 5, 12))
money = st.sidebar.number_input("Modal Awal (Rp)", value=1_000_000, step=500_000)
strategy = st.sidebar.selectbox(
    "Pilih Strategi Backtesting",
    ["Final Signal", "Buy & Hold", "MACD Only", "MA Crossover", "Volume Entry"]
)

# Indikator yang digunakan
indicators = {
    "Ichimoku": st.sidebar.checkbox("Ichimoku", value=True),
    "MA": st.sidebar.checkbox("Moving Average", value=True),
    "MACD": st.sidebar.checkbox("MACD", value=True),
    "SO": st.sidebar.checkbox("Stochastic Oscillator", value=True),
    "Volume": st.sidebar.checkbox("Volume", value=True)
}

# Filter sinyal
signal_filter = st.sidebar.multiselect(
    "Filter Sinyal", ['Buy', 'Sell', 'Hold'], default=['Buy', 'Sell', 'Hold']
)

# perubahan parameter indikator
with st.sidebar.expander("Setting Parameter Indikator"):
    params = {
        'ma_short': st.number_input("MA Short", value=20, min_value=1),
        'ma_long': st.number_input("MA Long", value=50, min_value=1),
        'macd_fast': st.number_input("MACD Fast", value=12, min_value=1),
        'macd_slow': st.number_input("MACD Slow", value=26, min_value=1),
        'macd_signal': st.number_input("MACD Signal", value=9, min_value=1),
        'so_k': st.number_input("Stochastic %K", value=14, min_value=1),
        'so_d': st.number_input("Stochastic %D", value=3, min_value=1),
        'volume_ma': st.number_input("Volume MA", value=20, min_value=1),
        'tenkan': st.number_input("Ichimoku Tenkan-sen", value=9, min_value=1),
        'kijun': st.number_input("Ichimoku Kijun-sen", value=26, min_value=1),
        'senkou_b': st.number_input("Ichimoku Senkou Span B", value=52, min_value=1),
        'shift': st.number_input("Ichimoku Shift-26 Periode", value=26, min_value=1)
    }

# Tab Navigasi
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Analisis",
    "Analisis Tersimpan",
    "Backtesting Analisis",
    "Backtesting Profit",
    "Data Realtime",
    "Evaluasi Indikator",
    "Evaluasi Kombinasi Indikator",
    "Semua Akurasi Strategi"
])

with tab1:
    st.subheader("Analisis Saham")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        data = get_data_from_db(ticker, interval)
        if not data.empty:
            data = compute_indicators(data, indicators, params)
            data['Final_Signal'] = compute_final_signal(data, indicators)
            data_in_range = data.loc[start_date:end_date]
            plot_indicators(data_in_range, indicators)
            display_analysis_table_with_summary(data_in_range, indicators, signal_filter)
            save_analysis_to_json_db(ticker, data_in_range, indicators)


# Tab 2 - Load Analisis Tersimpan
with tab2:
    st.subheader("Analisis Tersimpan")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        saved_titles = fetch_saved_titles(ticker)
        if saved_titles:
            selected_title = st.selectbox("Pilih Judul Analisis", saved_titles)
            df_loaded = load_analysis_by_title(ticker, selected_title)
            display_analysis_table_with_summary(df_loaded, indicators, signal_filter)
        else:
            st.info("Belum ada hasil analisis yang tersimpan untuk ticker ini.")

with tab3:
    from modules.evaluation_log import save_accuracy_evaluation_to_db
    from modules.visuals import plot_signal_markers
    st.subheader("Backtesting Analisis")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_bt = fetch_backtesting_data(ticker, start_date, end_date)
        if not df_bt.empty:
            signal_series = apply_strategy(df_bt, strategy)
            result_bt = evaluate_strategy_accuracy(df_bt.copy())
            save_accuracy_evaluation_to_db(
                ticker=ticker,
                interval=interval,
                strategy=strategy,
                indicators_dict=indicators,
                params_dict=params,
                accuracy_value=result_bt["accuracy"]
            )
            display_accuracy_result(result_bt, "Akurasi Backtesting Analisis")
            df_pairs = evaluate_signal_pairs(df_bt, signal_series)
            st.subheader("Evaluasi Pasangan Sinyal")
            if df_pairs.empty:
                st.warning("Tidak ada pasangan sinyal valid ditemukan dalam rentang waktu yang dipilih.")
            else:
                st.dataframe(df_pairs, use_container_width=True)
            run_backtesting_analysis(df_bt, money, key_prefix=f"{ticker}_{interval}_tab3")
        # Tambahkan filter sinyal
        plot_signal_markers(df_bt)  # tanpa parameter tambahan

with tab4:
    st.subheader("Backtesting Profit")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_bt = fetch_backtesting_data(ticker, start_date, end_date)
        if not df_bt.empty:
            signal_series = apply_strategy(df_bt, strategy)
            result_profit = result_profit = evaluate_strategy_accuracy(df_bt.copy())
            from modules.evaluation_log import save_accuracy_evaluation_to_db
            save_accuracy_evaluation_to_db(
                ticker=ticker,
                interval=interval,
                strategy=strategy,
                indicators_dict=indicators,
                params_dict=params,
                accuracy_value=result_profit["accuracy"]
            )
            display_accuracy_result(result_profit, "Akurasi Backtesting Profit")
            df_result, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
            df_bt, money, signal_series, key_prefix=f"{ticker}_{interval}_tab4"
            )
            save_backtesting_to_db(ticker, money, final_value, gain, gain_pct, accuracy)
            plot_accuracy_history(ticker)

with tab5:
    st.subheader("Data Realtime (Marketstack)")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        realtime_ticker = ticker.replace(".JK", ".XIDX")
        df_rt = get_realtime_data_from_db(realtime_ticker)

        if df_rt is not None and not df_rt.empty:
            df_rt = compute_indicators(df_rt, indicators, params)
            df_rt['Final_Signal'] = compute_final_signal(df_rt, indicators)

            result_rt = evaluate_strategy_accuracy(df_rt)
            if result_rt:
                display_accuracy_result(result_rt, "Akurasi Realtime")

            plot_indicators(df_rt, indicators)
            display_analysis_table_with_summary(df_rt, indicators, signal_filter)
            show_signal_recap(df_rt, indicators)
        else:
            st.warning("Tidak ada data realtime ditemukan untuk ticker ini.")
    else:
        st.warning("Pilih ticker terlebih dahulu.")

with tab6:
    st.subheader("Evaluasi Per Indikator")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_eval = get_data_from_db(ticker, interval)
        df_eval = df_eval.loc[start_date:end_date]
        if not df_eval.empty:
            df_result_eval = evaluate_individual_indicators(ticker, df_eval, params, interval, money)
            st.dataframe(df_result_eval, use_container_width=True)
        else:
            st.warning("Data tidak tersedia untuk ticker dan interval yang dipilih.")

with tab7:
    st.subheader("Evaluasi Kombinasi Indikator")
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_eval = get_data_from_db(ticker, interval)
        df_eval = df_eval.loc[start_date:end_date]
        if not df_eval.empty:
            df_combo_result = evaluate_indicator_combinations(ticker, df_eval, params, interval, money)
            st.dataframe(df_combo_result, use_container_width=True)

with tab8:
    st.subheader("Semua Riwayat Akurasi Strategi")
    from modules.evaluation_log import get_all_accuracy_logs

    all_logs_df = get_all_accuracy_logs()
    if not all_logs_df.empty:
        st.dataframe(all_logs_df, use_container_width=True)

        best_row = all_logs_df.iloc[0]
        st.success(f"Akurasi Tertinggi: {best_row['accuracy']*100:.2f}% | Ticker: {best_row['ticker']} | Strategi: {best_row['strategy']}")
    else:
        st.info("Belum ada data akurasi yang tersedia.")
