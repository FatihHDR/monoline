import os, time, base64
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

user_data = os.path.abspath('playwright_user_data')
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled']
    )
    page = context.pages[0] if context.pages else context.new_page()

    # Check 535 and 429
    test_urls = [
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236.html', # 535
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f4e0f9a4b6ba944d303934353534.html', # 429
    ]

    for u in test_urls:
        print(f"\nNavigating to: {u}")
        page.goto(u, wait_until='domcontentloaded', timeout=30000)
        time.sleep(1)
        soup = BeautifulSoup(page.content(), 'html.parser')
        col3 = soup.find('div', id='collapseThree')
        pdf_a = col3.find('a', href=lambda h: h and '/pdf/' in h) if col3 else None
        if pdf_a:
            pdf_url = pdf_a['href']
            print("PDF URL:", pdf_url)
            # Fetch inside page
            res = page.evaluate('''async (url) => {
                const r = await fetch(url);
                return {
                    status: r.status,
                    type: r.headers.get("content-type"),
                    len: (await r.clone().text()).length,
                    is_pdf: (await r.clone().text()).startsWith("%PDF")
                };
            }''', pdf_url)
            print("Fetch inside page result:", res)

    context.close()
