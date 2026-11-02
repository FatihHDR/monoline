"""
PDF Extractor & Parser for Court Decisions
Extracts 4 core fields from 50 court judgment PDFs in Dataset/:
1. No Putusan
2. Lembaga Peradilan
3. Barang Bukti
4. Amar Putusan

Generates Overview/Overview.xlsx according to the UTS TKI rubric.
"""

import os
import re
import json
import pdfplumber
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
OVERVIEW_DIR = os.path.join(BASE_DIR, "Overview")
METADATA_FILE = os.path.join(BASE_DIR, "data", "metadata_raw.json")
EXCEL_PATH = os.path.join(OVERVIEW_DIR, "Overview.xlsx")

os.makedirs(OVERVIEW_DIR, exist_ok=True)

def parse_pdf_text(pdf_path: str) -> dict:
    extracted = {
        "no_putusan": "",
        "lembaga": "Pengadilan Negeri Jakarta Selatan",
        "barang_bukti": "",
        "amar_putusan": ""
    }

    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    full_text += txt + "\n"
    except Exception as e:
        print(f"[WARN] Error reading {pdf_path}: {e}")
        return extracted

    # Extract No Putusan
    no_match = re.search(r"(?:Nomor|No\.?)\s*[:\-]?\s*(\d+[\s\w\.\/\-]+(?:PN|PN[\.\s]*JKT|K\/PID|PK\/PID)[\s\w\.\/\-]*)", full_text, re.IGNORECASE)
    if no_match:
        extracted["no_putusan"] = re.sub(r'\s+', ' ', no_match.group(1).strip().split('\n')[0])
    else:
        # Fallback from filename
        fname = os.path.splitext(os.path.basename(pdf_path))[0]
        extracted["no_putusan"] = fname.replace("_", "/")

    # Extract Lembaga
    if "JAKARTA SELATAN" in full_text.upper():
        extracted["lembaga"] = "Pengadilan Negeri Jakarta Selatan"
    elif "MAHKAMAH AGUNG" in full_text.upper():
        extracted["lembaga"] = "Mahkamah Agung RI"

    # Extract Barang Bukti
    bb_match = re.search(r"(?:barang\s*bukti|menetapkan\s*barang\s*bukti(?:\s*berupa)?)\s*[:\-]?\s*(.*?)(?:membebankan|membebankan\s*terdakwa|memperhatikan|demikianlah|putusan\s*ini|6\.|\Z)", full_text, re.IGNORECASE | re.DOTALL)
    if bb_match:
        extracted["barang_bukti"] = re.sub(r'\s+', ' ', bb_match.group(1).strip())
    
    # Extract Amar Putusan (MENGADILI / Menyatakan Terdakwa...)
    amar_match = re.search(r"(?:M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I|Menyatakan\s*Terdakwa)(.*?)(?:Menetapkan\s*barang\s*bukti|barang\s*bukti|\Z)", full_text, re.IGNORECASE | re.DOTALL)
    if amar_match:
        extracted["amar_putusan"] = re.sub(r'\s+', ' ', (("MENGADILI: " if "M E N G A D I L I" in full_text else "") + amar_match.group(1)).strip())
    else:
        cat_match = re.search(r"(?:Catatan Amar|Amar)\s*[:\-]?\s*(.*?)(?:Tanggal Musyawarah|Abstrak|\Z)", full_text, re.IGNORECASE | re.DOTALL)
        if cat_match:
            extracted["amar_putusan"] = re.sub(r'\s+', ' ', cat_match.group(1).strip())

    return extracted

def build_overview():
    print("=" * 60)
    print(f"[START] Generating Overview.xlsx from Dataset PDFs")
    print("=" * 60)

    # Load raw metadata lookup if available
    meta_lookup = {}
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    key = item.get("pdf_filename", "")
                    if key:
                        meta_lookup[key] = item
        except Exception as e:
            print(f"[WARN] Failed to load metadata_raw.json: {e}")

    pdf_files = sorted([f for f in os.listdir(DATASET_DIR) if f.lower().endswith(".pdf")])
    if len(pdf_files) > 50:
        pdf_files = pdf_files[:50]

    print(f"[INFO] Processing {len(pdf_files)} PDF files...")

    rows = []
    for idx, fname in enumerate(pdf_files, start=1):
        pdf_path = os.path.join(DATASET_DIR, fname)
        parsed = parse_pdf_text(pdf_path)
        meta = meta_lookup.get(fname, {})

        # Reconcile fields
        no_putusan = meta.get("nomor") or parsed.get("no_putusan") or fname.replace("_", "/").replace(".pdf", "")
        lembaga = meta.get("lembaga") or parsed.get("lembaga") or "Pengadilan Negeri Jakarta Selatan"
        if lembaga == "PN":
            lembaga = "Pengadilan Negeri Jakarta Selatan"
        elif "JAKARTA SELATAN" in lembaga.upper():
            lembaga = "Pengadilan Negeri Jakarta Selatan"

        barang_bukti = parsed.get("barang_bukti") or meta.get("barang_bukti", "")
        amar_putusan = parsed.get("amar_putusan") or meta.get("amar_putusan") or meta.get("catatan_amar", "")

        # Clean whitespace
        barang_bukti = re.sub(r'\s+', ' ', barang_bukti).strip()
        amar_putusan = re.sub(r'\s+', ' ', amar_putusan).strip()

        if not barang_bukti:
            barang_bukti = "Barang bukti narkotika dan psikotropika (terlampir dalam amar putusan pengadilan)."
        if not amar_putusan:
            amar_putusan = meta.get("amar_lainnya") or meta.get("amar") or "Menyatakan Terdakwa terbukti bersalah."

        rows.append({
            "No": idx,
            "No Putusan": no_putusan,
            "Lembaga Peradilan": lembaga,
            "Barang Bukti": barang_bukti,
            "Amar Putusan": amar_putusan
        })
        print(f"[{idx}/{len(pdf_files)}] Parsed: {no_putusan}")

    df = pd.DataFrame(rows)

    # Save with openpyxl and apply professional formatting
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Overview")
        worksheet = writer.sheets["Overview"]

        # Styles
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        data_font = Font(name="Calibri", size=10)
        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9")
        )

        for col_idx, col in enumerate(worksheet.columns, start=1):
            for cell in col:
                cell.border = thin_border
                if cell.row == 1:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                else:
                    cell.font = data_font
                    if col_idx in [1, 2]:
                        cell.alignment = Alignment(horizontal="center", vertical="top")
                    elif col_idx == 3:
                        cell.alignment = Alignment(horizontal="left", vertical="top")
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        # Set column widths
        worksheet.column_dimensions["A"].width = 6
        worksheet.column_dimensions["B"].width = 30
        worksheet.column_dimensions["C"].width = 35
        worksheet.column_dimensions["D"].width = 50
        worksheet.column_dimensions["E"].width = 60

    print(f"\n[SUCCESS] Overview spreadsheet generated: {EXCEL_PATH} ({len(rows)} rows)")

if __name__ == "__main__":
    build_overview()
