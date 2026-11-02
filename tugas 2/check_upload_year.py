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

    for year in ['2023', '2024', '2025']:
        url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/upload/tahun/{year}.html"
        print(f"\n--- Checking UPLOAD year {year}: {url} ---")
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(1)
        soup = BeautifulSoup(page.content(), 'html.parser')
        d_links = []
        for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
            h = a['href']
            if h not in d_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                d_links.append(h)
        print(f"Upload year {year} page 1 has {len(d_links)} decisions.")
        
        for dl in d_links[:5]:
            page.goto(dl, wait_until='domcontentloaded', timeout=30000)
            d_soup = BeautifulSoup(page.content(), 'html.parser')
            col3 = d_soup.find('div', id='collapseThree')
            has_pdf = False
            pdf_href = None
            if col3 and col3.find('a', href=re.compile(r'/pdf/')):
                has_pdf = True
                pdf_href = col3.find('a', href=re.compile(r'/pdf/'))['href']
            nomor = ""
            for tr in d_soup.find_all('tr'):
                tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if len(tds) >= 2 and 'nomor' in tds[0].lower():
                    nomor = tds[1]
                    break
            print(f"  [{nomor}] Has PDF: {has_pdf} | Href: {pdf_href}")

    context.close()
