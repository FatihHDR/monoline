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
    page.goto('https://putusan3.mahkamahagung.go.id/direktori.html', wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    detail_url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f5d30aed86529080313433383431.html'
    print("Testing in-page fetch of:", detail_url)
    res_text = page.evaluate('''async (url) => {
        const resp = await fetch(url);
        return {
            status: resp.status,
            text: await resp.text()
        };
    }''', detail_url)

    print("In-page fetch status:", res_text['status'])
    print("Text length:", len(res_text['text']))
    print("Has /pdf/:", '/pdf/' in res_text['text'])
    print("Has icon-files:", 'icon-files' in res_text['text'])
    context.close()
