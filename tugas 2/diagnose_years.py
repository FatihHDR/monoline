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
    time.sleep(2)

    # Test PDF availability by year for PN Jaksel Narkotika
    years = [2023, 2022, 2021, 2020, 2019, 2018]
    for yr in years:
        url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{yr}.html"
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

        # Check first 5 on this year's page
        pdf_success = 0
        for dl in d_links[:5]:
            chk = page.evaluate(r'''async (u) => {
                try {
                    const r = await fetch(u);
                    const txt = await r.text();
                    const m = txt.match(/href="([^"]+\/pdf\/[^"]+)"/);
                    if (!m) return false;
                    const pr = await fetch(m[1]);
                    const ct = pr.headers.get("content-type") || "";
                    if (!ct.includes("text/html") && pr.status === 200) {
                        const buf = await pr.arrayBuffer();
                        const bytes = new Uint8Array(buf);
                        return (bytes.length > 1000 && bytes[0] === 0x25 && bytes[1] === 0x50);
                    }
                    return false;
                } catch(e) { return false; }
            }''', dl)
            if chk:
                pdf_success += 1

        print(f"Year {yr}: {len(d_links)} total on page 1 | PDF available in first 5: {pdf_success}/5")

    context.close()
