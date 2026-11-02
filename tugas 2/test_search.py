import os
import time
from playwright.sync_api import sync_playwright

def test_search():
    user_data = os.path.abspath('playwright_user_data')
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=False,
            channel='chrome',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized'
            ],
            viewport=None
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("[INFO] Navigating to search.html...")
        page.goto('https://putusan3.mahkamahagung.go.id/search.html', timeout=60000)
        page.wait_for_load_state('domcontentloaded')
        time.sleep(2)
        print(f"[INFO] Page Title: {page.title()}")

        # Fill Keyword
        print("[INFO] Filling keyword: NARKOTIKA DAN PSIKOTROPIKA")
        page.fill('input[name="q"]', 'NARKOTIKA DAN PSIKOTROPIKA')
        time.sleep(1)

        # Select Court: PN JAKARTA SELATAN (400214PN88)
        print("[INFO] Selecting court: PN JAKARTA SELATAN")
        page.select_option('select[name="court"]', value='400214PN88')
        time.sleep(1)

        # Check for captcha
        cb = page.locator('#altcha-checkbox-captcha-widget-inline')
        if cb.count() > 0:
            print(f"[INFO] Captcha checkbox found! Checked state: {cb.is_checked()}")
            if not cb.is_checked():
                print("[INFO] Clicking captcha checkbox...")
                cb.click()
                for _ in range(15):
                    time.sleep(1)
                    if cb.is_checked():
                        print("[INFO] Captcha resolved successfully!")
                        break

        # Submit search
        print("[INFO] Submitting search...")
        page.click('button[type="submit"]')
        page.wait_for_load_state('domcontentloaded')
        time.sleep(5)

        print(f"[INFO] Current URL after search: {page.url}")
        print(f"[INFO] Page Title after search: {page.title()}")

        with open('search_results.html', 'w', encoding='utf-8') as f:
            f.write(page.content())
        print("[INFO] Saved search_results.html")

        context.close()

if __name__ == '__main__':
    test_search()
