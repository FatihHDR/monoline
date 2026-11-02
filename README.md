# Dataset-Narkotika_XXX_YYY

Proyek Ujian Tengah Semester (UTS) **Temu Kembali Informasi (TKI)** — akuisisi,
ekstraksi, dan *preprocessing* dataset putusan **Pidana Khusus Narkotika** dari
Direktori Putusan Mahkamah Agung Republik Indonesia.

> **Nama repositori:** ganti `XXX` dan `YYY` dengan 3 digit terakhir NIM masing-masing
> anggota, mis. `Dataset-Narkotika_123_456`.

---

## Anggota Kelompok

| Nama | NIM |
| --- | --- |
| [Anggota 1] | [NIM 1] |
| [Anggota 2] | [NIM 2] |

---

## Struktur Direktori

```text
Dataset-Narkotika_XXX_YYY/
│
├── Dataset/
│   └── Narkotika.zip             # Zip berisi 50 file PDF putusan asli
│
├── Overview/
│   └── Overview.xlsx             # Spreadsheet rekap 50 putusan (Excel)
│
├── src/
│   ├── crawler.py                # Script otomasi akuisisi data dari MA
│   ├── extractor.py              # RegEx parser untuk ekstraksi metadata & amar
│   └── preprocessing.py          # Pipeline NLP (Tokenizing, Stopwords, Stemming)
│
├── notebooks/
│   ├── Task3_Web_Crawler.ipynb   # Google Colab Task 3 (Scraper & Extractor)
│   └── Task4_Preprocessing.ipynb # Google Colab Task 4 (Indexing & TF-IDF)
│
├── data/
│   └── extracted_decisions.csv   # Hasil ekstraksi terstruktur (.csv)
│
├── docs/
│   └── Task1_State_of_the_Art.md # Tabel SOTA (Tugas 1)
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Instalasi

```bash
git clone https://github.com/<username>/Dataset-Narkotika_XXX_YYY.git
cd Dataset-Narkotika_XXX_YYY

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

## Cara Menjalankan

### 1. Akuisisi data (Crawler)

Untuk mengunduh PDF putusan asli melalui Playwright dan menyimpannya langsung
ke `Dataset/`, jalankan:

```bash
python "tugas 2/download_50_pdfs.py"
```

Pengunduh hanya menghitung berkas dengan signature PDF serta teks awal putusan
pengadilan yang sesuai. Respons HTML dan halaman detail yang dicetak ke PDF
akan dilewati; hasil kurang dari 50 berarti lampiran PDF asli yang dapat diakses
belum mencukupi, bukan diganti dengan cetakan halaman. Untuk setiap putusan
yang menyediakan tautan **Download PDF**, Playwright mengeklik tautan tersebut
dan menyimpan unduhan otomatis ke `Dataset/` tanpa dialog pemilihan lokasi.
Jendela browser menampilkan daftar/putusan yang sedang diperiksa; jika sumber
mengembalikan halaman verifikasi, selesaikan verifikasi tersebut di browser
dalam batas waktu yang tersedia. Proses tidak menyelesaikan CAPTCHA secara
otomatis. Jika akses tetap dibatasi (`403` atau `429`), proses berhenti dan
dapat dilanjutkan setelah akses tersedia.

Alternatif crawler berbasis `requests` untuk pencarian berdasarkan kata kunci:

```bash
python src/crawler.py --pn "Negeri Jakarta Barat" --out Dataset --max 50
```

| Argumen | Default | Keterangan |
| --- | --- | --- |
| `--pn` | *(wajib)* | Kata kunci nama Pengadilan Negeri |
| `--out` | `Dataset` | Direktori keluaran berkas PDF |
| `--max` | `50` | Jumlah maksimum putusan |
| `--delay` | `1.0` | Jeda antar permintaan (detik) |

### 2. Ekstraksi metadata & amar putusan (RegEx)

```bash
python src/extractor.py --dir Dataset --out data/extracted_decisions.csv
```

Menghasilkan `data/extracted_decisions.csv` dengan kolom:
`File`, `No Putusan`, `Lembaga Peradilan`, `Barang Bukti`, `Amar Putusan`.

### 3. Preprocessing & indexing

```bash
python src/preprocessing.py
```

Modul ini menyediakan:
- `preprocess_text()` / `preprocess_corpus()` — cleaning, case folding, stopword removal, stemming Sastrawi
- `build_tfidf_index()` — matriks TF-IDF
- `build_inverted_index()` — inverted index `{term: {doc_id}}`

---

## Notebook Google Colab

| Notebook | Deskripsi |
| --- | --- |
| [`notebooks/Task3_Web_Crawler.ipynb`](notebooks/Task3_Web_Crawler.ipynb) | Crawling PDF + ekstraksi RegEx ke CSV |
| [`notebooks/Task4_Preprocessing.ipynb`](notebooks/Task4_Preprocessing.ipynb) | Pipeline NLP, TF-IDF, inverted index, uji query |

> Ganti `REPO_URL` di dalam notebook dengan URL repositori kelompok Anda.

---

## Tahapan Pengerjaan (Checklist)

- [ ] **Tugas 1 (SOTA):** Kumpulkan 5 jurnal Scopus/IEEE (2021–2026), isi tabel pada
      [`docs/Task1_State_of_the_Art.md`](docs/Task1_State_of_the_Art.md), ekspor PDF, unggah ke LMS.
- [ ] **Tugas 2 (Akuisisi Dataset):** Unduh 50 PDF putusan Pidana Khusus Narkotika
      (belum berkekuatan hukum tetap), susun `Overview/Overview.xlsx`, dorong ke GitHub.
- [ ] **Tugas 3 (Crawler & Extractor):** Jalankan `src/crawler.py` + `src/extractor.py`
      untuk menghasilkan `data/extracted_decisions.csv`; kumpulkan tautan Colab & Drive.
- [ ] **Tugas 4 (Preprocessing & Indexing):** Terapkan pipeline NLP pada 50 putusan,
      hitung bobot TF-IDF, pastikan notebook berjalan tanpa galat.

---

## Catatan Etika Pengambilan Data

- Crawler memakai jeda (`delay`) antar permintaan untuk menghormati beban server MA.
- Data yang diambil bersifat publik dan digunakan semata-mata untuk keperluan akademik.
- Patuhi `robots.txt` serta batas frekuensi permintaan yang wajar.
