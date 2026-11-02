"""
Automated Legal Data Mining & Scraper using Playwright
Target: Mahkamah Agung RI Decision Directory
Lembaga Peradilan: Pengadilan Negeri Jakarta Selatan
Kategori: PIDANA KHUSUS -> NARKOTIKA DAN PSIKOTROPIKA
Tahun: 2023 - 2025
Exclusion: Filter out decisions with status 'BERKEKUATAN HUKUM TETAP'
Target Quantity: Exactly 50 court judgment PDF documents
Output: Saved directly in Dataset/ directory
"""

import os
import re
import sys
import time
import json
import base64
from urllib.parse import urljoin

import pdfplumber
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
DATA_DIR = os.path.join(BASE_DIR, "data")
METADATA_FILE = os.path.join(DATA_DIR, "metadata_raw.json")
PROFILE_DIR = os.path.join(BASE_DIR, "playwright_user_data")
BASE_URL = "https://putusan3.mahkamahagung.go.id"

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)

TARGET_TOTAL = 50
YEARS = [2024, 2023, 2025]

def clean_filename(text: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', text)
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    return cleaned


def is_court_pdf(path: str, case_number: str = "") -> bool:
    try:
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


def is_pdf_payload(payload: bytes) -> bool:
    return len(payload) > 1000 and payload.startswith(b"%PDF-")


def extract_decision_info(soup: BeautifulSoup) -> dict:
    info = {
        "nomor": "",
        "lembaga": "Pengadilan Negeri Jakarta Selatan",
        "tahun": "",
        "amar": "",
        "amar_lainnya": "",
        "catatan_amar": "",
        "barang_bukti": "",
        "amar_putusan": "",
        "status_bht": False
    }

    full_text = soup.get_text()
    if "berkekuatan hukum tetap" in full_text.lower():
        info["status_bht"] = True

    for tr in soup.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(tds) >= 2:
            key = tds[0].lower().strip()
            val = tds[1].strip()
            if "nomor" in key and not info["nomor"]:
                info["nomor"] = val
            elif "lembaga peradilan" in key:
                info["lembaga"] = val
            elif "tahun" in key and not info["tahun"]:
                info["tahun"] = val
            elif "amar lainnya" in key:
                info["amar_lainnya"] = val
            elif "catatan amar" in key:
                info["catatan_amar"] = val
            elif "amar" in key and not info["amar"]:
                info["amar"] = val

    # Parse Barang Bukti and Amar Putusan from catatan_amar or full_text
    catatan = info["catatan_amar"] or full_text
    # Extract Barang Bukti
    bb_match = re.search(r"(?:barang\s*bukti|menetapkan\s*barang\s*bukti(?:\s*berupa)?)\s*[:\-]?\s*(.*?)(?:membebankan|membebankan\s*terdakwa|memperhatikan|demikianlah|putusan\s*ini|6\.|\Z)", catatan, re.IGNORECASE | re.DOTALL)
    if bb_match:
        info["barang_bukti"] = bb_match.group(1).strip()
    else:
        # Fallback search
        bb_fallback = re.search(r"barang\s*bukti\s*:(.*?)(?:membebankan|\Z)", catatan, re.IGNORECASE | re.DOTALL)
        if bb_fallback:
            info["barang_bukti"] = bb_fallback.group(1).strip()

    # Extract Amar Putusan (MENGADILI / Menyatakan Terdakwa...)
    amar_match = re.search(r"(?:M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I|Menyatakan\s*Terdakwa)(.*?)(?:Menetapkan\s*barang\s*bukti|barang\s*bukti|\Z)", catatan, re.IGNORECASE | re.DOTALL)
    if amar_match:
        info["amar_putusan"] = (("MENGADILI: " if "M E N G A D I L I" in catatan else "") + amar_match.group(1)).strip()
    else:
        info["amar_putusan"] = info["catatan_amar"] or info["amar_lainnya"] or info["amar"]

    return info

def main():
    print("=" * 60)
    print(f"[START] Mahkamah Agung RI Decision Scraper")
    print(f"Lembaga: Pengadilan Negeri Jakarta Selatan")
    print(f"Klasifikasi: Pidana Khusus -> Narkotika dan Psikotropika")
    print(f"Tahun: 2023 - 2025")
    print(f"Target Quantity: {TARGET_TOTAL} PDFs")
    print(f"Destination: {DATASET_DIR}")
    print("=" * 60)

    # Check existing files
    existing_files = [
        f for f in os.listdir(DATASET_DIR)
        if f.lower().endswith(".pdf") and is_court_pdf(os.path.join(DATASET_DIR, f))
    ]
    total_saved = len(existing_files)
    print(f"[INFO] Existing valid PDFs in Dataset: {total_saved}/{TARGET_TOTAL}")
    if total_saved >= TARGET_TOTAL:
        print("[SUCCESS] Target already satisfied!")
        return

    metadata_list = []
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)
        except Exception:
            metadata_list = []

    seen_urls = {m.get("url") for m in metadata_list if "url" in m}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("[INFO] Browser siap; membuka daftar putusan yang sudah difilter.")

        access_blocked = False
        for year in YEARS:
            if total_saved >= TARGET_TOTAL:
                break

            print(f"\n[INFO] ================= Processing Year: {year} =================")
            page_idx = 1
            max_pages = 12

            while page_idx <= max_pages and total_saved < TARGET_TOTAL:
                if page_idx == 1:
                    list_url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}.html"
                else:
                    list_url = f"https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-jakarta-selatan/kategori/narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}/page/{page_idx}.html"

                print(f"[INFO] Loading {year} Page {page_idx}: {list_url}")
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
                    page_idx += 1
                    continue

                status = list_response.status if list_response else None
                if status in (403, 429):
                    print(f"[BLOCKED] Server returned {status} for {list_url}; stopping politely.")
                    access_blocked = True
                    break
                if status != 200:
                    print(f"[WARN] List returned {status or 'no response'}, skipping page.")
                    break

                time.sleep(1.0)
                soup = BeautifulSoup(page.content(), 'html.parser')
                decision_links = []
                for a in soup.find_all('a', href=re.compile(r'/direktori/putusan/')):
                    h = urljoin(BASE_URL, a['href'])
                    if h not in decision_links and not any(k in h for k in ['kategori', 'pengadilan', 'tahun']):
                        decision_links.append(h)

                if not decision_links:
                    print(f"[INFO] No more decisions found on page {page_idx}.")
                    break

                print(f"[INFO] Found {len(decision_links)} decisions on page {page_idx}.")

                for decision_index, d_url in enumerate(decision_links, start=1):
                    if total_saved >= TARGET_TOTAL:
                        break

                    if d_url in seen_urls:
                        continue

                    seen_urls.add(d_url)

                    try:
                        print(
                            f"[INFO] Opening decision {decision_index}/{len(decision_links)} "
                            f"({total_saved}/{TARGET_TOTAL} verified): {d_url}",
                            flush=True,
                        )
                        detail_response = page.goto(
                            d_url,
                            wait_until="domcontentloaded",
                            timeout=45000,
                        )
                        if detail_response is None or detail_response.status != 200:
                            status = detail_response.status if detail_response else None
                            if status in (403, 429):
                                print(f"[BLOCKED] Server returned {status} for {d_url}; stopping politely.")
                                access_blocked = True
                                break
                            print(f"[SKIP] Detail returned {status or 'no response'}: {d_url}")
                            continue

                        d_soup = BeautifulSoup(page.content(), 'html.parser')
                        meta = extract_decision_info(d_soup)
                        meta["url"] = d_url

                        # Exclusion check: Status BERKEKUATAN HUKUM TETAP
                        if meta["status_bht"]:
                            print(f"[EXCLUDE] Status Berkekuatan Hukum Tetap: {meta.get('nomor', d_url)}")
                            continue

                        nomor = meta["nomor"] or f"putusan_{total_saved+1}"
                        clean_no = clean_filename(nomor)
                        pdf_filename = f"{clean_no}.pdf"
                        dest_path = os.path.join(DATASET_DIR, pdf_filename)

                        # Only accept the original attachment, never a print of the detail page.
                        col3 = d_soup.find("div", id="collapseThree")
                        if col3:
                            pdf_a = col3.find("a", href=re.compile(r'/pdf/'))
                            if pdf_a:
                                pdf_url = pdf_a["href"]
                                fetch_res = page.evaluate('''async (url) => {
                                    try {
                                        const r = await fetch(url);
                                        const buf = await r.arrayBuffer();
                                        const bytes = new Uint8Array(buf);
                                        const isPdf = r.ok && bytes.length > 1000 &&
                                            bytes[0] === 0x25 && bytes[1] === 0x50 &&
                                            bytes[2] === 0x44 && bytes[3] === 0x46 &&
                                            bytes[4] === 0x2d;
                                        if (!isPdf) return {
                                            ok: false,
                                            status: r.status,
                                            contentType: r.headers.get("content-type") || "",
                                            prefix: Array.from(bytes.slice(0, 5))
                                        };
                                        let bin = "";
                                        for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                                        return {
                                            ok: true,
                                            size: bytes.length,
                                            contentType: r.headers.get("content-type") || "",
                                            b64: btoa(bin)
                                        };
                                    } catch (e) {
                                        return { ok: false, error: String(e) };
                                    }
                                }''', pdf_url)

                                if fetch_res.get("ok") and fetch_res.get("b64"):
                                    raw = base64.b64decode(fetch_res["b64"])
                                    if not is_pdf_payload(raw):
                                        print(f"[SKIP] Invalid PDF payload for {nomor}")
                                        continue
                                    temp_path = dest_path + ".part"
                                    with open(temp_path, "wb") as f_out:
                                        f_out.write(raw)
                                    if not is_court_pdf(temp_path, nomor):
                                        os.remove(temp_path)
                                        print(f"[SKIP] Response is not the court judgment PDF for {nomor}")
                                        continue
                                    os.replace(temp_path, dest_path)
                                    total_saved += 1
                                    meta["pdf_path"] = dest_path
                                    meta["pdf_filename"] = pdf_filename
                                    meta["pdf_size"] = len(raw)
                                    metadata_list.append(meta)
                                    print(f"[DOWNLOADED] [{total_saved}/{TARGET_TOTAL}] {pdf_filename} ({len(raw)} bytes)")

                                    with open(METADATA_FILE, "w", encoding="utf-8") as f_meta:
                                        json.dump(metadata_list, f_meta, ensure_ascii=False, indent=2)
                                else:
                                    print(
                                        f"[SKIP] Not an original PDF for {nomor}: "
                                        f"status={fetch_res.get('status', 'error')}, "
                                        f"type={fetch_res.get('contentType', 'unknown')}, "
                                        f"prefix={fetch_res.get('prefix', fetch_res.get('error', 'unknown'))}"
                                    )
                                    if fetch_res.get("status") in (403, 429):
                                        print("[BLOCKED] PDF endpoint refused further access; stopping politely.")
                                        access_blocked = True
                                        break
                            else:
                                print(f"[SKIP] No downloadable PDF attachment: {nomor}")
                        else:
                            print(f"[SKIP] No attachment section: {nomor}")

                    except Exception as err:
                        if context.is_closed():
                            raise RuntimeError("Browser ditutup sebelum proses unduh selesai.") from err
                        print(f"[WARN] Error on {d_url}: {err}")
                        continue

                if access_blocked:
                    break
                page_idx += 1

            if access_blocked:
                break

        context.close()

    print("\n" + "=" * 60)
    if total_saved < TARGET_TOTAL:
        print(f"[INCOMPLETE] Verified original PDFs: {total_saved}/{TARGET_TOTAL}.")
        if access_blocked:
            print("[INFO] Resume later after the source site permits access again.")
    else:
        print(f"[COMPLETE] Acquisition finished! Total PDFs: {total_saved}/{TARGET_TOTAL}")
    print(f"Files saved in: {DATASET_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
