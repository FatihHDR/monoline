import os, time
from playwright.sync_api import sync_playwright

user_data = os.path.abspath('playwright_user_data')
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled']
    )
    page = context.pages[0] if context.pages else context.new_page()
    pdf_url = 'https://putusan3.mahkamahagung.go.id/direktori/download_file/0b662ab4a441a08ff87ea44ec8ceed8e/pdf/zaf0f74c3111e86c867e313133383236'
    print("[INFO] Navigating directly to PDF URL:", pdf_url)
    resp = page.goto(pdf_url, timeout=30000)
    print("[INFO] Response status:", resp.status if resp else "None")
    print("[INFO] Response headers content-type:", resp.headers.get('content-type') if resp else "None")
    body = resp.body() if resp else b""
    print(f"[INFO] Received {len(body)} bytes. Magic prefix: {body[:10]}")
    if body[:4] == b'%PDF':
        out_file = os.path.join(os.getcwd(), 'Dataset', '535_Pid.Sus_2023_PN_JKT.SEL.pdf')
        with open(out_file, 'wb') as f:
            f.write(body)
        print(f"[SUCCESS] Saved valid PDF to {out_file} (size: {len(body)})")
    context.close()
