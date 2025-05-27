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
    indikator_list = ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']
    results = []

    # Strategi individu
    for ind in indikator_list:
        ind_dict = {key: (key == ind) for key in indikator_list}
        df_ind = compute_indicators(df.copy(), ind_dict, params)
        df_ind['Final_Signal'] = compute_final_signal(df_ind, ind_dict)
        signal_series = apply_custom_strategy(df_ind, f"{ind} Only")
        try:
            _, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
                df_ind, money, signal_series, key_prefix=f"{ticker}_{ind}_single", enable_download=False)
            results.append({
                "Strategi": f"{ind} Only",
                "Akurasi (%)": round(accuracy * 100, 2),
                "Profit (Rp)": round(gain, 2),
                "Profit (%)": round(gain_pct, 2)
            })
        except Exception as e:
            results.append({"Strategi": f"{ind} Only", "Error": str(e)})

    # Kombinasi indikator (2–5)
    for r in [2, 3, 4, 5]:
        for combo in combinations(indikator_list, r):
            combo_dict = {key: key in combo for key in indikator_list}
            df_combo = compute_indicators(df.copy(), combo_dict, params)
            df_combo['Final_Signal'] = compute_final_signal(df_combo, combo_dict)
            signal_series = apply_custom_strategy(df_combo, "Final Signal")
            try:
                _, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
                    df_combo, money, signal_series, key_prefix=f"{ticker}_{'_'.join(combo)}", enable_download=False)
                results.append({
                    "Strategi": f"Kombinasi: {', '.join(combo)}",
                    "Akurasi (%)": round(accuracy * 100, 2),
                    "Profit (Rp)": round(gain, 2),
                    "Profit (%)": round(gain_pct, 2)
                })
            except Exception as e:
                results.append({"Strategi": f"Kombinasi: {', '.join(combo)}", "Error": str(e)})

    # Strategi logika tambahan
    logic_strategies = [
        "Ichimoku + MA Only", "All Agree", "3 of 5 Majority",
        "MACD + Volume Confirm", "Ichimoku + MA Trend", "SO + MACD",
        "Final Signal", "Buy & Hold"
    ]
    full_dict = {key: True for key in indikator_list}
    df_full = compute_indicators(df.copy(), full_dict, params)
    df_full['Final_Signal'] = compute_final_signal(df_full, full_dict)

    for strat in logic_strategies:
        try:
            signal_series = apply_custom_strategy(df_full.copy(), strat)
            _, final_value, gain, gain_pct, accuracy = run_backtesting_profit(
                df_full, money, signal_series, key_prefix=f"{ticker}_{strat.replace(' ', '_')}", enable_download=False)
            results.append({
                "Strategi": strat,
                "Akurasi (%)": round(accuracy * 100, 2),
                "Profit (Rp)": round(gain, 2),
                "Profit (%)": round(gain_pct, 2)
            })
        except Exception as e:
            results.append({"Strategi": strat, "Error": str(e)})

    df_result = pd.DataFrame(results).sort_values(by="Profit (Rp)", ascending=False).reset_index(drop=True)

    if not df_result.empty:
        st.subheader("Grafik Profit per Strategi")
        clean_profit_pct = df_result['Profit (%)'].fillna(0)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_result['Strategi'],
            y=clean_profit_pct,
            marker_color=['green' if x >= 0 else 'red' for x in clean_profit_pct],
            text=[f"{x:.2f}%" for x in clean_profit_pct],
            textposition="outside"
        ))
        fig.update_layout(
            height=450,
            xaxis_tickangle=-30,
            xaxis_title="Strategi",
            yaxis_title="Profit (%)",
            margin=dict(l=20, r=20, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    return df_result
