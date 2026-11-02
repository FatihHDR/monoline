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

    test_decisions = [
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf1a290d2ef5260b683313033303332.html',
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/11f1d5f4275d3f06c0fc323030303033.html'
    ]

    for d in test_decisions:
        page.goto(d, wait_until='domcontentloaded', timeout=30000)
        time.sleep(2)
        pdf_a = page.locator('a[href*="/pdf/"]')
        print(f"\nDecision: {d}")
        print("PDF links count:", pdf_a.count())
        if pdf_a.count() > 0:
            link = pdf_a.first.get_attribute('href')
            print("Target PDF link:", link)
            try:
                with page.expect_download(timeout=10000) as d_info:
                    pdf_a.first.click()
                d_file = d_info.value
                dest = os.path.join(os.getcwd(), 'Dataset', d_file.suggested_filename)
                d_file.save_as(dest)
                print(f"SUCCESS! Downloaded real PDF: {d_file.suggested_filename} ({os.path.getsize(dest)} bytes)")
            except Exception as e:
                print("Download failed:", type(e).__name__)

    context.close()
