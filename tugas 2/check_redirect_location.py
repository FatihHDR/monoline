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

    def handle_response(response):
        if response.status in [301, 302, 303, 307, 308]:
            print(f">> REDIRECT {response.status}: {response.url} -> Location: {response.headers.get('location')}")

    page.on('response', handle_response)

    url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236.html'
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(1)

    pdf_elem = page.locator('a[href*="/pdf/"]')
    if pdf_elem.count() > 0:
        pdf_elem.first.click()
        time.sleep(3)

    context.close()
