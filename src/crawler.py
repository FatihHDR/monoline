"""Modul akuisisi (crawler & scraper) putusan Pidana Khusus Narkotika.

Sumber: Direktori Putusan Mahkamah Agung Republik Indonesia
        https://putusan3.mahkamahagung.go.id

Modul ini menyediakan tiga tahap terpisah agar mudah diuji dan dipakai ulang
dari notebook maupun CLI:

1. ``fetch_decision_links``  -> kumpulkan tautan halaman detail putusan
2. ``fetch_pdf_url``         -> temukan tautan unduhan PDF dari halaman detail
3. ``download_pdf``          -> unduh berkas PDF ke disk

Semua permintaan memakai jeda (delay) untuk menghormati beban server.
"""

from __future__ import annotations

import argparse
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://putusan3.mahkamahagung.go.id"
SEARCH_URL = f"{BASE_URL}/direktori/kategori/narkotika-dan-psikotropika.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

DEFAULT_DELAY = 1.0
DEFAULT_TIMEOUT = 30


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_decision_links(
    pn_keyword: str,
    max_results: int = 50,
    delay: float = DEFAULT_DELAY,
    session: requests.Session | None = None,
) -> list[str]:
    """Mengambil tautan halaman detail putusan berdasarkan kata kunci PN.

    Mengembalikan daftar URL absolut halaman detail (uniquely deduplicated).
    """
    session = session or _build_session()
    links: list[str] = []
    seen: set[str] = set()
    page = 1

    while len(links) < max_results:
        url = f"{SEARCH_URL}?q={pn_keyword}&page={page}"
        response = session.get(url, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.content, "html.parser")
        page_links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "/direktori/putusan/" not in href:
                continue
            absolute = urljoin(BASE_URL, href)
            if absolute not in seen:
                seen.add(absolute)
                page_links.append(absolute)

        if not page_links:
            break

        links.extend(page_links)
        page += 1
        time.sleep(delay)  # Ethical delay / penghormatan beban server

    return links[:max_results]


def fetch_pdf_url(
    detail_url: str, session: requests.Session | None = None
) -> str | None:
    """Menemukan URL unduhan PDF dari halaman detail putusan."""
    session = session or _build_session()
    response = session.get(detail_url, timeout=DEFAULT_TIMEOUT)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if ".pdf" in href.lower():
            return urljoin(BASE_URL, href)

    for iframe in soup.find_all(["iframe", "embed", "object"]):
        src = iframe.get("src") or iframe.get("data")
        if src and ".pdf" in src.lower():
            return urljoin(BASE_URL, src)

    return None


def download_pdf(
    pdf_url: str,
    save_path: str,
    session: requests.Session | None = None,
) -> bool:
    """Mengunduh berkas PDF putusan. Mengembalikan ``True`` bila berhasil."""
    session = session or _build_session()
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    response = session.get(pdf_url, stream=True, timeout=DEFAULT_TIMEOUT)
    if response.status_code != 200:
        return False

    with open(save_path, "wb") as handle:
        for chunk in response.iter_content(1024):
            handle.write(chunk)
    return True


def crawl(
    pn_keyword: str,
    out_dir: str,
    max_results: int = 50,
    delay: float = DEFAULT_DELAY,
) -> list[str]:
    """Pipeline lengkap: ambil tautan -> temukan PDF -> unduh."""
    session = _build_session()
    os.makedirs(out_dir, exist_ok=True)

    downloaded: list[str] = []
    detail_links = fetch_decision_links(
        pn_keyword, max_results=max_results, delay=delay, session=session
    )

    for index, detail_url in enumerate(detail_links, start=1):
        pdf_url = fetch_pdf_url(detail_url, session=session)
        if not pdf_url:
            print(f"[{index}] PDF tidak ditemukan: {detail_url}")
            continue

        filename = os.path.basename(pdf_url.split("?")[0]) or f"putusan_{index}.pdf"
        save_path = os.path.join(out_dir, filename)
        if download_pdf(pdf_url, save_path, session=session):
            downloaded.append(save_path)
            print(f"[{index}] Tersimpan: {save_path}")
        else:
            print(f"[{index}] Gagal mengunduh: {pdf_url}")

        time.sleep(delay)

    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawler putusan narkotika MA RI")
    parser.add_argument("--pn", required=True, help="Kata kunci Pengadilan Negeri")
    parser.add_argument("--out", default="Dataset", help="Direktori keluaran PDF")
    parser.add_argument("--max", type=int, default=50, help="Jumlah maksimum putusan")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Jeda detik")
    args = parser.parse_args()

    results = crawl(args.pn, args.out, max_results=args.max, delay=args.delay)
    print(f"\nSelesai. {len(results)} berkas PDF terunduh ke '{args.out}'.")


if __name__ == "__main__":
    main()
