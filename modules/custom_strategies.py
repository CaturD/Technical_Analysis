import pandas as pd

def apply_custom_strategy(df, strategy):
    if strategy == "Final Signal":
        return df['Final_Signal']

    elif strategy == "Buy & Hold":
        signals = ['Hold'] * len(df)
        if len(df) > 1:
            signals[0], signals[-1] = 'Buy', 'Sell'
        return pd.Series(signals, index=df.index)

    elif strategy.endswith("Only"):
        key = strategy.replace(" Only", "")
        col = f"Signal_{key}" if key != 'Volume' else 'Signal_Volume'
        if key == 'Volume':
            return df.get(col, pd.Series(['Hold'] * len(df), index=df.index)).replace({
                'High Volume': 'Buy',
                'Low Volume': 'Sell'
            })
        return df.get(col, pd.Series(['Hold'] * len(df), index=df.index))

    elif strategy == "Ichimoku + MA Only":
        return df.apply(lambda row:
            row['Signal_Ichimoku'] if row['Signal_Ichimoku'] == row['Signal_MA'] and row['Signal_Ichimoku'] in ['Buy', 'Sell']
            else 'Hold', axis=1)

    elif strategy == "All Agree":
        return df.apply(lambda row:
            'Buy' if all(row.get(f"Signal_{i}") == 'Buy' for i in ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume'])
            else 'Sell' if all(row.get(f"Signal_{i}") == 'Sell' for i in ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume'])
            else 'Hold', axis=1)

    elif strategy == "3 of 5 Majority":
        def majority(row):
            signals = [row.get(f"Signal_{i}") for i in ['MA', 'MACD', 'Ichimoku', 'SO', 'Volume']]
            buy = signals.count('Buy')
            sell = signals.count('Sell')
            return 'Buy' if buy >= 3 else 'Sell' if sell >= 3 else 'Hold'
        return df.apply(majority, axis=1)

    elif strategy == "MACD + Volume Confirm":
        return df.apply(lambda row:
            'Buy' if row.get('Signal_MACD') == 'Buy' and row.get('Signal_Volume') == 'High Volume'
            else 'Sell' if row.get('Signal_MACD') == 'Sell' and row.get('Signal_Volume') == 'Low Volume'
            else 'Hold', axis=1)

    elif strategy == "Ichimoku + MA Trend":
        return df.apply(lambda row:
            'Buy' if row.get('Signal_Ichimoku') == 'Buy' and row.get('MA5', 0) > row.get('MA20', 0)
            else 'Sell' if row.get('Signal_Ichimoku') == 'Sell' and row.get('MA5', 0) < row.get('MA20', 0)
            else 'Hold', axis=1)

    elif strategy == "SO + MACD":
        return df.apply(lambda row:
            'Buy' if row.get('Signal_SO') == 'Buy' and row.get('Signal_MACD') == 'Buy'
            else 'Sell' if row.get('Signal_SO') == 'Sell' and row.get('Signal_MACD') == 'Sell'
            else 'Hold', axis=1)

    else:
        return pd.Series(['Hold'] * len(df), index=df.index)