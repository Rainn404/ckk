@echo off
title SIPEKA DF - Sistem Pemeriksa Kesalahan Data Digital Farming
color 0A

echo =====================================================================
echo      SIPEKA DF - Digital Farming Data Discrepancy Checker
echo        Pemeriksa Kesalahan Data Panen & Angkut Kelapa Sawit
echo =====================================================================
echo.

REM 1. Periksa apakah Python terpasang di sistem
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python tidak terdeteksi pada sistem Windows Anda!
    echo.
    echo Silakan unduh dan instal Python versi 3.10 atau yang lebih baru dari:
    echo https://www.python.org/downloads/
    echo.
    echo PENTING: Saat instalasi, pastikan mencentang pilihan:
    echo "Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python terdeteksi.

REM 2. Periksa dan pasang pustaka yang diperlukan jika belum ada
echo [INFO] Memeriksa dependensi sistem...
python -c "import pymupdf" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Memasang modul yang diperlukan dari requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Gagal memasang dependensi! Pastikan koneksi internet aktif saat instalasi awal.
        pause
        exit /b 1
    )
)

echo [OK] Seluruh dependensi siap.
echo.
echo [INFO] Membuka browser ke http://127.0.0.1:8080 ...
start "" "http://127.0.0.1:8080"

echo [INFO] Menjalankan server lokal SIPEKA DF...
echo Jangan tutup jendela terminal ini selama menggunakan aplikasi.
echo Tekan Ctrl+C untuk menghentikan server.
echo.

python app.py 8080

pause
