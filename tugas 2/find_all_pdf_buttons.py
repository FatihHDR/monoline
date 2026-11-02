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
    page.goto('https://putusan3.mahkamahagung.go.id/direktori.html', wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    # Let's inspect pages from PN Jakarta Selatan Narkotika
    # We want to see how many decisions per page have the Download PDF link!
    for p_num in range(1, 10):
        if p_num == 1:
            url = "https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1.html"
        else:
            url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/page/{p_num}.html"

        res = page.evaluate('''async (u) => {
            try {
                const r = await fetch(u);
                return { status: r.status, text: await r.text() };
            } catch(e) { return { status: 0, text: "" }; }
        }''', url)

        soup = BeautifulSoup(res.get('text', ''), 'html.parser')
        d_links = []
        for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
            h = a['href']
            if h not in d_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                d_links.append(h)

        print(f"Page {p_num}: {len(d_links)} decisions found.")
        # Check each decision for the Download PDF link in HTML
        pdf_links = []
        for dl in d_links:
            d_res = page.evaluate('''async (u) => {
                try {
                    const r = await fetch(u);
                    const txt = await r.text();
                    const has_pdf = txt.includes('/pdf/');
                    let pdf_url = null;
                    if (has_pdf) {
                        const m = txt.match(/href="([^"]+\/pdf\/[^"]+)"/);
                        if (m) pdf_url = m[1];
                    }
                    return { has_pdf, pdf_url };
                } catch(e) { return { has_pdf: false, pdf_url: null }; }
            }''', dl)
            if d_res.get('pdf_url'):
                pdf_links.append((dl, d_res['pdf_url']))

        print(f"  -> Page {p_num} has {len(pdf_links)} decisions with PDF link:")
        for dl, pu in pdf_links:
            print(f"     Decision: {dl} -> PDF: {pu}")

    context.close()
