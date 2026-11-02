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

    # Check 2023 first (older decisions are more likely to have final PDFs attached)
    for year in ['2023', '2024', '2025']:
        list_url = f'https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}.html'
        print(f"\n=== Checking year {year} at {list_url} ===")
        page.goto(list_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(2)
        soup = BeautifulSoup(page.content(), 'html.parser')

        # Collect decision links
        links = []
        for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
            href = a['href']
            if href not in links and not any(k in href for k in ['kategori', 'pengadilan', 'tahun']):
                links.append(href)

        print(f"Found {len(links)} decisions on page 1 of {year}")
        for d_url in links[:8]:
            page.goto(d_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(1)
            d_soup = BeautifulSoup(page.content(), 'html.parser')
            col3 = d_soup.find('div', id='collapseThree')
            pdf_link = None
            if col3:
                for a in col3.find_all('a', href=True):
                    pdf_link = a['href']
                    break
            
            # Check status Berkekuatan Hukum Tetap
            has_bht = 'berkekuatan hukum tetap' in d_soup.get_text().lower()
            nomor = ""
            for tr in d_soup.find_all('tr'):
                tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if len(tds) >= 2 and 'nomor' in tds[0].lower():
                    nomor = tds[1]
                    break

            print(f"[{nomor}] PDF: {pdf_link} | BHT: {has_bht}")

    context.close()
