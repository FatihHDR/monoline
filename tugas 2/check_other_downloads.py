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

    # Let's check a few putusans across different years
    test_urls = [
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f5d30aed86529080313433383431.html',
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f4e0f9a4b6ba944d303934353534.html',
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaee204dca5e6910bc0b303734383137.html',
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaee3fed18d610ca944d313333363435.html'
    ]

    for u in test_urls:
        print(f"\nChecking: {u}")
        page.goto(u, wait_until='domcontentloaded', timeout=30000)
        time.sleep(1)
        pdf_a = page.locator('a[href*="/pdf/"]')
        print("  PDF link count:", pdf_a.count())
        if pdf_a.count() > 0:
            link = pdf_a.first.get_attribute('href')
            print("  Href:", link)
            # Try context.request.get with full headers
            res = context.request.get(link, headers={'Referer': u})
            print("  Request status:", res.status, "content-type:", res.headers.get('content-type'))
            body = res.body()
            print("  Body len:", len(body), "prefix:", body[:20])

    context.close()
