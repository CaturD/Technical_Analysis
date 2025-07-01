import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from modules.indicators import compute_indicators
from modules.analysis import compute_final_signal
from modules.custom_strategies import apply_custom_strategy
from modules.backtesting import run_backtesting_profit
from itertools import combinations

# Evaluasi semua strategi: individual, kombinasi, dan logika

def evaluate_strategies_combined(ticker, df, params, interval, money):
    from modules.indicators import compute_indicators
    from modules.analysis import compute_final_signal
    from modules.custom_strategies import apply_custom_strategy
    from modules.backtesting import run_backtesting_profit
    from itertools import combinations

    indikator_list = ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']
    results = []

    # Evaluasi indikator satu per satu
    for ind in indikator_list:
        ind_dict = {key: (key == ind) for key in indikator_list}
        df_ind = compute_indicators(df.copy(), ind_dict, params)
        df_ind['Final_Signal'] = compute_final_signal(df_ind, ind_dict)
        signal_series = apply_custom_strategy(df_ind, f"{ind} Only")
        try:
            _, final_value, gain, gain_pct, winrate = run_backtesting_profit(
                df_ind, money, signal_series, key_prefix=f"{ticker}_{ind}_single", enable_download=False)
            results.append({
                "Indikator / Kombinasi": f"{ind} Only",
                "Win Rate (%)": round(winrate * 100, 2),
                "Profit (Rp)": round(gain, 2),
                "Profit (%)": round(gain_pct, 2)
            })
        except Exception as e:
            results.append({"Indikator / Kombinasi": f"{ind} Only", "Error": str(e)})

    # Evaluasi kombinasi indikator (2–5)
    for r in [2, 3, 4, 5]:
        for combo in combinations(indikator_list, r):
            combo_dict = {key: key in combo for key in indikator_list}
            df_combo = compute_indicators(df.copy(), combo_dict, params)
            df_combo['Final_Signal'] = compute_final_signal(df_combo, combo_dict)
            signal_series = apply_custom_strategy(df_combo, "Final Signal")
            try:
                combo_key = f"{ticker}_{'_'.join(sorted(combo))}"
                _, final_value, gain, gain_pct, winrate = run_backtesting_profit(
                    df_combo, money, signal_series, key_prefix=combo_key, enable_download=False)
                results.append({
                    "Indikator / Kombinasi": f"Kombinasi: {', '.join(combo)}",
                    "Win Rate (%)": round(winrate * 100, 2),
                    "Profit (Rp)": round(gain, 2),
                    "Profit (%)": round(gain_pct, 2)
                })
            except Exception as e:
                results.append({"Indikator / Kombinasi": f"Kombinasi: {', '.join(combo)}", "Error": str(e)})

    # Buat DataFrame hasil
    df_result = pd.DataFrame(results)
    if "Winrate (%)" in df_result.columns:
        df_result.rename(columns={"Winrate (%)": "Win Rate (%)"}, inplace=True)
    if 'Profit (Rp)' in df_result.columns:
        df_result = df_result.sort_values(by="Profit (Rp)", ascending=False).reset_index(drop=True)
    else:
        df_result = df_result.reset_index(drop=True)

    # Tampilkan grafik jika data tersedia
    if 'Profit (%)' in df_result.columns and df_result['Profit (%)'].notna().any():
        st.subheader("Grafik Profit per Indikator/Kombinasi")
        clean_profit_pct = df_result['Profit (%)'].fillna(0)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_result['Indikator / Kombinasi'],
            y=clean_profit_pct,
            marker_color=['green' if x >= 0 else 'red' for x in clean_profit_pct],
            text=[f"{x:.2f}%" for x in clean_profit_pct],
            textposition="outside"
        ))
        fig.update_layout(
            height=450,
            xaxis_tickangle=-30,
            xaxis_title="Indikator/Kombinasi",
            yaxis_title="Profit (%)",
            margin=dict(l=20, r=20, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)
        # Tampilkan kombinasi terbaik berdasarkan profit
        if 'Profit (Rp)' in df_result.columns and df_result['Profit (Rp)'].notna().any():
            df_filtered = df_result[df_result['Indikator / Kombinasi'].str.startswith("Kombinasi")]
            if not df_filtered.empty:
                top_combo = df_filtered.loc[df_filtered['Profit (Rp)'].idxmax()]
                st.success(f"Kombinasi terbaik: **{top_combo['Indikator / Kombinasi']}** "
                        f"(Profit: Rp{top_combo['Profit (Rp)']:,.1f} | "
                        f"Win Rate: {top_combo['Win Rate (%)']:.2f}%)")
    else:
        st.info("Tidak ada data 'Profit (%)' yang valid untuk ditampilkan dalam grafik.")

    return df_result
