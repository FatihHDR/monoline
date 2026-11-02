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
    target_url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236'
    print("Navigating to:", target_url)
    res = page.goto(target_url, timeout=30000)
    print("Status:", res.status)
    print("Content-type:", res.headers.get('content-type'))
    body = res.body()
    print("Body len:", len(body), "Magic:", body[:20])
    context.close()
