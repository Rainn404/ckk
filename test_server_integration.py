"""
Integration test for SIPEKA DF HTTP Server endpoints.
"""

import os
import time
import json
import urllib.request
import threading
import app

def run_tests():
    server_thread = threading.Thread(target=app.run_server, args=(8095,), daemon=True)
    server_thread.start()
    time.sleep(1)

    print("--- 1. Testing GET / ---")
    with urllib.request.urlopen("http://127.0.0.1:8095/") as res:
        assert res.status == 200
        html = res.read().decode("utf-8")
        assert "SIPEKA DF" in html
        print("[PASSED] GET / returned 200 and SIPEKA DF dashboard")

    print("\n--- 2. Testing Static Files ---")
    with urllib.request.urlopen("http://127.0.0.1:8095/static/css/style.css") as res:
        assert res.status == 200
        print("[PASSED] GET /static/css/style.css returned 200")
    with urllib.request.urlopen("http://127.0.0.1:8095/static/js/app.js") as res:
        assert res.status == 200
        print("[PASSED] GET /static/js/app.js returned 200")

    print("\n--- 3. Testing POST /api/upload-and-compare ---")
    boundary = "----SipekaBoundary12345"
    with open("test_data/tc7_mandor_offset.pdf", "rb") as f:
        m_bytes = f.read()
    with open("test_data/tc7_kcs_offset.pdf", "rb") as f:
        k_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="mandor_file"; filename="tc7_mandor_offset.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("latin1") + m_bytes + (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="kcs_file"; filename="tc7_kcs_offset.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("latin1") + k_bytes + f"\r\n--{boundary}--\r\n".encode("latin1")

    req = urllib.request.Request(
        "http://127.0.0.1:8095/api/upload-and-compare",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        assert data["success"] is True
        assert data["comparison"]["has_offsetting_differences"] is True
        print("[PASSED] POST /api/upload-and-compare returned valid comparison with offsetting differences!")

    print("\n--- 4. Testing GET /api/history ---")
    with urllib.request.urlopen("http://127.0.0.1:8095/api/history") as res:
        assert res.status == 200
        h_data = json.loads(res.read().decode("utf-8"))
        assert len(h_data.get("history", [])) > 0
        print(f"[PASSED] GET /api/history returned {len(h_data['history'])} records.")

    print("\n--- 5. Testing POST /api/export/csv ---")
    csv_payload = json.dumps({
        "comparison_result": data["comparison"],
        "mandor_meta": data["mandor_meta"],
        "kcs_meta": data["kcs_meta"],
        "mandor_file": data["mandor_filename"],
        "kcs_file": data["kcs_filename"]
    }).encode("utf-8")
    
    csv_req = urllib.request.Request(
        "http://127.0.0.1:8095/api/export/csv",
        data=csv_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(csv_req) as res:
        assert res.status == 200
        csv_text = res.read().decode("utf-8-sig")
        assert "SIPEKA DF" in csv_text
        assert "REKAPITULASI TOTAL PER BLOK" in csv_text
        print("[PASSED] POST /api/export/csv successfully returned Excel-ready CSV with UTF-8 BOM!")

    print("\n=== ALL SERVER INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
