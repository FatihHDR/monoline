import os, time
from playwright.sync_api import sync_playwright
import pdfplumber

user_data = os.path.abspath('playwright_user_data')
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled']
    )
    page = context.pages[0] if context.pages else context.new_page()
    url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaef108896c5e32ca127303035333530.html'
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)
    
    out_pdf = os.path.join(os.getcwd(), 'Dataset', '173_Pid.Sus_2024_PN_JKT.SEL.pdf')
    # Generate PDF of the decision
    page.pdf(path=out_pdf, format='A4', print_background=True)
    print("Generated PDF size:", os.path.getsize(out_pdf))
    context.close()

with pdfplumber.open(out_pdf) as pdf:
    print("Pages:", len(pdf.pages))
    text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    print("Contains 173/Pid.Sus/2024:", "173/Pid.Sus/2024" in text)
    print("Contains PN JAKARTA SELATAN:", "PN JAKARTA SELATAN" in text)
    print("Contains Narkotika:", "Narkotika" in text)
    print("Text length:", len(text))
    print("Sample text:\n", text[:300])
