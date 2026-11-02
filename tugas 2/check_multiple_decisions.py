import os, time, re
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

    # Let's inspect listing for 2024
    list_url = 'https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/2024.html'
    print('Loading list:', list_url)
    page.goto(list_url, timeout=60000)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(2)
    soup = BeautifulSoup(page.content(), 'html.parser')

    # Collect decision links
    links = []
    for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
        href = a['href']
        if href not in links and not any(k in href for k in ['kategori', 'pengadilan', 'tahun']):
            links.append(href)

    print(f"Found {len(links)} decision links on page 1 of 2024:")
    for l in links[:5]:
        print(" ", l)

    # Now visit the first 5 decisions and check their download buttons or links
    for idx, d_url in enumerate(links[:5], start=1):
        print(f"\n[{idx}] Visiting {d_url}...")
        page.goto(d_url, timeout=60000)
        page.wait_for_load_state('domcontentloaded')
        time.sleep(1)
        d_soup = BeautifulSoup(page.content(), 'html.parser')

        # Check for any <a> with .pdf or download or unduh
        found_pdf = False
        for a in d_soup.find_all('a', href=True):
            href = a['href']
            txt = a.get_text(strip=True)
            if '.pdf' in href.lower() or 'pdf' in href.lower() or 'download' in href.lower() or 'unduh' in txt.lower():
                print(f"  -> Found link: [{txt}] href={href}")
                found_pdf = True
        if not found_pdf:
            print("  -> No direct pdf link found on this detail page.")

    context.close()
