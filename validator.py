"""
SIPEKA DF - Validator Module
Melakukan validasi konsistensi identitas antara Laporan Mandor dan Laporan KCS
sebelum proses perbandingan data dilakukan.
"""

from typing import Dict, Any, List, Tuple


def normalize_meta_value(val: Any) -> str:
    """Normalisasi nilai string untuk perbandingan toleran (case-insensitive, tanpa spasi ganda)."""
    if val is None:
        return ""
    s = str(val).strip().upper()
    # Hapus spasi berlebih
    import re
    s = re.sub(r"\s+", " ", s)
    return s


def validate_reports_identity(mandor_meta: Dict[str, Any], kcs_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Membandingkan identitas kedua laporan:
    - Tanggal Laporan
    - Kebun / Estate
    - Afdeling
    - Tanggal Aktivitas / Panen
    - Jenis Laporan
    
    Returns dict:
        - is_valid: bool (True jika tidak ada ketidakcocokan fatal)
        - warnings: List[dict] (peringatan perbedaan yang perlu diketahui pengguna)
        - info: List[dict] (catatan informasi, misal identitas tidak terdeteksi)
        - match_summary: dict
    """
    warnings: List[Dict[str, str]] = []
    info: List[Dict[str, str]] = []

    # 1. Validasi Tanggal Aktivitas / Panen
    tgl_m = normalize_meta_value(mandor_meta.get("tanggal_aktivitas") or mandor_meta.get("tanggal_laporan"))
    tgl_k = normalize_meta_value(kcs_meta.get("tanggal_aktivitas") or kcs_meta.get("tanggal_laporan"))

    if tgl_m and tgl_k:
        if tgl_m != tgl_k:
            warnings.append({
                "field": "Tanggal Aktivitas / Panen",
                "mandor_value": mandor_meta.get("tanggal_aktivitas") or mandor_meta.get("tanggal_laporan"),
                "kcs_value": kcs_meta.get("tanggal_aktivitas") or kcs_meta.get("tanggal_laporan"),
                "severity": "warning",
                "message": f"Tanggal aktivitas kedua laporan berbeda! Mandor mencatat '{tgl_m}', sedangkan KCS mencatat '{tgl_k}'."
            })
    else:
        info.append({
            "field": "Tanggal Aktivitas",
            "message": "Informasi tanggal tidak lengkap pada salah satu atau kedua laporan (Tidak Dapat Diverifikasi)."
        })

    # 2. Validasi Afdeling
    afd_m = normalize_meta_value(mandor_meta.get("afdeling"))
    afd_k = normalize_meta_value(kcs_meta.get("afdeling"))

    if afd_m and afd_k:
        # Periksa apakah ada kesamaan inti (misal: 'AFD 1' vs 'AFDELING 1')
        clean_afd_m = afd_m.replace("AFDELING", "").replace("AFD", "").replace("DIVISI", "").replace("DIV", "").strip()
        clean_afd_k = afd_k.replace("AFDELING", "").replace("AFD", "").replace("DIVISI", "").replace("DIV", "").strip()
        
        if clean_afd_m != clean_afd_k and afd_m != afd_k:
            warnings.append({
                "field": "Afdeling",
                "mandor_value": mandor_meta.get("afdeling"),
                "kcs_value": kcs_meta.get("afdeling"),
                "severity": "danger",
                "message": f"Afdeling kedua laporan berbeda! Mandor mencatat '{mandor_meta.get('afdeling')}', sedangkan KCS mencatat '{kcs_meta.get('afdeling')}'."
            })
    else:
        info.append({
            "field": "Afdeling",
            "message": "Informasi Afdeling tidak ditemukan pada salah satu atau kedua laporan (Tidak Dapat Diverifikasi)."
        })

    # 3. Validasi Kebun / Estate
    kebun_m = normalize_meta_value(mandor_meta.get("kebun"))
    kebun_k = normalize_meta_value(kcs_meta.get("kebun"))

    if kebun_m and kebun_k:
        if kebun_m != kebun_k:
            warnings.append({
                "field": "Kebun / Unit",
                "mandor_value": mandor_meta.get("kebun"),
                "kcs_value": kcs_meta.get("kebun"),
                "severity": "warning",
                "message": f"Nama Kebun/Unit berbeda: Mandor '{mandor_meta.get('kebun')}' vs KCS '{kcs_meta.get('kebun')}'."
            })
    else:
        info.append({
            "field": "Kebun",
            "message": "Informasi Kebun tidak terdeteksi pada salah satu atau kedua laporan (Tidak Dapat Diverifikasi)."
        })

    # 4. Validasi Jenis Laporan
    jenis_m = mandor_meta.get("jenis_laporan")
    jenis_k = kcs_meta.get("jenis_laporan")
    if jenis_m and jenis_k:
        if jenis_m == jenis_k:
            warnings.append({
                "field": "Jenis Laporan",
                "mandor_value": jenis_m,
                "kcs_value": jenis_k,
                "severity": "warning",
                "message": f"Kedua file terdeteksi sebagai jenis yang sama ({jenis_m}). Pastikan Anda mengunggah Form Pengumpulan Buah (PB24A) pada slot Mandor dan Form Pengangkutan Buah (PB24B) pada slot KCS."
            })

    has_critical_warning = any(w["severity"] == "danger" for w in warnings)

    return {
        "has_warnings": len(warnings) > 0,
        "has_critical_warning": has_critical_warning,
        "warnings": warnings,
        "info": info,
        "identity_matched": len(warnings) == 0,
        "mandor_meta": mandor_meta,
        "kcs_meta": kcs_meta
    }
