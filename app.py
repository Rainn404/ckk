"""
SIPEKA DF - Python API Server (Backend Logika)
===============================================
Arsitektur proyek:
  - UI      : HTML murni (templates/index.html) + CSS + JavaScript (static/)
  - Backend : Python (app.py) sebagai REST API server berbasis http.server standar

Tugas Python di sini:
  1. Menyajikan file HTML/CSS/JS statis ke browser
  2. Menerima upload PDF dari browser melalui POST /api/upload-and-compare
  3. Menjalankan mesin ekstraksi data PDF (pdf_reader, data_extractor)
  4. Menjalankan mesin komparasi & validasi (comparator, validator)
  5. Menyimpan & mengelola riwayat pemeriksaan (history_manager)
  6. Menghasilkan ekspor CSV & HTML siap cetak (exporter)

Python TIDAK merender template. index.html adalah file HTML statis biasa.
"""

import os
import re
import sys
import json
import logging
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Tuple, Optional

import pdf_reader
import data_extractor
import validator
import comparator
import history_manager
import exporter

# Setup logging lokal
LOG_FILE = os.path.join(os.path.dirname(__file__), "sipeka_server.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sipeka.app")
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
MAX_UPLOAD_SIZE = 30 * 1024 * 1024  # 30 MB

os.makedirs(UPLOADS_DIR, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Membersihkan nama file dari path traversal dan karakter ilegal."""
    base = os.path.basename(filename)
    # Hapus karakter yang tidak aman
    clean = re.sub(r'[^A-Za-z0-9_.\-\s()]', '_', base)
    return clean or "uploaded.pdf"


def parse_multipart(body: bytes, boundary: str) -> Dict[str, Dict[str, Any]]:
    """
    Parser multipart/form-data murni menggunakan Python Standard Library
    (kompatibel penuh dengan Python 3.13 dan 3.14 setelah modul cgi dihapus).
    """
    fields: Dict[str, Dict[str, Any]] = {}
    boundary_bytes = boundary.encode("latin1")
    delimiter = b"--" + boundary_bytes

    parts = body.split(delimiter)
    for part in parts:
        if not part or part == b"--\r\n" or part == b"--" or part == b"\r\n":
            continue

        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]

        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue

        headers_part = part[:header_end].decode("latin1", errors="replace")
        content_part = part[header_end + 4:]

        # Parsing header field
        disposition_match = re.search(r'Content-Disposition:\s*form-data;\s*name="([^"]+)"(?:;\s*filename="([^"]*)")?', headers_part, re.IGNORECASE)
        if disposition_match:
            field_name = disposition_match.group(1)
            filename = disposition_match.group(2)
            
            content_type_match = re.search(r'Content-Type:\s*([^\r\n;]+)', headers_part, re.IGNORECASE)
            content_type = content_type_match.group(1).strip() if content_type_match else "text/plain"

            fields[field_name] = {
                "filename": filename,
                "content_type": content_type,
                "data": content_part
            }

    return fields


class SipekaRequestHandler(BaseHTTPRequestHandler):
    """Handler permintaan HTTP untuk antarmuka dan API SIPEKA DF."""

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json(self, data: Any, status_code: int = 200):
        """Mengirim respons dalam format JSON."""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def send_file_response(self, content: bytes, content_type: str, status_code: int = 200, filename: Optional[str] = None):
        """Mengirim berkas biner/teks dengan header yang tepat."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        """Dukungan preflight CORS lokal."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Menangani rute GET untuk halaman HTML dan aset statis."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            # 1. Halaman Utama
            if path in ("/", "/index.html"):
                index_path = os.path.join(TEMPLATES_DIR, "index.html")
                if os.path.exists(index_path):
                    with open(index_path, "rb") as f:
                        self.send_file_response(f.read(), "text/html; charset=utf-8")
                else:
                    self.send_json({"error": "Template index.html tidak ditemukan"}, 404)
                return

            # 2. File Statis (CSS, JS, Ikon)
            if path.startswith("/static/"):
                rel_path = path[len("/static/"):].lstrip("/\\")
                # Cegah directory traversal
                safe_path = os.path.normpath(os.path.join(STATIC_DIR, rel_path))
                if safe_path.startswith(STATIC_DIR) and os.path.isfile(safe_path):
                    mime = "text/plain"
                    if safe_path.endswith(".css"):
                        mime = "text/css; charset=utf-8"
                    elif safe_path.endswith(".js"):
                        mime = "application/javascript; charset=utf-8"
                    elif safe_path.endswith(".png"):
                        mime = "image/png"
                    elif safe_path.endswith(".jpg") or safe_path.endswith(".jpeg"):
                        mime = "image/jpeg"
                    elif safe_path.endswith(".svg"):
                        mime = "image/svg+xml"
                    elif safe_path.endswith(".json"):
                        mime = "application/json"

                    with open(safe_path, "rb") as f:
                        self.send_file_response(f.read(), mime)
                    return
                else:
                    self.send_json({"error": "Berkas statis tidak ditemukan"}, 404)
                    return

            # 3. API Riwayat (GET /api/history)
            if path == "/api/history":
                hist = history_manager.get_all_history()
                self.send_json({"success": True, "history": hist})
                return

            # 4. API Detail Riwayat (GET /api/history/<id>)
            if path.startswith("/api/history/"):
                rec_id = path[len("/api/history/"):].strip()
                item = history_manager.get_history_by_id(rec_id)
                if item:
                    self.send_json({"success": True, "record": item})
                else:
                    self.send_json({"success": False, "error": "Riwayat tidak ditemukan"}, 404)
                return

            # Rute tidak dikenal
            self.send_json({"error": "Endpoint tidak ditemukan"}, 404)

        except Exception as e:
            logger.error(f"Error pada GET {path}: {e}", exc_info=True)
            self.send_json({"success": False, "error": "Terjadi kesalahan internal pada server."}, 500)

    def do_POST(self):
        """Menangani rute POST untuk upload, pembandingan data, dan ekspor."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > MAX_UPLOAD_SIZE:
                self.send_json({"success": False, "error": f"Ukuran file melebihi batas maksimum ({MAX_UPLOAD_SIZE // (1024*1024)} MB)."}, 400)
                return

            body = self.rfile.read(content_length)

            # 1. API Upload & Bandingkan Data
            if path == "/api/upload-and-compare":
                content_type = self.headers.get("Content-Type", "")
                if "multipart/form-data" not in content_type:
                    self.send_json({"success": False, "error": "Format permintaan harus multipart/form-data."}, 400)
                    return

                boundary_match = re.search(r'boundary=([^\s;]+)', content_type)
                if not boundary_match:
                    self.send_json({"success": False, "error": "Header boundary multipart tidak ditemukan."}, 400)
                    return

                boundary = boundary_match.group(1).strip('"\'')
                form_fields = parse_multipart(body, boundary)

                mandor_field = form_fields.get("mandor_file")
                kcs_field = form_fields.get("kcs_file")

                # Validasi kelengkapan kedua file
                if not mandor_field or not mandor_field.get("filename") or len(mandor_field.get("data", b"")) == 0:
                    self.send_json({"success": False, "error": "File Laporan Mandor (PB24A) belum dipilih atau kosong."}, 400)
                    return

                if not kcs_field or not kcs_field.get("filename") or len(kcs_field.get("data", b"")) == 0:
                    self.send_json({"success": False, "error": "File Laporan KCS (PB24B) belum dipilih atau kosong."}, 400)
                    return

                # Validasi ekstensi PDF
                if not mandor_field["filename"].lower().endswith(".pdf"):
                    self.send_json({"success": False, "error": "Format file Laporan Mandor tidak valid. Hanya file berekstensi .pdf yang diperbolehkan."}, 400)
                    return

                if not kcs_field["filename"].lower().endswith(".pdf"):
                    self.send_json({"success": False, "error": "Format file Laporan KCS tidak valid. Hanya file berekstensi .pdf yang diperbolehkan."}, 400)
                    return

                mandor_safe_name = sanitize_filename(mandor_field["filename"])
                kcs_safe_name = sanitize_filename(kcs_field["filename"])

                mandor_temp_path = os.path.join(UPLOADS_DIR, f"mandor_{os.getpid()}_{mandor_safe_name}")
                kcs_temp_path = os.path.join(UPLOADS_DIR, f"kcs_{os.getpid()}_{kcs_safe_name}")

                try:
                    # Simpan file sementara
                    with open(mandor_temp_path, "wb") as f:
                        f.write(mandor_field["data"])
                    with open(kcs_temp_path, "wb") as f:
                        f.write(kcs_field["data"])

                    # 1. Baca PDF Mandor
                    mandor_pdf_res = pdf_reader.read_pdf(mandor_temp_path)
                    if not mandor_pdf_res["success"]:
                        self.send_json({
                            "success": False,
                            "error": f"Laporan Mandor gagal diproses: {mandor_pdf_res['error_message']}",
                            "is_scanned": mandor_pdf_res.get("is_scanned", False)
                        }, 400)
                        return

                    # 2. Baca PDF KCS
                    kcs_pdf_res = pdf_reader.read_pdf(kcs_temp_path)
                    if not kcs_pdf_res["success"]:
                        self.send_json({
                            "success": False,
                            "error": f"Laporan KCS gagal diproses: {kcs_pdf_res['error_message']}",
                            "is_scanned": kcs_pdf_res.get("is_scanned", False)
                        }, 400)
                        return

                    # 3. Ekstraksi Data Mandor & KCS
                    mandor_extracted = data_extractor.extract_pdf_data(mandor_pdf_res)
                    kcs_extracted = data_extractor.extract_pdf_data(kcs_pdf_res)

                    if len(mandor_extracted["rows"]) == 0:
                        self.send_json({
                            "success": False,
                            "error": "Tidak ada baris data panen yang berhasil diekstrak dari Laporan Mandor. Periksa apakah struktur tabel terbaca dengan baik.",
                        }, 400)
                        return

                    if len(kcs_extracted["rows"]) == 0:
                        self.send_json({
                            "success": False,
                            "error": "Tidak ada baris data angkut yang berhasil diekstrak dari Laporan KCS. Periksa apakah struktur tabel terbaca dengan baik.",
                        }, 400)
                        return

                    # 4. Validasi Identitas Kedua Laporan
                    validation_res = validator.validate_reports_identity(
                        mandor_extracted["metadata"],
                        kcs_extracted["metadata"]
                    )

                    # 5. Jalankan Mesin Pembanding Data
                    comparison_res = comparator.compare_datasets(
                        mandor_extracted.get("production_records", mandor_extracted["rows"]),
                        kcs_extracted.get("production_records", kcs_extracted["rows"]),
                        mandor_extracted["metadata"],
                        kcs_extracted["metadata"],
                        mandor_berondolan=mandor_extracted.get("berondolan_data"),
                        kcs_berondolan=kcs_extracted.get("berondolan_data"),
                        mandor_berondolan_pipil=mandor_extracted.get("berondolan_pipil_data"),
                        kcs_berondolan_pipil=kcs_extracted.get("berondolan_pipil_data"),
                        mandor_luasan=mandor_extracted.get("luasan_data"),
                        kcs_luasan=kcs_extracted.get("luasan_data")
                    )

                    # 6. Simpan ke Riwayat Lokal
                    history_rec = history_manager.save_history_record(
                        mandor_safe_name,
                        kcs_safe_name,
                        mandor_extracted["metadata"],
                        kcs_extracted["metadata"],
                        comparison_res
                    )

                    # Kirim hasil
                    self.send_json({
                        "success": True,
                        "history_id": history_rec.get("id"),
                        "mandor_filename": mandor_safe_name,
                        "kcs_filename": kcs_safe_name,
                        "mandor_meta": mandor_extracted["metadata"],
                        "kcs_meta": kcs_extracted["metadata"],
                        "mandor_summary": mandor_extracted["summary"],
                        "kcs_summary": kcs_extracted["summary"],
                        "mandor_raw_preview": mandor_extracted.get("raw_extracted_preview"),
                        "kcs_raw_preview": kcs_extracted.get("raw_extracted_preview"),
                        "validation": validation_res,
                        "comparison": comparison_res
                    })
                    return

                finally:
                    # Bersihkan file sementara setelah pemrosesan selesai
                    for p in (mandor_temp_path, kcs_temp_path):
                        if os.path.exists(p):
                            try:
                                os.remove(p)
                            except Exception as ce:
                                logger.warning(f"Gagal menghapus file sementara {p}: {ce}")

            # 2. API Ekspor CSV (POST /api/export/csv)
            if path == "/api/export/csv":
                payload = json.loads(body.decode("utf-8"))
                csv_data = exporter.export_to_csv(
                    payload.get("comparison_result", {}),
                    payload.get("mandor_meta", {}),
                    payload.get("kcs_meta", {}),
                    payload.get("mandor_file", "Laporan_Mandor.pdf"),
                    payload.get("kcs_file", "Laporan_KCS.pdf")
                )
                csv_bytes = csv_data.encode("utf-8-sig")
                self.send_file_response(csv_bytes, "text/csv; charset=utf-8", 200, "Hasil_Pemeriksaan_SIPEKA_DF.csv")
                return

            # 3. API Ekspor HTML Siap Cetak (POST /api/export/html)
            if path == "/api/export/html":
                payload = json.loads(body.decode("utf-8"))
                html_data = exporter.generate_printable_html(
                    payload.get("comparison_result", {}),
                    payload.get("mandor_meta", {}),
                    payload.get("kcs_meta", {}),
                    payload.get("mandor_file", "Laporan_Mandor.pdf"),
                    payload.get("kcs_file", "Laporan_KCS.pdf")
                )
                self.send_file_response(html_data.encode("utf-8"), "text/html; charset=utf-8", 200)
                return

            # Rute tidak dikenal
            self.send_json({"error": "Endpoint POST tidak ditemukan"}, 404)

        except Exception as e:
            logger.error(f"Error pada POST {path}: {e}", exc_info=True)
            self.send_json({"success": False, "error": "Terjadi kesalahan pada pemrosesan server."}, 500)

    def do_DELETE(self):
        """Menangani penghapusan riwayat."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            if path == "/api/history":
                history_manager.clear_all_history()
                self.send_json({"success": True, "message": "Seluruh riwayat berhasil dihapus."})
                return

            if path.startswith("/api/history/"):
                rec_id = path[len("/api/history/"):].strip()
                deleted = history_manager.delete_history_by_id(rec_id)
                if deleted:
                    self.send_json({"success": True, "message": "Riwayat berhasil dihapus."})
                else:
                    self.send_json({"success": False, "error": "Riwayat tidak ditemukan."}, 404)
                return

            self.send_json({"error": "Endpoint DELETE tidak ditemukan"}, 404)

        except Exception as e:
            logger.error(f"Error pada DELETE {path}: {e}", exc_info=True)
            self.send_json({"success": False, "error": "Gagal menghapus riwayat."}, 500)


def run_server(port: int = 8080):
    """Menjalankan server HTTP lokal SIPEKA DF."""
    server_address = ("127.0.0.1", port)
    
    # Coba port target, jika sedang terpakai coba port cadangan
    ports_to_try = [port, 8081, 8501, 8888, 8000]
    httpd = None
    active_port = port

    for p in ports_to_try:
        try:
            httpd = HTTPServer(("127.0.0.1", p), SipekaRequestHandler)
            active_port = p
            break
        except OSError:
            logger.warning(f"Port {p} sedang digunakan, mencoba port berikutnya...")

    if not httpd:
        print("ERROR: Tidak dapat mengikat port lokal.")
        sys.exit(1)

    print("==================================================================")
    print("      SIPEKA DF - Sistem Pemeriksa Kesalahan Data Digital Farming")
    print("==================================================================")
    print(f" Status  : Berjalan secara lokal")
    print(f" Alamat  : http://127.0.0.1:{active_port}")
    print(" Tekan Ctrl+C untuk menghentikan server.")
    print("==================================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nMenghentikan server SIPEKA DF...")
    finally:
        httpd.server_close()
        print("Server dihentikan.")


if __name__ == "__main__":
    port_arg = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    run_server(port_arg)
