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

    # Let's test checking decisions across years for PN Jakarta Selatan
    # e.g., 2022, 2021, 2020, 2019, 2018, 2017
    # To see which years have high PDF attachment rates!
    for yr in [2022, 2021, 2020, 2019, 2018]:
        url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{yr}.html"
        print(f"\nChecking Year {yr}: {url}")
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

        print(f"Year {yr} has {len(d_links)} decisions on page 1.")
        # Check first 8 decisions on this year
        available_count = 0
        for dl in d_links[:8]:
            chk = page.evaluate(r'''async (u) => {
                try {
                    const r = await fetch(u);
                    const txt = await r.text();
                    const m = txt.match(/href="([^"]+\/pdf\/[^"]+)"/);
                    if (!m) return { ok: false, reason: "no_link" };
                    const pr = await fetch(m[1]);
                    const ct = pr.headers.get("content-type") || "";
                    if (!ct.includes("text/html") && pr.status === 200) {
                        const buf = await pr.arrayBuffer();
                        const bytes = new Uint8Array(buf);
                        if (bytes.length > 1000 && bytes[0] === 0x25 && bytes[1] === 0x50) {
                            return { ok: true, size: bytes.length };
                        }
                    }
                    return { ok: false, reason: "redirect_or_not_pdf" };
                } catch(e) { return { ok: false, reason: e.toString() }; }
            }''', dl)
            if chk.get('ok'):
                available_count += 1
                print(f"  [PDF OK] {dl} ({chk['size']} bytes)")
            else:
                print(f"  [NO PDF] {dl} ({chk.get('reason')})")

        print(f"Year {yr} rate: {available_count}/8 have working PDFs")

    context.close()
