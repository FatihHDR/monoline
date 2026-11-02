import os, time, base64
from playwright.sync_api import sync_playwright

user_data = os.path.abspath('playwright_user_data')
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled']
    )
    page = context.pages[0] if context.pages else context.new_page()
    # Go to the detail page first so Referer is set
    detail_url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0f5d30aed86529080313433383431.html'
    page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    pdf_url = 'https://putusan3.mahkamahagung.go.id/direktori/download_file/bf7023fd979965cc546fa04d1049ce94/pdf/zaf0f5d30aed86529080313433383431'
    print("Testing fetch of PDF arrayBuffer inside page...")
    res = page.evaluate('''async (url) => {
        try {
            const resp = await fetch(url);
            if (!resp.ok) return { ok: false, status: resp.status };
            const buffer = await resp.arrayBuffer();
            let binary = '';
            const bytes = new Uint8Array(buffer);
            const len = bytes.byteLength;
            for (let i = 0; i < len; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return {
                ok: true,
                status: resp.status,
                size: len,
                b64: btoa(binary)
            };
        } catch (e) {
            return { ok: false, error: e.toString() };
        }
    }''', pdf_url)

    print("Result:", res.get('ok'), res.get('status'), res.get('size'))
    if res.get('ok') and res.get('b64'):
        raw = base64.b64decode(res['b64'])
        print(f"Decoded {len(raw)} bytes. Prefix: {raw[:10]}")
        if raw[:4] == b'%PDF':
            print("SUCCESS! VALID PDF ACQUIRED VIA IN-PAGE FETCH!")
            with open('test_inpage_pdf.pdf', 'wb') as f:
                f.write(raw)

    context.close()
