# 03 — Case Explorer, Drill-Down Bukti, Reset/Re-run, & Ekspor CSV (F07)

Dokumen ini mendefinisikan logika penelusuran bukti *trace* per kasus di **Case Explorer**, mekanisme **Reset / Re-run All** tanpa pembacaan ulang disk, serta skema dan prosedur penulisan file CSV yang atomik (`core/exporter.py`).

---

## 1. Penelusuran Jejak Kasus & Sorotan Bukti (*Case Explorer Drill-Down*)

### 1.1 Ekstraksi Trace Kronologis (`extract_case_trace`)
Ketika pengguna mencari sebuah `case_id` secara manual di halaman **Case Explorer** atau melakukan *drill-down* (klik ganda / tombol **"Lihat Rincian Case"**) dari halaman Exercise 11.7, 11.15, 11.18, maupun 11.22:

1. **Parameter Input:**
   * `dataset: LoadedDataset` (berisi `raw_df` yang sudah terurut deterministik).
   * `case_id: str` (di-*strip* spasinya; pencarian bersifat *exact match* pada `case:concept:name`).
   * `highlight_indices: set[int] | None` (himpunan nilai `_orig_idx` dari `result.evidence_event_indices.get(case_id, [])`).
   * `source_exercise: str | None` (contoh: `"11.7 C"`, `"11.15"`, `"11.18"`, `"11.22"`).
2. **Pembentukan `CaseTraceTable` (`pd.DataFrame`):**
   Saring baris `raw_df[raw_df["case:concept:name"] == case_id]`, pertahankan urutan `(time:timestamp, _orig_idx)`, dan bentuk tabel dengan skema berikut:

| Nama Kolom | Tipe Data | Aturan Pembentukan |
| :--- | :--- | :--- |
| `step_no` | `int32` | Nomor urut langkah kronologis di dalam *trace* ($1, 2, \dots, k_c$). |
| `_orig_idx` | `int64` | Indeks baris asli dari file XES. |
| `time:timestamp` | `string` | Format string UTC: `YYYY-MM-DD HH:MM:SS.fff UTC`. |
| `concept:name` | `string` | Nama aktivitas. |
| `lifecycle:transition` | `string` | Nilai `lifecycle:transition` (tampilkan `"-"` jika `pd.NA`). |
| `org:resource` | `string` | Nilai `org:resource` (tampilkan `"-"` jika `pd.NA`). |
| `is_evidence` | `bool` | `True` jika `_orig_idx in highlight_indices`, selain itu `False`. |
| `evidence_badge` | `string` | `"[EVIDENCE]"` jika `is_evidence == True`, selain itu `""`. |

3. **Perilaku Visual di `CaseExplorerPage`:**
   * Setiap baris dengan `is_evidence == True` diberi warna latar `#FEF08A` (kuning lembut) dan teks `#713F12` tebal oleh `PandasTableModel.data(index, Qt.BackgroundRole)`.
   * Tabel otomatis melakukan *scroll* (`scrollTo`) ke baris pertama yang memiliki `is_evidence == True`.
   * Jika `case_id` tidak ditemukan di `dataset.case_summary_df`, kembalikan `DataFrame` kosong berkolom sama dan tampilkan status *"Case ID '<input>' tidak ditemukan di dalam event log aktif"* tanpa melempar *unhandled exception*.

---

## 2. Alur *Reset / Re-run All* Tanpa Impor Ulang

Untuk memenuhi aturan efisiensi memori BPIC17 ($\sim 1{,}2$ juta *event*):
1. Ketika tombol **Reset / Re-run All** ditekan pada kondisi `DATASET_READY` atau `RESULTS_READY`:
   * **DILARANG** memanggil `pm4py.read_xes()` atau membaca ulang file dari disk.
   * Bersihkan *cache* hasil analisis: `session_state.analysis_results.clear()`.
   * Bersihkan status filter pencarian `case_id` dan *highlight* bukti di **Case Explorer**.
   * Jalankan `AnalysisWorker(session_state.loaded_dataset)` di `QThread` untuk menghitung ulang seluruh soal (`11.7 A` s/d `11.7 E`, `11.15`, `11.18`, `11.22`) langsung dari `raw_df` dan `case_summary_df` yang sudah ada di memori.
2. Karena seluruh algoritma bersifat deterministik (menggunakan *mergesort* dengan *tie-breaker* `_orig_idx`), hasil *Re-run* dijamin **100% identik** hingga ke urutan baris dan angka desimal.

---

## 3. Spesifikasi & Skema Ekspor CSV (`core/exporter.py`)

### 3.1 Aturan Penulisan File CSV Atomik & Sanitasi Privasi
1. **Format Standar CSV:**
   * Encoding: `utf-8-sig` (UTF-8 dengan BOM agar langsung terbaca rapi di Microsoft Excel pada Windows/macOS maupun pembaca teks standar).
   * Delimiter: koma (`,`), quoting: `csv.QUOTE_MINIMAL`, line terminator: `\n`.
   * Pembulatan angka desimal (`mean_cycle_time_days`, `cycle_time_days`, `percentage`): simpan dengan presisi **4 angka di belakang koma** (`round(val, 4)`) di dalam CSV agar tidak kehilangan ketelitian audit, atau `""` (kosong) jika bernilai `None`.
2. **Sanitasi `dataset_filename`:**
   * Wajib hanya menggunakan nama file dasar: `Path(dataset.file_path).name` (contoh: `BPI_Challenge_2017.xes.gz`). Dilarang menulis *full directory path* milik komputer pengguna.
3. **Prosedur Tulis Atomik (*Atomic Write via Temp File*):**
   ```python
   temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
   df.to_csv(temp_path, index=False, encoding="utf-8-sig")
   os.replace(temp_path, output_path)
   ```

### 3.2 Skema File 1: `summary_results.csv`
Berisi tepat **8 baris** (masing-masing untuk `11.7 A`, `11.7 B`, `11.7 C`, `11.7 D`, `11.7 E`, `11.15`, `11.18`, dan `11.22`) dengan urutan kolom wajib berikut:

| No | Nama Kolom CSV | Tipe / Format | Contoh Nilai |
| :--- | :--- | :--- | :--- |
| 1 | `exercise_code` | `string` | `"11.7 C"`, `"11.15"`, `"11.22"` |
| 2 | `title` | `string` | `"Successful Cases (Contains O_Accepted)"` |
| 3 | `filter_rule` | `string` | Penjelasan lengkap aturan filter & rumus |
| 4 | `case_count` | `int` | `17228` |
| 5 | `total_cases_denominator` | `int` | `31509` |
| 6 | `percentage` | `float` (4 desimal) | `54.6764` |
| 7 | `mean_cycle_time_days` | `float` (4 desimal) / `""` | `22.4512` (kosong `""` jika tidak relevan) |
| 8 | `dataset_filename` | `string` | `"BPI_Challenge_2017.xes.gz"` |
| 9 | `executed_at` | `string` (ISO-8601 UTC) | `"2026-11-21T04:30:00Z"` |

### 3.3 Skema File 2: `cases_<exercise_code>.csv`
Nama file dinormalisasi dengan mengganti titik dan spasi menjadi garis bawah (contoh: `cases_11_7_C.csv`, `cases_11_7_D.csv`, `cases_11_7_E.csv`, `cases_11_15.csv`, `cases_11_18.csv`, `cases_11_22.csv`):

| Soal Target | Nama File Kanonik | Urutan Kolom Wajib di CSV |
| :--- | :--- | :--- |
| **11.7 C / D / E** | `cases_11_7_C.csv`<br>`cases_11_7_D.csv`<br>`cases_11_7_E.csv` | `case_id`, `cycle_time_days`, `event_count`, `last_activity`, `matching_event_count`, `evidence_orig_indices` |
| **11.15** | `cases_11_15.csv` | `case_id`, `complete_count`, `cycle_time_days`, `event_count`, `evidence_orig_indices` |
| **11.18** | `cases_11_18.csv` | `case_id`, `matching_resources`, `max_resource_complete_count`, `total_fraud_complete_count`, `cycle_time_days`, `event_count`, `evidence_orig_indices` |
| **11.22** | `cases_11_22.csv` | `case_id`, `first_cancelled_idx`, `first_cancelled_time`, `following_accepted_idx`, `following_accepted_time`, `cycle_time_days`, `event_count`, `evidence_orig_indices` |

*(Catatan: Kolom `evidence_orig_indices` berisi string daftar `_orig_idx` bukti yang dipisahkan titik-koma, misal `"104;112"`, agar auditor dapat melacak baris XES asli langsung dari file CSV).*

---

## 4. Penanganan *Edge Cases* & Skenario Kegagalan (F07)

| ID Skenario | Kondisi Input / Aksi Pengguna | Perilaku Sistem yang Diwajibkan |
| :--- | :--- | :--- |
| **EC-07.1** | Pengguna menekan tombol **Export CSV** sebelum analisis dijalankan (`analysis_results` kosong). | Tombol Export wajib dalam keadaan `Disabled` pada state `EMPTY_IDLE` dan `DATASET_READY`. Jika dipanggil via fungsi, lempar `ExportPrerequisiteError`. |
| **EC-07.2** | Pengguna memilih folder tujuan ekspor yang *read-only* atau file CSV tujuan sedang dikunci aplikasi lain (mis. Excel). | Tangkap `PermissionError` / `OSError`, hapus file `.tmp` jika sempat terbuat, lempar `CSVExportIOError`, dan tampilkan dialog peringatan ramah pengguna tanpa menutup aplikasi. |
| **EC-07.3** | Sebuah soal menghasilkan `0` *case* yang lolos (`matched_cases_df` kosong). | Ekspor CSV **tetap berhasil** membuat file `.csv` yang berisi baris *header* kolom lengkap dengan `0` baris data (tidak melempar error). |
