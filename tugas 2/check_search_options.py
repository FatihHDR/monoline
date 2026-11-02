import os, time
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
    page.goto('https://putusan3.mahkamahagung.go.id/search.html', timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(2)
    soup = BeautifulSoup(page.content(), 'html.parser')
    
    for sel in soup.find_all('select'):
        name = sel.get('name')
        print(f"\nSelect: {name}")
        opts = [(o.get('value'), o.get_text(strip=True)) for o in sel.find_all('option')]
        print(f"  Options ({len(opts)}):", opts[:10])

    context.close()
