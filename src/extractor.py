"""Modul ekstraksi metadata & amar putusan dari teks PDF putusan.

Alur:
    PDF -> teks (pdfplumber) -> field terstruktur (Regex) -> DataFrame/CSV

Field yang diekstrak:
    No Putusan, Lembaga Peradilan, Barang Bukti, Amar Putusan
"""

from __future__ import annotations

import argparse
import glob
import os
import re

import pandas as pd
import pdfplumber

DEFAULT_OUTPUT = "data/extracted_decisions.csv"

COLUMNS = ["No Putusan", "Lembaga Peradilan", "Barang Bukti", "Amar Putusan"]


def extract_text_from_pdf(pdf_path: str) -> str:
    """Membaca seluruh teks dari file PDF putusan."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text


def parse_decision_details(text: str) -> dict:
    """Mengekstrak bidang-bidang kunci dari teks putusan menggunakan Regex."""
    no_putusan_match = re.search(r"PUTUSAN\s+Nomor\s+([^\n]+)", text, re.IGNORECASE)
    no_putusan = no_putusan_match.group(1).strip() if no_putusan_match else "N/A"

    pn_match = re.search(r"(PENGADILAN\s+NEGERI[ \t]+[A-Z][A-Z \t]*)", text)
    lembaga = pn_match.group(1).strip() if pn_match else "Pengadilan Negeri"

    bb_match = re.search(
        r"Menetapkan barang bukti berupa:\s*([\s\S]*?)"
        r"(?=Dirampas|Dikembalikan|Membebankan|$)",
        text,
        re.IGNORECASE,
    )
    barang_bukti = bb_match.group(1).strip() if bb_match else "N/A"

    amar_match = re.search(
        r"M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I\s*:?([\s\S]*?)"
        r"(?=Demikianlah diputuskan|$)",
        text,
        re.IGNORECASE,
    )
    amar_putusan = amar_match.group(1).strip() if amar_match else "N/A"

    return {
        "No Putusan": no_putusan,
        "Lembaga Peradilan": lembaga,
        "Barang Bukti": barang_bukti,
        "Amar Putusan": amar_putusan,
    }


def extract_folder(pdf_dir: str) -> pd.DataFrame:
    """Mengekstrak seluruh PDF dalam sebuah direktori menjadi DataFrame."""
    rows = []
    for pdf_path in sorted(glob.glob(os.path.join(pdf_dir, "*.pdf"))):
        try:
            text = extract_text_from_pdf(pdf_path)
            row = parse_decision_details(text)
            row["File"] = os.path.basename(pdf_path)
            rows.append(row)
        except Exception as exc:  # noqa: BLE001 - lanjutkan ke berkas berikutnya
            print(f"Gagal memproses {pdf_path}: {exc}")

    frame = pd.DataFrame(rows, columns=["File", *COLUMNS])
    return frame


def save_csv(frame: pd.DataFrame, output_path: str = DEFAULT_OUTPUT) -> str:
    """Menyimpan DataFrame hasil ekstraksi ke berkas CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ekstraktor putusan narkotika")
    parser.add_argument("--dir", default="Dataset", help="Direktori berkas PDF")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="Berkas CSV keluaran")
    args = parser.parse_args()

    frame = extract_folder(args.dir)
    path = save_csv(frame, args.out)
    print(f"Selesai. {len(frame)} putusan diekstrak ke '{path}'.")


if __name__ == "__main__":
    main()
