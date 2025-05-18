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
st.title("Dashboard Analisis & Backtesting Saham")

# Sidebar
ticker_list = get_ticker_list()
ticker = st.sidebar.selectbox("Pilih Ticker", ticker_list)
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Analisis",
    "Analisis Tersimpan",
    "Backtesting Analisis",
    "Backtesting Profit",
    "Data Realtime",
    "Evaluasi Indikator",
    "Evaluasi Kombinasi Indikator"
])

with tab1:
    st.subheader("Analisis Saham")
    data = get_data_from_db(ticker, interval)
    if not data.empty:
        data = compute_indicators(data, indicators, params)
        data['Final_Signal'] = compute_final_signal(data, indicators)
        data_in_range = data.loc[start_date:end_date]

        # result = evaluate_strategy_accuracy(data_in_range.copy())
        # display_accuracy_result(result, "Akurasi Historis")

        plot_indicators(data_in_range, indicators)
        display_analysis_table_with_summary(data_in_range, indicators, signal_filter)
        save_analysis_to_json_db(ticker, data_in_range, indicators)
        # show_signal_recap(data_in_range, indicators)

# Tab 2 - Load Analisis Tersimpan
with tab2:
    st.subheader("Analisis Tersimpan")
    saved_titles = fetch_saved_titles(ticker)
    if saved_titles:
        selected_title = st.selectbox("Pilih Judul Analisis", saved_titles)
        df_loaded = load_analysis_by_title(ticker, selected_title)
        display_analysis_table_with_summary(df_loaded, indicators, signal_filter)
        # show_signal_recap(df_loaded, indicators)
    else:
        st.info("Belum ada hasil analisis yang tersimpan untuk ticker ini.")

with tab3:
    from modules.evaluation_log import save_accuracy_evaluation_to_db
    from modules.visuals import plot_signal_markers
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
    if ticker:
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
    df_eval = get_data_from_db(ticker, interval)
    df_eval = df_eval.loc[start_date:end_date]
    if not df_eval.empty:
        df_result_eval = evaluate_individual_indicators(ticker, df_eval, params, interval, money)
        st.dataframe(df_result_eval, use_container_width=True)
    else:
        st.warning("Data tidak tersedia untuk ticker dan interval yang dipilih.")

with tab7:
    st.subheader("Evaluasi Kombinasi Indikator")
    df_eval = get_data_from_db(ticker, interval)
    df_eval = df_eval.loc[start_date:end_date]
    if not df_eval.empty:
        df_combo_result = evaluate_indicator_combinations(ticker, df_eval, params, interval, money)
        st.dataframe(df_combo_result, use_container_width=True)
        # if not df_combo_result.empty:
        #     fig = px.bar(df_combo_result, x='Kombinasi', y='Keuntungan (%)', title='Profit Kombinasi (%)')
        #     st.plotly_chart(fig, use_container_width=True)


# with tab5:
#     # st.subheader("Rekapitulasi Sinyal")
#     df_bt = fetch_backtesting_data(ticker, start_date, end_date)
#     if not df_bt.empty:
#         show_signal_recap(df_bt, indicators)
#     else:
#         st.warning("Tidak ada data tersedia untuk rekapitulasi sinyal.")

# Grafik
# import plotly.express as px

# if not df_result_eval.empty:
#     fig = px.bar(df_result_eval, x='Indikator', y='Akurasi', title='Akurasi per Indikator (%)')
#     st.plotly_chart(fig, use_container_width=True)

#     fig2 = px.bar(df_result_eval, x='Indikator', y='Keuntungan (%)', title='Profit per Indikator (%)')
#     st.plotly_chart(fig2, use_container_width=True)


# import streamlit as st
# import pandas as pd
# from datetime import datetime
# from modules.database import get_ticker_list, get_data_from_db
# from modules.indicators import compute_indicators
# from modules.visuals import plot_indicators
# from modules.database import get_realtime_data_from_db
# from modules.analysis import evaluate_strategy_accuracy
# from modules.analysis import (
#     compute_final_signal,
#     display_analysis_table_with_summary,
#     save_analysis_to_json_db,
#     fetch_saved_titles,
#     load_analysis_by_title,
#     show_signal_recap
# )
# from modules.backtesting import (
#     fetch_backtesting_data,
#     run_backtesting_analysis,
#     run_backtesting_profit,
#     save_backtesting_to_db,
#     plot_accuracy_history,
#     apply_strategy,
#     evaluate_signal_pairs
# )

# def display_accuracy_result(result, label="Akurasi Historis"):
#     if result:
#         st.metric(label, f"{result['accuracy']*100:.2f}%")
#         with st.expander("Distribusi Sinyal"):
#             df = pd.DataFrame(
#                 [{'Sinyal': k, 'Jumlah': v} for k, v in result['signal_distribution'].items()]
#             )
#             st.dataframe(df, use_container_width=True)

# st.set_page_config(layout="wide")
# st.title("Dashboard Analisis & Backtesting Saham")

# # Sidebar
# ticker_list = get_ticker_list()
# ticker = st.sidebar.selectbox("Pilih Ticker", ticker_list)
# interval = st.sidebar.selectbox("Pilih Interval", [
#     "1 minute", "2 minutes", "3 minutes", "5 minutes", "10 minutes", "15 minutes", "30 minutes", "45 minutes",
#     "1 hour", "2 hours", "3 hours", "4 hours",
#     "1 day", "1 week", "1 month", "3 months", "6 months", "12 months"
# ])
# st.sidebar.markdown(f"**Interval terpilih:** {interval}")
# start_date = st.sidebar.date_input("Tanggal Mulai", datetime(2025, 4, 12))
# end_date = st.sidebar.date_input("Tanggal Selesai", datetime(2025, 5, 12))
# money = st.sidebar.number_input("Modal Awal (Rp)", value=1_000_000, step=500_000)
# strategy = st.sidebar.selectbox(
#     "Pilih Strategi Backtesting",
#     ["Final Signal", "Buy & Hold", "MACD Only", "MA Crossover", "Volume Entry"]
# )

# # Indikator yang digunakan
# indicators = {
#     "Ichimoku": st.sidebar.checkbox("Ichimoku", value=True),
#     "MA": st.sidebar.checkbox("Moving Average", value=True),
#     "MACD": st.sidebar.checkbox("MACD", value=True),
#     "SO": st.sidebar.checkbox("Stochastic Oscillator", value=True),
#     "Volume": st.sidebar.checkbox("Volume", value=True)
# }

# # Filter sinyal
# signal_filter = st.sidebar.multiselect(
#     "Filter Sinyal", ['Buy', 'Sell', 'Hold'], default=['Buy', 'Sell', 'Hold']
# )

# # perubahan parameter indikator
# with st.sidebar.expander("Setting Parameter Indikator"):
#     params = {
#         'ma_short': st.number_input("MA Short", value=20, min_value=1),
#         'ma_long': st.number_input("MA Long", value=50, min_value=1),
#         'macd_fast': st.number_input("MACD Fast", value=12, min_value=1),
#         'macd_slow': st.number_input("MACD Slow", value=26, min_value=1),
#         'macd_signal': st.number_input("MACD Signal", value=9, min_value=1),
#         'so_k': st.number_input("Stochastic %K", value=14, min_value=1),
#         'so_d': st.number_input("Stochastic %D", value=3, min_value=1),
#         'volume_ma': st.number_input("Volume MA", value=20, min_value=1),
#         'tenkan': st.number_input("Ichimoku Tenkan-sen", value=9, min_value=1),
#         'kijun': st.number_input("Ichimoku Kijun-sen", value=26, min_value=1),
#         'senkou_b': st.number_input("Ichimoku Senkou Span B", value=52, min_value=1),
#         'shift': st.number_input("Ichimoku Shift-26 Periode", value=26, min_value=1)
#     }

# # Tab Navigasi
# tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
#     "Analisis",
#     "Analisis Tersimpan",
#     "Backtesting Analisis",
#     "Backtesting Profit",
#     "Rekapitulasi Sinyal",
#     "Data Realtime"
# ])

# with tab1:
#     st.subheader("Analisis Saham")
#     data = get_data_from_db(ticker, interval)
#     if not data.empty:
#         data = compute_indicators(data, indicators, params)
#         data['Final_Signal'] = compute_final_signal(data, indicators)
#         data_in_range = data.loc[start_date:end_date]

#         # result = evaluate_strategy_accuracy(data_in_range)
#         # display_accuracy_result(result, "Akurasi Historis")

#         plot_indicators(data_in_range, indicators)
#         display_analysis_table_with_summary(data_in_range, indicators, signal_filter)
#         save_analysis_to_json_db(ticker, data_in_range, indicators)
#         show_signal_recap(data_in_range, indicators)
# # # Tab 1 - Analisis old
# # with tab1:
# #     st.subheader("Analisis Saham")
# #     data = get_data_from_db(ticker, interval)
# #     if not data.empty:
# #         # data = compute_indicators(data, indicators)
# #         data = compute_indicators(data, indicators, params)
# #         data['Final_Signal'] = compute_final_signal(data, indicators)
# #         data_in_range = data.loc[start_date:end_date]  
# #         plot_indicators(data_in_range, indicators)
# #         display_analysis_table_with_summary(data_in_range, indicators, signal_filter)
# #         save_analysis_to_json_db(ticker, data_in_range, indicators)
# #         show_signal_recap(data_in_range, indicators)

# # # new
# # with tab1:
# #     st.subheader("Analisis Saham")
# #     data = get_data_from_db(ticker, interval)
# #     if not data.empty:
# #         data = compute_indicators(data, indicators, params)
# #         data['Final_Signal'] = compute_final_signal(data, indicators)
# #         data_in_range = data.loc[start_date:end_date]
        
# #         result = evaluate_strategy_accuracy(data_in_range)
# #         if result:
# #             st.metric("Akurasi Historis", f"{result['accuracy']*100:.2f}%")
# #             st.write("Distribusi sinyal:", result['signal_distribution'])

# #         plot_indicators(data_in_range, indicators)
# #         display_analysis_table_with_summary(data_in_range, indicators, signal_filter)
# #         save_analysis_to_json_db(ticker, data_in_range, indicators)
# #         show_signal_recap(data_in_range, indicators)


# # Tab 2 - Load Analisis Tersimpan
# with tab2:
#     st.subheader("Analisis Tersimpan")
#     saved_titles = fetch_saved_titles(ticker)
#     if saved_titles:
#         selected_title = st.selectbox("Pilih Judul Analisis", saved_titles)
#         df_loaded = load_analysis_by_title(ticker, selected_title)
#         display_analysis_table_with_summary(df_loaded, indicators, signal_filter)
#         show_signal_recap(df_loaded, indicators)
#     else:
#         st.info("Belum ada hasil analisis yang tersimpan untuk ticker ini.")

# # # Tab 3 - Backtesting Analisis + Evaluasi Pasangan Sinyal
# # with tab3:
# #     df_bt = fetch_backtesting_data(ticker, start_date, end_date)
# #     if not df_bt.empty:
# #         # st.subheader("Backtesting Analisis")
# #         signal_series = apply_strategy(df_bt, strategy)
# #         from modules.backtesting import evaluate_signal_pairs
# #         df_pairs = evaluate_signal_pairs(df_bt, signal_series)
# #         st.subheader("Evaluasi Pasangan Sinyal")
# #         st.dataframe(df_pairs, use_container_width=True)
# #         # if not df_pairs.empty:
# #         #     total_trades = len(df_pairs)
# #         #     profitable_trades = (df_pairs['Profit'] > 0).sum()
# #         #     losing_trades = (df_pairs['Profit'] < 0).sum()
# #         #     total_profit = df_pairs['Profit'].sum()
# #         #     avg_profit = df_pairs['Profit'].mean()
# #         #     win_rate = profitable_trades / total_trades * 100 if total_trades else 0
# #         #     st.markdown("### Statistik Evaluasi Sinyal")
# #         #     st.markdown(f"Jumlah pasangan sinyal: **{total_trades}**")
# #         #     st.markdown(f"Jumlah untung: **{profitable_trades}**, rugi: **{losing_trades}**")
# #         #     st.markdown(f"Total profit: **{total_profit:,.2f}**")
# #         #     st.markdown(f"Rata-rata profit per pasangan: **{avg_profit:,.2f}**")
# #         #     st.markdown(f"Win rate: **{win_rate:.2f}%**")
            
# #         run_backtesting_analysis(df_bt, money)

# with tab3:
#     df_bt = fetch_backtesting_data(ticker, start_date, end_date)
#     if not df_bt.empty:
#         result_bt = evaluate_strategy_accuracy(df_bt)
#         display_accuracy_result(result_bt, "Akurasi Evaluasi Sinyal")
#         signal_series = apply_strategy(df_bt, strategy)
#         df_pairs = evaluate_signal_pairs(df_bt, signal_series)
#         st.subheader("Evaluasi Pasangan Sinyal")
#         st.dataframe(df_pairs, use_container_width=True)
#         run_backtesting_analysis(df_bt, money)


# with tab4:
#     df_bt = fetch_backtesting_data(ticker, start_date, end_date)
#     if not df_bt.empty:
#         signal_series = apply_strategy(df_bt, strategy)
#         result_profit = evaluate_strategy_accuracy(df_bt)
#         display_accuracy_result(result_profit, "Akurasi Backtesting Profit")
#         df_result, final_value, gain, gain_pct, accuracy = run_backtesting_profit(df_bt, money, signal_series)
#         save_backtesting_to_db(ticker, money, final_value, gain, gain_pct, accuracy)
#         plot_accuracy_history(ticker)


# # Tab 4 - Backtesting Profit + Akurasi
# with tab4:
#     df_bt = fetch_backtesting_data(ticker, start_date, end_date)
#     if not df_bt.empty:
#         signal_series = apply_strategy(df_bt, strategy)
#         df_result, final_value, gain, gain_pct, accuracy = run_backtesting_profit(df_bt, money, signal_series)
#         save_backtesting_to_db(ticker, money, final_value, gain, gain_pct, accuracy)
#         plot_accuracy_history(ticker)

        # # New Tambahkan setelah evaluasi pasangan sinyal
        # excel_data = export_evaluation_to_excel(df_result, df_pairs, ticker, interval)
        # st.download_button(
        #     label="Unduh Hasil Evaluasi (.xlsx)",
        #     data=excel_data,
        #     file_name=f"evaluasi_{ticker}_{interval}.xlsx",
        #     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        # )  
        # df_pairs = evaluate_signal_pairs(df_bt, signal_series)
        # st.subheader("Evaluasi Pasangan Sinyal Buy–Sell")
        # st.dataframe(df_pairs, use_container_width=True)




# Data REALTIME old
# with tab6:
#     st.subheader("Data Realtime (Marketstack)")

#     realtime_ticker = ticker.replace(".JK", ".XIDX")
#     df_rt = get_realtime_data_from_db(realtime_ticker)

#     if not df_rt.empty:
#         df_rt = compute_indicators(df_rt, indicators, params)
#         df_rt['Final_Signal'] = compute_final_signal(df_rt, indicators)

#         plot_indicators(df_rt, indicators)
#         display_analysis_table_with_summary(df_rt, indicators, signal_filter)
#         show_signal_recap(df_rt, indicators)


# with tab6:
#     st.subheader("Data Realtime (Marketstack)")

#     if ticker:
#         realtime_ticker = ticker.replace(".JK", ".XIDX")
#         st.caption(f"Ticker realtime: {realtime_ticker}")
#         df_rt = get_realtime_data_from_db(realtime_ticker)

#         if not df_rt.empty:
#             df_rt = compute_indicators(df_rt, indicators, params)
#             df_rt['Final_Signal'] = compute_final_signal(df_rt, indicators)

#             result_rt = evaluate_strategy_accuracy(df_rt)
#             if result_rt:
#                 st.metric("Akurasi Realtime", f"{result_rt['accuracy']*100:.2f}%")
#                 st.write("Distribusi sinyal:", result_rt['signal_distribution'])

#             plot_indicators(df_rt, indicators)
#             display_analysis_table_with_summary(df_rt, indicators, signal_filter)
#             show_signal_recap(df_rt, indicators)
#         else:
#             st.warning("Tidak ada data realtime ditemukan untuk ticker ini.")
#     else:
#         st.warning("Pilih ticker terlebih dahulu.")


