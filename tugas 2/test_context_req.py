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
    detail_url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f5d30aed86529080313433383431.html'
    res = context.request.get(detail_url)
    print("context.request.get status:", res.status)
    print("body len:", len(res.body()))
    context.close()
