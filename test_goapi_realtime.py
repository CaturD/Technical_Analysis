import requests
import json

GOAPI_KEY = "3adfd705-abc7-5fc9-4274-a86cadff"
ticker = "BBCA"  # ganti ke kode lain jika ingin mencoba emiten berbeda

def fetch_goapi_realtime(ticker):
    url = f"https://api.goapi.id/v1/stock/idx/prices/latest?ticker={ticker}&api_key={GOAPI_KEY}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()

        if not result or 'data' not in result or not result['data']:
            print(f"❌ Tidak ada data untuk {ticker} dari GoAPI. Respon: {result}")
            return None

        d = result['data']
        formatted_data = [{
            "Date": d.get('date'),
            "Open": d.get('open'),
            "High": d.get('high'),
            "Low": d.get('low'),
            "Close": d.get('close'),
            "Volume": d.get('volume'),
            "Name": d.get('ticker')
        }]
        return formatted_data

    except Exception as e:
        print(f"❌ Gagal mengambil data GoAPI untuk {ticker}: {e}")
        return None
