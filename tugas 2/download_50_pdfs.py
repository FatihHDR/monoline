import os
import re
import time
import json
from urllib.parse import urljoin

import pdfplumber
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "https://putusan3.mahkamahagung.go.id"
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
DATA_DIR = os.path.join(BASE_DIR, "data")
METADATA_FILE = os.path.join(DATA_DIR, "metadata_raw.json")
USER_DATA_DIR = os.path.join(BASE_DIR, "playwright_user_data")

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

TARGET_NEW = 50


def clean_filename(text: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', text)
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    return cleaned


def is_court_pdf(path: str, case_number: str = "") -> bool:
    try:
        if not os.path.isfile(path):
            return False
        with open(path, "rb") as handle:
            if handle.read(5) != b"%PDF-":
                return False
        with pdfplumber.open(path) as document:
            text = " ".join(
                page.extract_text(layout=False) or ""
                for page in document.pages[:3]
            ).upper()
        if "DEMI KEADILAN" not in text or "KETUHANAN YANG MAHA ESA" not in text:
            return False
        if case_number:
            normalize = lambda value: re.sub(r"[^A-Z0-9]", "", value.upper())
            if normalize(case_number) not in normalize(text):
                return False
        return True
    except Exception as error:
        print(f"[WARN] Could not verify PDF {path}: {error}")
        return False


def wait_for_manual_verification(page, selector: str) -> bool:
    title = page.title().lower()
    try:
        body = page.locator("body").inner_text(timeout=5000).lower()
    except PlaywrightTimeoutError:
        body = ""
    challenge_terms = ("just a moment", "verify you are human", "captcha", "turnstile")
    if not any(term in title or term in body for term in challenge_terms):
        return False

    print(
        "[ACTION] Cloudflare meminta verifikasi manusia. Klik checkbox "
        "'Verify you are human' di jendela Chrome dan jangan tutup jendela. "
        "Unduhan akan dilanjutkan otomatis setelah halaman putusan terbuka "
        "(maksimal 10 menit)."
    )
    try:
        page.wait_for_selector(selector, state="attached", timeout=600000)
    except PlaywrightTimeoutError:
        print("[BLOCKED] Verifikasi situs belum selesai.")
        return False
    except PlaywrightError as error:
        print(f"[BLOCKED] Browser ditutup saat verifikasi: {error}")
        return False
    return True


def extract_metadata(soup: BeautifulSoup) -> dict:
    meta = {
        "nomor": "",
        "lembaga": "Pengadilan Negeri Jakarta Selatan",
        "tahun": "",
        "amar": "",
        "amar_lainnya": "",
        "catatan_amar": "",
        "status_bht": False,
        "barang_bukti": "",
        "amar_putusan": ""
    }
    
    full_text = soup.get_text()
    if "berkekuatan hukum tetap" in full_text.lower():
        meta["status_bht"] = True

    for tr in soup.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(tds) >= 2:
            key = tds[0].lower().strip()
            val = tds[1].strip()
            if "nomor" in key and not meta["nomor"]:
                meta["nomor"] = val
            elif "lembaga peradilan" in key:
                meta["lembaga"] = val
            elif "tahun" in key and not meta["tahun"]:
                meta["tahun"] = val
            elif "amar lainnya" in key:
                meta["amar_lainnya"] = val
            elif "catatan amar" in key:
                meta["catatan_amar"] = val
            elif "amar" in key and not meta["amar"]:
                meta["amar"] = val

    return meta

def main():
    print(f"==================================================")
    print(f"[START] Collecting {TARGET_NEW} new court decision PDFs")
    print(f"Target Directory: {DATASET_DIR}")
    print(f"==================================================")

    # Count existing valid PDFs
    existing = [
        f for f in os.listdir(DATASET_DIR)
        if f.lower().endswith(".pdf") and is_court_pdf(os.path.join(DATASET_DIR, f))
    ]
    existing_files = set(existing)
    print(f"[INFO] Existing valid PDFs preserved: {len(existing_files)}")
    print(f"[INFO] Target: {TARGET_NEW} new verified PDFs")

    metadata_list = []
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)
        except Exception:
            metadata_list = []

    seen_urls = set()
    for item in metadata_list:
        filename = item.get("pdf_filename")
        url = item.get("url")
        if not filename or not url:
            continue
        existing_path = os.path.join(DATASET_DIR, filename)
        if is_court_pdf(existing_path, item.get("nomor", "")):
            seen_urls.add(url)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("[INFO] Browser siap; membuka daftar putusan yang sudah difilter.")

        # Build list of page URLs to crawl
        # 1) Years 2023, 2024, 2025
        page_urls = []
        for yr in [2023, 2024, 2025]:
            for p_num in range(1, 15):
                if p_num == 1:
                    u = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{yr}.html"
                else:
                    u = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{yr}/page/{p_num}.html"
                page_urls.append((yr, p_num, u))

        access_blocked = False
        new_downloaded = 0
        for label, p_num, list_url in page_urls:
            if new_downloaded >= TARGET_NEW:
                break

            print(f"\n[INFO] Loading list [{label} P{p_num}]: {list_url}")
            try:
                list_response = page.goto(
                    list_url,
                    wait_until="domcontentloaded",
                    timeout=45000,
                )
            except Exception as e:
                if context.is_closed():
                    raise RuntimeError("Browser ditutup sebelum proses unduh selesai.") from e
                print(f"[WARN] Error fetching list {list_url}: {e}")
                continue

            status = list_response.status if list_response else None
            if status in (403, 429):
                if not wait_for_manual_verification(
                    page,
                    'a[href*="/direktori/putusan/"]',
                ):
                    print(f"[BLOCKED] Server returned {status} for {list_url}; stopping politely.")
                    access_blocked = True
                    break
            if status != 200:
                if status not in (403, 429):
                    status = status if status is not None else "no response"
                    print(f"[WARN] List returned {status}, skipping page.")
                    continue

            time.sleep(1.5)
            soup = BeautifulSoup(page.content(), 'html.parser')
            decision_links = []
            for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
                h = urljoin(BASE_URL, a['href'])
                if h not in decision_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                    decision_links.append(h)

            if not decision_links:
                print(f"[INFO] No decisions found on this page.")
                break

            print(f"[INFO] Found {len(decision_links)} decisions. Scanning for PDFs...")

            for decision_index, d_url in enumerate(decision_links, start=1):
                if new_downloaded >= TARGET_NEW:
                    break

                if d_url in seen_urls:
                    continue

                seen_urls.add(d_url)

                try:
                    print(
                        f"[INFO] Opening decision {decision_index}/{len(decision_links)} "
                        f"({new_downloaded}/{TARGET_NEW} new PDFs): {d_url}",
                        flush=True,
                    )
                    detail_response = page.goto(
                        d_url,
                        wait_until="domcontentloaded",
                        timeout=45000,
                    )
                    if detail_response is None or detail_response.status != 200:
                        status = detail_response.status if detail_response else "no response"
                        if status in (403, 429):
                            if not wait_for_manual_verification(page, "#page-title h1"):
                                print(f"[BLOCKED] Server returned {status} for {d_url}; stopping politely.")
                                access_blocked = True
                                break
                        else:
                            print(f"[SKIP] Detail page returned {status or 'no response'}: {d_url}")
                            continue

                    d_soup = BeautifulSoup(page.content(), 'html.parser')
                    meta = extract_metadata(d_soup)
                    meta["url"] = d_url

                    page_heading = d_soup.select_one("#page-title")
                    heading_text = (
                        page_heading.get_text(" ", strip=True).upper()
                        if page_heading
                        else ""
                    )
                    if (
                        "JAKARTA SELATAN" not in meta["lembaga"].upper()
                        and "PN JAKARTA SELATAN" not in heading_text
                    ):
                        print(f"[SKIP] Not a PN Jakarta Selatan decision: {d_url}")
                        continue
                    if meta["tahun"] not in {"2023", "2024", "2025"}:
                        print(f"[SKIP] Outside the 2023-2025 range: {meta.get('nomor', d_url)}")
                        continue

                    # Check exclusion constraint
                    if meta["status_bht"]:
                        print(f"[SKIP] BERKEKUATAN HUKUM TETAP: {meta.get('nomor', d_url)}")
                        continue

                    col3 = d_soup.find('div', id='collapseThree')
                    if not col3:
                        print(f"[SKIP] No attachment section: {meta.get('nomor', d_url)}")
                        continue

                    pdf_button = page.locator('#collapseThree a[href*="/pdf/"]')
                    if pdf_button.count() == 0:
                        print(f"[SKIP] No downloadable PDF attachment: {meta.get('nomor', d_url)}")
                        continue

                    nomor = meta['nomor'] or f"putusan_{new_downloaded+1}"
                    clean_no = clean_filename(nomor)
                    filename = f"{clean_no}.pdf"
                    dest_file = os.path.join(DATASET_DIR, filename)

                    if filename in existing_files:
                        print(f"[EXISTS] Preserving existing PDF: {filename}")
                        continue
                    if os.path.exists(dest_file):
                        print(f"[SKIP] Destination already exists and is not a verified PDF: {filename}")
                        continue

                    temp_file = dest_file + ".part"
                    try:
                        with page.expect_download(timeout=10000) as download_info:
                            pdf_button.first.click()
                        download = download_info.value
                        download.save_as(temp_file)
                    except PlaywrightTimeoutError:
                        print(f"[SKIP] Click did not start a PDF download: {nomor}")
                        continue

                    if not is_court_pdf(temp_file, nomor):
                        os.remove(temp_file)
                        print(f"[SKIP] Download is not the expected court judgment PDF: {nomor}")
                        continue

                    os.replace(temp_file, dest_file)
                    new_downloaded += 1
                    existing_files.add(filename)
                    meta["pdf_path"] = dest_file
                    meta["pdf_filename"] = filename
                    meta["pdf_size"] = os.path.getsize(dest_file)
                    existing_index = next(
                        (i for i, item in enumerate(metadata_list) if item.get("url") == d_url),
                        None,
                    )
                    if existing_index is None:
                        metadata_list.append(meta)
                    else:
                        metadata_list[existing_index] = meta
                    seen_urls.add(d_url)
                    print(
                        f"[SUCCESS] [{new_downloaded}/{TARGET_NEW} new] "
                        f"Downloaded: {filename} ({meta['pdf_size']} bytes)"
                    )

                    with open(METADATA_FILE, "w", encoding="utf-8") as mf:
                        json.dump(metadata_list, mf, ensure_ascii=False, indent=2)

                except Exception as ex:
                    if context.is_closed() or page.is_closed():
                        print(
                            "[STOPPED] Browser ditutup sebelum target tercapai; "
                            f"PDF baru terverifikasi: {new_downloaded}/{TARGET_NEW}."
                        )
                        access_blocked = True
                        break
                    print(f"[WARN] Error on decision {d_url}: {ex}")
                    continue
                finally:
                    time.sleep(1.5)

            if access_blocked or new_downloaded >= TARGET_NEW:
                break

        context.close()

    print(f"\n==================================================")
    if new_downloaded < TARGET_NEW:
        if access_blocked:
            print("[INFO] Resume later after the source site permits access again.")
        print(
            f"[INCOMPLETE] Downloaded {new_downloaded}/{TARGET_NEW} new verified "
            "original PDFs. No page printouts were substituted."
        )
        print(f"[INFO] Existing PDFs preserved: {len(existing_files) - new_downloaded}")
        print(f"Files saved in: {DATASET_DIR}")
        print("==================================================")
        raise SystemExit(1)

    print(f"[DONE] Downloaded exactly {new_downloaded} new verified PDF files.")
    print(f"[INFO] Total valid PDFs in Dataset: {len(existing_files)}")
    print(f"Files saved in: {DATASET_DIR}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
