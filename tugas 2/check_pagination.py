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

    # Base URL for 2023
    base_url = 'https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/2023.html'
    page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)
    soup = BeautifulSoup(page.content(), 'html.parser')
    
    # Find all pagination links
    for a in soup.find_all('a', href=True):
        if 'page' in a['href'].lower() or any(a.get_text(strip=True) == str(n) for n in range(1, 10)):
            print(f"Pagination: '{a.get_text(strip=True)}' -> {a['href']}")

    context.close()
