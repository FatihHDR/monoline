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

    print("[INFO] Navigating to search.html...")
    page.goto('https://putusan3.mahkamahagung.go.id/search.html', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(2)

    cb = page.locator('#altcha-checkbox-captcha-widget-inline')
    if cb.count() > 0:
        print("[INFO] Captcha checkbox found! State:", cb.is_checked())
        if not cb.is_checked():
            cb.click()
            for _ in range(15):
                time.sleep(1)
                if cb.is_checked():
                    print("[INFO] Captcha solved!")
                    break

    # Fill keyword
    page.fill('input[name="q"]', 'narkotika')
    # Click search button
    page.click('button[type="submit"]')
    page.wait_for_load_state('domcontentloaded')
    time.sleep(3)
    print("[INFO] Search submitted! URL:", page.url)

    # Now navigate to a decision that has a PDF download link
    test_putusan = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236.html'
    print("[INFO] Navigating to test putusan:", test_putusan)
    page.goto(test_putusan, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    pdf_elem = page.locator('a[href*="/pdf/"]')
    print("[INFO] PDF link count:", pdf_elem.count())
    if pdf_elem.count() > 0:
        pdf_url = pdf_elem.first.get_attribute('href')
        print("[INFO] PDF URL:", pdf_url)
        # Monitor redirect / response
        def log_resp(r):
            if 'pdf' in r.url or 'download_file' in r.url:
                print(f">> Resp {r.status}: {r.url} | Location: {r.headers.get('location')} | Content-Type: {r.headers.get('content-type')}")
        page.on('response', log_resp)
        pdf_elem.first.click()
        time.sleep(5)

    context.close()
