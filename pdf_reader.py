"""
SIPEKA DF - PDF Reader Module
Membaca teks, tabel, dan mendeteksi kondisi khusus (scan/OCR, enkripsi, kerusakan) pada file PDF.
Menggunakan PyMuPDF (pymupdf).
"""

import os
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("sipeka.pdf_reader")


def read_pdf(file_path: str) -> Dict[str, Any]:
    """
    Membaca file PDF dan mengembalikan struktur teks, tabel, dan metadata.
    
    Returns dict:
        - success: bool
        - error_message: str | None
        - is_scanned: bool (True jika dokumen berupa scan gambar tanpa text layer)
        - is_encrypted: bool
        - page_count: int
        - pages_text: List[str]
        - tables: List[List[List[str]]] (daftar tabel per halaman)
        - raw_lines: List[str]
    """
    result: Dict[str, Any] = {
        "success": False,
        "error_message": None,
        "is_scanned": False,
        "is_encrypted": False,
        "page_count": 0,
        "pages_text": [],
        "tables": [],
        "raw_lines": [],
        "file_name": os.path.basename(file_path),
        "file_size": 0
    }

    if not os.path.exists(file_path):
        result["error_message"] = f"File tidak ditemukan: {os.path.basename(file_path)}"
        return result

    try:
        result["file_size"] = os.path.getsize(file_path)
    except Exception as e:
        logger.warning(f"Gagal membaca ukuran file: {e}")

    try:
        import pymupdf
    except ImportError:
        result["error_message"] = "Modul 'pymupdf' belum terpasang di sistem. Jalankan: pip install pymupdf"
        return result

    doc = None
    try:
        doc = pymupdf.open(file_path)
        
        if doc.is_encrypted:
            result["is_encrypted"] = True
            result["error_message"] = "File PDF terkunci/terenkripsi dengan kata sandi dan tidak dapat dibaca."
            return result

        result["page_count"] = len(doc)
        if result["page_count"] == 0:
            result["error_message"] = "File PDF kosong (tidak memiliki halaman)."
            return result

        total_char_count = 0
        total_image_count = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            
            # Ekstrak teks halaman
            page_text = page.get_text("text") or ""
            result["pages_text"].append(page_text)
            total_char_count += len(page_text.strip())

            # Hitung gambar pada halaman
            try:
                images = page.get_images()
                total_image_count += len(images)
            except Exception:
                pass

            # Pisahkan ke dalam raw_lines
            for line in page_text.splitlines():
                stripped = line.strip()
                if stripped:
                    result["raw_lines"].append(stripped)

            # Ekstrak tabel menggunakan PyMuPDF TableFinder
            page_tables = []
            try:
                tabs = page.find_tables()
                if tabs and len(tabs.tables) > 0:
                    for t in tabs.tables:
                        extracted = t.extract()
                        if extracted and len(extracted) > 1:
                            # Bersihkan None dan strip whitespace
                            clean_table = []
                            for row in extracted:
                                clean_row = [str(c).strip() if c is not None else "" for c in row]
                                clean_table.append(clean_row)
                            page_tables.append(clean_table)
            except Exception as te:
                logger.debug(f"Pencarian tabel halaman {page_idx + 1} menghasilkan: {te}")

            result["tables"].append(page_tables)

        # Deteksi apakah PDF berupa scan gambar murni tanpa teks digital
        # Jika karakter yang terbaca sangat sedikit (< 20 karakter total) namun ada gambar atau halaman > 0
        if total_char_count < 25 and (total_image_count > 0 or result["page_count"] > 0):
            result["is_scanned"] = True
            result["error_message"] = (
                "File PDF terdeteksi sebagai hasil pemindaian (scan) atau gambar tanpa lapisan teks digital. "
                "Sistem SIPEKA DF memerlukan PDF berbasis teks digital (bukan gambar) atau memerlukan OCR sebelum dapat diproses."
            )
            return result

        result["success"] = True
        return result

    except Exception as e:
        logger.error(f"Error membaca PDF {file_path}: {e}", exc_info=True)
        result["error_message"] = f"Gagal membaca file PDF (berkas rusak atau format tidak valid): {str(e)}"
        return result
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
