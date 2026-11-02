import os, time, re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

user_data = os.path.abspath('playwright_user_data')
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled'],
        accept_downloads=True
    )
    page = context.pages[0] if context.pages else context.new_page()

    # Test pages 2, 3, 4 of 2023
    for p_num in [2, 3, 4]:
        url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/2023/page/{p_num}.html"
        print(f"\n--- Checking Page {p_num} of 2023 ---")
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(1)
        soup = BeautifulSoup(page.content(), 'html.parser')
        d_links = []
        for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
            h = a['href']
            if h not in d_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                d_links.append(h)
        print(f"Page {p_num} has {len(d_links)} decisions.")
        
        # Check first 5 on this page
        for dl in d_links[:5]:
            page.goto(dl, wait_until='domcontentloaded', timeout=30000)
            d_soup = BeautifulSoup(page.content(), 'html.parser')
            col3 = d_soup.find('div', id='collapseThree')
            has_pdf = False
            if col3 and col3.find('a', href=re.compile(r'/pdf/')):
                has_pdf = True
            nomor = ""
            for tr in d_soup.find_all('tr'):
                tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if len(tds) >= 2 and 'nomor' in tds[0].lower():
                    nomor = tds[1]
                    break
            print(f"  [{nomor}] Has PDF link: {has_pdf}")

    context.close()
