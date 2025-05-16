# Dashboard Analisis & Backtesting Saham (Streamlit)

Aplikasi ini adalah dashboard interaktif berbasis **Streamlit** untuk melakukan **analisis teknikal** dan **simulasi backtesting** saham Indonesia. Data saham tersimpan dalam database MySQL dalam format JSON.

---

## Fitur Utama

- **Analisis Saham** dengan indikator teknikal:

  - Ichimoku Kinko Hyo
  - Moving Average (MA)
  - MACD
  - Stochastic Oscillator (SO)
  - Volume

- **Backtesting Analisis** → Menampilkan jumlah sinyal Buy/Sell/Hold

- **Backtesting Profit** → Simulasi portofolio berdasarkan sinyal final

- **Rekapitulasi Sinyal** → Total sinyal per indikator

- **Pemanggilan Analisis Tersimpan** berdasarkan `title`

- **Ekspor ke Excel**:

  - Hasil backtesting (nilai portofolio & profit)
  - Rekap sinyal analisis

---

## Struktur Folder

```
project_root/
│
├── main.py                        # Aplikasi utama Streamlit
├── modules/
│   ├── database.py               # Fungsi pengambilan data dari MySQL
│   ├── indicators.py             # Perhitungan semua indikator teknikal
│   ├── visuals.py                # Grafik harga dan indikator dengan Plotly
│   ├── analysis.py               # Simpan, tampil, dan muat ulang hasil analisis
│   └── backtesting.py            # Fungsi backtesting dan penyimpanan hasil
```

---

## Cara Menjalankan

1. Pastikan MySQL aktif dan tersedia database bernama `indonesia_stock`.
2. Jalankan perintah berikut:

```bash
streamlit run main.py
```

3. Buka browser dan akses `http://localhost:8501`

---

## Ketergantungan (Dependencies)

Pastikan semua library berikut sudah diinstal:

```bash
pip install streamlit pandas mysql-connector-python sqlalchemy plotly xlsxwriter
```

Tambahan opsional:

- `ta-lib` jika kamu ingin pakai library eksternal untuk indikator teknikal

---

## Catatan Teknis

- Data harga saham disimpan dalam tabel `stock_data` dalam kolom JSON
- Hasil analisis disimpan di tabel `analisis_indikator`
- Hasil backtesting disimpan di tabel `data_backtesting`
- Semua tabel dibuat otomatis jika belum tersedia

---

## Status

Seluruh fitur dari aplikasi referensi (teman) telah diadopsi, ditambah dengan fitur-fitur baru:

- Ekspor Excel otomatis
- Modularisasi kode ke dalam folder `modules`
- UI berbasis tab navigasi di Streamlit

---

## requirements.txt

pip install -r requirements.txt

untuk menginstall semua dependensi proyek ini secara otomatis.
