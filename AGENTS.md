# AGENTS.md — Konstitusi Proyek & Peta Navigasi Konteks

**Identitas & Batasan Produk:**  
Aplikasi Desktop Analisis Event Log BPIC17 (*standalone*, 100% *offline*, biaya operasional Rp 0) berbasis Python, PM4Py, Pandas, dan PySide6. Aplikasi ini memuat file `.xes`/`.xes.gz` ke dalam memori sekali saat impor, mengevaluasi delapan soal analitik wajib Bab 11 (Exercise 11.7 A–E, 11.15, 11.18, 11.22), menyediakan bukti jejak kasus (*case evidence*) yang dapat diaudit di *Case Explorer*, dan mengekspor hasil ke CSV.  
**Out of Scope:** Tidak mencakup *Process Discovery* (Alpha/Heuristics/Inductive Miner, Petri net), tidak menggunakan database server atau cloud API, serta menunda fitur opsional Tahap 12 (*fast/slow cases*, *generic filter builder*, visualisasi DFG, ekspor PDF) hingga fitur wajib F01–F07 dan *unit test* lulus 100%.

---

## 1. Hukum Invarian Sistem (*System Invariants*)

Aturan berikut bersifat mutlak dan tidak boleh dilanggar di lapisan kode mana pun:

1. **Zero Hard-Coding & Reproduktibilitas:** Seluruh angka jawaban (jumlah *case*, rata-rata *cycle time*, persentase, daftar *case*) wajib dihitung dinamis dari dataset aktif di memori. Setiap output wajib menyertakan aturan filter, satuan waktu (`hari`), dan denominator eksplisit ($\text{Persentase} = \frac{\text{Matched Cases}}{\text{Total Active Cases}} \times 100\%$).
2. **Zero Code/Notebook Interaction & Thread Safety:** Seluruh alur kerja pengguna (impor, analisis, *drill-down* bukti, ekspor CSV) dijalankan murni dari GUI. Seluruh pembacaan file XES dan komputasi analitik berat **dilarang** dijalankan di *Main GUI Thread* (wajib melalui `QThread` dengan *mutex/cancel guard*).
3. **Single-Parse In-Memory & Integritas *Cycle Time*:** File `.xes`/`.xes.gz` hanya di-*parse* **satu kali** saat impor untuk membentuk `RawEventLogTable` dan `CaseSummaryTable` (*pre-computed*). Durasi kasus (`cycle_time_days`) wajib dihitung dari selisih *timestamp* akhir dan awal pada ***trace* utuh** sebelum filter soal apa pun diterapkan.
4. **Determinisme Urutan *Event* (`_orig_idx`):** Kolom indeks baris asli dari file XES wajib bernama kanonik `_orig_idx` (`int64`). Pengurutan *event* dalam satu *trace* wajib memakai *stable sort* (`kind="mergesort"`) berdasarkan `(time:timestamp, _orig_idx)` setelah normalisasi waktu ke `datetime64[ns, UTC]`.
5. **Konsistensi Level *Case* & Non-Eksklusivitas (11.7):** Satu *case* hanya dihitung maksimal **1 kali** dalam agregasi soal meskipun *event* pemicu muncul berulang kali. Kategori 11.7 C (`contains` `O_Accepted`) dan 11.7 D (`contains` `O_Refused`) dievaluasi secara independen (satu *case* sah masuk keduanya), sedangkan 11.7 E mengevaluasi aktivitas paling akhir (`last_activity == "O_Cancelled"`).
6. **Semantik *Lifecycle* & *Resource* Ketat (11.15 & 11.18):** Hanya aktivitas `W_Assess Potential Fraud` dengan `lifecycle:transition` bernilai `"complete"` (setelah normalisasi `.str.strip().str.lower()`) yang dihitung. Status lain (`schedule`, `start`, `suspend`, `resume`, `ate_abort`, `withdraw`) wajib diabaikan. Untuk 11.18, nilai `org:resource` kosong (`NaN`, `None`, `""`, atau spasi) wajib dibuang sebelum pengelompokan agar *missing resource* tidak pernah dianggap sebagai satu *resource* yang sama.
7. **Semantik *Eventually Follows* Level *Case* (11.22):** Pola `O_Cancelled` diikuti `O_Accepted` dievaluasi pada level *case/trace* (tidak dicampur dengan level `OfferID`) berdasarkan posisi indeks urutan $i < j$ dalam satu *trace* yang telah terurut deterministik (tidak harus bersebelahan dan tidak harus berakhir di `O_Cancelled`).

---

## 2. Tech Stack & Struktur Direktori

* **Runtime & Core:** Python 3.10 / 3.11 (`venv`), `pm4py`, `pandas`, `numpy`, `csv`.
* **Desktop GUI:** `PySide6` (Qt Model/View `QTableView` + `QAbstractTableModel`, konkurensi `QThread`).
* **Testing & Quality:** `pytest`, `mypy`, `ruff`.

```text
bpic17-analyzer/
├── AGENTS.md                        # [TIER 1] Konstitusi & peta konteks agen
├── BACKLOG.md                       # [TIER 3] Pelacak tahapan (Stages) & milestone
├── requirements.txt
├── main.py                          # Entry point aplikasi GUI desktop
├── main_cli.py                      # Skrip CLI untuk verifikasi cepat vs Fluxicon Disco
├── docs/                            # [TIER 2] Konteks modular (Selective Loading)
│   ├── ARCHITECTURE.md              # Topologi layer, QThread state machine, & isolasi
│   ├── DESIGN_SYSTEM.md             # Ergonomi UI/UX, wireframe, & visual states
│   └── specs/
│       ├── 01-data-schema-and-loader.md
│       ├── 02-core-analytics-engine.md
│       ├── 03-case-explorer-and-csv-export.md
│       └── 04-contracts-models-and-errors.md
├── core/                            # [TIER 3] Pure Python domain engine (Zero PySide6 import!)
│   ├── __init__.py
│   ├── models.py                    # Single Source of Truth kontrak dataclass & kode error
│   ├── loader.py                    # F01: Parsing XES/XES.GZ via PM4Py & normalisasi
│   ├── metrics.py                   # F02: Pre-kalkulasi CaseSummaryTable & LogOverview
│   ├── analyzers.py                 # F03–F06: Logika 11.7 (A-E), 11.15, 11.18, 11.22
│   └── exporter.py                  # F07: Ekspor CSV ringkasan & daftar case
├── ui/                              # [TIER 3] Lapisan presentasi PySide6
│   ├── __init__.py
│   ├── main_window.py
│   ├── workers.py
│   ├── table_models.py
│   └── pages/
│       ├── overview_page.py
│       ├── ex11_7_page.py
│       ├── ex11_15_18_page.py
│       ├── ex11_22_page.py
│       └── case_explorer_page.py
└── tests/
    ├── conftest.py                  # Generator log sintetis (DataFrame & .xes)
    └── test_analyzers.py            # Unit test wajib 8+ skenario edge case
```

---

## 3. Peta Navigasi Konteks (*Context Routing Map*)

> **INSTRUKSI TEGAS UNTUK AI AGENT:** Jangan pernah memuat seluruh file di dalam `docs/` sekaligus! Pilih **hanya** dokumen yang relevan dengan *milestone* aktif di `BACKLOG.md`:

* **Memulai sesi kerja atau memilih tugas berikutnya** $\rightarrow$ Baca `BACKLOG.md`.
* **Merancang/mengubah struktur *thread*, *worker*, *state* aplikasi, atau batas modul** $\rightarrow$ Baca `docs/ARCHITECTURE.md`.
* **Membangun jendela GUI, tabel, *badge*, warna *highlight*, atau interaksi halaman** $\rightarrow$ Baca `docs/DESIGN_SYSTEM.md`.
* **Mengerjakan parsing XES (`core/loader.py`) atau agregasi dasar (`core/metrics.py`)** $\rightarrow$ Baca `docs/specs/01-data-schema-and-loader.md`.
* **Mengerjakan algoritma soal Bab 11 (`core/analyzers.py`) atau `tests/test_analyzers.py`** $\rightarrow$ Baca `docs/specs/02-core-analytics-engine.md`.
* **Mengerjakan *drill-down* Case Explorer, *re-run/reset*, atau ekspor CSV (`core/exporter.py`)** $\rightarrow$ Baca `docs/specs/03-case-explorer-and-csv-export.md`.
* **Mengerjakan `core/models.py`, sinyal `QThread`, skema validasi, atau penanganan error** $\rightarrow$ Baca `docs/specs/04-contracts-models-and-errors.md`.
* **Aturan *Code-as-Docs*:** Setelah `core/models.py` selesai dibuat dan lulus *test* di Stage 1, jadikan `core/models.py` sebagai *Single Source of Truth* untuk struktur data dan tipe kontrak.

---

## 4. Perintah Verifikasi Mandiri (*Self-Verification Commands*)

Jalankan perintah berikut di terminal sebelum menandai *milestone* sebagai `[x]` di `BACKLOG.md`:

```bash
pytest -v                        # Menjalankan seluruh unit test & skenario edge case
python -m mypy core ui           # Pemeriksaan static typing ketat
python -m ruff check core ui tests  # Pemeriksaan linter & standar kode
```

---

## 5. Daftar Larangan Keras (*Do's & Don'ts*)

* **DILARANG** mengimpor `PySide6` di dalam folder `core/` (`core/` harus 100% dapat dijalankan oleh `pytest` dan `main_cli.py` secara *headless*).
* **DILARANG** menggunakan `QTableWidget` untuk tabel daftar *case* atau *event* (wajib gunakan `QTableView` + `QAbstractTableModel` agar tabel $>30{.}000$ baris tidak membekukan UI).
* **DILARANG** memodifikasi ` pandas.DataFrame` (`RawEventLogTable` / `CaseSummaryTable`) secara *in-place* dari beberapa thread; perlakukan *cache* DataFrame sebagai *read-only* setelah impor selesai.
* **DILARANG** menghitung `cycle_time_days` setelah memfilter baris *event* pada sebuah *trace*; selalu ambil `cycle_time_days` dari `CaseSummaryTable` yang dihitung dari *trace* utuh.
* **DILARANG** memanggil `pm4py.read_xes()` ulang ketika pengguna berpindah tab atau menekan tombol **Run Analysis** / **Reset / Re-run All**.
