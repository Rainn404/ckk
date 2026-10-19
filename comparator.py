"""
SIPEKA DF - Comparator Engine Module (Refactored & Enhanced)
Membandingkan data aktivitas panen Mandor (PB24A) dan pengangkutan KCS (PB24B).
Memisahkan produksi janjang buah dari berondolan dan luasan.
Mendeteksi selisih per pekerja, duplikasi sejati, baris hilang, serta selisih yang saling meniadakan (offsetting).
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple


def compare_datasets(
    mandor_rows: List[Dict[str, Any]],
    kcs_rows: List[Dict[str, Any]],
    mandor_meta: Optional[Dict[str, Any]] = None,
    kcs_meta: Optional[Dict[str, Any]] = None,
    mandor_berondolan: Optional[Dict[str, Any]] = None,
    kcs_berondolan: Optional[Dict[str, Any]] = None,
    mandor_berondolan_pipil: Optional[Dict[str, Any]] = None,
    kcs_berondolan_pipil: Optional[Dict[str, Any]] = None,
    mandor_luasan: Optional[Dict[str, Any]] = None,
    kcs_luasan: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Membandingkan data laporan Mandor dan KCS.
    Rumus Utama: Selisih = Nilai KCS - Nilai Mandor
    """
    mandor_meta = mandor_meta or {}
    kcs_meta = kcs_meta or {}
    mandor_berondolan = mandor_berondolan or {"available": False}
    kcs_berondolan = kcs_berondolan or {"available": False}
    mandor_berondolan_pipil = mandor_berondolan_pipil or {"available": False}
    kcs_berondolan_pipil = kcs_berondolan_pipil or {"available": False}
    mandor_luasan = mandor_luasan or {"available": False}
    kcs_luasan = kcs_luasan or {"available": False}

    tgl_aktivitas = (
        mandor_meta.get("tanggal_aktivitas") or
        kcs_meta.get("tanggal_aktivitas") or
        mandor_meta.get("tanggal_laporan") or
        kcs_meta.get("tanggal_laporan") or
        "-"
    )

    # 1. Indeks baris berdasarkan kunci unik transaksi: (blok, kode_pekerja)
    def index_rows(rows: List[Dict[str, Any]]) -> Tuple[Dict[Tuple[str, str], List[Dict[str, Any]]], List[Dict[str, Any]]]:
        indexed = defaultdict(list)
        duplicates = []
        for r in rows:
            blok = (r.get("blok") or "").strip().upper()
            pekerja = (r.get("kode_pekerja") or "").strip().upper()
            
            # Abaikan jika blok atau pekerja tidak valid
            if not blok or blok in ("-", "NONE"):
                blok = "TIDAK TERIDENTIFIKASI"
            
            key = (blok, pekerja)
            indexed[key].append(r)

        # Cek duplikat sejati: kunci (blok, pekerja) muncul lebih dari sekali pada sumber yang sama
        for key, items in indexed.items():
            if len(items) > 1 and key[0] != "TIDAK TERIDENTIFIKASI" and key[1]:
                duplicates.append({"key": key, "items": items})

        return indexed, duplicates

    mandor_by_key, mandor_dups = index_rows(mandor_rows)
    kcs_by_key, kcs_dups = index_rows(kcs_rows)

    all_keys = set(mandor_by_key.keys()).union(set(kcs_by_key.keys()))

    results: List[Dict[str, Any]] = []
    
    # Rekapitulasi per Blok
    blocks_summary = defaultdict(lambda: {
        "mandor_total": 0.0,
        "kcs_total": 0.0,
        "mandor_rows": 0,
        "kcs_rows": 0,
        "discrepancies": 0
    })

    affected_blocks = set()
    affected_workers = set()
    row_number = 1

    sorted_keys = sorted(all_keys, key=lambda k: (k[0], k[1]))

    for key in sorted_keys:
        blok, pekerja = key
        m_list = mandor_by_key.get(key, [])
        k_list = kcs_by_key.get(key, [])

        is_dup_m = len(m_list) > 1
        is_dup_k = len(k_list) > 1

        # Skenario 1: Duplikat Sejati pada salah satu atau kedua dokumen
        if is_dup_m or is_dup_k:
            dup_source = []
            if is_dup_m: dup_source.append(f"Mandor ({len(m_list)}x)")
            if is_dup_k: dup_source.append(f"KCS ({len(k_list)}x)")

            m_val = sum(r["jumlah_buah"] for r in m_list if r.get("jumlah_buah") is not None) if m_list else None
            k_val = sum(r["jumlah_buah"] for r in k_list if r.get("jumlah_buah") is not None) if k_list else None
            
            selisih = None
            if m_val is not None and k_val is not None:
                selisih = k_val - m_val

            status = "Duplikat"
            keterangan = f"Kombinasi blok & pekerja tercatat ganda pada laporan {', '.join(dup_source)}."
            
            affected_blocks.add(blok)
            if pekerja: affected_workers.add(pekerja)
            blocks_summary[blok]["discrepancies"] += 1
            if m_val is not None: blocks_summary[blok]["mandor_total"] += m_val
            if k_val is not None: blocks_summary[blok]["kcs_total"] += k_val

            results.append({
                "no": row_number,
                "tanggal": tgl_aktivitas,
                "blok": blok,
                "kode_pekerja": pekerja or "-",
                "data_mandor": m_val,
                "data_kcs": k_val,
                "raw_mandor": ", ".join([str(r.get("raw_jumlah", "")) for r in m_list]),
                "raw_kcs": ", ".join([str(r.get("raw_jumlah", "")) for r in k_list]),
                "selisih": selisih,
                "status": status,
                "keterangan": keterangan,
                "severity": "orange",
                "detail": {
                    "is_duplicate": True,
                    "mandor_occurrences": len(m_list),
                    "kcs_occurrences": len(k_list),
                    "reason": f"Kunci transaksi (Blok {blok}, {pekerja}) memiliki entri ganda pada berkas yang sama."
                }
            })
            row_number += 1
            continue

        # Skenario 2: Hanya ada di KCS
        if not m_list and k_list:
            k_row = k_list[0]
            k_val = k_row.get("jumlah_buah")
            status = "Hanya Ada di KCS"
            keterangan = "Tercatat diangkut KCS, namun tidak ditemukan di laporan panen Mandor."
            
            affected_blocks.add(blok)
            if pekerja: affected_workers.add(pekerja)
            blocks_summary[blok]["discrepancies"] += 1
            blocks_summary[blok]["kcs_rows"] += 1
            if k_val is not None: blocks_summary[blok]["kcs_total"] += k_val

            results.append({
                "no": row_number,
                "tanggal": tgl_aktivitas,
                "blok": blok,
                "kode_pekerja": pekerja or "-",
                "data_mandor": None,
                "data_kcs": k_val,
                "raw_mandor": "-",
                "raw_kcs": k_row.get("raw_jumlah", "-"),
                "selisih": k_val if k_val is not None else None,
                "status": status,
                "keterangan": keterangan,
                "severity": "orange",
                "detail": {
                    "reason": "KCS mencatat pemuatan janjang, tetapi pemanen tidak terdaftar dalam form PB24A Mandor. Periksa apakah pemanen bantuan atau salah blok."
                }
            })
            row_number += 1
            continue

        # Skenario 3: Hanya ada di Mandor
        if m_list and not k_list:
            m_row = m_list[0]
            m_val = m_row.get("jumlah_buah")
            status = "Hanya Ada di Mandor"
            keterangan = "Tercatat dipanen Mandor, namun belum tercatat diangkut oleh KCS."
            
            affected_blocks.add(blok)
            if pekerja: affected_workers.add(pekerja)
            blocks_summary[blok]["discrepancies"] += 1
            blocks_summary[blok]["mandor_rows"] += 1
            if m_val is not None: blocks_summary[blok]["mandor_total"] += m_val

            results.append({
                "no": row_number,
                "tanggal": tgl_aktivitas,
                "blok": blok,
                "kode_pekerja": pekerja or "-",
                "data_mandor": m_val,
                "data_kcs": None,
                "raw_mandor": m_row.get("raw_jumlah", "-"),
                "raw_kcs": "-",
                "selisih": -m_val if m_val is not None else None,
                "status": status,
                "keterangan": keterangan,
                "severity": "orange",
                "detail": {
                    "reason": "Buah telah dipanen oleh Mandor tetapi belum dimuat oleh KCS (indikasi buah restan di TPH)."
                }
            })
            row_number += 1
            continue

        # Skenario 4: Ada di kedua laporan (Pencocokan 1-to-1)
        m_row = m_list[0]
        k_row = k_list[0]
        m_val = m_row.get("jumlah_buah")
        k_val = k_row.get("jumlah_buah")

        blocks_summary[blok]["mandor_rows"] += 1
        blocks_summary[blok]["kcs_rows"] += 1
        if m_val is not None: blocks_summary[blok]["mandor_total"] += m_val
        if k_val is not None: blocks_summary[blok]["kcs_total"] += k_val

        if m_val is None or k_val is None:
            status = "Data Tidak Lengkap"
            empty_side = "Mandor" if m_val is None else "KCS"
            if m_val is None and k_val is None: empty_side = "Mandor & KCS"
            keterangan = f"Nilai angka jumlah buah kosong pada laporan {empty_side}."
            
            affected_blocks.add(blok)
            if pekerja: affected_workers.add(pekerja)
            blocks_summary[blok]["discrepancies"] += 1

            results.append({
                "no": row_number,
                "tanggal": tgl_aktivitas,
                "blok": blok,
                "kode_pekerja": pekerja or "-",
                "data_mandor": m_val,
                "data_kcs": k_val,
                "raw_mandor": m_row.get("raw_jumlah", "-"),
                "raw_kcs": k_row.get("raw_jumlah", "-"),
                "selisih": None,
                "status": status,
                "keterangan": keterangan,
                "severity": "gray",
                "detail": {"reason": "Salah satu nilai tidak terbaca atau berupa sel kosong."}
            })
            row_number += 1
            continue

        selisih = k_val - m_val

        if selisih == 0:
            status = "Cocok"
            keterangan = "Jumlah buah sesuai antara laporan Mandor dan KCS."
            severity = "green"
            detail_reason = "Data identik dan terverifikasi."
        else:
            status = "Berbeda"
            severity = "red"
            affected_blocks.add(blok)
            if pekerja: affected_workers.add(pekerja)
            blocks_summary[blok]["discrepancies"] += 1

            if selisih > 0:
                keterangan = f"KCS mencatat lebih banyak {abs(selisih):g} janjang dibanding Mandor."
                detail_reason = f"KCS ({k_val:g}) > Mandor ({m_val:g}). Selisih: +{selisih:g}. Kemungkinan terjadi penggabungan janjang pekerja lain atau kelebihan hitung."
            else:
                keterangan = f"KCS mencatat lebih sedikit {abs(selisih):g} janjang dibanding Mandor."
                detail_reason = f"KCS ({k_val:g}) < Mandor ({m_val:g}). Selisih: {selisih:g}. Kemungkinan buah tertinggal di TPH (restan) atau afkir."

        results.append({
            "no": row_number,
            "tanggal": tgl_aktivitas,
            "blok": blok,
            "kode_pekerja": pekerja or "-",
            "data_mandor": m_val,
            "data_kcs": k_val,
            "raw_mandor": m_row.get("raw_jumlah", ""),
            "raw_kcs": k_row.get("raw_jumlah", ""),
            "selisih": selisih,
            "status": status,
            "keterangan": keterangan,
            "severity": severity,
            "detail": {
                "mandor_val": m_val,
                "kcs_val": k_val,
                "diff": selisih,
                "reason": detail_reason,
                "page_mandor": m_row.get("page", 1),
                "page_kcs": k_row.get("page", 1)
            }
        })
        row_number += 1

    # 5. Rekonsiliasi Atribut Tambahan (Berondolan, Berondolan Pipil, Luasan)
    # Dipisahkan dari jumlah buah janjang sesuai instruksi spesifikasi!
    additional_attributes: List[Dict[str, Any]] = []

    # A. Berondolan Utama
    m_brd_tot = mandor_berondolan.get("total")
    k_brd_tot = kcs_berondolan.get("total")
    if mandor_berondolan.get("available") or kcs_berondolan.get("available"):
        if m_brd_tot is not None and k_brd_tot is not None:
            brd_diff = k_brd_tot - m_brd_tot
            brd_status = "Cocok" if brd_diff == 0 else "Berbeda"
            additional_attributes.append({
                "attribute": "Berondolan (Kg/Sak)",
                "mandor_value": m_brd_tot,
                "kcs_value": k_brd_tot,
                "selisih": brd_diff,
                "status": brd_status,
                "keterangan": "Sesuai" if brd_diff == 0 else f"Selisih berondolan: {brd_diff:+g}"
            })
        else:
            additional_attributes.append({
                "attribute": "Berondolan (Kg/Sak)",
                "mandor_value": m_brd_tot,
                "kcs_value": k_brd_tot,
                "selisih": None,
                "status": "Tidak Dapat Dibandingkan",
                "keterangan": "Salah satu laporan tidak mencantumkan data berondolan."
            })

    # B. Berondolan Pipil
    m_pipil_tot = mandor_berondolan_pipil.get("total")
    k_pipil_tot = kcs_berondolan_pipil.get("total")
    if mandor_berondolan_pipil.get("available") or kcs_berondolan_pipil.get("available"):
        if m_pipil_tot is not None and k_pipil_tot is not None:
            pipil_diff = k_pipil_tot - m_pipil_tot
            pipil_status = "Cocok" if pipil_diff == 0 else "Berbeda"
            additional_attributes.append({
                "attribute": "Berondolan Dipipil",
                "mandor_value": m_pipil_tot,
                "kcs_value": k_pipil_tot,
                "selisih": pipil_diff,
                "status": pipil_status,
                "keterangan": "Sesuai" if pipil_diff == 0 else f"Selisih pipil: {pipil_diff:+g}"
            })
        else:
            missing_report = "Mandor" if not mandor_berondolan_pipil.get("available") else "KCS"
            additional_attributes.append({
                "attribute": "Berondolan Dipipil",
                "mandor_value": m_pipil_tot,
                "kcs_value": k_pipil_tot,
                "selisih": None,
                "status": f"Tidak Tersedia pada Laporan {missing_report}",
                "keterangan": f"Kolom berondolan dipipil tidak terdapat pada laporan {missing_report}."
            })

    # C. Luasan (Ha)
    m_luas_tot = mandor_luasan.get("total")
    k_luas_tot = kcs_luasan.get("total")
    if mandor_luasan.get("available") or kcs_luasan.get("available"):
        if m_luas_tot is not None and k_luas_tot is not None:
            luas_diff = k_luas_tot - m_luas_tot
            luas_status = "Cocok" if luas_diff == 0 else "Berbeda"
            additional_attributes.append({
                "attribute": "Luasan Panen (Ha)",
                "mandor_value": m_luas_tot,
                "kcs_value": k_luas_tot,
                "selisih": luas_diff,
                "status": luas_status,
                "keterangan": "Sesuai" if luas_diff == 0 else f"Selisih luasan: {luas_diff:+g} Ha"
            })
        else:
            missing_report = "Mandor" if not mandor_luasan.get("available") else "KCS"
            additional_attributes.append({
                "attribute": "Luasan Panen (Ha)",
                "mandor_value": m_luas_tot,
                "kcs_value": k_luas_tot,
                "selisih": None,
                "status": f"Tidak Tersedia pada Laporan {missing_report}",
                "keterangan": f"Laporan {missing_report} tidak mencatat luasan (bukan selisih produksi buah)."
            })

    # 6. Analisis Total Keseluruhan dan Blok
    total_mandor = sum(r["data_mandor"] for r in results if r["data_mandor"] is not None)
    total_kcs = sum(r["data_kcs"] for r in results if r["data_kcs"] is not None)
    total_selisih = total_kcs - total_mandor

    # Analisis Selisih yang Saling Meniadakan (Offsetting Differences)
    has_discrepancies = any(r["status"] != "Cocok" for r in results)
    has_offsetting_differences = (total_selisih == 0) and has_discrepancies

    # Ringkasan blok terformat
    block_breakdown = []
    for blk, bdata in sorted(blocks_summary.items(), key=lambda x: str(x[0])):
        b_selisih = bdata["kcs_total"] - bdata["mandor_total"]
        block_breakdown.append({
            "blok": blk,
            "mandor_total": bdata["mandor_total"],
            "kcs_total": bdata["kcs_total"],
            "selisih": b_selisih,
            "discrepancies": bdata["discrepancies"],
            "status": "Cocok" if b_selisih == 0 and bdata["discrepancies"] == 0 else "Perlu Verifikasi"
        })

    status_counts = {
        "Cocok": sum(1 for r in results if r["status"] == "Cocok"),
        "Berbeda": sum(1 for r in results if r["status"] == "Berbeda"),
        "Hanya Ada di Mandor": sum(1 for r in results if r["status"] == "Hanya Ada di Mandor"),
        "Hanya Ada di KCS": sum(1 for r in results if r["status"] == "Hanya Ada di KCS"),
        "Data Tidak Lengkap": sum(1 for r in results if r["status"] == "Data Tidak Lengkap"),
        "Duplikat": sum(1 for r in results if r["status"] == "Duplikat"),
        "Perlu Verifikasi": sum(1 for r in results if r["status"] in ("Berbeda", "Hanya Ada di Mandor", "Hanya Ada di KCS", "Data Tidak Lengkap", "Duplikat"))
    }

    return {
        "results": results,
        "additional_attributes": additional_attributes,
        "total_rows_compared": len(results),
        "status_counts": status_counts,
        "total_mandor": total_mandor,
        "total_kcs": total_kcs,
        "total_selisih": total_selisih,
        "has_offsetting_differences": has_offsetting_differences,
        "affected_blocks_count": len(affected_blocks),
        "affected_workers_count": len(affected_workers),
        "affected_blocks": sorted(list(affected_blocks)),
        "affected_workers": sorted(list(affected_workers)),
        "block_breakdown": block_breakdown,
        "disclaimer": (
            "PENTING: Perbedaan antara laporan pengumpulan buah (Mandor) dan pengangkutan buah (KCS) "
            "belum tentu merupakan kesalahan input. Perbedaan dapat disebabkan oleh waktu pencatatan, "
            "buah restan (tertinggal di TPH), atau proses operasional lapangan. Harap gunakan data ini "
            "sebagai panduan verifikasi lapangan."
        )
    }
