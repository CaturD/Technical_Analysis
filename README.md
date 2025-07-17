# Dashboard Analisis & Backtesting Saham

Dashboard ini dibuat dengan **Streamlit** untuk menganalisis pergerakan saham Indonesia sekaligus melakukan simulasi backtesting sederhana. Seluruh data harga tersimpan di database MySQL dalam bentuk JSON sehingga mudah dipanggil ulang.

---

## Fitur Utama

- **Analisis Saham** menggunakan beberapa indikator teknikal (Ichimoku, MA, MACD, Stochastic, dan Volume)
- **Backtesting Analisis** untuk menampilkan jumlah sinyal _Buy/Sell/Hold_
- **Backtesting Profit** guna mensimulasikan portofolio berdasarkan sinyal akhir
- **Rekapitulasi Sinyal** per indikator
- Memuat kembali analisis tersimpan berdasarkan `title`

---

## Instalasi

1. Pastikan Python 3.9 atau lebih baru terpasang.
2. Install dependensi melalui:
   ```bash
   pip install -r requirements.txt
   ```
3. Aktifkan MySQL dan buat database bernama `indonesia_stock` (tabel akan dibuat otomatis saat aplikasi dijalankan).
4. Jika ingin mengambil data real-time, isi `API_KEY` pada `config.py` dengan key milik Anda.

## Pengambilan Data

- **Data historis** dapat diunduh lewat `fetch_historical_data.py`.
- **Data real-time** tersedia melalui `fetch_realtime_marketstack.py` atau `fetch_realtime_alpha.py`.
- Script `auto_fetch_after_close.py` dapat dijadwalkan agar data harian otomatis tersimpan setelah pasar tutup.

---

## Menjalankan Dashboard

```bash
streamlit run main.py
```

Buka `http://localhost:8501` di browser untuk mengakses antarmuka.

---

## Struktur Proyek

```
project_root/
├── main.py                       # Aplikasi Streamlit
├── modules/
│   ├── analysis.py               # Logika analisis dan penyimpanan ke DB
│   ├── backtesting.py            # Fungsi backtesting
│   ├── database.py               # Koneksi MySQL
│   ├── indicators.py             # Perhitungan indikator teknikal
│   └── ...
├── fetch_historical_data.py      # Mengambil data historis
└── ...
```

---

## Catatan

- Data harga disimpan pada tabel `stock_data` (atau variasinya) dalam database.
- Hasil analisis berada di tabel `analisis_indikator` dan backtesting di `data_backtesting`.
- Contoh `API_KEY` pada repo hanyalah placeholder, ganti sesuai milik Anda.
