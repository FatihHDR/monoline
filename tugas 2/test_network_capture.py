import os, time
from playwright.sync_api import sync_playwright

user_data = os.path.abspath('playwright_user_data')
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled'],
        accept_downloads=True
    )
    page = context.pages[0] if context.pages else context.new_page()

    pdf_responses = []

    def handle_response(response):
        ct = response.headers.get('content-type', '')
        if 'pdf' in ct or 'octet-stream' in ct or 'download_file' in response.url:
            print(f"<< CAPTURED: {response.status} | {ct} | {response.url}")
            try:
                b = response.body()
                print(f"   Body size: {len(b)} bytes | starts with: {b[:15]}")
                if b[:4] == b'%PDF':
                    pdf_responses.append(b)
            except Exception as e:
                print("   Error getting body:", e)

    page.on('response', handle_response)

    url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236.html'
    print("[INFO] Navigating to detail page...")
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    # Click the PDF download link
    pdf_elem = page.locator('a[href*="/pdf/"]')
    print("[INFO] PDF elem count:", pdf_elem.count())
    if pdf_elem.count() > 0:
        target_url = pdf_elem.first.get_attribute('href')
        print("[INFO] Target URL:", target_url)
        print("[INFO] Clicking link...")
        pdf_elem.first.click()
        time.sleep(5)

    if pdf_responses:
        out_file = os.path.join(os.getcwd(), 'Dataset', '535_Pid.Sus_2023_PN_JKT.SEL.pdf')
        with open(out_file, 'wb') as f:
            f.write(pdf_responses[0])
        print(f"[SUCCESS] Wrote {len(pdf_responses[0])} bytes to {out_file}!")
    else:
        print("[INFO] No binary PDF captured in response.")

    context.close()
