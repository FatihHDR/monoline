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
    url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236.html'
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    # Click PDF download link with expect_download
    print("[INFO] Waiting for download...")
    with page.expect_download(timeout=60000) as download_info:
        page.locator('a[href*="/pdf/"]').first.click()

    download = download_info.value
    print("[INFO] Suggested filename:", download.suggested_filename)
    dest_path = os.path.join(os.getcwd(), 'Dataset', download.suggested_filename)
    download.save_as(dest_path)
    print(f"[INFO] Downloaded successfully: {dest_path} (size: {os.path.getsize(dest_path)} bytes)")
    context.close()
