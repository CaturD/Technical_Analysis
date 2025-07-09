# modules/realtime.py
import requests
import pandas as pd

def fetch_realtime_data_marketstack(ticker, api_key):
    url = f"http://api.marketstack.com/v1/intraday/latest"
    params = {
        'access_key': api_key,
        'symbols': ticker
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json().get('data', [])
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['date'])
    df = df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })
    df = df[['datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    return df
