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
    apply_custom_strategy,
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
# st.title("DASHBOARD TREND HARGA SAHAM")
st.markdown("<h1 style='text-align: center;'>DASHBOARD TREND HARGA SAHAM</h1>", unsafe_allow_html=True)
st.markdown("""
Dashboard ini digunakan untuk menganalisis dan memprediksi arah tren harga saham menggunakan berbagai indikator teknikal populer seperti Moving Average, MACD, Ichimoku Cloud, dan lainnya.
Dengan fitur analisis dan backtesting untuk:
- Mengetahui sinyal buy, sell, atau hold.
- Melihat performa strategi berdasarkan data historis.
- Mengevaluasi efektivitas kombinasi indikator dengan menggunakan filter di sidebar untuk menyesuaikan analisis dengan preferensi Anda.
""")

from modules.evaluation_log import get_all_accuracy_logs

# Load data
df_logs = get_all_accuracy_logs()
if not df_logs.empty and 'accuracy' in df_logs.columns:
    df_sorted = df_logs.sort_values(by='accuracy', ascending=False).reset_index(drop=True)
else:
    st.warning("Belum ada data strategi yang tersimpan atau tabel belum tersedia.")
    df_sorted = pd.DataFrame()


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

with cols[1]:
    df_show = df_sorted.iloc[slide_index:slide_index + per_page]
    if not df_show.empty:
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
    else:
        st.info("Tidak ada strategi yang dapat ditampilkan.")


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
start_date = st.sidebar.date_input("Tanggal Mulai", datetime(2024, 5, 12))
end_date = st.sidebar.date_input("Tanggal Selesai", datetime(2025, 5, 12))
money = st.sidebar.number_input("Modal Awal (Rp)", value=1_000_000, step=500_000)
strategy = st.sidebar.selectbox(
    "Pilih Strategi Backtesting",
    [
        "Final Signal", "Buy & Hold",
        "MA Only", "MACD Only", "Ichimoku Only", "SO Only", "Volume Only",
        "Ichimoku + MA Only", "All Agree", "3 of 5 Majority",
        "MACD + Volume Confirm", "Ichimoku + MA Trend", "SO + MACD"
    ]
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
    "Evaluasi Indikator dan kombinasi",
    # "Evaluasi Kombinasi Indikator",
    "Semua Akurasi Strategi",
    "Evaluasi Gabungan"
])

with tab1:
    st.subheader("Analisis Saham")
    st.markdown("""
        Fitur ini menghitung indikator teknikal untuk menentukan sinyal akhir: **Buy**, **Sell**, atau **Hold**.
        - Sinyal ditentukan dengan mayoritas dari semua indikator yang dipilih.
        - Filter sinyal di sidebar untuk menampilkan sinyal tertentu.
        - Sinyal yang sering muncul berurutan mengindikasikan kekuatan tren.
        """,)
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
    st.markdown("""
        Fitur ini Untuk dapat melihat kembali hasil analisis terdahulu yang disimpan ke database.
        - Fitur ini untuk membandingkan strategi antar waktu.
        - Analisis ditampilkan sama seperti sebelumnya tanpa dihitung ulang.
        """,)
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
    st.markdown("""
        Fitur ini membandingkan sinyal akhir (`Final_Signal`) dengan arah harga keesokan harinya.
        - Akurasi dihitung dari jumlah sinyal benar (Buy/Sell sesuai arah harga) dibagi total sinyal.
        - Evaluasi ini membantu mengukur keandalan analisis Anda.
        """,)
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_bt = fetch_backtesting_data(ticker, start_date, end_date)
        if not df_bt.empty:
            signal_series = apply_custom_strategy(df_bt, strategy)
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
        if not df_bt.empty and 'Close' in df_bt.columns:
            plot_signal_markers(df_bt)
        else:
            st.warning("Data tidak valid untuk ditampilkan dalam grafik sinyal.")
        # tanpa parameter tambahan

with tab4:
    st.subheader("Backtesting Profit")
    st.markdown(""" 
        Fitur ini mensimulasikan hasil jika strategi diterapkan dengan uang sungguhan ke data historis.
        - Dihitung dengan modal awal, membeli saat sinyal Buy, menjual saat Sell.
        - Memberikan nilai akhir portofolio, profit nominal, dan profit persentase.
        - Semakin positif hasil profit, strategi semakin optimal.
        """,)
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_bt = fetch_backtesting_data(ticker, start_date, end_date)
        if not df_bt.empty:
            signal_series = apply_custom_strategy(df_bt, strategy)
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
    st.markdown("""
        Sistem menganalisis saham menggunakan data terkini dari pasar.
        - Menunjukkan sinyal saat ini berdasarkan indikator yang Anda pilih.
        - Akurasi realtime juga dihitung berdasarkan harga saat ini.
        """,)
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
    st.subheader("Evaluasi Gabungan Indikator")
    st.markdown("""
        Fitur ini akan menguji performa **masing-masing indikator** dan juga seluruh **kombinasi indikator **.
        - Hasil ditampilkan dalam satu tabel gabungan.
    """)
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_eval = get_data_from_db(ticker, interval)
        df_eval = df_eval.loc[start_date:end_date]
        if not df_eval.empty:
            from modules.evaluation_log import evaluate_all_indicator_and_combinations
            df_result_combined = evaluate_all_indicator_and_combinations(ticker, df_eval, params, interval, money)
            st.dataframe(df_result_combined, use_container_width=True)
        else:
            st.warning("Data tidak tersedia untuk ticker dan interval yang dipilih.")

# with tab6:
#     st.subheader("Evaluasi Per Indikator")
#     st.markdown("""
#         Fitur ini untuk mengetahui kinerja masing-masing indikator teknikal jika digunakan secara tunggal.
#         - Sistem akan menghitung akurasi dan profit dari tiap indikator.
#         - Dapat membantu memilih indikator yang paling konsisten.
#         """,)
#     for ticker in tickers:
#         st.markdown(f"### {ticker}")
#         df_eval = get_data_from_db(ticker, interval)
#         df_eval = df_eval.loc[start_date:end_date]
#         if not df_eval.empty:
#             df_result_eval = evaluate_individual_indicators(ticker, df_eval, params, interval, money)
#             st.dataframe(df_result_eval, use_container_width=True)
#         else:
#             st.warning("Data tidak tersedia untuk ticker dan interval yang dipilih.")

# with tab7:
#     st.subheader("Evaluasi Kombinasi Indikator")
#     st.markdown("""
#         Fitur ini untuk melakukan uji performa kombinasi 2–3 indikator sekaligus.
#         - Digunakan untuk menemukan sinergi antar indikator.
#         - Hasil yang bagus berarti kombinasi indikator saling melengkapi.
#         """,)
#     for ticker in tickers:
#         st.markdown(f"### {ticker}")
#         df_eval = get_data_from_db(ticker, interval)
#         df_eval = df_eval.loc[start_date:end_date]
#         if not df_eval.empty:
#             df_combo_result = evaluate_indicator_combinations(ticker, df_eval, params, interval, money)
#             st.dataframe(df_combo_result, use_container_width=True)

with tab7:
    st.subheader("Semua Riwayat Akurasi Strategi")
    st.markdown("""
        Menampilkkan rekapan seluruh strategi yang pernah diuji.
        - Disusun berdasarkan akurasi tertinggi.
        - Gunakan data ini untuk memilih strategi paling konsisten.
        """,)
    from modules.evaluation_log import get_all_accuracy_logs
    all_logs_df = get_all_accuracy_logs()
    if not all_logs_df.empty:
        st.dataframe(all_logs_df, use_container_width=True)

        best_row = all_logs_df.iloc[0]
        st.success(f"Akurasi Tertinggi: {best_row['accuracy']*100:.2f}% | Ticker: {best_row['ticker']} | Strategi: {best_row['strategy']}")
    else:
        st.info("Belum ada data akurasi yang tersedia.")

with tab8:
    from modules.multi_eval import save_multi_ticker_evaluation_to_db
    st.subheader("Evaluasi Gabungan Saham")
    st.markdown("""
    Fitur ini menghitung akurasi dan total profit dari semua ticker yang dipilih menggunakan kombinasi indikator yang sedang aktif.
    """)

    from modules.analysis import evaluate_strategy_accuracy
    from modules.backtesting import run_backtesting_profit, apply_custom_strategy

    total_signals = 0
    total_correct = 0
    total_profit = 0
    total_initial = 0
    total_final = 0
    hasil_ticker = []

    if st.button("Evaluasi Gabungan Akurasi & Profit"):
        for ticker in tickers:
            df_bt = fetch_backtesting_data(ticker, start_date, end_date)
            if df_bt is not None and not df_bt.empty:
                df_bt['Final_Signal'] = compute_final_signal(df_bt, indicators)
                result = evaluate_strategy_accuracy(df_bt.copy())
                signal_series = apply_custom_strategy(df_bt, strategy)
                _, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
                    df_bt, money, signal_series, key_prefix=f"{ticker}_bulk_eval")

                total_signals += result['total_signals']
                total_correct += result['correct_predictions']
                total_profit += gain
                total_initial += money
                total_final += final_value

                hasil_ticker.append({
                    "Ticker": ticker,
                    "Akurasi (%)": round(accuracy * 100, 2),
                    "Profit (Rp)": round(gain, 2),
                    "Final Uang": round(final_value, 2)
                })

        if hasil_ticker:
            df_hasil = pd.DataFrame(hasil_ticker)
            st.markdown("### Ringkasan Per Ticker")
            st.dataframe(df_hasil, use_container_width=True)

            akurasi_total = (total_correct / total_signals) * 100 if total_signals > 0 else 0
            st.markdown("### Akumulasi Gabungan")
            st.metric("Akurasi Gabungan (%)", f"{akurasi_total:.2f}%")
            st.metric("Total Profit (Rp)", f"{total_profit:,.0f}")
            st.metric("Modal Awal Total", f"{total_initial:,.0f}")
            st.metric("Total Nilai Akhir", f"{total_final:,.0f}")
            st.markdown("---")
            save_button = st.button("Simpan Hasil Gabungan ke Database", key="save_combined_eval")
            if save_button:
                success, message = save_multi_ticker_evaluation_to_db(
                    tickers=tickers,
                    interval=interval,
                    indicators_dict=indicators,
                    strategy=strategy,
                    start_date=start_date,
                    end_date=end_date,
                    total_accuracy=akurasi_total,
                    total_profit=total_profit,
                    total_money=total_initial,
                    final_money=total_final
                )
                if success:
                    st.success(message)
                else:
                    st.warning(message)
        else:
            st.warning("Tidak ada data valid untuk dianalisis.")


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


# Cards
# with cols[1]:
#     df_show = df_sorted.iloc[slide_index:slide_index + per_page]
#     card_cols = st.columns(len(df_show))
#     for i, (_, row) in enumerate(df_show.iterrows()):
#         color = "green" if row['accuracy'] >= 0.5 else "red"
#         with card_cols[i]:
#             st.markdown(f"""
#                 <div style='padding: 10px; border-radius: 10px; background-color: #f9f9f9; border: 1px solid #ddd; text-align:center;'>
#                     <strong>{row['ticker']}</strong><br>
#                     <span style='color: {color}; font-size: 18px; font-weight: bold;'>{row['accuracy']*100:.2f}%</span><br>
#                     <span style='font-size: 14px;'>{row['indicators']}</span><br>
#                     <span style='font-size: 13px;'>({row['strategy']})</span>
#                 </div>
#             """, unsafe_allow_html=True)