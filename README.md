# 🚑 Optimasi Rute Distribusi Vaksin Sleman (Algoritma A*)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![Algorithm](https://img.shields.io/badge/Algorithm-A*%20Search-green)

Aplikasi berbasis web interaktif untuk menentukan rute distribusi obat dan vaksin tercepat dari **Depot Dinas Kesehatan Kabupaten Sleman** ke Puskesmas-Puskesmas tujuan, dengan mempertimbangkan batasan ketahanan wadah angkut (*Cold Chain Constraint*) dan simulasi kondisi cuaca.

---

## 👥 Anggota Kelompok (UGM)
- **Nazwa Nazira** 
- **Maulida Musyarofah** 
- **Artya Asqishan** 

---

## 📌 Fitur Utama
1. **Pencarian Rute Optimal (Algoritma A*):** Menghitung jalur tercepat pada jaringan jalan Sleman berbobot menggunakan heuristik jarak garis lurus (*Haversine*) yang disesuaikan dengan batas kecepatan ideal.
2. **Penyesuaian Faktor Cuaca:** Mengintegrasikan faktor pengali waktu tempuh (Cerah = 1.0x, Hujan = 1.2x) secara seragam dengan jaminan heuristik tetap *admissible*.
3. **Pemeriksaan Batasan Cold Chain:** Mengkalkulasi akumulasi waktu perjalanan + waktu *loading* (30 menit) dan mengevaluasi kelayakannya terhadap ambang batas ketahanan *Vaccine Carrier* (12 jam) atau *Cold Box* (48 jam).
4. **Peta Interaktif (Folium + OSRM):** Menampilkan rute riil mengikuti lekukan jalan fisik serta melampirkan *direct link* navigasi langsung ke **Google Maps**.

---

## 🛠️️ Teknologi & Library
- **Bahasa Pemrograman:** Python
- **Framework UI:** Streamlit
- **Peta & Geometrik Jalan:** Folium, Streamlit-Folium, OSRM API
- **Struktur Data:** Priority Queue (`heapq`)

---

## 📂 Struktur Repositori

```text
optimasi-rute-vaksin-a-star/
│
├── docs/                        # Dokumen pendukung proyek
│   ├── Laporan_Proyek_AI.pdf    # Laporan lengkap proyek
│   └── Slide_Presentasi.pdf     # Slide presentasi
│
├── app.py                       # Kode utama aplikasi Streamlit
├── README.md                    # Dokumentasi proyek
└── requirements.txt             # Daftar dependensi library Python
