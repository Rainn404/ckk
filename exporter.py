"""
SIPEKA DF - Exporter Module
Mengekspor hasil pemeriksaan ke format CSV (Excel-ready dengan UTF-8 BOM)
dan HTML Report yang siap cetak / simpan sebagai PDF melalui browser.
"""

import io
import csv
from datetime import datetime
from typing import Dict, Any, List


def export_to_csv(
    comparison_result: Dict[str, Any],
    mandor_meta: Dict[str, Any],
    kcs_meta: Dict[str, Any],
    mandor_file: str = "Laporan_Mandor.pdf",
    kcs_file: str = "Laporan_KCS.pdf"
) -> str:
    """
    Menghasilkan string CSV dengan BOM UTF-8 (\ufeff) agar kompatibel
    dengan Microsoft Excel pada sistem Windows.
    Menggunakan separator titik koma (;) atau koma (,) standar.
    """
    output = io.StringIO()
    # Tulis BOM UTF-8 untuk Excel
    output.write("\ufeff")

    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # 1. Header Metadata Laporan
    writer.writerow(["SISTEM PEMERIKSA KESALAHAN DATA DIGITAL FARMING (SIPEKA DF)"])
    writer.writerow(["LAPORAN HASIL PEMERIKSAAN KONSISTENSI DATA PANEN & ANGKUT"])
    writer.writerow([])
    writer.writerow(["Waktu Pemeriksaan", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
    writer.writerow(["File Mandor (PB24A)", mandor_file])
    writer.writerow(["File KCS (PB24B)", kcs_file])
    writer.writerow(["Kebun / Estate", mandor_meta.get("kebun") or kcs_meta.get("kebun") or "-"])
    writer.writerow(["Afdeling", mandor_meta.get("afdeling") or kcs_meta.get("afdeling") or "-"])
    writer.writerow(["Tanggal Aktivitas", mandor_meta.get("tanggal_aktivitas") or kcs_meta.get("tanggal_aktivitas") or "-"])
    writer.writerow([])

    # 2. Ringkasan Statistik
    counts = comparison_result.get("status_counts", {})
    writer.writerow(["--- RINGKASAN PEMERIKSAAN ---"])
    writer.writerow(["Total Baris Dibandingkan", comparison_result.get("total_rows_compared", 0)])
    writer.writerow(["Data Cocok", counts.get("Cocok", 0)])
    writer.writerow(["Data Berbeda", counts.get("Berbeda", 0)])
    writer.writerow(["Hanya Ada di Mandor", counts.get("Hanya Ada di Mandor", 0)])
    writer.writerow(["Hanya Ada di KCS", counts.get("Hanya Ada di KCS", 0)])
    writer.writerow(["Data Tidak Lengkap", counts.get("Data Tidak Lengkap", 0)])
    writer.writerow(["Duplikat", counts.get("Duplikat", 0)])
    writer.writerow(["Total Perlu Verifikasi", counts.get("Perlu Verifikasi", 0)])
    writer.writerow(["Total Janjang Mandor", comparison_result.get("total_mandor", 0)])
    writer.writerow(["Total Janjang KCS", comparison_result.get("total_kcs", 0)])
    writer.writerow(["Total Selisih (KCS - Mandor)", comparison_result.get("total_selisih", 0)])
    
    if comparison_result.get("has_offsetting_differences", False):
        writer.writerow(["PERINGATAN", "Terdapat selisih antar-blok yang saling meniadakan (Total akhir sama tetapi distribusi berbeda)!"])
    writer.writerow([])

    # 3. Ringkasan per Blok
    writer.writerow(["--- REKAPITULASI TOTAL PER BLOK ---"])
    writer.writerow(["No", "Blok", "Total Mandor (JJG)", "Total KCS (JJG)", "Selisih (KCS - Mandor)", "Status", "Jml Ketidaksesuaian"])
    for idx, b in enumerate(comparison_result.get("block_breakdown", []), 1):
        writer.writerow([
            idx,
            b.get("blok", "-"),
            b.get("mandor_total", 0),
            b.get("kcs_total", 0),
            b.get("selisih", 0),
            b.get("status", "-"),
            b.get("discrepancies", 0)
        ])
    writer.writerow([])

    # 4. Detail Data Per Baris
    writer.writerow(["--- DETAIL PEMERIKSAAN PER BARIS PEKERJA & BLOK ---"])
    writer.writerow(["No", "Tanggal", "Blok", "Kode Pekerja", "Data Mandor (JJG)", "Data KCS (JJG)", "Selisih", "Status", "Keterangan"])
    
    for r in comparison_result.get("results", []):
        m_val = r.get("data_mandor")
        k_val = r.get("data_kcs")
        diff = r.get("selisih")
        writer.writerow([
            r.get("no", ""),
            r.get("tanggal", "-"),
            r.get("blok", "-"),
            r.get("kode_pekerja", "-"),
            f"{m_val:g}" if m_val is not None else "-",
            f"{k_val:g}" if k_val is not None else "-",
            f"{diff:+g}" if diff is not None else "-",
            r.get("status", "-"),
            r.get("keterangan", "-")
        ])

    # 5. Rekonsiliasi Atribut Tambahan (Berondolan & Luasan)
    add_attrs = comparison_result.get("additional_attributes", [])
    if add_attrs:
        writer.writerow([])
        writer.writerow(["--- REKONSILIASI ATRIBUT TAMBAHAN (BERONDOLAN & LUASAN) ---"])
        writer.writerow(["Atribut", "Nilai Mandor", "Nilai KCS", "Selisih", "Status", "Keterangan"])
        for a in add_attrs:
            diff_str = f"{a['selisih']:+g}" if a.get("selisih") is not None else "-"
            m_str = f"{a['mandor_value']:g}" if a.get("mandor_value") is not None else "-"
            k_str = f"{a['kcs_value']:g}" if a.get("kcs_value") is not None else "-"
            writer.writerow([
                a.get("attribute", "-"),
                m_str,
                k_str,
                diff_str,
                a.get("status", "-"),
                a.get("keterangan", "-")
            ])

    writer.writerow([])
    writer.writerow(["CATATAN PENTING:"])
    writer.writerow([comparison_result.get("disclaimer", "")])

    return output.getvalue()


def generate_printable_html(
    comparison_result: Dict[str, Any],
    mandor_meta: Dict[str, Any],
    kcs_meta: Dict[str, Any],
    mandor_file: str = "Laporan_Mandor.pdf",
    kcs_file: str = "Laporan_KCS.pdf"
) -> str:
    """Menghasilkan dokumen HTML lengkap siap cetak (Print / Save as PDF)."""
    now_str = datetime.now().strftime("%d %B %Y, %H:%M WIB")
    counts = comparison_result.get("status_counts", {})
    results = comparison_result.get("results", [])
    blocks = comparison_result.get("block_breakdown", [])
    has_offset = comparison_result.get("has_offsetting_differences", False)

    # Buat baris tabel HTML
    table_rows_html = []
    for r in results:
        status = r.get("status", "")
        badge_class = "badge-success" if status == "Cocok" else ("badge-danger" if status == "Berbeda" else "badge-warning")
        
        m_val = r.get("data_mandor")
        k_val = r.get("data_kcs")
        diff = r.get("selisih")
        
        m_str = f"{m_val:g}" if m_val is not None else "<span class='text-muted'>-</span>"
        k_str = f"{k_val:g}" if k_val is not None else "<span class='text-muted'>-</span>"
        d_str = f"<strong>{diff:+g}</strong>" if diff is not None else "<span class='text-muted'>-</span>"

        table_rows_html.append(f"""
        <tr>
            <td class="text-center">{r.get('no')}</td>
            <td>{r.get('tanggal', '-')}</td>
            <td><strong>{r.get('blok', '-')}</strong></td>
            <td><code>{r.get('kode_pekerja', '-')}</code></td>
            <td class="text-end">{m_str}</td>
            <td class="text-end">{k_str}</td>
            <td class="text-end">{d_str}</td>
            <td><span class="badge {badge_class}">{status}</span></td>
            <td><small>{r.get('keterangan', '-')}</small></td>
        </tr>
        """)

    block_rows_html = []
    for idx, b in enumerate(blocks, 1):
        b_status = b.get("status", "")
        b_badge = "badge-success" if b_status == "Cocok" else "badge-warning"
        block_rows_html.append(f"""
        <tr>
            <td class="text-center">{idx}</td>
            <td><strong>{b.get('blok', '-')}</strong></td>
            <td class="text-end">{b.get('mandor_total', 0):g}</td>
            <td class="text-end">{b.get('kcs_total', 0):g}</td>
            <td class="text-end"><strong>{b.get('selisih', 0):+g}</strong></td>
            <td><span class="badge {b_badge}">{b_status}</span></td>
            <td class="text-center">{b.get('discrepancies', 0)}</td>
        </tr>
        """)

    offset_alert_html = ""
    if has_offset:
        offset_alert_html = """
        <div class="alert-box alert-danger">
            <strong>PERINGATAN SELISIH SALING MENIADAKAN:</strong>
            Total janjang Mandor dan KCS sama persis, tetapi terdapat selisih antar-blok yang saling meniadakan! Harap verifikasi rincian per blok dan baris.
        </div>
        """

    # Atribut tambahan HTML
    add_attrs_html = []
    for a in comparison_result.get("additional_attributes", []):
        m_val = f"{a['mandor_value']:g}" if a.get("mandor_value") is not None else "<span class='text-muted'>-</span>"
        k_val = f"{a['kcs_value']:g}" if a.get("kcs_value") is not None else "<span class='text-muted'>-</span>"
        diff_val = f"<strong>{a['selisih']:+g}</strong>" if a.get("selisih") is not None else "<span class='text-muted'>-</span>"
        badge_cls = "badge-success" if a.get("status") == "Cocok" else ("badge-warning" if "Tidak" in a.get("status", "") else "badge-danger")
        add_attrs_html.append(f"""
        <tr>
            <td><strong>{a.get('attribute', '-')}</strong></td>
            <td class="text-end">{m_val}</td>
            <td class="text-end">{k_val}</td>
            <td class="text-end">{diff_val}</td>
            <td><span class="badge {badge_cls}">{a.get('status', '-')}</span></td>
            <td><small>{a.get('keterangan', '-')}</small></td>
        </tr>
        """)

    add_attrs_section = ""
    if add_attrs_html:
        add_attrs_section = f"""
        <h2>Rekonsiliasi Atribut Tambahan (Berondolan & Luasan)</h2>
        <table>
            <thead>
                <tr>
                    <th>Atribut</th>
                    <th class="text-end">Mandor</th>
                    <th class="text-end">KCS</th>
                    <th class="text-end">Selisih</th>
                    <th>Status</th>
                    <th>Keterangan</th>
                </tr>
            </thead>
            <tbody>
                {"".join(add_attrs_html)}
            </tbody>
        </table>
        """

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Laporan Hasil Pemeriksaan - SIPEKA DF</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 20px 30px;
            color: #212529;
            background: #fff;
            font-size: 13px;
            line-height: 1.4;
        }}
        .header {{
            border-bottom: 2px solid #1e4d2b;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #1e4d2b;
            margin: 0 0 5px 0;
            font-size: 22px;
            letter-spacing: -0.5px;
        }}
        .header .subtitle {{
            color: #555;
            font-size: 13px;
            margin: 0;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 20px;
        }}
        .meta-item {{
            display: flex;
            justify-content: space-between;
            padding: 2px 0;
        }}
        .meta-label {{
            font-weight: 600;
            color: #495057;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
            background: #fafafa;
        }}
        .stat-card .val {{
            font-size: 20px;
            font-weight: 700;
            color: #1e4d2b;
        }}
        .stat-card .lbl {{
            font-size: 11px;
            color: #6c757d;
            text-transform: uppercase;
        }}
        .alert-box {{
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 12px;
        }}
        .alert-danger {{
            background: #f8d7da;
            border: 1px solid #f5c2c7;
            color: #842029;
        }}
        h2 {{
            color: #1e4d2b;
            font-size: 15px;
            margin: 25px 0 10px 0;
            border-left: 4px solid #1e4d2b;
            padding-left: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 12px;
        }}
        th, td {{
            border: 1px solid #dee2e6;
            padding: 6px 8px;
        }}
        th {{
            background: #1e4d2b;
            color: white;
            font-weight: 600;
            text-align: left;
        }}
        .text-center {{ text-align: center; }}
        .text-end {{ text-align: right; }}
        .badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
        }}
        .badge-success {{ background: #d1e7dd; color: #0f5132; }}
        .badge-danger {{ background: #f8d7da; color: #842029; }}
        .badge-warning {{ background: #fff3cd; color: #664d03; }}
        .disclaimer-box {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 12px;
            border-radius: 6px;
            margin-top: 30px;
            font-size: 11px;
            color: #6c757d;
        }}
        .btn-print {{
            background: #1e4d2b;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            margin-bottom: 15px;
        }}
        @media print {{
            .btn-print {{ display: none; }}
            body {{ margin: 0; font-size: 11px; }}
            th {{ background: #222 !important; color: #fff !important; -webkit-print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
    <button class="btn-print" onclick="window.print()">Cetak / Simpan sebagai PDF</button>

    <div class="header">
        <h1>SIPEKA DF — Sistem Pemeriksa Kesalahan Data Digital Farming</h1>
        <div class="subtitle">Laporan Resmi Pemeriksaan Rekonsiliasi Data Panen (Mandor) & Angkut (KCS)</div>
    </div>

    <div class="meta-grid">
        <div class="meta-item"><span class="meta-label">Waktu Pemeriksaan:</span> <span>{now_str}</span></div>
        <div class="meta-item"><span class="meta-label">Kebun / Estate:</span> <span>{mandor_meta.get('kebun') or kcs_meta.get('kebun') or '-'}</span></div>
        <div class="meta-item"><span class="meta-label">Afdeling:</span> <span>{mandor_meta.get('afdeling') or kcs_meta.get('afdeling') or '-'}</span></div>
        <div class="meta-item"><span class="meta-label">Tanggal Panen/Aktivitas:</span> <span>{mandor_meta.get('tanggal_aktivitas') or kcs_meta.get('tanggal_aktivitas') or '-'}</span></div>
        <div class="meta-item"><span class="meta-label">File Mandor (PB24A):</span> <span>{mandor_file}</span></div>
        <div class="meta-item"><span class="meta-label">File KCS (PB24B):</span> <span>{kcs_file}</span></div>
    </div>

    {offset_alert_html}

    <div class="stats-grid">
        <div class="stat-card">
            <div class="val">{comparison_result.get('total_rows_compared', 0)}</div>
            <div class="lbl">Baris Dibandingkan</div>
        </div>
        <div class="stat-card">
            <div class="val" style="color:#0f5132">{counts.get('Cocok', 0)}</div>
            <div class="lbl">Data Cocok</div>
        </div>
        <div class="stat-card">
            <div class="val" style="color:#842029">{counts.get('Perlu Verifikasi', 0)}</div>
            <div class="lbl">Perlu Verifikasi</div>
        </div>
        <div class="stat-card">
            <div class="val">{comparison_result.get('total_selisih', 0):+g}</div>
            <div class="lbl">Total Selisih (JJG)</div>
        </div>
    </div>

    <h2>Rekapitulasi Total Berdasarkan Blok</h2>
    <table>
        <thead>
            <tr>
                <th style="width:40px" class="text-center">No</th>
                <th>Blok</th>
                <th class="text-end">Total Mandor (JJG)</th>
                <th class="text-end">Total KCS (JJG)</th>
                <th class="text-end">Selisih (KCS - Mandor)</th>
                <th>Status</th>
                <th class="text-center">Jml Selisih Baris</th>
            </tr>
        </thead>
        <tbody>
            {"".join(block_rows_html)}
        </tbody>
    </table>

    {add_attrs_section}

    <h2>Rincian Perbedaan dan Verifikasi Baris</h2>
    <table>
        <thead>
            <tr>
                <th style="width:30px" class="text-center">No</th>
                <th>Tanggal</th>
                <th>Blok</th>
                <th>Kode Pekerja</th>
                <th class="text-end">Mandor</th>
                <th class="text-end">KCS</th>
                <th class="text-end">Selisih</th>
                <th>Status</th>
                <th>Keterangan / Rekomendasi Verifikasi</th>
            </tr>
        </thead>
        <tbody>
            {"".join(table_rows_html)}
        </tbody>
    </table>

    <div class="disclaimer-box">
        <strong>Pernyataan Verifikasi:</strong><br>
        {comparison_result.get('disclaimer', '')}
    </div>
</body>
</html>
"""
    return html
