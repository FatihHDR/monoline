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
    page.goto(pdf_url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)
    content = page.content()
    with open('download_page.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Saved download_page.html. Title:", page.title())
    context.close()
