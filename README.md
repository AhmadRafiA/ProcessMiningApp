# BPIC17 Event Log Analyzer

Aplikasi desktop analitis dan utilitas CLI (*100% standalone & offline*, biaya operasional Rp 0) berbasis Python, PM4Py, Pandas, dan PySide6 untuk memproses dan mengevaluasi seluruh soal analitik wajib **Bab 11** (*Exercise 11.7 A–E, 11.15, 11.18, 11.22*) pada dataset **BPI Challenge 2017 (BPIC17)**.

Dilengkapi dengan **Case Explorer** untuk audit jejak kasus secara kronologis dengan penyorotan bukti visual (*evidence highlight*), mekanisme **Reset / Re-run All** di memori tanpa pembacaan ulang disk, ekspor CSV atomik, serta **CLI Verification Tool** untuk pencocokan cepat terhadap hasil *Fluxicon Disco*.

---

## 1. Fitur Utama & Keunggulan

* **Zero Hard-Coding & Reproduktibilitas 100%:** Seluruh angka hasil, durasi rata-rata kasus (*cycle time*), persentase, dan daftar kasus dihitung dinamis dari dataset aktif di memori dengan aturan filter dan denominator eksplisit.
* **Strict Two-Layer Architecture:**
  * `core/`: Mesin analitik murni berbasis Python (`pm4py`, `pandas`, `numpy`) tanpa dependensi GUI (`Zero PySide6 imports!`), dapat dijalankan secara *headless* via CLI dan `pytest`.
  * `ui/`: Lapisan antarmuka desktop PySide6 dengan model tabel tervirtualisasi (`QTableView` + `QAbstractTableModel`) yang lancar merender $>30.000$ baris pada $\sim 60\text{ FPS}$ tanpa membekukan UI.
* **Non-Blocking UI & Concurrency Guard:** Seluruh proses parsing XES berat dan komputasi analitik dijalankan di latar belakang via `QThread` dengan *single active worker mutex*, laporan progres bertahap, dan penanganan penutupan jendela aplikasi yang anggun.
* **Audit Bukti 1-Klik (*1-Click Evidence Drill-Down*):** Klik ganda pada baris kasus di halaman analitik langsung membuka kasus tersebut di **Case Explorer**, menyorot baris *event* bukti audit dengan latar kuning lembut (`#FEF08A`) dan badge `[EVIDENCE]`, serta melakukan *auto-scroll* ke bukti pertama.
* **Single-Parse In-Memory & Reset Cepat:** File `.xes` / `.xes.gz` hanya dibaca satu kali saat impor. Aksi **Reset / Re-run All** menghitung ulang seluruh soal langsung dari RAM tanpa menyentuh disk.
* **Ekspor CSV Atomik & Privasi Data:** Penulisan CSV ringkasan (`summary_results.csv`) dan daftar kasus (`cases_<exercise_code>.csv`) dilakukan secara atomik melalui file sementara (`.tmp` $\rightarrow$ `os.replace`), dengan encoding UTF-8 with BOM (`utf-8-sig`) dan pembersihan path lokal komputer pengguna (*privacy sanitization*).

---

## 2. Persyaratan Sistem & Instalasi

### Persyaratan
* Python 3.10, 3.11, atau 3.12 (64-bit)
* RAM minimum: 4 GB (disarankan 8 GB untuk memuat dataset BPIC17 $\sim 1{,}2$ juta *event*)
* Sistem Operasi: macOS, Linux, atau Windows

### Langkah Instalasi

1. **Clone atau buka repositori:**
   ```bash
   cd /path/to/bpic17-analyzer
   ```

2. **Buat dan aktifkan virtual environment:**
   * Di macOS / Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   * Di Windows (Command Prompt / PowerShell):
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. **Install dependensi:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. Cara Menjalankan Aplikasi Desktop (GUI)

Jalankan perintah berikut dari terminal:

```bash
python main.py
```

### Panduan Alur Kerja GUI:
1. **Import XES:** Klik tombol biru **Import XES** di header atas dan pilih file log (misalnya `BPI_Challenge_2017.xes.gz` atau `BPI_Challenge_2017.xes`).
2. **Tab Overview:** Tinjau statistika dasar log (Total Cases, Total Events, Rentang Waktu UTC, Mean Cycle Time, Atribut Terdeteksi), distribusi frekuensi aktivitas, dan tabel seluruh kasus lengkap dengan pencarian real-time `case_id`.
3. **Run Analysis:** Klik tombol hijau **Run Analysis** di header atas untuk menghitung seluruh soal Bab 11.
4. **Tinjau Halaman Analisis:**
   * **Exercise 11.7 (A–E):** Klik kartu C, D, atau E untuk mengganti daftar kasus yang ditampilkan di tabel bawah.
   * **Exercise 11.15 & 11.18:** Tinjau panel pengulangan fraud assessment dan pengulangan oleh resource yang sama.
   * **Exercise 11.22:** Tinjau proporsi kasus dengan pola *Eventually Follows* (`O_Cancelled` $\rightarrow$ `O_Accepted`).
5. **Drill-down ke Case Explorer:** Klik ganda baris mana saja pada tabel kasus (atau tekan **Lihat Rincian Case**) untuk menelusuri seluruh *event* kronologis kasus tersebut beserta sorotan baris buktinya.
6. **Ekspor CSV:**
   * Klik **Export Summary CSV** di header atas untuk mengekspor 8 baris jawaban kanonik ke `summary_results.csv`.
   * Klik tombol **Export CSV** di masing-masing halaman soal untuk mengekspor daftar kasus beserta kolom `evidence_orig_indices`.
7. **Reset / Re-run All:** Tekan tombol **Reset / Re-run All** kapan saja untuk menghitung ulang seluruh soal di RAM tanpa membaca ulang file dari disk.

---

## 4. Cara Menjalankan CLI Verification Tool (Disco Benchmark)

Untuk keperluan verifikasi cepat, benchmarking headless, atau pencocokan hasil terhadap *Fluxicon Disco*, gunakan utilitas CLI `main_cli.py`:

```bash
# Menjalankan verifikasi analitis lengkap terhadap file XES
python main_cli.py /path/to/BPI_Challenge_2017.xes.gz

# Menampilkan 10 sampel Case ID per soal untuk dicocokkan di Disco
python main_cli.py /path/to/BPI_Challenge_2017.xes.gz --samples 10

# Mengeksekusi analisis sekaligus mengekspor seluruh CSV ke folder output
python main_cli.py /path/to/BPI_Challenge_2017.xes.gz --export-dir ./exports

# Melihat opsi bantuan CLI
python main_cli.py --help
```

Output CLI mencakup:
* Log Overview & Frekuensi Aktivitas Teratas.
* Tabel Ringkasan Jawaban 8 Soal Bab 11 (Matched Cases, Denominator, Persentase, Mean Cycle Time).
* Sampel Case ID per soal (lengkap dengan metrik durasi dan event) untuk verifikasi silang cepat pada filter *Fluxicon Disco*.

---

## 5. Menjalankan Pengujian Otomatis & Verifikasi Mutu

Proyek ini menerapkan standar mutu ketat dengan 100% test passing dan static analysis tanpa celah:

```bash
# 1. Menjalankan seluruh unit & integration test (58 test)
pytest -v

# 2. Pemeriksaan tipe data statis ketat (Strict Mypy)
python -m mypy core ui tests

# 3. Pemeriksaan standar kode dan linter (Ruff)
python -m ruff check core ui tests
```

---

## 6. Struktur Direktori Proyek

```text
bpic17-analyzer/
├── AGENTS.md                        # Konstitusi proyek & hukum invarian sistem
├── BACKLOG.md                       # Pelacak milestone dan tahapan pengerjaan
├── README.md                        # Dokumentasi teknis & panduan penggunaan
├── requirements.txt                 # Daftar dependensi Python
├── pyproject.toml                   # Konfigurasi pytest, ruff, dan mypy
├── main.py                          # Entry point aplikasi GUI desktop (PySide6)
├── main_cli.py                      # Utilitas CLI headless untuk verifikasi Disco
├── core/                            # Pure Domain Engine (Zero PySide6 imports!)
│   ├── __init__.py
│   ├── models.py                    # Kontrak data (LoadedDataset, AnalysisResult, error codes)
│   ├── loader.py                    # F01: Pembacaan XES/XES.GZ via PM4Py, normalisasi UTC & _orig_idx
│   ├── metrics.py                   # F02: Pre-komputasi CaseSummaryTable & frekuensi aktivitas
│   ├── analyzers.py                 # F03–F06: Mesin kalkulasi soal 11.7, 11.15, 11.18, 11.22 & trace
│   └── exporter.py                  # F07: Ekspor CSV atomik (.tmp -> os.replace) & sanitasi path
├── ui/                              # Lapisan Antarmuka & Konkurensi PySide6
│   ├── __init__.py
│   ├── main_window.py               # MainWindow, Header, Sidebar, Status Bar, State Machine, About
│   ├── workers.py                   # ImportWorker & AnalysisWorker berbasis QThread
│   ├── table_models.py              # PandasTableModel (QAbstractTableModel virtualized)
│   └── pages/
│       ├── __init__.py
│       ├── overview_page.py         # Halaman 1: Ringkasan log, kartu KPI & tabel eksplorasi
│       ├── ex11_7_page.py           # Halaman 2: Exercise 11.7 (A–E) & seleksi kartu C/D/E
│       ├── ex11_15_18_page.py       # Halaman 3: Exercise 11.15 & 11.18 (Panel ganda)
│       ├── ex11_22_page.py          # Halaman 4: Exercise 11.22 (Eventually Follows)
│       └── case_explorer_page.py    # Halaman 5: Case Explorer & bukti jejak [EVIDENCE]
├── docs/                            # Dokumentasi Arsitektur & Spesifikasi Detail
│   ├── ARCHITECTURE.md              # Topologi sistem, state machine, konkurensi QThread
│   ├── DESIGN_SYSTEM.md             # Ergonomi UI, wireframe, palet warna, component states
│   └── specs/
│       ├── 01-data-schema-and-loader.md
│       ├── 02-core-analytics-engine.md
│       ├── 03-case-explorer-and-csv-export.md
│       └── 04-contracts-models-and-errors.md
└── tests/                           # Suite Pengujian Otomatis (58 Tests)
    ├── conftest.py                  # Generator log sintetis & fixture canonical scenarios T-01..T-10
    ├── test_stage1_loader_metrics.py# Pengujian loader XES, normalisasi waktu, dan metrics
    ├── test_analyzers.py            # Pengujian aturan bisnis 11.7, 11.15, 11.18, 11.22
    ├── test_stage3_ui.py            # Pengujian model tabel, worker thread, UI pages, dan main window
    ├── test_stage4_exporter.py      # Pengujian ekspor CSV atomik, penanganan error, tombol GUI
    └── test_stage5_cli.py           # Pengujian utilitas CLI, format tabel, argumen, dan exit code
```

---

## 7. Prinsip Invarian Sistem (*System Invariants*)

1. **Zero Hard-Coding:** Angka jawaban tidak pernah di-*hardcode*; seluruh hasil dihitung murni dari dataset aktif di RAM.
2. **Determinisme Urutan (`_orig_idx`):** Urutan *event* dalam satu *trace* diurutkan menggunakan *stable sort* (`mergesort`) berdasarkan `(time:timestamp, _orig_idx)` untuk menjamin hasil 100% konsisten lintas-platform.
3. **Integritas Cycle Time:** Durasi kasus (`cycle_time_days`) selalu dihitung dari selisih *timestamp* akhir dan awal pada ***trace* utuh** sebelum filter soal diterapkan.
4. **Semantik Non-Eksklusif (11.7):** Kategori 11.7 C (`contains` `O_Accepted`) dan 11.7 D (`contains` `O_Refused`) dievaluasi secara independen (satu kasus dapat masuk keduanya).
5. **Semantik Lifecycle Ketat (11.15 & 11.18):** Hanya aktivitas `W_Assess Potential Fraud` dengan `lifecycle:transition == "complete"` (dinormalisasi *lowercase*) yang dihitung. Untuk 11.18, nilai `org:resource` kosong dieliminasi dan tidak dianggap sebagai satu resource yang sama.
6. **Eventually Follows (11.22):** Pola `O_Cancelled` diikuti `O_Accepted` dievaluasi pada level *trace* terurut deterministik berdasarkan indeks $i < j$.
