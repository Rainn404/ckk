"""
SIPEKA DF - History Manager Module
Menyimpan dan mengelola riwayat hasil pemeriksaan dalam format JSON lokal (data/history.json).
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "history.json")


def _ensure_data_dir():
    d = os.path.dirname(HISTORY_FILE)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


def get_all_history() -> List[Dict[str, Any]]:
    """Mengambil seluruh daftar riwayat pemeriksaan, diurutkan dari terbaru."""
    _ensure_data_dir()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                # Urutkan dari yang paling baru
                return sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
            return []
    except Exception:
        return []


def save_history_record(
    mandor_filename: str,
    kcs_filename: str,
    mandor_meta: Dict[str, Any],
    kcs_meta: Dict[str, Any],
    comparison_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Menyimpan hasil pemeriksaan ke file JSON lokal."""
    _ensure_data_dir()
    hist = get_all_history()

    now = datetime.now()
    record_id = str(uuid.uuid4())[:8]

    status_counts = comparison_result.get("status_counts", {})
    tgl = (
        mandor_meta.get("tanggal_aktivitas") or
        mandor_meta.get("tanggal_laporan") or
        kcs_meta.get("tanggal_aktivitas") or
        kcs_meta.get("tanggal_laporan") or
        now.strftime("%d/%m/%Y")
    )
    afd = mandor_meta.get("afdeling") or kcs_meta.get("afdeling") or "-"
    kebun = mandor_meta.get("kebun") or kcs_meta.get("kebun") or "-"

    record = {
        "id": record_id,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_display": now.strftime("%d %b %Y %H:%M"),
        "mandor_filename": mandor_filename,
        "kcs_filename": kcs_filename,
        "tanggal_laporan": tgl,
        "afdeling": afd,
        "kebun": kebun,
        "total_rows": comparison_result.get("total_rows_compared", 0),
        "matched_count": status_counts.get("Cocok", 0),
        "diff_count": status_counts.get("Berbeda", 0),
        "need_verification_count": status_counts.get("Perlu Verifikasi", 0),
        "total_mandor": comparison_result.get("total_mandor", 0),
        "total_kcs": comparison_result.get("total_kcs", 0),
        "total_selisih": comparison_result.get("total_selisih", 0),
        "has_offsetting_differences": comparison_result.get("has_offsetting_differences", False),
        "affected_blocks_count": comparison_result.get("affected_blocks_count", 0),
        "affected_workers_count": comparison_result.get("affected_workers_count", 0),
        # Simpan hasil perbandingan agar bisa dibuka kembali dari riwayat
        "comparison_result": comparison_result,
        "mandor_meta": mandor_meta,
        "kcs_meta": kcs_meta
    }

    hist.insert(0, record)

    # Batasi riwayat maksimal 100 entri terakhir
    if len(hist) > 100:
        hist = hist[:100]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

    return record


def get_history_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """Mengambil satu riwayat berdasarkan ID."""
    hist = get_all_history()
    for item in hist:
        if item.get("id") == record_id:
            return item
    return None


def delete_history_by_id(record_id: str) -> bool:
    """Menghapus satu entri riwayat berdasarkan ID."""
    _ensure_data_dir()
    hist = get_all_history()
    new_hist = [h for h in hist if h.get("id") != record_id]
    if len(new_hist) != len(hist):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_hist, f, indent=2, ensure_ascii=False)
        return True
    return False


def clear_all_history() -> bool:
    """Menghapus seluruh riwayat pemeriksaan."""
    _ensure_data_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    return True
