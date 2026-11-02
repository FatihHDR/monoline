import os, time
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

    # Let's test search directly for narkotika in PN Jakarta Selatan
    # Let's look at decisions from 2023, 2022, 2021 to see PDF download behavior
    urls_to_test = [
        # Some sample decisions from direktori
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaee204dca5e6910bc0b303734383137.html', # 299/Pid.Sus/2023
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/0eb5394484848c3e48c0c8252911645c.html', # 140/Pid.Sus/2018
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaedb645ac0ce0f89305303932333037.html', # 796/Pid.B/2022
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/ddf2cee6b1f2307f9103cbda10934c32.html', # 370/Pid.Sus/2018
        'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaec110acd1ddc70aaef303831313033.html'  # 1028/Pid.Sus/2020
    ]

    for u in urls_to_test:
        page.goto(u, wait_until='domcontentloaded', timeout=30000)
        time.sleep(1)
        soup = BeautifulSoup(page.content(), 'html.parser')
        col3 = soup.find('div', id='collapseThree')
        links = []
        if col3:
            for a in col3.find_all('a', href=True):
                links.append(a['href'])
        print(f"\nURL: {u}")
        print(f"Links found in collapseThree: {links}")
        for link in links:
            if '/pdf/' in link:
                print("Testing click on:", link)
                # Let's see what happens on click or download
                try:
                    with page.expect_download(timeout=10000) as d_info:
                        page.locator(f'a[href="{link}"]').click()
                    d = d_info.value
                    print(f"SUCCESS! Downloaded: {d.suggested_filename}")
                except Exception as e:
                    print("Download event failed:", type(e).__name__)

    context.close()
