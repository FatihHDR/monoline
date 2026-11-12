"""Download putusan PDF (PN Jakarta Selatan, Narkotika, 2023-2025).

Pendekatan yang dipakai:
- Browser Chrome asli (persistent profile) supaya cookie/clearance situs
  (Cloudflare + ALTCHA) tetap valid.
- Semua pengambilan data memakai ``fetch()`` dari dalam halaman (same-origin,
  credentials include). Dengan cara ini kita tidak pernah membuka endpoint
  unduhan secara langsung sehingga tidak memicu halaman verifikasi bot.
- PDF diambil sebagai byte, divalidasi signature ``%PDF-`` + isi putusan,
  lalu disimpan ke ``Dataset/``.

Script bersifat resumable: jalankan ulang kapan saja, berkas yang sudah ada
dan valid akan dipertahankan.
"""

import base64
import json
import os
import random
import re
import sys
import time
from urllib.parse import urljoin

import pdfplumber
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "https://putusan3.mahkamahagung.go.id"
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
DATA_DIR = os.path.join(BASE_DIR, "data")
METADATA_FILE = os.path.join(DATA_DIR, "metadata_raw.json")
PROFILE_DIR = os.path.join(BASE_DIR, "playwright_user_data")

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

TARGET_TOTAL = 100
YEARS = [2023, 2024, 2025]
MAX_PAGES = 30
MIN_DELAY = 0.8
MAX_DELAY = 1.8

FETCH_TEXT_JS = """async (url) => {
    try {
        const r = await fetch(url, {credentials: "include"});
        return {status: r.status, url: r.url, text: await r.text()};
    } catch (e) {
        return {status: -1, url: url, text: "", error: String(e)};
    }
}"""

FETCH_PDF_JS = """async (url) => {
    try {
        const r = await fetch(url, {credentials: "include"});
        const buf = await r.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let bin = "";
        const chunk = 0x8000;
        for (let i = 0; i < bytes.length; i += chunk) {
            bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
        }
        return {
            ok: r.ok,
            status: r.status,
            type: r.headers.get("content-type") || "",
            len: bytes.length,
            prefix: Array.from(bytes.slice(0, 5)),
            b64: btoa(bin)
        };
    } catch (e) {
        return {ok: false, status: -1, error: String(e), len: 0};
    }
}"""


def sleep_polite(low=MIN_DELAY, high=MAX_DELAY):
    time.sleep(random.uniform(low, high))


def clean_filename(text: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", text)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned


def is_court_pdf(path: str, case_number: str = "") -> bool:
    """True bila berkas adalah PDF putusan pengadilan yang bisa diekstrak."""
    try:
        if not os.path.isfile(path) or os.path.getsize(path) < 2000:
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
    except Exception as error:  # noqa: BLE001
        print(f"[WARN] Gagal memverifikasi PDF {os.path.basename(path)}: {error}")
        return False


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
        "amar_putusan": "",
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
                if val:
                    meta["lembaga"] = val
            elif "tahun" in key and not meta["tahun"]:
                meta["tahun"] = val
            elif "amar lainnya" in key:
                meta["amar_lainnya"] = val
            elif "catatan amar" in key:
                meta["catatan_amar"] = val
            elif "amar" in key and not meta["amar"]:
                meta["amar"] = val

    catatan = meta["catatan_amar"] or full_text
    bb_match = re.search(
        r"(?:barang\s*bukti|menetapkan\s*barang\s*bukti(?:\s*berupa)?)\s*[:\-]?\s*"
        r"(.*?)(?:membebankan|memperhatikan|demikianlah|putusan\s*ini|\Z)",
        catatan,
        re.IGNORECASE | re.DOTALL,
    )
    if bb_match:
        meta["barang_bukti"] = bb_match.group(1).strip()

    amar_match = re.search(
        r"(?:M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I|Menyatakan\s*Terdakwa)"
        r"(.*?)(?:Menetapkan\s*barang\s*bukti|barang\s*bukti|\Z)",
        catatan,
        re.IGNORECASE | re.DOTALL,
    )
    if amar_match:
        prefix = "MENGADILI: " if "M E N G A D I L I" in catatan else ""
        meta["amar_putusan"] = (prefix + amar_match.group(1)).strip()
    else:
        meta["amar_putusan"] = meta["catatan_amar"] or meta["amar_lainnya"] or meta["amar"]

    return meta


def find_pdf_url(soup: BeautifulSoup) -> str | None:
    col3 = soup.find("div", id="collapseThree")
    scope = col3 if col3 else soup
    anchor = scope.find("a", href=re.compile(r"/download_file/.*/pdf/"))
    if not anchor:
        return None
    return urljoin(BASE_URL, anchor["href"])


def list_url(year: int, page_num: int) -> str:
    base = (
        f"{BASE_URL}/direktori/index/pengadilan/pn-jakarta-selatan/kategori/"
        f"narkotika-dan-psikotropika-1/tahunjenis/putus/tahun/{year}"
    )
    if page_num == 1:
        return f"{base}.html"
    return f"{base}/page/{page_num}.html"


def decision_links_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=re.compile(r"/direktori/putusan/")):
        href = urljoin(BASE_URL, anchor["href"])
        if href in links:
            continue
        if any(token in href for token in ("kategori", "pengadilan", "tahun")):
            continue
        links.append(href)
    return links


def fetch_text(page, url: str, label: str = "", retries: int = 4):
    for attempt in range(1, retries + 1):
        result = page.evaluate(FETCH_TEXT_JS, url)
        status = result.get("status")
        if status == 200 and result.get("text"):
            return result
        if status in (403, 429):
            wait = 15 * attempt
            print(f"[BLOCKED] {label} status {status}; tunggu {wait}s lalu coba lagi "
                  f"({attempt}/{retries}) ...", flush=True)
            time.sleep(wait)
        else:
            print(f"[WARN] {label} status {status}; ulang ({attempt}/{retries})", flush=True)
            time.sleep(2 * attempt)
    return None


def fetch_pdf_bytes(page, url: str, retries: int = 4):
    for attempt in range(1, retries + 1):
        result = page.evaluate(FETCH_PDF_JS, url)
        if (
            result.get("ok")
            and result.get("len", 0) > 2000
            and result.get("prefix") == [37, 80, 68, 70, 45]  # %PDF-
            and result.get("b64")
        ):
            return base64.b64decode(result["b64"])
        if result.get("status") in (403, 429):
            wait = 15 * attempt
            print(f"[BLOCKED] PDF status {result.get('status')}; tunggu {wait}s "
                  f"({attempt}/{retries}) ...", flush=True)
            time.sleep(wait)
        else:
            print(f"[WARN] PDF bukan byte valid (status={result.get('status')}, "
                  f"len={result.get('len')}); ulang ({attempt}/{retries})", flush=True)
            time.sleep(2 * attempt)
    return None


def load_metadata() -> list[dict]:
    if not os.path.exists(METADATA_FILE):
        return []
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_metadata(records: list[dict]) -> None:
    with open(METADATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def main() -> None:
    print("=" * 62)
    print(f"[START] Mengumpulkan {TARGET_TOTAL} PDF putusan narkotika")
    print("        PN Jakarta Selatan | Tahun 2023-2025 | Non-BHT")
    print(f"        Tujuan: {DATASET_DIR}")
    print("=" * 62)

    metadata = load_metadata()
    metadata_by_file = {
        item.get("pdf_filename"): item
        for item in metadata
        if item.get("pdf_filename")
    }

    existing_files: set[str] = set()
    existing_numbers: set[str] = set()
    for name in os.listdir(DATASET_DIR):
        if not name.lower().endswith(".pdf"):
            continue
        path = os.path.join(DATASET_DIR, name)
        if not is_court_pdf(path):
            continue
        existing_files.add(name)
        item = metadata_by_file.get(name)
        if item and item.get("nomor"):
            existing_numbers.add(item["nomor"])

    total_saved = len(existing_files)
    print(f"[INFO] PDF valid yang sudah ada: {total_saved}/{TARGET_TOTAL}")

    if total_saved >= TARGET_TOTAL:
        print("[DONE] Target sudah terpenuhi.")
        return

    seen_urls = {
        item.get("url") for item in metadata if item.get("pdf_filename") in existing_files
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Buka halaman utama dulu agar cookie/clearance situs aktif.
        try:
            page.goto(f"{BASE_URL}/direktori.html", wait_until="domcontentloaded", timeout=60000)
        except PlaywrightError as error:
            print(f"[WARN] Gagal membuka halaman utama: {error}")
        time.sleep(2)
        print("[INFO] Browser siap.")

        try:
            stop_all = False
            for year in YEARS:
                if stop_all or total_saved >= TARGET_TOTAL:
                    break
                print(f"\n[INFO] ============== Tahun {year} ==============")

                for page_num in range(1, MAX_PAGES + 1):
                    if stop_all or total_saved >= TARGET_TOTAL:
                        break

                    url = list_url(year, page_num)
                    listing = fetch_text(page, url, label=f"list {year} p{page_num}")
                    if listing is None:
                        print(f"[STOP] Daftar {year} halaman {page_num} tidak dapat diakses.")
                        stop_all = True
                        break

                    links = decision_links_from_html(listing["text"])
                    print(f"[INFO] {year} p{page_num}: {len(links)} putusan ditemukan.")
                    if not links:
                        break

                    for index, detail_url in enumerate(links, start=1):
                        if total_saved >= TARGET_TOTAL:
                            break
                        if detail_url in seen_urls:
                            continue
                        seen_urls.add(detail_url)

                        detail = fetch_text(
                            page, detail_url,
                            label=f"detail {year} p{page_num} #{index}",
                        )
                        if detail is None:
                            continue

                        soup = BeautifulSoup(detail["text"], "html.parser")
                        meta = extract_metadata(soup)
                        meta["url"] = detail_url

                        nomor = meta.get("nomor", "")
                        if not nomor:
                            print(f"[SKIP] Nomor putusan tidak ditemukan: {detail_url}")
                            continue
                        if meta["status_bht"]:
                            print(f"[SKIP] Sudah BHT: {nomor}")
                            continue
                        if "JKT.SEL" not in nomor.upper() and "JAKARTA SELATAN" not in meta["lembaga"].upper():
                            print(f"[SKIP] Bukan PN Jakarta Selatan: {nomor}")
                            continue
                        if nomor in existing_numbers:
                            print(f"[SKIP] Sudah dimiliki: {nomor}")
                            continue

                        pdf_url = find_pdf_url(soup)
                        if not pdf_url:
                            print(f"[SKIP] Tidak ada lampiran PDF: {nomor}")
                            sleep_polite()
                            continue

                        filename = f"{clean_filename(nomor)}.pdf"
                        dest_file = os.path.join(DATASET_DIR, filename)
                        if filename in existing_files or os.path.exists(dest_file):
                            print(f"[SKIP] Berkas sudah ada: {filename}")
                            existing_numbers.add(nomor)
                            sleep_polite()
                            continue

                        print(f"[GET ] {nomor} ...", flush=True)
                        payload = fetch_pdf_bytes(page, pdf_url)
                        if payload is None:
                            print(f"[SKIP] Gagal mengunduh PDF: {nomor}")
                            sleep_polite()
                            continue

                        temp_file = dest_file + ".part"
                        with open(temp_file, "wb") as handle:
                            handle.write(payload)

                        if not is_court_pdf(temp_file, nomor):
                            os.remove(temp_file)
                            print(f"[SKIP] Bukan PDF putusan yang valid: {nomor}")
                            sleep_polite()
                            continue

                        os.replace(temp_file, dest_file)
                        total_saved += 1
                        existing_files.add(filename)
                        existing_numbers.add(nomor)

                        meta["pdf_path"] = dest_file
                        meta["pdf_filename"] = filename
                        meta["pdf_size"] = len(payload)

                        record_index = next(
                            (i for i, item in enumerate(metadata)
                             if item.get("pdf_filename") == filename),
                            None,
                        )
                        if record_index is None:
                            metadata.append(meta)
                        else:
                            metadata[record_index] = meta
                        save_metadata(metadata)

                        print(
                            f"[OK  ] [{total_saved}/{TARGET_TOTAL}] {filename} "
                            f"({len(payload)} bytes)",
                            flush=True,
                        )
                        sleep_polite()

                    sleep_polite(1.5, 3.0)
        finally:
            context.close()

    print("\n" + "=" * 62)
    if total_saved >= TARGET_TOTAL:
        print(f"[DONE] {total_saved}/{TARGET_TOTAL} PDF putusan tersimpan di Dataset/.")
    else:
        print(f"[INCOMPLETE] {total_saved}/{TARGET_TOTAL} PDF tersimpan. "
              "Jalankan ulang untuk melanjutkan.")
    print("=" * 62)
    if total_saved < TARGET_TOTAL:
        sys.exit(1)


if __name__ == "__main__":
    main()
