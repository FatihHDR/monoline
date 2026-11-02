import os, time
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
    url = 'https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf0fc0f9b72ee14855b313330373231.html'
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(1)
    soup = BeautifulSoup(page.content(), 'html.parser')
    col3 = soup.find('div', id='collapseThree')
    if col3:
        print("HTML of collapseThree:")
        print(col3.prettify())
    else:
        print("collapseThree not found")
    context.close()
