# modules/next_step.py
import pandas as pd

def generate_next_step_recommendation(df, indicators):
    result = {
        'date': df.index[-1].strftime('%Y-%m-%d'),
        'recommendation': 'Hold',
        'confidence': '60%',
        'reasons': []
    }

    signal = df['Final_Signal'].iloc[-1]
    result['recommendation'] = signal

    # MA
    if indicators.get("MA") and 'Signal_MA' in df.columns and df['Signal_MA'].iloc[-1] == signal:
        result['reasons'].append("Moving Average mendukung pergerakan sinyal ini")

    # MACD
    if indicators.get("MACD") and 'Signal_MACD' in df.columns and df['Signal_MACD'].iloc[-1] == signal:
        result['reasons'].append("MACD menunjukkan arah yang selaras")

    # Volume
    if indicators.get("Volume") and 'Signal_Volume' in df.columns:
        volume_signal = df['Signal_Volume'].iloc[-1]
        if signal == 'Buy' and volume_signal == 'High Volume':
            result['reasons'].append("Volume menunjukkan tekanan beli yang tinggi")
        elif signal == 'Sell' and volume_signal == 'Low Volume':
            result['reasons'].append("Volume menunjukkan tekanan jual yang tinggi")

    # Ichimoku
    if indicators.get("Ichimoku") and 'Signal_Ichimoku' in df.columns and df['Signal_Ichimoku'].iloc[-1] == signal:
        result['reasons'].append("Ichimoku mendukung arah sinyal ini")

    # Stochastic Oscillator (SO)
    if indicators.get("SO") and 'Signal_SO' in df.columns and df['Signal_SO'].iloc[-1] == signal:
        result['reasons'].append("Stochastic Oscillator mendukung arah pergerakan sinyal ini")

    # Hitung confidence
    confidence_score = 60 + 10 * len(result['reasons'])
    result['confidence'] = f"{min(confidence_score, 99)}%"

    return result
