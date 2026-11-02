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
    page.goto('https://putusan3.mahkamahagung.go.id/direktori.html', wait_until='domcontentloaded', timeout=30000)
    time.sleep(1)

    queries = [
        'https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1.html',
        'https://putusan3.mahkamahagung.go.id/search.html?q=%22PN+JKT.SEL%22+narkotika',
        'https://putusan3.mahkamahagung.go.id/search.html?q=%22Pengadilan+Negeri+Jakarta+Selatan%22+narkotika'
    ]

    for q in queries:
        print(f"\nTesting Query: {q}")
        res = page.evaluate('''async (url) => {
            const r = await fetch(url);
            return { status: r.status, text: await r.text() };
        }''', q)

        soup = BeautifulSoup(res['text'], 'html.parser')
        d_links = []
        for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
            h = a['href']
            if h not in d_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                d_links.append(h)
        print(f"Total decision links: {len(d_links)}")

        # Check how many have /pdf/
        pdf_count = 0
        for dl in d_links[:10]:
            d_res = page.evaluate('''async (url) => {
                const r = await fetch(url);
                return { status: r.status, text: await r.text() };
            }''', dl)
            if '/pdf/' in d_res.get('text', ''):
                pdf_count += 1
        print(f"PDFs found in first 10: {pdf_count}/10")

    context.close()
