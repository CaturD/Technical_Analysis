import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from modules.database import get_ticker_list, get_data_from_db
# from modules.evaluation_log import get_all_accuracy_logs
from modules.indicators import compute_indicators
from modules.visuals import plot_indicators, plot_signal_pairs
from modules.backtesting import show_indicator_explanation
from modules.next_step import generate_next_step_recommendation
from modules.evaluation_log import get_top_strategies_by_profit
# from modules.evaluate_best_strategy import evaluate_strategies_combined
from modules.analysis import (
    compute_final_signal, display_analysis_table_with_summary, save_analysis_to_json_db,
    fetch_saved_titles, load_analysis_by_title, show_signal_recap, evaluate_strategy_accuracy
)
from modules.backtesting import (
    fetch_backtesting_data, run_backtesting_profit,
    save_backtesting_to_db, plot_accuracy_history, evaluate_signal_pairs, show_indicator_explanation,
    # evaluate_individual_indicators
    evaluate_individual_indicators, experiment_buy_sell_combinations
)
from modules.evaluation_log import (
    evaluate_indicator_combinations, get_all_accuracy_logs, save_accuracy_evaluation_to_db,
)
from modules.evaluate_best_strategy import evaluate_strategies_combined
from modules.multi_eval import save_multi_ticker_evaluation_to_db
from modules.best_indicator import get_best_indicator
from modules.strategy_utils import generate_combination_results

# Jalankan di awal main.py
import mysql.connector

def display_accuracy_result(result, label="Akurasi Historis"):
    if result:
        st.metric(label, f"{result['accuracy']*100:.2f}%")
        with st.expander("Distribusi Sinyal"):
            df = pd.DataFrame(
                [{'Sinyal': k, 'Jumlah': v} for k, v in result['signal_distribution'].items()]
            )
            st.dataframe(df, use_container_width=True)

st.set_page_config(layout="wide")
st.markdown("""
    <h1 style='text-align: center;'>DASHBOARD TREND HARGA SAHAM</h1>
""", unsafe_allow_html=True)
st.markdown("""
Dashboard ini digunakan untuk menganalisis dan memprediksi arah tren harga saham menggunakan berbagai indikator teknikal populer seperti Moving Average, MACD, Ichimoku Cloud, dan lainnya.
Dengan fitur analisis dan backtesting untuk:
- Mengetahui sinyal buy, sell, atau hold.
- Melihat performa strategi berdasarkan data historis.
- Mengevaluasi efektivitas kombinasi indikator dengan menggunakan filter di sidebar untuk menyesuaikan analisis dengan preferensi Anda.
""")

# Load data
# df_logs = get_all_accuracy_logs()
# if not df_logs.empty and 'accuracy' in df_logs.columns:
#     df_logs = get_top_strategies_by_profit(20)
df_logs = get_top_strategies_by_profit(20)
if not df_logs.empty and 'profit' in df_logs.columns:
    df_sorted = df_logs.sort_values(by='profit', ascending=False).reset_index(drop=True)
# else:
elif df_logs.empty:
    st.warning("Belum ada data strategi yang tersimpan atau tabel belum tersedia.")
    df_sorted = pd.DataFrame()
else:
    df_sorted = df_logs.reset_index(drop=True)

st.markdown("#### Top Strategi Saham Berdasarkan Profit")

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
            with card_cols[i]:
                if {'start_date', 'end_date'}.issubset(df_show.columns) and \
                        pd.notnull(row.get('start_date')) and pd.notnull(row.get('end_date')):
                    periode = f"{row['start_date']} - {row['end_date']}"
                else:
                    periode = '-'

                color = 'green' if row.get('profit_percentage', 0) >= 0 else 'red'

                st.markdown(
                    f"""
                    <div style='padding: 10px; border-radius: 10px; background-color: #f9f9f9; border: 1px solid #ddd; text-align:center;'>
                        <strong style='color:{color};'>{row['ticker']}</strong><br>
                        <span style='font-size: 13px;'>Profit: {row['profit_percentage']:.2f}%</span><br>
                        <span style='font-size: 13px;'>Akurasi: {row['accuracy']*100:.2f}%</span><br>
                        <span style='font-size: 13px;'>Periode: {periode}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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
start_date = st.sidebar.date_input("Tanggal Mulai", datetime(2024, 5, 31))
end_date = st.sidebar.date_input("Tanggal Selesai", datetime(2025, 5, 31))
money = st.sidebar.number_input("Modal Awal (Rp)", value=1_000_000, step=500_000)

# Indikator yang digunakan
indicators = {
    "Ichimoku": st.sidebar.checkbox("Ichimoku", value=True),
    "MA": st.sidebar.checkbox("Moving Average", value=True),
    "MACD": st.sidebar.checkbox("MACD", value=True),
    "SO": st.sidebar.checkbox("Stochastic Oscillator", value=True),
    "Volume": st.sidebar.checkbox("Volume", value=True)
}

if sum(indicators.values()) == 1:
    st.info("Anda hanya mengaktifkan 1 indikator. Final_Signal akan mengikuti sinyal dari indikator tersebut.")
elif sum(indicators.values()) == 0:
    st.error("Tidak ada indikator aktif. Silakan aktifkan minimal 1 indikator.")
    st.stop()

# Filter sinyal
signal_filter = st.sidebar.multiselect(
    "Filter Sinyal", ['Buy', 'Sell', 'Hold'], default=['Buy', 'Sell', 'Hold']
)

# perubahan parameter indikator
with st.sidebar.expander("Setting Parameter Indikator"):
    params = {
        'ma5': st.number_input("MA5", value=5, min_value=1),
        'ma10': st.number_input("MA10", value=10, min_value=1),
        'ma20': st.number_input("MA20", value=20, min_value=1),
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
# tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_panduan = st.tabs([
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_panduan = st.tabs([
    "Analisis",
    "Analisis Tersimpan",
    "Backtesting Analisis",
    "Backtesting Profit",
    "Semua Akurasi Strategi",
    "Evaluasi Gabungan",
    "Evaluasi Strategi Terbaik",
    # "Winrate Evaluasi Strategi",
    "Panduan Dashboard"
])

with tab1:
    st.subheader("Analisis Saham")
    st.markdown("""
        Fitur ini menghitung indikator teknikal untuk menentukan sinyal akhir: **Buy**, **Sell**, atau **Hold**.
        - Sinyal ditentukan dengan mayoritas dari semua indikator yang dipilih.
        - Filter sinyal di sidebar untuk menampilkan sinyal tertentu.
        - Sinyal yang sering muncul berurutan mengindikasikan kekuatan tren.
    """)
    for ticker in tickers:
        st.markdown(f"### {ticker}")
        data = get_data_from_db(ticker, interval)
        if not data.empty:
            data = compute_indicators(data, indicators, params)
            data['Final_Signal'] = compute_final_signal(data, indicators)
            data_in_range = data.loc[start_date:end_date]
            plot_indicators(data_in_range, indicators)
            show_indicator_explanation(indicators)  
            display_analysis_table_with_summary(data_in_range, indicators, signal_filter)
            save_analysis_to_json_db(ticker, data_in_range, indicators)

        st.markdown("Tren Pergerakan Saham Tahunan per Indikator & Kombinasi")

        # Tambahkan kolom tahun dari index
        data['Year'] = data.index.year

        def tentukan_tren(grup):
            buy = (grup == 'Buy').sum()
            sell = (grup == 'Sell').sum()
            total = len(grup)
            if buy / total > 0.4:
                return "Uptrend"
            elif sell / total > 0.4:
                return "Downtrend"
            else:
                return "Sideways"

        tren_rows = []

        # Indikator individual
        for indikator in ['Signal_MA', 'Signal_MACD', 'Signal_Ichimoku', 'Signal_SO', 'Signal_Volume']:
            if indikator in data.columns:
                tren_dict = {'Ticker': ticker, 'Indikator': indikator.replace("Signal_", "")}
                for tahun in [2022, 2023, 2024, 2025]:
                    df_tahun = data[data['Year'] == tahun]
                    if not df_tahun.empty:
                        tren = tentukan_tren(df_tahun[indikator])
                    else:
                        tren = '-'
                    tren_dict[f'Tren {tahun}'] = tren
                tren_rows.append(tren_dict)

        # Kombinasi indikator aktif (Final_Signal)
        tren_combo = {'Ticker': ticker, 'Indikator': 'Kombinasi'}
        for tahun in [2022, 2023, 2024, 2025]:
            df_tahun = data[data['Year'] == tahun]
            if not df_tahun.empty:
                tren = tentukan_tren(df_tahun['Final_Signal'])
            else:
                tren = '-'
            tren_combo[f'Tren {tahun}'] = tren
        tren_rows.append(tren_combo)

        # Buat dan tampilkan tabel
        df_tren_multi = pd.DataFrame(tren_rows)
        st.dataframe(df_tren_multi, use_container_width=True)

        st.markdown("#### Total Sinyal per Indikator")

        indikator_aktif = [k for k, v in indicators.items() if v]
        sinyal_ringkasan = []

        # Hitung jumlah sinyal per indikator aktif
        for indikator in indikator_aktif:
            kolom = f"Signal_{indikator}"
            if kolom in data.columns:
                sinyal_counts = data[kolom].value_counts().to_dict()

                if indikator == 'Volume':
                    sinyal_ringkasan.append({
                        'Indikator': indikator,
                        'High Volume': sinyal_counts.get('High Volume', 0),
                        'Low Volume': sinyal_counts.get('Low Volume', 0),
                        'Hold': '-'  # tidak relevan
                    })
                else:
                    sinyal_ringkasan.append({
                        'Indikator': indikator,
                        'Buy': sinyal_counts.get('Buy', 0),
                        'Sell': sinyal_counts.get('Sell', 0),
                        'Hold': sinyal_counts.get('Hold', 0)
                    })

        df_sinyal_summary = pd.DataFrame(sinyal_ringkasan)
        st.dataframe(df_sinyal_summary, use_container_width=True)


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

    st.subheader("Backtesting Analisis")
    st.markdown("""
        Fitur ini membandingkan sinyal akhir (`Final_Signal`) dengan arah harga keesokan harinya.
        - Akurasi dihitung dari jumlah sinyal benar (Buy/Sell sesuai arah harga) dibagi total sinyal.
        - Evaluasi ini membantu mengukur keandalan analisis Anda.
    """)

    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_bt = fetch_backtesting_data(ticker, start_date, end_date)

        if df_bt.empty:
            st.warning("Data tidak tersedia.")
            continue
        df_bt = compute_indicators(df_bt, indicators, params)
        df_bt['Final_Signal'] = compute_final_signal(df_bt, indicators)
        signal_series = df_bt['Final_Signal']
        df_pairs = evaluate_signal_pairs(df_bt, signal_series)
        if not df_pairs.empty and 'Profit (%)' in df_pairs.columns:
            num_profit = (df_pairs['Profit (%)'] > 0).sum()
            total = len(df_pairs)
            acc_pair = (num_profit / total) * 100
            st.metric("Akurasi Pasangan Sinyal", f"{acc_pair:.2f}%")

        if not df_pairs.empty and 'Hold Days' in df_pairs.columns:
            up_days = df_pairs[df_pairs['Trend'] == 'Uptrend']['Hold Days'].mean()
            down_days = df_pairs[df_pairs['Trend'] == 'Downtrend']['Hold Days'].mean()
            # if not pd.isna(up_days):
            #     st.metric("Rata-rata Hold Uptrend", f"{up_days:.1f} hari")
            # if not pd.isna(down_days):
            #     st.metric("Rata-rata Hold Downtrend", f"{down_days:.1f} hari")


        st.subheader("Evaluasi Pasangan Sinyal")
        if df_pairs.empty:
            st.warning("Tidak ada pasangan sinyal valid ditemukan.")
        else:
            st.dataframe(df_pairs, use_container_width=True)
            # plot_signal_pairs(df_bt, df_pairs)
            plot_signal_pairs(df_bt, df_pairs, show_lines=True)

            st.subheader("Grafik Profit per Pasangan Sinyal")
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Bar(
                x=[f"Pasangan {i+1}" for i in range(len(df_pairs))],
                y=df_pairs['Profit'],
                marker_color=['green' if x >= 0 else 'red' for x in df_pairs['Profit']],
                text=df_pairs['Profit'],
                textposition='outside'
            ))
            fig_profit.update_layout(
                xaxis_title="Pasangan Buy–Sell",
                yaxis_title="Profit (Rp)",
                height=400,
                margin=dict(l=20, r=20, t=40, b=40)
            )
            st.plotly_chart(fig_profit, use_container_width=True)

            st.subheader("Pasangan All Sinyal")
            st.markdown(
                """
                Tab ini menguji berbagai kombinasi antara urutan sinyal **Buy** ke-n
                dengan beberapa sinyal **Sell** setelahnya. Hasil profit setiap
                kombinasi ditampilkan pada tabel berikut.
                """
            )
            df_combo = experiment_buy_sell_combinations(df_bt, signal_series)
            if df_combo.empty:
                st.info("Tidak ada kombinasi pasangan all buy/sell yang valid.")
            else:
                st.dataframe(df_combo, use_container_width=True)

                if 'Hold Days' in df_combo.columns:
                    up_days = df_combo[df_combo['Trend'] == 'Uptrend']['Hold Days'].mean()
                    down_days = df_combo[df_combo['Trend'] == 'Downtrend']['Hold Days'].mean()
                    # col1, col2 = st.columns(2)
                    # if not pd.isna(up_days):
                    #     col1.metric("Rata-rata Hold Uptrend", f"{up_days:.1f} hari")
                    # if not pd.isna(down_days):
                    #     col2.metric("Rata-rata Hold Downtrend", f"{down_days:.1f} hari")

                plot_signal_pairs(df_bt, df_combo, show_lines=False)

        st.markdown("---")
        st.subheader("Rekomendasi Langkah Selanjutnya")
        try:
            if not df_bt.empty and 'Final_Signal' in df_bt.columns:
                next_step = generate_next_step_recommendation(df_bt, indicators)
                st.markdown(f"""
                **Ticker:** `{ticker}`  
                **Tanggal terakhir data:** `{next_step['date']}`  
                **Rekomendasi:** **{next_step['recommendation']}**  
                **Keyakinan:** `{next_step['confidence']}`  
                **Alasan Pendukung:**  
                """)
                for reason in next_step['reasons']:
                    st.write(f"- {reason}")
            else:
                st.warning("Data atau sinyal tidak tersedia untuk rekomendasi.")
        except Exception as e:
            st.error(f"Gagal menampilkan rekomendasi langkah selanjutnya: {e}")


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
            df_bt = compute_indicators(df_bt, indicators, params)
            df_bt['Final_Signal'] = compute_final_signal(df_bt, indicators)
            signal_series = df_bt['Final_Signal']
            result_profit = result_profit = evaluate_strategy_accuracy(df_bt.copy())
            from modules.evaluation_log import save_accuracy_evaluation_to_db
            save_accuracy_evaluation_to_db(
                ticker=ticker,
                interval=interval,
                strategy="Final_Signal",
                indicators_dict=indicators,
                params_dict=params,
                accuracy_value=result_profit["accuracy"]
            )
            display_accuracy_result(result_profit, "Akurasi Backtesting Profit")
            df_result, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
            df_bt, money, signal_series, key_prefix=f"{ticker}_{interval}_tab4"
            )
            # save_backtesting_to_db(ticker, money, final_value, gain, gain_pct, accuracy)
            save_backtesting_to_db(
                ticker, money, final_value, gain, gain_pct, accuracy,
                start_date, end_date
            )
            plot_accuracy_history(ticker)

with tab5:
    st.subheader("Semua Riwayat Akurasi Strategi")
    st.markdown("""
        Menampilkkan rekapan seluruh strategi yang pernah diuji.
        - Disusun berdasarkan akurasi tertinggi.
        - Gunakan data ini untuk memilih strategi paling konsisten.
        """,)
    # from modules.evaluation_log import get_all_accuracy_logs
    all_logs_df = get_all_accuracy_logs()
    if not all_logs_df.empty:
        st.dataframe(all_logs_df, use_container_width=True)

        best_row = all_logs_df.iloc[0]
        st.success(f"Akurasi Tertinggi: {best_row['accuracy']*100:.2f}% | Ticker: {best_row['ticker']} | Strategi: {best_row['strategy']}")
    else:
        st.info("Belum ada data akurasi yang tersedia.")

with tab6:
    from modules.multi_eval import save_multi_ticker_evaluation_to_db
    st.subheader("Evaluasi Gabungan Saham")
    st.markdown("""
    Fitur ini menghitung akurasi dan total profit dari semua ticker yang dipilih menggunakan kombinasi indikator yang sedang aktif.
    """)

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
                signal_series = df_bt['Final_Signal']
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
                    strategy="Final_Signal",
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

with tab7:
    st.subheader("Evaluasi Strategi Terbaik (Per Indikator & Kombinasi)")
    st.markdown(
        """
        Fitur ini mengevaluasi dan membandingkan performa dari:
        - Setiap indikator teknikal secara individual
        - Kombinasi 2–5 indikator
        - Strategi logika seperti All Agree, Final Signal, dll
        Output berupa tabel & grafik akurasi dan profit. Di bawah tabel
        strategi, ditampilkan juga indikator tunggal dengan profit tertinggi.
        """
    )

    for ticker in tickers:
        st.markdown(f"### {ticker}")
        df_eval = get_data_from_db(ticker, interval)
        df_eval = df_eval.loc[start_date:end_date]
        if not df_eval.empty:
            df_result = evaluate_strategies_combined(
                ticker, df_eval, params, interval, money
            )
            st.dataframe(df_result, use_container_width=True)

            st.markdown("**Indikator Tunggal Terbaik**")
            best_row, df_best = get_best_indicator(
                ticker, df_eval, params, interval, money
            )
            st.dataframe(df_best, use_container_width=True)
            if best_row:
                st.success(
                    f"Indikator terbaik: {best_row['Indikator']} - Profit Rp{best_row['Keuntungan (Rp)']:,.0f} "
                    f"({best_row['Keuntungan (%)']:.2f}%)"
                )
            else:
                st.warning("Tidak ada hasil evaluasi yang dapat ditentukan.")
        else:
            st.warning(
                "Data tidak tersedia untuk ticker dan interval yang dipilih."
            )

# with tab_exp:
#     st.subheader("Eksperimen Buy/Sell")
#     st.markdown(
#         """
#         Tab ini menguji berbagai kombinasi antara urutan sinyal **Buy** ke-n
#         dengan beberapa sinyal **Sell** setelahnya. Hasil profit setiap
#         kombinasi ditampilkan pada tabel berikut.
#         """
#     )
#     for ticker in tickers:
#         st.markdown(f"### {ticker}")
#         df_bt = fetch_backtesting_data(ticker, start_date, end_date)
#         if df_bt.empty:
#             st.warning("Data tidak tersedia.")
#             continue
#         df_bt = compute_indicators(df_bt, indicators, params)
#         df_bt['Final_Signal'] = compute_final_signal(df_bt, indicators)
#         signal_series = df_bt['Final_Signal']
#         df_combo = experiment_buy_sell_combinations(df_bt, signal_series)
#         if df_combo.empty:
#             st.info("Tidak ada kombinasi buy/sell yang valid.")
#         else:
#             st.dataframe(df_combo, use_container_width=True)

#             if 'Hold Days' in df_combo.columns:
#                 up_days = df_combo[df_combo['Trend'] == 'Uptrend']['Hold Days'].mean()
#                 down_days = df_combo[df_combo['Trend'] == 'Downtrend']['Hold Days'].mean()
#                 col1, col2 = st.columns(2)
#                 if not pd.isna(up_days):
#                     col1.metric("Rata-rata Hold Uptrend", f"{up_days:.1f} hari")
#                 if not pd.isna(down_days):
#                     col2.metric("Rata-rata Hold Downtrend", f"{down_days:.1f} hari")

#             # Hide dashed connectors for the experiment tab
#             plot_signal_pairs(df_bt, df_combo, show_lines=False)

with tab_panduan:
    st.subheader("Panduan Penggunaan Dashboard")
    st.markdown("""
    Dashboard ini dirancang untuk membantu pengguna menganalisis dan mengevaluasi arah tren harga saham berdasarkan indikator teknikal.

    ### Tujuan
    - Menentukan waktu terbaik untuk beli (Buy), jual (Sell), atau tahan (Hold)
    - Membandingkan strategi berdasarkan **akurasi** dan **profit historis**
    - Menguji kombinasi indikator dan strategi logika

    ### Penjelasan Fitur
    - **Analisis Saham**: Menampilkan sinyal dari indikator teknikal dan sinyal gabungan (`Final Signal`) berdasarkan voting mayoritas.
    - **Backtesting Analisis**: Mengukur akurasi sinyal terhadap arah harga keesokan harinya.
    - **Backtesting Profit**: Simulasi keuntungan jika strategi dijalankan dengan modal sungguhan.
    - **Evaluasi Gabungan**: Menggabungkan hasil dari beberapa saham untuk melihat akurasi dan total keuntungan.
    - **Strategi Terbaik**: Menampilkan hasil evaluasi setiap indikator dan kombinasi strategi.

    ### Cara Membaca Sinyal
    - **Buy**: Disarankan untuk membeli karena sinyal teknikal menunjukkan potensi kenaikan harga.
    - **Sell**: Disarankan menjual karena potensi harga turun.
    - **Hold**: Tidak ada sinyal jelas, tunggu konfirmasi dari pasar.

    ### Tips Interpretasi
    - Sinyal yang **muncul berurutan** cenderung lebih kuat (misal: Buy muncul 3 hari berturut-turut).
    - Kombinasi beberapa indikator lebih stabil dibanding 1 indikator tunggal.
    - Perhatikan **akurasi** dan **profit** secara bersamaan untuk memilih strategi terbaik.

    ### Tentang Parameter Indikator
    - Anda bisa menyesuaikan parameter seperti MA period, MACD Fast/Slow, dll. di sidebar.
    - Parameter default mengikuti literatur umum namun bisa diubah sesuai karakteristik saham.

    """)

