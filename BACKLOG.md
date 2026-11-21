# BACKLOG.md — Peta Jalan Tahapan (*Stages*) & Milestone Eksekusi

**Keterangan Status Milestone:**
* `[ ]` Belum dikerjakan
* `[~]` Sedang dikerjakan
* `[x]` Selesai dan telah lulus seluruh *automated test* (`pytest -v`, `mypy`, `ruff`)

> **Aturan Eksekusi Agen:** Kerjakan *milestone* secara berurutan dari Stage 1 hingga Stage 5. Sebelum mengerjakan sebuah *milestone*, baca **hanya** file yang tercantum pada baris `Referensi:` di bawah *milestone* tersebut. Setelah `M1.2` selesai, jadikan `core/models.py` sebagai *Single Source of Truth* struktur data.

---

## Stage 1: Foundation, Contracts, & Data Schema (Pure Python & Test Setup)

Fokus: Menyiapkan struktur proyek, dependensi, kontrak tipe data murni (`core/models.py`), generator log sintetis, serta modul pemuatan XES dan pre-kalkulasi metrik dasar (`core/loader.py`, `core/metrics.py`).

* **[x] M1.1 — Inisialisasi Struktur Repositori, `requirements.txt`, & Konfigurasi Tooling**
  * Buat kerangka folder `core/`, `ui/`, `ui/pages/`, `tests/`, serta file `requirements.txt` (`pm4py`, `pandas`, `numpy`, `PySide6`, `pytest`, `mypy`, `ruff`).
  * Pastikan `pytest`, `mypy`, dan `ruff` dapat dijalankan tanpa error konfigurasi.
  * `Referensi: AGENTS.md, docs/ARCHITECTURE.md`

* **[x] M1.2 — Implementasi Kontrak Data & Hierarki Error (`core/models.py`)**
  * Implementasikan konstanta `EXERCISE_CODES`, dataclass `LogOverview`, `LoadedDataset`, `AnalysisResult`, serta hierarki exception `BPICAnalyzerError` beserta 7 sub-kelas kode error standar.
  * Pastikan `core/models.py` memiliki *type annotations* penuh dan 0 ketergantungan pada `PySide6`.
  * `Referensi: docs/specs/04-contracts-models-and-errors.md`

* **[x] M1.3 — Implementasi Parsing XES, Validasi, & Normalisasi Deterministik (`core/loader.py`)**
  * Implementasikan `load_xes_raw()` menggunakan `pm4py.read_xes()`, penyematan kolom kanonik `_orig_idx` (`int64`), validasi 3 kolom wajib, degradasi anggun untuk 2 kolom opsional (`lifecycle:transition`, `org:resource`), normalisasi `time:timestamp` ke UTC, pembersihan string *resource* kosong ke `pd.NA`, dan *stable sort* (`kind="mergesort"`) berdasarkan `(case:concept:name, time:timestamp, _orig_idx)`.
  * `Referensi: docs/specs/01-data-schema-and-loader.md, docs/specs/04-contracts-models-and-errors.md`

* **[x] M1.4 — Implementasi Pre-Kalkulasi `CaseSummaryTable` & `LogOverview` (`core/metrics.py`)**
  * Implementasikan `compute_case_summary()` (durasi `cycle_time_days` dari *trace* utuh, penanganan *case* 1 *event* = `0.0` hari, penentuan `first_activity` dan `last_activity`), `compute_activity_frequency()`, serta fasad `build_loaded_dataset()`.
  * `Referensi: docs/specs/01-data-schema-and-loader.md, docs/specs/04-contracts-models-and-errors.md`

---

## Stage 2: Core Domain & Analytics Engine (100% Headless Testable)

Fokus: Mengimplementasikan seluruh algoritma soal wajib Bab 11 (Exercise 11.7 A–E, 11.15, 11.18, 11.22) dan membuktikan kebenarannya melalui *unit test* terisolasi dengan generator dataset sintetis.

* **[x] M2.1 — Pembuatan Generator Log Sintetis & Fixture Edge Cases (`tests/conftest.py`)**
  * Buat fixture `pytest` yang menghasilkan `LoadedDataset` dan file `.xes` sintetis yang mencakup 10+ skenario *edge case* (timestamp kembar, 1-event case, multi `O_Accepted`, `O_Accepted` + `O_Refused` bersamaan, `O_Cancelled` di tengah vs di akhir, variasi huruf besar/kecil `complete`, *resource* kosong/`NaN`/spasi, multi-resource $\ge 2$, dan urutan `O_Cancelled` $\rightarrow$ `O_Accepted`).
  * `Referensi: docs/specs/01-data-schema-and-loader.md, docs/specs/02-core-analytics-engine.md`

* **[x] M2.2 — Implementasi Analisis Exercise 11.7 A–E (`core/analyzers.py`)**
  * Implementasikan `analyze_exercise_11_7()` untuk menghitung 11.7 A (total unique cases), 11.7 B (rata-rata cycle time seluruh case), 11.7 C (`contains O_Accepted`), 11.7 D (`contains O_Refused`), dan 11.7 E (`last_activity == "O_Cancelled"`), lengkap dengan `matched_cases_df` dan `evidence_event_indices`.
  * `Referensi: docs/specs/02-core-analytics-engine.md, core/models.py`

* **[x] M2.3 — Implementasi Analisis Exercise 11.15 & 11.18 (`core/analyzers.py`)**
  * Implementasikan `analyze_exercise_11_15()` (`W_Assess Potential Fraud` dengan $\ge 2$ kejadian berstatus `complete`) dan `analyze_exercise_11_18()` ($\ge 2$ kejadian `complete` oleh `org:resource` valid yang sama setelah membuang nilai kosong/`NaN`).
  * `Referensi: docs/specs/02-core-analytics-engine.md, core/models.py`

* **[x] M2.4 — Implementasi Analisis Exercise 11.22 & Orkestrator Analisis (`core/analyzers.py`)**
  * Implementasikan `analyze_exercise_11_22()` (evaluasi indeks $i < j$ untuk `O_Cancelled` diikuti `O_Accepted` pada level *case*, perhitungan persentase beserta denominator total *case*), serta fungsi `run_all_required_analyses()`.
  * `Referensi: docs/specs/02-core-analytics-engine.md, core/models.py`

* **[x] M2.5 — Pengujian Otomatis Lengkap Seluruh Skenario Edge Cases (`tests/test_analyzers.py`)**
  * Implementasikan *unit test* komprehensif untuk skenario `EC-01.1` s/d `EC-02.3` dan `T-01` s/d `T-10`. Seluruh pengujian di `pytest -v` wajib lulus 100%.
  * `Referensi: docs/specs/01-data-schema-and-loader.md, docs/specs/02-core-analytics-engine.md`

---

## Stage 3: Client Data Layer, Thread Workers, & Primary UI Shell

Fokus: Membangun lapisan virtualisasi tabel PySide6 (`QAbstractTableModel`), *worker* `QThread` anti-*freeze*, kerangka `MainWindow`, serta halaman Overview dan halaman analisis soal.

* **[x] M3.1 — Implementasi Model Tabel Teroptimasi (`ui/table_models.py`) & Worker `QThread` (`ui/workers.py`)**
  * Implementasikan `PandasTableModel(QAbstractTableModel)` dengan dukungan pemformatan angka ribuan, desimal 2 digit + satuan, serta pewarnaan baris bukti (`#FEF08A`).
  * Implementasikan `ImportWorker` dan `AnalysisWorker` dengan sinyal progres, *cancellation flag*, dan *thread cleanup* yang aman.
  * `Referensi: docs/ARCHITECTURE.md, docs/DESIGN_SYSTEM.md, docs/specs/04-contracts-models-and-errors.md`

* **[x] M3.2 — Implementasi Kerangka Jendela Utama (`ui/main_window.py`) & Halaman `Overview` (`ui/pages/overview_page.py`)**
  * Bangun Top Header Bar, Left Sidebar (5 menu), `QStackedWidget`, Bottom Status Bar, manajemen *State Machine* (`EMPTY_IDLE` $\rightarrow$ `LOADING_XES` $\rightarrow$ `DATASET_READY` $\rightarrow$ `RESULTS_READY`), dialog `About`, serta halaman **Overview** (5 kartu metrik, tabel frekuensi aktivitas, dan tabel seluruh *case* dengan pencarian `case_id`).
  * `Referensi: docs/ARCHITECTURE.md, docs/DESIGN_SYSTEM.md`

* **[x] M3.3 — Implementasi Halaman Analisis Soal (`ex11_7_page.py`, `ex11_15_18_page.py`, `ex11_22_page.py`)**
  * Bangun halaman **Exercise 11.7 (A–E)**, **Exercise 11.15 & 11.18**, dan **Exercise 11.22** sesuai spesifikasi kartu metrik, kotak aturan filter, denominator eksplisit, dan sinyal `request_case_drilldown` (klik ganda / tombol **"Lihat Rincian Case"**).
  * `Referensi: docs/DESIGN_SYSTEM.md, docs/specs/02-core-analytics-engine.md, docs/specs/04-contracts-models-and-errors.md`

---

## Stage 4: Secondary Workflows — Case Explorer, Reset/Re-run, & Atomic CSV Export

Fokus: Menyelesaikan fitur penelusuran bukti kronologis di **Case Explorer**, mekanisme *Reset / Re-run All* di memori, dan ekspor CSV atomik.

* **[x] M4.1 — Implementasi Ekstraksi Trace & Halaman `Case Explorer` (`core/analyzers.py` & `ui/pages/case_explorer_page.py`)**
  * Implementasikan `extract_case_trace()` beserta halaman **Case Explorer** yang menerima navigasi 1-klik dari halaman soal, menampilkan *badge* `[EVIDENCE]`, menyorot baris bukti dengan warna `#FEF08A`, dan melakukan *auto-scroll* ke bukti pertama.
  * `Referensi: docs/DESIGN_SYSTEM.md, docs/specs/03-case-explorer-and-csv-export.md`

* **[x] M4.2 — Implementasi Ekspor CSV Atomik (`core/exporter.py`) & Alur `Reset / Re-run All`**
  * Implementasikan `export_summary_csv()` (`summary_results.csv`) dan `export_exercise_cases_csv()` (`cases_<exercise_code>.csv`) dengan penulisan atomik `.tmp` $\rightarrow$ `os.replace`, sanitasi `dataset_filename`, serta pengujian `pytest` untuk ekspor CSV dan penanganan `PermissionError`.
  * Hubungkan tombol **Reset / Re-run All** dan tombol **Export CSV** di GUI.
  * `Referensi: docs/ARCHITECTURE.md, docs/specs/03-case-explorer-and-csv-export.md`

---

## Stage 5: CLI Verification Tool, Disco Benchmarking, & Production Hardening

Fokus: Menyelesaikan titik masuk aplikasi (`main.py` & `main_cli.py`), memverifikasi angka terhadap dataset BPIC17 asli / Fluxicon Disco, dan memastikan kualitas kode akhir.

* **[x] M5.1 — Implementasi Entry Point GUI (`main.py`), Verifikasi CLI (`main_cli.py`), & `README.md`**
  * Buat `main.py` untuk menjalankan aplikasi desktop PySide6 dan `main_cli.py` untuk mengeksekusi analisis dataset dari terminal guna pencocokan cepat dengan benchmark *Fluxicon Disco*.
  * Dokumentasikan cara instalasi (`venv` + `requirements.txt`), cara menjalankan GUI, CLI, dan `pytest` di `README.md`.
  * `Referensi: AGENTS.md, docs/ARCHITECTURE.md`

* **[x] M5.2 — Audit Kualitas Akhir (*End-to-End Verification & Hardening*)**
  * Jalankan `pytest -v`, `python -m mypy core ui`, dan `python -m ruff check core ui tests`.
  * Verifikasi ketahanan memori, responsivitas tabel $>30.000$ baris, dan penutupan jendela aplikasi saat `QThread` aktif.
  * `Referensi: AGENTS.md, docs/ARCHITECTURE.md, docs/DESIGN_SYSTEM.md`

