# SIPEKA DF — Sistem Pemeriksa Kesalahan Data Digital Farming

**SIPEKA DF** adalah aplikasi desktop-web lokal yang dirancang khusus untuk Asisten Afdeling, Krani Cek Sawit (KCS), dan Mandor Panen di perkebunan kelapa sawit guna mendeteksi perbedaan, potensi pergeseran data, dan kesalahan input laporan aktivitas panen serta pengangkutan secara otomatis, akurat, dan cepat.

---

## Daftar Isi

1. [Latar Belakang & Masalah](#latar-belakang--masalah)
2. [Persyaratan Sistem](#persyaratan-sistem)
3. [Panduan Instalasi & Menjalankan](#panduan-instalasi--menjalankan)
4. [Struktur Proyek](#struktur-proyek)
5. [Fitur Utama](#fitur-utama)
6. [Rumus & Aturan Rekonsiliasi](#rumus--aturan-rekonsiliasi)
7. [Penanganan Selisih Saling Meniadakan (Offsetting Differences)](#penanganan-selisih-saling-meniadakan-offsetting-differences)
8. [Pengujian 14 Skenario Wajib](#pengujian-14-skenario-wajib)
9. [Batasan Aplikasi & Keamanan](#batasan-aplikasi--keamanan)

---

## Latar Belakang & Masalah

Pada operasional perkebunan kelapa sawit:
- **Mandor Panen** mencatat produksi harian janjang buah per pemanen melalui Form **PB24A (Form Pengumpulan Buah)**.
- **Krani Cek Sawit / Krani Transport (KCS)** mencatat penerimaan dan pemuatan janjang buah dari TPH ke truk pengangkut melalui Form **PB24B (Form Pengangkutan Buah)**.

Sering kali terdapat selisih antara kedua laporan ini akibat:
- Kesalahan pengetikan (*typo*) kode pekerja atau nomor blok.
- Buah tertinggal di TPH (*restan*) yang belum terangkut.
- Salah memilih afdeling atau tanggal kegiatan.
- Penggabungan hasil panen lebih dari satu pemanen ke satu pencatatan angkut.

Pemeriksaan manual baris demi baris pada dokumen PDF memakan waktu dan berisiko luput. SIPEKA DF hadir untuk memverifikasi kedua dokumen dalam waktu kurang dari 2 detik secara lokal di komputer Windows tanpa memerlukan koneksi internet maupun framework berat.

---

## Persyaratan Sistem

- **Sistem Operasi**: Windows 10, Windows 11, atau Windows Server.
- **Python**: Versi 3.10 atau yang lebih baru (mendukung Python 3.14).
- **Peramban Web (Browser)**: Google Chrome, Microsoft Edge, Mozilla Firefox, atau Opera.
- **Koneksi Internet**: Hanya diperlukan 1 kali saat instalasi dependensi awal. Setelah itu aplikasi berjalan **100% offline**.
- **RAM**: Minimal 2 GB.
- **Ruang Disk**: Minimal 100 MB.

---

## Panduan Instalasi & Menjalankan

### Cara 1: Menggunakan `run.bat` (Sangat Disarankan)

1. Pastikan Python telah terpasang di komputer Anda.
2. Cukup lakukan **klik dua kali pada file `run.bat`**.
3. Skrip akan otomatis:
   - Memeriksa instalasi Python.
   - Memeriksa dan menginstal paket yang diperlukan dari `requirements.txt` jika belum ada.
   - Menjalankan server lokal di alamat `http://127.0.0.1:8080`.
   - Membuka peramban web default Anda secara otomatis.

### Cara 2: Menjalankan Manual melalui Terminal / PowerShell

```bash
# 1. Buka folder proyek
cd c:\xampp\htdocs\sipeka

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Jalankan server lokal
python app.py 8080
```
Buka browser dan akses alamat: `http://127.0.0.1:8080`.

---

## Struktur Proyek

### Arsitektur: HTML UI + Python API

| Lapisan | File | Tanggung Jawab |
|---------|------|----------------|
| **UI** | `templates/index.html` | Antarmuka pengguna — HTML murni, Glassmorphism |
| **UI** | `static/css/style.css` | Tema, layout responsif, animasi |
| **UI** | `static/js/app.js` | Interaksi browser, filter, upload, tampilan data |
| **API** | `app.py` | Server HTTP lokal, routing endpoint REST API |
| **Logika** | `pdf_reader.py` | Pembaca PDF & deteksi scan/OCR |
| **Logika** | `data_extractor.py` | Ekstraktor metadata & tabel blok/pekerja |
| **Logika** | `comparator.py` | Mesin pembanding data & kalkulasi selisih |
| **Logika** | `validator.py` | Pemeriksa konsistensi identitas laporan |
| **Logika** | `history_manager.py` | Pengelola riwayat JSON lokal |
| **Logika** | `exporter.py` | Ekspor CSV (BOM UTF-8) & HTML siap cetak |

```
sipeka/
├── run.bat                     # Peluncur otomatis 1-klik untuk Windows
├── requirements.txt            # Daftar pustaka yang diperlukan
├── README.md                   # Dokumentasi ini
│
├── [UI - HTML Murni]
│   ├── templates/index.html    # Halaman utama (Glassmorphism, responsif mobile)
│   └── static/
│       ├── css/style.css       # Stylesheet — Deep Forest Glassmorphism theme
│       └── js/app.js           # Frontend controller (navigasi, upload, filter, kartu)
│
├── [Backend - Python Logika & API]
│   ├── app.py                  # Server HTTP + routing REST API /api/*
│   ├── pdf_reader.py           # Ekstraksi teks dari PDF (PyMuPDF)
│   ├── data_extractor.py       # Parsing data PB24A (Mandor) & PB24B (KCS)
│   ├── comparator.py           # Mesin komparasi multi-kunci (Blok + Kode Pekerja)
│   ├── validator.py            # Validasi identitas (afdeling, tanggal, kebun)
│   ├── history_manager.py      # Riwayat pemeriksaan (data/history.json)
│   └── exporter.py             # Ekspor CSV & laporan HTML siap cetak
│
├── [Data & Pengujian]
│   ├── data/history.json       # Penyimpanan riwayat lokal
│   ├── uploads/                # Direktori temporer upload PDF
│   ├── test_data/              # PDF sintetis untuk pengujian
│   ├── test_sipeka.py          # Suite pengujian 14 skenario wajib
│   └── generate_synthetic_data.py  # Pembuat data pengujian
```

> **Catatan**: Python HANYA menangani logika dan API (`/api/*`). File HTML adalah HTML statis
> biasa yang disajikan oleh Python server — tidak ada *template rendering* di Python.

---

## Fitur Utama

### 1. Dashboard Eksekutif
- Menampilkan metrik riil sesi aktif: total baris, jumlah data cocok, data berbeda, dan perlu verifikasi.
- **Tidak menampilkan angka statistik palsu** saat belum ada pemeriksaan yang dijalankan.

### 2. Area Unggah Berkas Berpasangan
- Slot 1: Laporan Mandor (PB24A - Pengumpulan Buah).
- Slot 2: Laporan KCS (PB24B - Pengangkutan Buah).
- Mendukung *drag & drop*, menampilkan nama berkas dan ukuran file secara langsung.
- Validasi ekstensi PDF dan batas ukuran berkas.

### 3. Validasi Identitas Dokumen
Sebelum data dibandingkan, sistem memverifikasi:
- Tanggal panen / aktivitas.
- Afdeling / Divisi.
- Kebun / Unit kerja.
Jika tanggal atau afdeling berbeda, sistem menampilkan modal konfirmasi agar pengguna waspada dan tidak salah memasangkan berkas.

### 4. Mesin Pembanding Multi-Kunci
Pencocokan dilakukan berdasarkan kombinasi `(Blok, Kode Pekerja)` bukan sekadar urutan baris, sehingga urutan baris yang acak pada salah satu dokumen tidak mempengaruhi akurasi perbandingan.

### 5. Rekapitulasi Blok & Peringatan "Offsetting Differences"
- Menampilkan rekap total janjang per masing-masing blok.
- Memberikan peringatan khusus apabila total keseluruhan Mandor dan KCS sama persis namun distribusi per bloknya berselisih saling meniadakan.

### 6. Ekspor Hasil Siap Pakai
- **Ekspor CSV untuk Excel**: Dilengkapi dengan UTF-8 BOM (`\ufeff`) dan pemisah titik koma agar dapat langsung dibuka di Microsoft Excel tanpa masalah karakter atau format angka.
- **Cetak / Simpan PDF**: Menghasilkan tata letak laporan formal yang siap dicetak ke kertas atau disimpan sebagai PDF.

### 7. Riwayat Pemeriksaan Lokal
Riwayat perbandingan tersimpan di `data/history.json` dan dapat ditinjau kembali atau dihapus dengan konfirmasi keamanan.

---

## Rumus & Aturan Rekonsiliasi

### Rumus Selisih
$$\text{Selisih} = \text{Nilai Laporan KCS} - \text{Nilai Laporan Mandor}$$

### Arti Nilai Selisih
- **Selisih = 0**: Data dinyatakan **Cocok**.
- **Selisih > 0**: KCS mencatat lebih banyak dari Mandor. Kemungkinan ada penggabungan janjang atau kelebihan hitung angkut.
- **Selisih < 0**: KCS mencatat lebih sedikit dari Mandor. Kemungkinan buah restan (tertinggal di TPH) atau afkir.

### Status Pemeriksaan
1. **Cocok** (Hijau): Nilai kedua pihak sama persis.
2. **Berbeda** (Merah): Nilai angka kedua laporan memiliki selisih.
3. **Hanya Ada di Mandor** (Oranye): Tercatat dipanen, namun tidak ada di rekapan KCS.
4. **Hanya Ada di KCS** (Oranye): Tercatat diangkut, namun tidak terdaftar di rekapan Mandor.
5. **Data Tidak Lengkap** (Abu-abu): Nilai kosong atau tidak terbaca pada salah satu dokumen.
6. **Duplikat** (Abu-abu): Kombinasi blok dan pekerja yang sama muncul lebih dari 1 kali dalam satu laporan.
7. **Perlu Verifikasi**: Kategori umum seluruh baris bermasalah untuk ditindaklanjuti Asisten Afdeling.

> **PENTING**: Perbedaan antara laporan pengumpulan buah dan pengangkutan buah belum tentu merupakan kecurangan atau kesalahan fatal. Perbedaan dapat disebabkan oleh faktor operasional lapangan. SIPEKA DF menggunakan istilah **Perlu Verifikasi** atau **Data Berbeda**, bukan langsung menuduh kesalahan.

---

## Penanganan Selisih Saling Meniadakan (Offsetting Differences)

Contoh kasus:
- **Blok 136**: Mandor = 72 jjg, KCS = 75 jjg (Selisih = +3)
- **Blok 137**: Mandor = 80 jjg, KCS = 77 jjg (Selisih = -3)
- **Total Keseluruhan**: Mandor = 152 jjg, KCS = 152 jjg (Selisih Total = 0)

Jika hanya melihat total akhir, laporan terlihat "sempurna" (selisih nol). Namun di lapangan, terjadi pergeseran janjang antar-blok. SIPEKA DF mendeteksi kondisi ini secara otomatis dan memunculkan banner peringatan merah:
`⚠️ PERHATIAN: Ditemukan Selisih Antar-Blok yang Saling Meniadakan (Offsetting Differences)!`

---

## Pengujian 14 Skenario Wajib

Aplikasi telah dilengkapi dengan suite pengujian otomatis (`test_sipeka.py`) yang menguji 14 skenario wajib:

| No | Skenario Pengujian | Berkas Uji Coba | Hasil |
|:--:|:---|:---|:---:|
| 1 | Kedua laporan memiliki data identik | `tc1_mandor_identical.pdf` vs `tc1_kcs_identical.pdf` | **PASSED** |
| 2 | Satu nilai berbeda pada satu pekerja | `tc1_mandor_identical.pdf` vs `tc2_kcs_diff_value.pdf` | **PASSED** |
| 3 | Satu blok hilang di laporan kedua | `tc1_mandor_identical.pdf` vs `tc3_kcs_missing_block.pdf` | **PASSED** |
| 4 | Pekerja hanya muncul di laporan pertama | `tc4_mandor_extra_worker.pdf` vs `tc1_kcs_identical.pdf` | **PASSED** |
| 5 | Nilai kosong pada salah satu laporan | `tc1_mandor_identical.pdf` vs `tc5_kcs_empty_val.pdf` | **PASSED** |
| 6 | Baris duplikat | `tc6_mandor_duplicate.pdf` vs `tc1_kcs_identical.pdf` | **PASSED** |
| 7 | Total sama tapi distribusi blok beda (*offset*) | `tc7_mandor_offset.pdf` vs `tc7_kcs_offset.pdf` | **PASSED** |
| 8 | Tanggal kedua laporan berbeda | `tc1_mandor_identical.pdf` vs `tc8_kcs_diff_date.pdf` | **PASSED** |
| 9 | Afdeling kedua laporan berbeda | `tc1_mandor_identical.pdf` vs `tc9_kcs_diff_afd.pdf` | **PASSED** |
| 10 | Berkas PDF rusak / corrupt | `tc10_corrupt.pdf` | **PASSED** |
| 11 | PDF scan gambar tanpa teks (perlu OCR) | `tc11_scanned_image.pdf` | **PASSED** |
| 12 | Format angka berbeda (1.250 vs 1,250) | `tc12_mandor_numformat.pdf` vs `tc12_kcs_numformat.pdf` | **PASSED** |
| 13 | Nama file dengan spasi & karakter khusus | `tc13 Laporan Mandor & KCS (Afdeling #1) [2026].pdf` | **PASSED** |
| 14 | Pengguna submit tanpa berkas | Validasi server 400 | **PASSED** |

Jalankan pengujian kapan saja dengan perintah:
```bash
python test_sipeka.py
```

---

## Batasan Aplikasi & Keamanan

1. **Format PDF**: Aplikasi dirancang untuk dokumen PDF digital hasil ekspor sistem Digital Farming atau ERP perkebunan.
2. **Dokumen Hasil Scan**: Jika dokumen berupa hasil foto atau scan murni tanpa teks digital, sistem akan mendeteksinya dan memberi tahu bahwa dokumen memerlukan OCR.
3. **Pembersihan Berkas**: Berkas yang diunggah ke folder `uploads/` hanya disimpan sementara selama proses perbandingan dan langsung dihapus setelah pemrosesan selesai.
4. **Keamanan Jaringan**: Server hanya mengikat alamat lokal `127.0.0.1` (localhost) sehingga tidak dapat diakses dari jaringan luar tanpa konfigurasi khusus.
