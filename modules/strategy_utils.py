import pandas as pd
from itertools import combinations
from modules.indicators import compute_indicators
from modules.analysis import compute_final_signal
from modules.custom_strategies import apply_custom_strategy
from modules.backtesting import run_backtesting_profit

def generate_combination_results(ticker, df, indikator_list, params, interval, money):
    results = []

    for r in [2, 3, 4, 5]:
        for combo in combinations(indikator_list, r):
            combo_dict = {key: key in combo for key in indikator_list}
            df_eval = compute_indicators(df.copy(), combo_dict, params)
            df_eval['Final_Signal'] = compute_final_signal(df_eval, combo_dict)
            signal_series = apply_custom_strategy(df_eval, "Final Signal")
            try:
                _, final_value, gain, gain_pct, winrate = run_backtesting_profit(
                    df_eval, money, signal_series, key_prefix=f"{ticker}_{'_'.join(combo)}"
                )
                results.append({
                    'Kombinasi': ', '.join(combo),
                    'Win Rate': round(winrate * 100, 2),
                    'Keuntungan (Rp)': round(gain),
                    'Keuntungan (%)': round(gain_pct, 2)
                })
            except:
                continue

    return pd.DataFrame(results).sort_values(by='Keuntungan (%)', ascending=False).reset_index(drop=True)
