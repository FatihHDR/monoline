import os, time, re, base64, json
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

    valid_pdfs = []

    # Check 2023 to 2025
    for year in [2023, 2024, 2025]:
        print(f"\n=================== YEAR {year} ===================")
        page_num = 1
        while page_num <= 15:
            if page_num == 1:
                list_url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}.html"
            else:
                list_url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}/page/{page_num}.html"

            res = page.evaluate('''async (url) => {
                const r = await fetch(url);
                return { status: r.status, text: await r.text() };
            }''', list_url)

            if res['status'] != 200:
                break

            soup = BeautifulSoup(res['text'], 'html.parser')
            decision_links = []
            for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
                h = a['href']
                if h not in decision_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                    decision_links.append(h)

            if not decision_links:
                break

            print(f"Year {year} Page {page_num}: checking {len(decision_links)} decisions...")

            # Check all decisions on this page in batch using JS
            batch_result = page.evaluate('''async (urls) => {
                const results = [];
                for (const u of urls) {
                    try {
                        const r = await fetch(u);
                        const txt = await r.text();
                        if (txt.includes('/pdf/')) {
                            // Extract pdf url
                            const match = txt.match(/href="([^"]+\/pdf\/[^"]+)"/);
                            if (match) {
                                const pdfUrl = match[1];
                                // Test fetching head of pdfUrl
                                const pr = await fetch(pdfUrl);
                                const ct = pr.headers.get("content-type") || "";
                                if (ct.includes("pdf") || pr.status === 200) {
                                    const buf = await pr.arrayBuffer();
                                    const bytes = new Uint8Array(buf);
                                    if (bytes.length > 1000 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46) {
                                        let bin = "";
                                        for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                                        results.push({
                                            url: u,
                                            pdfUrl: pdfUrl,
                                            html: txt,
                                            size: bytes.length,
                                            b64: btoa(bin)
                                        });
                                    }
                                }
                            }
                        }
                    } catch (e) {}
                }
                return results;
            }''', decision_links)

            for item in batch_result:
                d_soup = BeautifulSoup(item['html'], 'html.parser')
                bht = 'berkekuatan hukum tetap' in item['html'].lower()
                nomor = ""
                for tr in d_soup.find_all('tr'):
                    tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                    if len(tds) >= 2 and 'nomor' in tds[0].lower():
                        nomor = tds[1]
                        break
                if not bht and nomor:
                    valid_pdfs.append((nomor, item['pdfUrl'], item['size'], item['b64']))
                    clean_name = re.sub(r'[\\/*?:"<>|\s]', '_', nomor) + '.pdf'
                    dest = os.path.join(os.getcwd(), 'Dataset', clean_name)
                    with open(dest, 'wb') as f:
                        f.write(base64.b64decode(item['b64']))
                    print(f"  [SAVED {len(valid_pdfs)}] {nomor} ({item['size']} bytes) -> {clean_name}")

            page_num += 1

    print(f"\nTOTAL VALID 2023-2025 PDFS ACQUIRED: {len(valid_pdfs)}")
    context.close()
