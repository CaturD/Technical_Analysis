# FUNGSI NORNAL TIDAK MERUBAH INDIKATOR
# import talib as ta
# import pandas as pd

# def compute_indicators(data, indicators):
#     # Moving Averages
#     if indicators.get('MA'):
#         data['MA20'] = ta.SMA(data['Close'], timeperiod=20)
#         data['MA50'] = ta.SMA(data['Close'], timeperiod=50)
#         data['Signal_MA'] = 'Hold'
#         threshold = 0.01
#         diff = abs(data['MA20'] - data['MA50']) / data['MA50']
#         data.loc[(data['MA20'] > data['MA50']) & (diff > threshold), 'Signal_MA'] = 'Buy'
#         data.loc[(data['MA20'] < data['MA50']) & (diff > threshold), 'Signal_MA'] = 'Sell'

#     # MACD
#     if indicators.get('MACD'):
#         data['MACD'], data['MACD_signal'], data['MACD_hist'] = ta.MACD(
#             data['Close'], fastperiod=12, slowperiod=26, signalperiod=9
#         )
#         data['Signal_MACD'] = 'Hold'
#         threshold_macd = 0.1
#         diff_macd = abs(data['MACD'] - data['MACD_signal'])
#         data.loc[(data['MACD'] > data['MACD_signal']) & (diff_macd > threshold_macd), 'Signal_MACD'] = 'Buy'
#         data.loc[(data['MACD'] < data['MACD_signal']) & (diff_macd > threshold_macd), 'Signal_MACD'] = 'Sell'

#     # Ichimoku
#     if indicators.get('Ichimoku'):
#         data['Tenkan_sen'] = (data['High'].rolling(window=9).max() + data['Low'].rolling(window=9).min()) / 2
#         data['Kijun_sen'] = (data['High'].rolling(window=26).max() + data['Low'].rolling(window=26).min()) / 2
#         data['Senkou_span_A'] = ((data['Tenkan_sen'] + data['Kijun_sen']) / 2).shift(26)
#         data['Senkou_span_B'] = ((data['High'].rolling(window=52).max() + data['Low'].rolling(window=52).min()) / 2).shift(26)
#         data['Chikou_span'] = data['Close'].shift(-26)
#         data['Signal_Ichimoku'] = 'Hold'
#         data.loc[data['Close'] > data['Senkou_span_A'], 'Signal_Ichimoku'] = 'Buy'
#         data.loc[data['Close'] < data['Senkou_span_B'], 'Signal_Ichimoku'] = 'Sell'

#     # Stochastic Oscillator
#     if indicators.get('SO'):
#         data['SlowK'], data['SlowD'] = ta.STOCH(
#             data['High'], data['Low'], data['Close'],
#             fastk_period=14, slowk_period=3, slowd_period=3
#         )
#         data['Signal_SO'] = 'Hold'
#         threshold_so = 2
#         diff_so = abs(data['SlowK'] - data['SlowD'])
#         data.loc[(data['SlowK'] > data['SlowD']) & (diff_so > threshold_so), 'Signal_SO'] = 'Buy'
#         data.loc[(data['SlowK'] < data['SlowD']) & (diff_so > threshold_so), 'Signal_SO'] = 'Sell'

#     # Volume Analysis
#     if indicators.get('Volume'):
#         data['Volume_MA20'] = ta.SMA(data['Volume'], timeperiod=20)
#         data['Signal_Volume'] = 'Hold'
#         data.loc[data['Volume'] > data['Volume_MA20'], 'Signal_Volume'] = 'High Volume'
#         data.loc[data['Volume'] < data['Volume_MA20'], 'Signal_Volume'] = 'Low Volume'

#     return data

#  FUNGSI PERUBAHAN INDIKATOR
import talib as ta
import pandas as pd

def compute_indicators(data, indicators, params):
    # Moving Averages
    if indicators.get('MA'):
        data['MA20'] = ta.SMA(data['Close'], timeperiod=params['ma_short'])
        data['MA50'] = ta.SMA(data['Close'], timeperiod=params['ma_long'])
        data['Signal_MA'] = 'Hold'
        threshold = 0.01
        diff = abs(data['MA20'] - data['MA50']) / data['MA50']
        data.loc[(data['MA20'] > data['MA50']) & (diff > threshold), 'Signal_MA'] = 'Buy'
        data.loc[(data['MA20'] < data['MA50']) & (diff > threshold), 'Signal_MA'] = 'Sell'

    # MACD
    if indicators.get('MACD'):
        data['MACD'], data['MACD_signal'], data['MACD_hist'] = ta.MACD(
            data['Close'],
            fastperiod=params['macd_fast'],
            slowperiod=params['macd_slow'],
            signalperiod=params['macd_signal']
        )
        data['Signal_MACD'] = 'Hold'
        threshold_macd = 0.1
        diff_macd = abs(data['MACD'] - data['MACD_signal'])
        data.loc[(data['MACD'] > data['MACD_signal']) & (diff_macd > threshold_macd), 'Signal_MACD'] = 'Buy'
        data.loc[(data['MACD'] < data['MACD_signal']) & (diff_macd > threshold_macd), 'Signal_MACD'] = 'Sell'

    # Ichimoku
    if indicators.get('Ichimoku'):
        tenkan_period = params['tenkan']
        kijun_period = params['kijun']
        senkou_b_period = params['senkou_b']
        shift = params['shift']

        data['Tenkan_sen'] = (data['High'].rolling(window=tenkan_period).max() + data['Low'].rolling(window=tenkan_period).min()) / 2
        data['Kijun_sen'] = (data['High'].rolling(window=kijun_period).max() + data['Low'].rolling(window=kijun_period).min()) / 2
        data['Senkou_span_A'] = ((data['Tenkan_sen'] + data['Kijun_sen']) / 2).shift(shift)
        data['Senkou_span_B'] = ((data['High'].rolling(window=senkou_b_period).max() + data['Low'].rolling(window=senkou_b_period).min()) / 2).shift(shift)
        data['Chikou_span'] = data['Close'].shift(-shift)
        data['Signal_Ichimoku'] = 'Hold'
        data.loc[data['Close'] > data['Senkou_span_A'], 'Signal_Ichimoku'] = 'Buy'
        data.loc[data['Close'] < data['Senkou_span_B'], 'Signal_Ichimoku'] = 'Sell'

    # Stochastic Oscillator
    if indicators.get('SO'):
        data['SlowK'], data['SlowD'] = ta.STOCH(
            data['High'], data['Low'], data['Close'],
            fastk_period=params['so_k'], slowk_period=params['so_k'], slowd_period=params['so_d']
        )
        data['Signal_SO'] = 'Hold'
        threshold_so = 2
        diff_so = abs(data['SlowK'] - data['SlowD'])
        data.loc[(data['SlowK'] > data['SlowD']) & (diff_so > threshold_so), 'Signal_SO'] = 'Buy'
        data.loc[(data['SlowK'] < data['SlowD']) & (diff_so > threshold_so), 'Signal_SO'] = 'Sell'

    # Volume Analysis
    if indicators.get('Volume'):
        data['Volume_MA20'] = ta.SMA(data['Volume'], timeperiod=params['volume_ma'])
        data['Signal_Volume'] = 'Hold'
        data.loc[data['Volume'] > data['Volume_MA20'], 'Signal_Volume'] = 'High Volume'
        data.loc[data['Volume'] < data['Volume_MA20'], 'Signal_Volume'] = 'Low Volume'

    return data
