import os, time, re, base64
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
    page.goto('https://putusan3.mahkamahagung.go.id/direktori.html', wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    found_pdfs = []

    # Check across 2023, 2024, 2025
    for year in [2023, 2024, 2025]:
        print(f"\n=== Scanning Year {year} ===")
        for p_idx in range(1, 12):
            if len(found_pdfs) >= 50:
                break
            if p_idx == 1:
                list_url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}.html"
            else:
                list_url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}/page/{p_idx}.html"

            # Fetch list page in-page
            res = page.evaluate('''async (url) => {
                const r = await fetch(url);
                return { status: r.status, text: await r.text() };
            }''', list_url)

            if res['status'] != 200:
                break

            soup = BeautifulSoup(res['text'], 'html.parser')
            links = []
            for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
                h = a['href']
                if h not in links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                    links.append(h)

            print(f"Year {year} Page {p_idx}: {len(links)} decisions")
            if not links:
                break

            for d_url in links:
                if len(found_pdfs) >= 50:
                    break
                d_res = page.evaluate('''async (url) => {
                    const r = await fetch(url);
                    return { status: r.status, text: await r.text() };
                }''', d_url)

                if '/pdf/' in d_res.get('text', ''):
                    d_soup = BeautifulSoup(d_res['text'], 'html.parser')
                    bht = 'berkekuatan hukum tetap' in d_res['text'].lower()
                    nomor = ""
                    for tr in d_soup.find_all('tr'):
                        tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                        if len(tds) >= 2 and 'nomor' in tds[0].lower():
                            nomor = tds[1]
                            break
                    pdf_link = None
                    col3 = d_soup.find('div', id='collapseThree')
                    if col3 and col3.find('a', href=re.compile(r'/pdf/')):
                        pdf_link = col3.find('a', href=re.compile(r'/pdf/'))['href']
                    
                    if pdf_link and not bht:
                        found_pdfs.append((nomor, pdf_link, d_url))
                        print(f"  [{len(found_pdfs)}/50] FOUND PDF: {nomor} -> {pdf_link}")

    print(f"\nTOTAL FOUND VALID PDFS: {len(found_pdfs)}")
    context.close()
