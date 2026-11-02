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

    found_pdfs = []
    for page_num in range(1, 30):
        if len(found_pdfs) >= 50:
            break
        if page_num == 1:
            url = "https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1.html"
        else:
            url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/page/{page_num}.html"

        res = page.evaluate('''async (url) => {
            try {
                const r = await fetch(url);
                return { status: r.status, text: await r.text() };
            } catch(e) {
                return { status: 0, text: "" };
            }
        }''', url)

        if res['status'] != 200:
            continue

        soup = BeautifulSoup(res['text'], 'html.parser')
        d_links = []
        for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
            h = a['href']
            if h not in d_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                d_links.append(h)

        print(f"Page {page_num}: checking {len(d_links)} decisions...")

        for dl in d_links:
            if len(found_pdfs) >= 50:
                break
            d_res = page.evaluate(r'''async (u) => {
                try {
                    const r = await fetch(u);
                    const txt = await r.text();
                    if (!txt.includes('/pdf/')) return { ok: false };
                    const match = txt.match(/href="([^"]+\/pdf\/[^"]+)"/);
                    if (!match) return { ok: false };
                    const pr = await fetch(match[1]);
                    const ct = pr.headers.get("content-type") || "";
                    if (!ct.includes("text/html") && pr.status === 200) {
                        const buf = await pr.arrayBuffer();
                        const bytes = new Uint8Array(buf);
                        if (bytes.length > 1000 && bytes[0] === 0x25 && bytes[1] === 0x50) {
                            return { ok: true, pdfUrl: match[1], size: bytes.length, bht: txt.toLowerCase().includes("berkekuatan hukum tetap") };
                        }
                    }
                    return { ok: false };
                } catch (e) {
                    return { ok: false };
                }
            }''', dl)

            if d_res.get('ok') and not d_res.get('bht'):
                found_pdfs.append((dl, d_res['pdfUrl'], d_res['size']))
                print(f"  [SUCCESS {len(found_pdfs)}/50] Available PDF ({d_res['size']} bytes): {dl}")

    print(f"\nTOTAL ACCESSIBLE REAL PDFS: {len(found_pdfs)}")
    context.close()
