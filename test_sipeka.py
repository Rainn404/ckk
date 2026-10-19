"""
SIPEKA DF - Automated Test Suite
Menguji seluruh 14 skenario wajib sesuai spesifikasi teknis:
1. Kedua laporan memiliki data identik.
2. Satu nilai berbeda pada satu kode pekerja.
3. Satu blok tidak ditemukan di laporan kedua.
4. Satu kode pekerja hanya muncul pada laporan pertama.
5. Nilai kosong pada salah satu laporan.
6. Baris duplikat.
7. Total keseluruhan sama tetapi distribusi per blok berbeda (Offsetting).
8. Tanggal kedua laporan berbeda.
9. Afdeling kedua laporan berbeda.
10. PDF rusak atau tidak dapat dibaca.
11. PDF berupa hasil scan tanpa teks (gambar murni).
12. Angka menggunakan tanda desimal atau pemisah ribuan yang berbeda.
13. Nama file mengandung spasi atau karakter khusus.
14. Pengguna menekan tombol Bandingkan Data tanpa mengunggah kedua file.
"""

import os
import sys
import unittest
import pdf_reader
import data_extractor
import validator
import comparator
import exporter

TEST_DIR = os.path.join(os.path.dirname(__file__), "test_data")


class TestSipekaDF(unittest.TestCase):

    def test_01_identical_reports(self):
        """Skenario 1: Kedua laporan memiliki data identik."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_mandor_identical.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_kcs_identical.pdf"))
        self.assertTrue(m_pdf["success"])
        self.assertTrue(k_pdf["success"])

        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)
        self.assertEqual(len(m_data["rows"]), 4)
        self.assertEqual(len(k_data["rows"]), 4)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"], m_data["metadata"], k_data["metadata"])
        self.assertEqual(comp["status_counts"]["Cocok"], 4)
        self.assertEqual(comp["status_counts"]["Berbeda"], 0)
        self.assertEqual(comp["total_selisih"], 0)
        self.assertFalse(comp["has_offsetting_differences"])

    def test_02_single_diff_value(self):
        """Skenario 2: Satu nilai berbeda pada satu kode pekerja (AA19: 72 vs 69)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_mandor_identical.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc2_kcs_diff_value.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        self.assertEqual(comp["status_counts"]["Berbeda"], 1)
        self.assertEqual(comp["status_counts"]["Cocok"], 3)

        # Cari baris AA19
        row_aa19 = next(r for r in comp["results"] if r["kode_pekerja"] == "AA19")
        self.assertEqual(row_aa19["status"], "Berbeda")
        self.assertEqual(row_aa19["data_mandor"], 72.0)
        self.assertEqual(row_aa19["data_kcs"], 69.0)
        self.assertEqual(row_aa19["selisih"], -3.0)  # Selisih = KCS - Mandor

    def test_03_missing_block_in_second_report(self):
        """Skenario 3: Satu blok tidak ditemukan di laporan kedua (Blok 137 hilang di KCS)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_mandor_identical.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc3_kcs_missing_block.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        self.assertEqual(comp["status_counts"]["Hanya Ada di Mandor"], 2)
        # Blok 137 memiliki 2 pekerja BB01 & BB02
        blk_137_rows = [r for r in comp["results"] if r["blok"] == "137"]
        self.assertTrue(all(r["status"] == "Hanya Ada di Mandor" for r in blk_137_rows))

    def test_04_extra_worker_in_first_report(self):
        """Skenario 4: Satu kode pekerja hanya muncul pada laporan pertama (CC05)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc4_mandor_extra_worker.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_kcs_identical.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        row_cc05 = next(r for r in comp["results"] if r["kode_pekerja"] == "CC05")
        self.assertEqual(row_cc05["status"], "Hanya Ada di Mandor")

    def test_05_empty_value_in_report(self):
        """Skenario 5: Nilai kosong pada salah satu laporan (AA20 di KCS bernilai '-')."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_mandor_identical.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc5_kcs_empty_val.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        row_aa20 = next(r for r in comp["results"] if r["kode_pekerja"] == "AA20")
        self.assertEqual(row_aa20["status"], "Data Tidak Lengkap")
        self.assertIsNone(row_aa20["data_kcs"])

    def test_06_duplicate_rows(self):
        """Skenario 6: Baris duplikat (AA19 tercatat 2 kali di Mandor)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc6_mandor_duplicate.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_kcs_identical.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        row_dup = next(r for r in comp["results"] if r["kode_pekerja"] == "AA19")
        self.assertEqual(row_dup["status"], "Duplikat")

    def test_07_offsetting_differences(self):
        """Skenario 7: Total keseluruhan sama tetapi distribusi per blok berbeda (Offsetting)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc7_mandor_offset.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc7_kcs_offset.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        # Total harus sama persis (Selisih == 0)
        self.assertEqual(comp["total_selisih"], 0)
        self.assertEqual(comp["total_mandor"], comp["total_kcs"])
        # Tetapi sistem harus mendeteksi offsetting differences!
        self.assertTrue(comp["has_offsetting_differences"])
        self.assertEqual(comp["status_counts"]["Berbeda"], 2)

    def test_08_different_report_dates(self):
        """Skenario 8: Tanggal kedua laporan berbeda."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_mandor_identical.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc8_kcs_diff_date.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        val = validator.validate_reports_identity(m_data["metadata"], k_data["metadata"])
        self.assertTrue(val["has_warnings"])
        date_warning = next(w for w in val["warnings"] if "Tanggal" in w["field"])
        self.assertIsNotNone(date_warning)

    def test_09_different_afdelings(self):
        """Skenario 9: Afdeling kedua laporan berbeda (Afdeling 1 vs Afdeling 2)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc1_mandor_identical.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc9_kcs_diff_afd.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        val = validator.validate_reports_identity(m_data["metadata"], k_data["metadata"])
        self.assertTrue(val["has_warnings"])
        afd_warning = next(w for w in val["warnings"] if "Afdeling" in w["field"])
        self.assertEqual(afd_warning["severity"], "danger")

    def test_10_corrupt_pdf(self):
        """Skenario 10: PDF rusak atau tidak dapat dibaca."""
        res = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc10_corrupt.pdf"))
        self.assertFalse(res["success"])
        self.assertIsNotNone(res["error_message"])
        self.assertIn("rusak", res["error_message"].lower())

    def test_11_scanned_image_pdf(self):
        """Skenario 11: PDF berupa hasil scan tanpa teks (gambar murni)."""
        res = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc11_scanned_image.pdf"))
        self.assertFalse(res["success"])
        self.assertTrue(res["is_scanned"])
        self.assertIn("ocr", res["error_message"].lower())

    def test_12_number_formatting_differences(self):
        """Skenario 12: Format angka berbeda (titik vs koma, ribuan vs desimal)."""
        m_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc12_mandor_numformat.pdf"))
        k_pdf = pdf_reader.read_pdf(os.path.join(TEST_DIR, "tc12_kcs_numformat.pdf"))
        
        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)

        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        # Format "1.250" dan "1,250" harus terdeteksi cocok (1250.0 == 1250.0)
        # Format "72,5" dan "72.5" harus terdeteksi cocok (72.5 == 72.5)
        self.assertEqual(comp["status_counts"]["Cocok"], 2)
        self.assertEqual(comp["status_counts"]["Berbeda"], 0)

    def test_13_filenames_with_spaces_and_special_chars(self):
        """Skenario 13: Nama file mengandung spasi dan karakter khusus (&, #, [], @)."""
        special_m = os.path.join(TEST_DIR, "tc13 Laporan Mandor & KCS (Afdeling #1) [2026].pdf")
        special_k = os.path.join(TEST_DIR, "tc13 Laporan Pengangkutan & Krani + Cek Sawit @2026.pdf")
        
        m_pdf = pdf_reader.read_pdf(special_m)
        k_pdf = pdf_reader.read_pdf(special_k)
        self.assertTrue(m_pdf["success"])
        self.assertTrue(k_pdf["success"])

        m_data = data_extractor.extract_pdf_data(m_pdf)
        k_data = data_extractor.extract_pdf_data(k_pdf)
        comp = comparator.compare_datasets(m_data["rows"], k_data["rows"])
        self.assertEqual(comp["status_counts"]["Cocok"], 4)

    def test_14_missing_files_validation(self):
        """Skenario 14: Validasi penanganan jika file tidak diunggah atau kosong."""
        from app import parse_multipart
        # Simulasi multipart tanpa salah satu file
        body = b'--boundary123\r\nContent-Disposition: form-data; name="mandor_file"; filename=""\r\n\r\n--boundary123--'
        fields = parse_multipart(body, "boundary123")
        mandor_field = fields.get("mandor_file")
        self.assertTrue(not mandor_field or not mandor_field.get("filename") or len(mandor_field.get("data", b"")) == 0)

    def test_15_real_reports_pb24a_pb24b(self):
        """
        Pengujian Laporan Nyata PB24A & PB24B:
        - Memastikan 2004 dikenali sebagai tahun, bukan nomor blok.
        - Memastikan tidak ada penggabungan baris palsu menjadi Duplikat.
        - Memastikan 4 perbedaan pekerja terdeteksi dengan tepat.
        - Memastikan Luasan tidak dihitung sebagai selisih buah (-54).
        - Memastikan Berondolan cocok (409 vs 409).
        - Memastikan Selisih Saling Meniadakan (Offsetting) terdeteksi.
        """
        path_a = os.path.join(TEST_DIR, "PB24A _ Report.pdf")
        path_b = os.path.join(TEST_DIR, "PB24B _ Report.pdf")

        if not os.path.exists(path_a) or not os.path.exists(path_b):
            self.skipTest("Berkas PB24A atau PB24B tidak ditemukan di test_data.")

        m_pdf = pdf_reader.read_pdf(path_a)
        k_pdf = pdf_reader.read_pdf(path_b)
        self.assertTrue(m_pdf["success"])
        self.assertTrue(k_pdf["success"])

        m_ext = data_extractor.extract_pdf_data(m_pdf)
        k_ext = data_extractor.extract_pdf_data(k_pdf)

        # 1. Pastikan terdeteksi sebagai format matriks
        self.assertIn("Matriks", m_ext["summary"]["detected_format"])
        self.assertIn("Matriks", k_ext["summary"]["detected_format"])

        # 2. Pastikan '2004' BUKAN identitas blok
        self.assertNotIn("2004", m_ext["summary"]["unique_blocks"])
        self.assertNotIn("2004", k_ext["summary"]["unique_blocks"])
        self.assertIn("135", m_ext["summary"]["unique_blocks"])
        self.assertIn("136", m_ext["summary"]["unique_blocks"])
        self.assertIn("138", m_ext["summary"]["unique_blocks"])
        self.assertIn("139A", m_ext["summary"]["unique_blocks"])
        self.assertIn("139B", m_ext["summary"]["unique_blocks"])

        # 3. Jalankan pembandingan
        comp = comparator.compare_datasets(
            m_ext["production_records"],
            k_ext["production_records"],
            m_ext["metadata"],
            k_ext["metadata"],
            mandor_berondolan=m_ext["berondolan_data"],
            kcs_berondolan=k_ext["berondolan_data"],
            mandor_berondolan_pipil=m_ext["berondolan_pipil_data"],
            kcs_berondolan_pipil=k_ext["berondolan_pipil_data"],
            mandor_luasan=m_ext["luasan_data"],
            kcs_luasan=k_ext["luasan_data"]
        )

        # 4. Pastikan TIDAK ADA status Duplikat palsu
        self.assertEqual(comp["status_counts"]["Duplikat"], 0)

        # 5. Pastikan terdeteksi 4 perbedaan pekerja
        self.assertEqual(comp["status_counts"]["Berbeda"], 4)

        diff_map = {(r["blok"], r["kode_pekerja"]): r for r in comp["results"] if r["status"] == "Berbeda"}

        # Perbedaan 1: Blok 136 (AA17): Mandor 72, KCS 69 -> Selisih -3
        self.assertIn(("136", "AA17"), diff_map)
        r_136 = diff_map[("136", "AA17")]
        self.assertEqual(r_136["data_mandor"], 72.0)
        self.assertEqual(r_136["data_kcs"], 69.0)
        self.assertEqual(r_136["selisih"], -3.0)

        # Perbedaan 2: Blok 138 (AA24): Mandor 70, KCS 69 -> Selisih -1
        self.assertIn(("138", "AA24"), diff_map)
        r_138 = diff_map[("138", "AA24")]
        self.assertEqual(r_138["data_mandor"], 70.0)
        self.assertEqual(r_138["data_kcs"], 69.0)
        self.assertEqual(r_138["selisih"], -1.0)

        # Perbedaan 3: Blok 139A (AA10): Mandor 72, KCS 75 -> Selisih +3
        self.assertIn(("139A", "AA10"), diff_map)
        r_139a_10 = diff_map[("139A", "AA10")]
        self.assertEqual(r_139a_10["data_mandor"], 72.0)
        self.assertEqual(r_139a_10["data_kcs"], 75.0)
        self.assertEqual(r_139a_10["selisih"], 3.0)

        # Perbedaan 4: Blok 139A (AA13): Mandor 120, KCS 121 -> Selisih +1
        self.assertIn(("139A", "AA13"), diff_map)
        r_139a_13 = diff_map[("139A", "AA13")]
        self.assertEqual(r_139a_13["data_mandor"], 120.0)
        self.assertEqual(r_139a_13["data_kcs"], 121.0)
        self.assertEqual(r_139a_13["selisih"], 1.0)

        # 6. Pastikan Total Janjang Mandor = 1417, Total Janjang KCS = 1417, Selisih Total = 0
        self.assertEqual(comp["total_mandor"], 1417.0)
        self.assertEqual(comp["total_kcs"], 1417.0)
        self.assertEqual(comp["total_selisih"], 0.0)

        # 7. Pastikan Offsetting Differences terdeteksi (Total sama tapi distribusi beda)
        self.assertTrue(comp["has_offsetting_differences"])

        # 8. Pastikan Luasan TIDAK dihitung sebagai produksi buah (-54)
        fruit_diffs = [r["selisih"] for r in comp["results"] if r.get("selisih") is not None]
        self.assertNotIn(-54.0, fruit_diffs)

        # Cek rekonsiliasi atribut tambahan
        luas_attr = next(a for a in comp["additional_attributes"] if "Luasan" in a["attribute"])
        self.assertEqual(luas_attr["mandor_value"], 54.0)
        self.assertIn("Tidak Tersedia", luas_attr["status"])

        # Berondolan cocok (409 vs 409)
        brd_attr = next(a for a in comp["additional_attributes"] if "Berondolan (Kg/Sak)" in a["attribute"])
        self.assertEqual(brd_attr["mandor_value"], 409.0)
        self.assertEqual(brd_attr["kcs_value"], 409.0)
        self.assertEqual(brd_attr["status"], "Cocok")


if __name__ == "__main__":
    unittest.main()
