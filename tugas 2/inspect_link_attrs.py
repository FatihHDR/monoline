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
    url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f74c3111e86c867e313133383236.html'
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)
    
    # Evaluate attributes of the a tag
    info = page.eval_on_selector('a[href*="/pdf/"]', '''el => ({
        outerHTML: el.outerHTML,
        onclick: el.getAttribute("onclick"),
        href: el.href,
        target: el.target
    })''')
    print("PDF link info:", info)
    context.close()
