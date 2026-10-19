"""
SIPEKA DF - Data Extractor Module (Refactored & Enhanced)
Mengekstrak metadata, data produksi (per tahun, blok, kode pekerja), berondolan, luasan,
dan subtotal dari dokumen PDF kelapa sawit.
Mendukung format Matriks (Cross-Tabulation PB24A/PB24B) dan format Daftar Baris (List Table).
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("sipeka.data_extractor")


def clean_string(val: Any) -> str:
    """Membersihkan spasi ganda dan karakter kontrol."""
    if val is None:
        return ""
    s = str(val).strip()
    return re.sub(r"\s+", " ", s)


def normalize_code(val: Any) -> str:
    """Normalisasi kode blok atau pekerja (hilangkan spasi berlebih, jadikan uppercase)."""
    clean = clean_string(val).upper()
    # Hilangkan karakter spesial di awal/akhir kecuali alfanumerik
    clean = re.sub(r"^[^\w]+|[^\w]+$", "", clean)
    return clean


def parse_number(val: Any) -> Optional[float]:
    """
    Mengonversi string angka format Indonesia/Inggris ke float secara aman.
    Contoh:
    - '72' -> 72.0
    - '216,00' -> 216.0
    - '1.250' -> 1250.0
    - '1,250' -> 1250.0
    - '72,5' -> 72.5
    - ' - ' -> None
    """
    if val is None:
        return None
    s = clean_string(val)
    if not s or s in ("-", "--", "N/A", "NA", "null", "None"):
        return None

    # Hapus satuan jika ada
    s = re.sub(r"(?i)\s*(jjg|tbs|kg|sak|tandan|ha)\b", "", s).strip()

    if "." in s and "," in s:
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        if last_comma > last_dot:
            # Format Indonesia: 1.250,50 -> 1250.50
            s = s.replace(".", "").replace(",", ".")
        else:
            # Format US: 1,250.50 -> 1250.50
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            s = s.replace(".", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            s = s.replace(",", "")
        else:
            # Koma sebagai desimal (cth: 216,00 atau 72,5)
            s = s.replace(",", ".")

    try:
        filtered = re.sub(r"[^\d.-]", "", s)
        if not filtered or filtered in ("-", "."):
            return None
        return float(filtered)
    except (ValueError, TypeError):
        return None


def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """Mengekstrak metadata kebun, afdeling, tanggal, mandor/krani dari teks laporan."""
    meta = {
        "tanggal_laporan": None,
        "tanggal_aktivitas": None,
        "kebun": None,
        "afdeling": None,
        "nomor_dokumen": None,
        "nama_mandor": None,
        "nama_krani": None,
        "jenis_laporan": None,
        "total_tertera": None
    }

    # 1. Jenis Laporan
    if re.search(r"(?i)\b(PB24A|PENGUMPULAN\s+BUAH|MANDOR\s+PANEN|FORM\s+PB\s*24\s*A)\b", text):
        meta["jenis_laporan"] = "Laporan Mandor (PB24A)"
    elif re.search(r"(?i)\b(PB24B|PENGANGKUTAN\s+BUAH|KRANI\s+CEK\s+SAWIT|KCS|FORM\s+PB\s*24\s*B)\b", text):
        meta["jenis_laporan"] = "Laporan KCS (PB24B)"

    # 2. Tanggal (Format: MM/DD/YYYY, DD/MM/YYYY, dsb.)
    date_match = re.search(r"(?i)(?:tgl\s*panen|tanggal\s*panen|tgl\s*aktivitas|tanggal)\s*[:=]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
    if date_match:
        tgl = date_match.group(1).strip()
        meta["tanggal_aktivitas"] = tgl
        meta["tanggal_laporan"] = tgl
    else:
        general_date = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", text)
        if general_date:
            meta["tanggal_aktivitas"] = general_date.group(1)
            meta["tanggal_laporan"] = general_date.group(1)

    # 3. Kebun / Estate
    kebun_match = re.search(r"(?i)(?:kebun|estate|unit|pt)\s*[:=]?\s*([A-Za-z0-9\s.-]{3,35})(?=\s+(?:afdeling|afd|divisi|tgl|tanggal|\n|$))", text)
    if kebun_match:
        meta["kebun"] = clean_string(kebun_match.group(1))

    # 4. Afdeling / Divisi
    afd_match = re.search(r"(?i)(?:afdeling|afd|divisi|div)\s*[:=.-]?\s*([A-Za-z0-9_ -]{1,20})(?=\s*(?:kebun|estate|unit|pt|tgl|tanggal|\n|\r|$|\|))", text)
    if afd_match:
        meta["afdeling"] = clean_string(afd_match.group(1))

    # 5. Nomor Dokumen
    nomor_match = re.search(r"(?i)(?:nomor|no)\s*[:=]?\s*(PB24[AB]/[A-Za-z0-9/_-]+)", text)
    if nomor_match:
        meta["nomor_dokumen"] = clean_string(nomor_match.group(1))

    # 6. Mandor / Krani
    mandor_match = re.search(r"(?i)(?:mandor)\s*[:=]?\s*([A-Za-z0-9\s.]{3,30})(?=\s*(?:tgl|tanggal|panen|\n|$))", text)
    if mandor_match:
        m_name = clean_string(mandor_match.group(1))
        if not any(k in m_name.lower() for k in ["panen", "1", "satu", "asisten", "diketahui", "diperiksa"]):
            meta["nama_mandor"] = m_name

    krani_match = re.search(r"(?i)(?:krani\s*transport|krani\s*cek\s*sawit|krani|kcs)\s*[:=]?\s*([A-Za-z0-9\s.]{3,30})(?=\s*(?:tgl|\n|$))", text)
    if krani_match:
        meta["nama_krani"] = clean_string(krani_match.group(1))

    # 7. Total Tertera
    total_match = re.search(r"(?i)(?:grand\s+total|total\s+keseluruhan|total\s+produksi|total\s+angkut)\s*[:=]?\s*([\d.,]+)", text)
    if total_match:
        meta["total_tertera"] = parse_number(total_match.group(1))

    return meta


# ==============================================================================
# Deteksi dan Parsing Format Matriks (Cross-Tabulation PB24A / PB24B)
# ==============================================================================
def is_matrix_table(grid: List[List[str]]) -> Tuple[bool, int, Dict[int, str]]:
    """
    Mendeteksi apakah tabel merupakan format matriks silang (Cross-tabulation).
    Karakteristik:
    - Baris header atas memiliki banyak kolom kode pekerja (AA01, AA02, AA04, dll).
    - Kolom kiri berisi Tahun Tanam dan Nomor Blok.
    """
    if not grid or len(grid) < 3:
        return False, -1, {}

    # Periksa baris 0 s/d 4 untuk mencari baris header kode pekerja
    for r_idx in range(min(5, len(grid))):
        row = grid[r_idx]
        workers = {}
        for c_idx, cell in enumerate(row):
            if cell:
                c_clean = str(cell).strip().upper()
                # Pola kode pekerja: AA01, AA19, K01, PK01, dll (huruf diikuti angka)
                if re.match(r"^[A-Z]{1,3}\d{1,4}[A-Z]?$", c_clean):
                    workers[c_idx] = c_clean
        
        # Jika ditemukan setidaknya 3 kolom kode pekerja pada satu baris, ini adalah format matriks
        if len(workers) >= 3:
            return True, r_idx, workers

    return False, -1, {}


def parse_matrix_format(grid: List[List[str]], worker_row_idx: int, worker_cols: Dict[int, str], page_num: int = 1) -> Dict[str, Any]:
    """
    Mengekstrak data dari tabel format matriks silang (PTPN / Digital Farming standard).
    Memisahkan data produksi murni, data berondolan, data luasan, dan baris subtotal.
    """
    # Cari kolom Tahun dan Blok
    col_tahun = -1
    col_blok = -1

    for r_idx in range(min(worker_row_idx + 2, len(grid))):
        for c_idx, cell in enumerate(grid[r_idx]):
            if cell:
                c_lower = str(cell).strip().lower()
                if "tahun" in c_lower or "thn" in c_lower:
                    col_tahun = c_idx
                elif "blok" in c_lower or "block" in c_lower:
                    col_blok = c_idx

    # Fallback default posisi jika tidak tertulis eksplisit
    if col_tahun == -1 and col_blok == -1:
        col_tahun = 0
        col_blok = 1
    elif col_tahun != -1 and col_blok == -1:
        col_blok = col_tahun + 1
    elif col_blok != -1 and col_tahun == -1:
        col_tahun = max(0, col_blok - 1)

    production_records: List[Dict[str, Any]] = []
    berondolan_data: Dict[str, Any] = {"available": False, "total": None, "per_worker": {}, "raw": None}
    berondolan_pipil_data: Dict[str, Any] = {"available": False, "total": None, "per_worker": {}, "raw": None}
    luasan_data: Dict[str, Any] = {"available": False, "total": None, "per_worker": {}, "raw": None}
    subtotals: Dict[str, Any] = {"per_block": {}, "per_worker": {}, "grand_total": None}

    # Cari kolom jumlah blok (biasanya di kolom paling kanan setelah pekerja terakhir)
    col_jumlah_blok = max(worker_cols.keys()) + 1 if worker_cols else -1

    for r_idx in range(worker_row_idx + 1, len(grid)):
        row = grid[r_idx]
        if not row:
            continue

        first_val = str(row[col_tahun] if col_tahun != -1 and col_tahun < len(row) and row[col_tahun] is not None else (row[0] or "")).strip().lower()
        second_val = str(row[col_blok] if col_blok != -1 and col_blok < len(row) and row[col_blok] is not None else (row[1] if len(row) > 1 else "")).strip()

        row_text_all = " ".join([str(c or "").strip().lower() for c in row[:3]])

        # 1. Baris Subtotal / Jumlah per Pekerja
        if "jumlah" in row_text_all or "total" in row_text_all:
            subtotals["per_worker"] = {}
            for c_idx, w_code in worker_cols.items():
                if c_idx < len(row):
                    val = parse_number(row[c_idx])
                    if val is not None:
                        subtotals["per_worker"][w_code] = val
            # Grand Total ada di kolom paling kanan
            if col_jumlah_blok < len(row):
                gt_val = parse_number(row[col_jumlah_blok])
                if gt_val is not None:
                    subtotals["grand_total"] = gt_val
            continue

        # 2. Baris Berondolan Dipipil / Pipil
        if "berondolan dipipil" in row_text_all or "berondolan pipil" in row_text_all or "pipil" in row_text_all:
            berondolan_pipil_data["available"] = True
            for c_idx, w_code in worker_cols.items():
                if c_idx < len(row):
                    val = parse_number(row[c_idx])
                    if val is not None:
                        berondolan_pipil_data["per_worker"][w_code] = val
            if col_jumlah_blok < len(row):
                tot = parse_number(row[col_jumlah_blok])
                berondolan_pipil_data["total"] = tot
                berondolan_pipil_data["raw"] = str(row[col_jumlah_blok])
            continue

        # 3. Baris Berondolan Utama
        if "berondolan" in row_text_all:
            berondolan_data["available"] = True
            for c_idx, w_code in worker_cols.items():
                if c_idx < len(row):
                    val = parse_number(row[c_idx])
                    if val is not None:
                        berondolan_data["per_worker"][w_code] = val
            if col_jumlah_blok < len(row):
                tot = parse_number(row[col_jumlah_blok])
                berondolan_data["total"] = tot
                berondolan_data["raw"] = str(row[col_jumlah_blok])
            continue

        # 4. Baris Luasan
        if "luas" in row_text_all:
            luasan_data["available"] = True
            for c_idx, w_code in worker_cols.items():
                if c_idx < len(row):
                    val = parse_number(row[c_idx])
                    if val is not None:
                        luasan_data["per_worker"][w_code] = val
            if col_jumlah_blok < len(row):
                tot = parse_number(row[col_jumlah_blok])
                luasan_data["total"] = tot
                luasan_data["raw"] = str(row[col_jumlah_blok])
            continue

        # 5. Abaikan baris tanda tangan
        if any(k in row_text_all for k in ["dibuat", "diperiksa", "diketahui", "mandor", "krani", "asisten"]):
            continue

        # 6. Baris Produksi Transaksi (Tahun & Blok)
        tahun_val = str(row[col_tahun]).strip() if col_tahun != -1 and col_tahun < len(row) and row[col_tahun] is not None else ""
        blok_val = normalize_code(row[col_blok] if col_blok != -1 and col_blok < len(row) and row[col_blok] is not None else second_val)

        # Validasi bahwa blok valid (bukan header atau kata kosong)
        if not blok_val or blok_val in ("BLOK", "BLOCK", "-", "NONE", ""):
            continue

        # Simpan subtotal blok tertera
        if col_jumlah_blok < len(row):
            b_tot = parse_number(row[col_jumlah_blok])
            if b_tot is not None:
                subtotals["per_block"][blok_val] = b_tot

        # Ekstrak transaksi untuk setiap pemanen
        for c_idx, w_code in worker_cols.items():
            if c_idx < len(row):
                raw_cell = row[c_idx]
                num_val = parse_number(raw_cell)
                # Hanya simpan pemanen yang memiliki hasil panen > 0 pada blok tersebut
                # Jika 0, pemanen tidak bekerja pada blok ini
                if num_val is not None and num_val > 0:
                    production_records.append({
                        "tahun": tahun_val,
                        "blok": blok_val,
                        "kode_pekerja": w_code,
                        "jumlah_buah": num_val,
                        "raw_jumlah": str(raw_cell),
                        "berondolan": None,
                        "luasan": None,
                        "page": page_num,
                        "source": "matrix_table"
                    })

    return {
        "report_format": "matrix",
        "production_records": production_records,
        "berondolan_data": berondolan_data,
        "berondolan_pipil_data": berondolan_pipil_data,
        "luasan_data": luasan_data,
        "subtotals": subtotals
    }


# ==============================================================================
# Deteksi dan Parsing Format Daftar Baris (List Table)
# ==============================================================================
def parse_list_format(grid: List[List[str]], page_num: int = 1) -> Dict[str, Any]:
    """
    Mengekstrak data dari tabel daftar baris standar (kolom: No, Blok, Pekerja, Jumlah, dsb).
    """
    production_records: List[Dict[str, Any]] = []
    berondolan_data: Dict[str, Any] = {"available": False, "total": 0.0, "per_worker": {}, "raw": None}
    luasan_data: Dict[str, Any] = {"available": False, "total": 0.0, "per_worker": {}, "raw": None}
    subtotals: Dict[str, Any] = {"per_block": {}, "per_worker": {}, "grand_total": None}

    # Cari baris header
    header_idx = -1
    col_map = {"blok": -1, "pekerja": -1, "jumlah": -1, "berondolan": -1, "luasan": -1, "tahun": -1}

    for r_idx, row in enumerate(grid[:5]):
        for c_idx, cell in enumerate(row):
            if not cell:
                continue
            h = clean_string(cell).lower()
            if col_map["tahun"] == -1 and ("tahun" in h or "thn" in h):
                col_map["tahun"] = c_idx
            elif col_map["blok"] == -1 and any(k in h for k in ["blok", "block", "no blok", "kode blok"]):
                col_map["blok"] = c_idx
            elif col_map["pekerja"] == -1 and any(k in h for k in ["pekerja", "karyawan", "pemanen", "nik", "id pekerja", "kode pekerja", "no pekerja", "worker"]):
                col_map["pekerja"] = c_idx
            elif col_map["berondolan"] == -1 and any(k in h for k in ["berondolan", "brd"]):
                col_map["berondolan"] = c_idx
            elif col_map["luasan"] == -1 and any(k in h for k in ["luas", "luasan", "ha"]):
                col_map["luasan"] = c_idx
            elif col_map["jumlah"] == -1 and any(k in h for k in ["jumlah", "buah", "jjg", "janjang", "tbs", "tandan", "hasil"]):
                col_map["jumlah"] = c_idx

        if (col_map["blok"] != -1 or col_map["pekerja"] != -1) and col_map["jumlah"] != -1:
            header_idx = r_idx
            break

    if header_idx == -1:
        return {
            "report_format": "unknown",
            "production_records": [],
            "berondolan_data": berondolan_data,
            "berondolan_pipil_data": {"available": False, "total": None, "per_worker": {}, "raw": None},
            "luasan_data": luasan_data,
            "subtotals": subtotals
        }

    current_block = ""
    for row in grid[header_idx + 1:]:
        if not row or all(not str(c).strip() for c in row):
            continue

        row_str = " ".join([str(c) for c in row]).lower()
        if any(k in row_str for k in ["total", "subtotal", "jumlah keseluruhan", "rata-rata", "grand total"]):
            # Tangkap grand total
            if col_map["jumlah"] != -1 and col_map["jumlah"] < len(row):
                gt = parse_number(row[col_map["jumlah"]])
                if gt is not None:
                    subtotals["grand_total"] = gt
            continue

        tahun_val = ""
        if col_map["tahun"] != -1 and col_map["tahun"] < len(row):
            tahun_val = clean_string(row[col_map["tahun"]])

        blok_val = ""
        if col_map["blok"] != -1 and col_map["blok"] < len(row):
            blok_val = normalize_code(row[col_map["blok"]])
        if blok_val:
            current_block = blok_val
        else:
            blok_val = current_block

        pekerja_val = ""
        if col_map["pekerja"] != -1 and col_map["pekerja"] < len(row):
            pekerja_val = normalize_code(row[col_map["pekerja"]])

        jumlah_val = None
        raw_jumlah = ""
        if col_map["jumlah"] != -1 and col_map["jumlah"] < len(row):
            raw_jumlah = str(row[col_map["jumlah"]]).strip()
            jumlah_val = parse_number(raw_jumlah)

        brd_val = None
        if col_map["berondolan"] != -1 and col_map["berondolan"] < len(row):
            brd_val = parse_number(row[col_map["berondolan"]])
            if brd_val is not None:
                berondolan_data["available"] = True
                berondolan_data["total"] = (berondolan_data["total"] or 0.0) + brd_val

        luas_val = None
        if col_map["luasan"] != -1 and col_map["luasan"] < len(row):
            luas_val = parse_number(row[col_map["luasan"]])
            if luas_val is not None:
                luasan_data["available"] = True
                luasan_data["total"] = (luasan_data["total"] or 0.0) + luas_val

        if pekerja_val or blok_val:
            production_records.append({
                "tahun": tahun_val,
                "blok": blok_val,
                "kode_pekerja": pekerja_val,
                "jumlah_buah": jumlah_val,
                "raw_jumlah": raw_jumlah,
                "berondolan": brd_val,
                "luasan": luas_val,
                "page": page_num,
                "source": "list_table"
            })

    return {
        "report_format": "tabular_list",
        "production_records": production_records,
        "berondolan_data": berondolan_data,
        "berondolan_pipil_data": {"available": False, "total": None, "per_worker": {}, "raw": None},
        "luasan_data": luasan_data,
        "subtotals": subtotals
    }


def extract_pdf_data(pdf_read_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fungsi utama untuk mengekstrak data lengkap secara modular dan terpisah:
    - Metadata laporan
    - Data produksi per tahun, blok, kode pekerja
    - Data berondolan
    - Data berondolan dipipil
    - Data luasan
    - Subtotal & Grand total
    - Raw extraction preview untuk inspeksi pengguna
    """
    if not pdf_read_result.get("success", False):
        return {
            "success": False,
            "error_message": pdf_read_result.get("error_message", "Gagal membaca PDF"),
            "is_scanned": pdf_read_result.get("is_scanned", False),
            "metadata": {},
            "rows": [],
            "production_records": [],
            "berondolan_data": {"available": False, "total": None},
            "berondolan_pipil_data": {"available": False, "total": None},
            "luasan_data": {"available": False, "total": None},
            "subtotals": {},
            "summary": {},
            "raw_extracted_preview": {}
        }

    all_text = "\n".join(pdf_read_result.get("pages_text", []))
    meta = extract_metadata_from_text(all_text)

    tables_per_page = pdf_read_result.get("tables", [])
    
    production_records: List[Dict[str, Any]] = []
    berondolan_data: Dict[str, Any] = {"available": False, "total": None, "per_worker": {}, "raw": None}
    berondolan_pipil_data: Dict[str, Any] = {"available": False, "total": None, "per_worker": {}, "raw": None}
    luasan_data: Dict[str, Any] = {"available": False, "total": None, "per_worker": {}, "raw": None}
    subtotals: Dict[str, Any] = {"per_block": {}, "per_worker": {}, "grand_total": None}
    detected_format = "none"
    raw_preview_grid = []

    for page_idx, page_tables in enumerate(tables_per_page):
        page_num = page_idx + 1
        for table in page_tables:
            if not table or len(table) < 2:
                continue

            raw_preview_grid = table

            # Cek apakah format matriks (Cross-Tab PB24A / PB24B)
            is_mat, w_idx, w_cols = is_matrix_table(table)
            if is_mat:
                detected_format = "Matriks Silang (PB24 Cross-Tab)"
                res = parse_matrix_format(table, w_idx, w_cols, page_num)
                production_records.extend(res["production_records"])
                
                # Gabungkan data berondolan & luasan
                if res["berondolan_data"]["available"]:
                    berondolan_data = res["berondolan_data"]
                if res["berondolan_pipil_data"]["available"]:
                    berondolan_pipil_data = res["berondolan_pipil_data"]
                if res["luasan_data"]["available"]:
                    luasan_data = res["luasan_data"]
                subtotals = res["subtotals"]
            else:
                # Format daftar baris biasa
                res = parse_list_format(table, page_num)
                if len(res["production_records"]) > 0:
                    detected_format = "Daftar Baris Standar"
                    production_records.extend(res["production_records"])
                    if res["berondolan_data"]["available"]:
                        berondolan_data = res["berondolan_data"]
                    if res["luasan_data"]["available"]:
                        luasan_data = res["luasan_data"]
                    subtotals = res["subtotals"]

    # Fallback ke regex teks jika tabel kosong
    if len(production_records) == 0:
        logger.info("Mencoba fallback parsing regex baris teks...")
        from data_extractor import extract_from_lines  # fallback aman
        fallback_rows = []
        for line in pdf_read_result.get("raw_lines", []):
            m = re.search(r"(?:^|\s)([A-Za-z0-9_-]{1,10})[\s|,]+([A-Za-z0-9_-]{2,10})[\s|,]+([\d.,]+)", line)
            if m:
                b = normalize_code(m.group(1))
                p = normalize_code(m.group(2))
                j = parse_number(m.group(3))
                if b not in ("KEBUN", "AFDELING", "FORM", "DATE", "NO") and j is not None:
                    fallback_rows.append({
                        "tahun": "",
                        "blok": b,
                        "kode_pekerja": p,
                        "jumlah_buah": j,
                        "raw_jumlah": m.group(3),
                        "berondolan": None,
                        "luasan": None,
                        "page": 1,
                        "source": "text_regex"
                    })
        production_records = fallback_rows
        if fallback_rows:
            detected_format = "Ekstraksi Baris Teks (Regex)"

    # Ringkasan data produksi
    total_buah_terhitung = sum(r["jumlah_buah"] for r in production_records if r["jumlah_buah"] is not None)
    unique_blocks = sorted(list(set(r["blok"] for r in production_records if r["blok"])))
    unique_workers = sorted(list(set(r["kode_pekerja"] for r in production_records if r["kode_pekerja"])))

    summary = {
        "detected_format": detected_format,
        "total_rows": len(production_records),
        "total_buah": total_buah_terhitung,
        "total_tertera": subtotals.get("grand_total") or meta.get("total_tertera"),
        "unique_blocks_count": len(unique_blocks),
        "unique_workers_count": len(unique_workers),
        "unique_blocks": unique_blocks,
        "unique_workers": unique_workers
    }

    # Data raw preview untuk Requirement K (Tampilan Detail Ekstraksi)
    raw_preview = {
        "detected_format": detected_format,
        "total_production_extracted": len(production_records),
        "berondolan_info": berondolan_data,
        "berondolan_pipil_info": berondolan_pipil_data,
        "luasan_info": luasan_data,
        "subtotals_info": subtotals,
        "sample_grid": raw_preview_grid[:8] if raw_preview_grid else []
    }

    return {
        "success": True,
        "error_message": None,
        "is_scanned": False,
        "metadata": meta,
        "rows": production_records,  # Kompatibilitas mundur
        "production_records": production_records,
        "berondolan_data": berondolan_data,
        "berondolan_pipil_data": berondolan_pipil_data,
        "luasan_data": luasan_data,
        "subtotals": subtotals,
        "summary": summary,
        "raw_extracted_preview": raw_preview
    }
