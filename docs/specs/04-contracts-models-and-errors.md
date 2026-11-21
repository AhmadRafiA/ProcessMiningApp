# 04 — Kontrak Data (`models.py`), Antarmuka Modul, Sinyal `QThread`, & Kode Error

Dokumen ini merupakan spesifikasi kontrak formal antara lapisan domain (`core/`) dan lapisan antarmuka (`ui/`). Setelah Stage 1 selesai, implementasi di `core/models.py` menjadi *Single Source of Truth* untuk seluruh tipe data ini.

---

## 1. Kontrak `dataclass` di `core/models.py`

*(Catatan Rekonsiliasi: `MASTER_BLUEPRINT.md` menyebut `LogOverview` di pohon direktori `core/models.py` tetapi belum mendefinisikan field-nya; skema `LoadedDataset` dan `LogOverview` di bawah ini mengunci kontrak tersebut secara lengkap).*

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import pandas as pd

# Konstanta Kode Soal Kanonik
EXERCISE_CODES: tuple[str, ...] = (
    "11.7 A",
    "11.7 B",
    "11.7 C",
    "11.7 D",
    "11.7 E",
    "11.15",
    "11.18",
    "11.22",
)


@dataclass(frozen=True)
class LogOverview:
    """Ringkasan statistika dasar event log untuk halaman Overview (F01 & F02)."""
    dataset_filename: str               # Hanya nama file dasar (Path(p).name), tanpa path direktori OS
    total_cases: int                    # Total unique case_id
    total_events: int                   # Total baris event di RawEventLogTable
    start_time_utc: datetime            # Timestamp event paling awal di seluruh log (UTC)
    end_time_utc: datetime              # Timestamp event paling akhir di seluruh log (UTC)
    mean_cycle_time_days: float         # Rata-rata cycle_time_days seluruh case (trace utuh)
    median_cycle_time_days: float       # Median cycle_time_days seluruh case (trace utuh)
    detected_attributes: tuple[str, ...]  # Daftar seluruh kolom asli yang ditemukan di file XES
    has_lifecycle: bool                 # True jika kolom 'lifecycle:transition' tersedia di XES asli
    has_resource: bool                  # True jika kolom 'org:resource' tersedia di XES asli
    warnings: tuple[str, ...] = ()      # Pesan peringatan jika atribut opsional tidak tersedia


@dataclass(frozen=True)
class LoadedDataset:
    """Bungkusan dataset in-memory yang bersifat Read-Only setelah impor selesai."""
    file_path: Path                     # Path lokal untuk keperluan internal (jangan diekspor ke CSV!)
    overview: LogOverview               # Metadata & statistika global
    raw_df: pd.DataFrame                # RawEventLogTable (terurut deterministik via _orig_idx)
    case_summary_df: pd.DataFrame       # CaseSummaryTable (pre-computed dari trace utuh)
    activity_freq_df: pd.DataFrame      # ActivityFrequencyTable (distribusi frekuensi aktivitas)


@dataclass
class AnalysisResult:
    """Kontrak keluaran seragam untuk setiap soal di core/analyzers.py."""
    exercise_code: str                  # Wajib salah satu dari EXERCISE_CODES ("11.7 A" .. "11.22")
    title: str                          # Nama singkat analisis
    filter_rule: str                    # Penjelasan aturan filter & rumus (ditampilkan di UI & CSV)
    case_count: int                     # Jumlah case unik yang lolos filter
    total_cases: int                    # Denominator (total seluruh case aktif di dataset)
    mean_cycle_time_days: float | None  # Diisi untuk 11.7 B-E; None jika tidak relevan
    percentage: float | None            # (case_count / total_cases) * 100.0
    matched_cases_df: pd.DataFrame      # Tabel ringkas case terpilih (case_id, metrik/bukti)
    evidence_event_indices: dict[str, list[int]] = field(default_factory=dict)
    # Mapping: case_id -> list[_orig_idx] yang menjadi bukti lolosnya case tersebut
```

---

## 2. Kontrak Fungsi Publik Modul `core/` (*API Signatures*)

Seluruh fungsi di dalam `core/` wajib memiliki *type annotations* penuh (`mypy` strict) dan tidak boleh mengimpor modul `PySide6`:

| Modul | Signature Fungsi Kanonik | Deskripsi & Kontrak |
| :--- | :--- | :--- |
| `core/loader.py` | `load_xes_raw(file_path: str \| Path) -> tuple[pd.DataFrame, bool, bool, tuple[str, ...]]` | Membaca `.xes`/`.xes.gz` via `pm4py.read_xes()`, menyematkan `_orig_idx` (`int64`), memvalidasi 3 kolom wajib, menormalisasi `time:timestamp` ke UTC dan `org:resource` kosong ke `pd.NA`, serta mengurutkan dengan `mergesort`. Mengembalikan `(raw_df, has_lifecycle, has_resource, detected_cols)`. |
| `core/metrics.py` | `compute_case_summary(raw_df: pd.DataFrame) -> pd.DataFrame` | Menghitung `CaseSummaryTable` (`case_id`, `event_count`, `start_time`, `end_time`, `cycle_time_days`, `first_activity`, `last_activity`) dari *trace* utuh. |
| `core/metrics.py` | `compute_activity_frequency(raw_df: pd.DataFrame, total_cases: int) -> pd.DataFrame` | Menghitung `ActivityFrequencyTable` (`activity_name`, `event_count`, `case_count`, `case_coverage_pct`). |
| `core/metrics.py` | `build_loaded_dataset(file_path: str \| Path) -> LoadedDataset` | Fungsi fasad (*facade*) yang memanggil `load_xes_raw`, `compute_case_summary`, dan `compute_activity_frequency`, lalu merakit objek `LoadedDataset`. |
| `core/analyzers.py` | `analyze_exercise_11_7(dataset: LoadedDataset) -> dict[str, AnalysisResult]` | Mengembalikan dictionary dengan kunci `"11.7 A"`, `"11.7 B"`, `"11.7 C"`, `"11.7 D"`, `"11.7 E"`. |
| `core/analyzers.py` | `analyze_exercise_11_15(dataset: LoadedDataset) -> AnalysisResult` | Mengevaluasi soal 11.15 (`W_Assess Potential Fraud` dengan $\ge 2$ `complete`). |
| `core/analyzers.py` | `analyze_exercise_11_18(dataset: LoadedDataset) -> AnalysisResult` | Mengevaluasi soal 11.18 ($\ge 2$ `complete` oleh `org:resource` valid yang sama). |
| `core/analyzers.py` | `analyze_exercise_11_22(dataset: LoadedDataset) -> AnalysisResult` | Mengevaluasi soal 11.22 (`O_Cancelled` *eventually followed by* `O_Accepted` pada indeks $i < j$). |
| `core/analyzers.py` | `run_all_required_analyses(dataset: LoadedDataset) -> dict[str, AnalysisResult]` | Menjalankan seluruh 8 soal wajib dan mengembalikan `dict[exercise_code, AnalysisResult]`. |
| `core/analyzers.py` | `extract_case_trace(dataset: LoadedDataset, case_id: str, highlight_indices: set[int] \| None = None) -> pd.DataFrame` | Mengambil rincian seluruh *event* kronologis untuk `case_id` beserta kolom `step_no`, `is_evidence`, dan `evidence_badge`. |
| `core/exporter.py` | `export_summary_csv(results: dict[str, AnalysisResult], dataset_filename: str, output_path: str \| Path) -> Path` | Menulis `summary_results.csv` secara atomik (`.tmp` $\rightarrow$ `os.replace`). |
| `core/exporter.py` | `export_exercise_cases_csv(result: AnalysisResult, output_path: str \| Path) -> Path` | Menulis `cases_<exercise_code>.csv` lengkap dengan kolom `evidence_orig_indices` secara atomik. |

---

## 3. Kontrak Sinyal `QThread` & Komunikasi Antar-Halaman (`ui/`)

### 3.1 Sinyal Worker (`ui/workers.py`)
Setiap worker mewarisi `QObject` yang dipindahkan ke `QThread` (`worker.moveToThread(thread)`):

| Kelas Worker | Nama Signal | Tipe Payload Signal | Keterangan |
| :--- | :--- | :--- | :--- |
| `ImportWorker` | `progress_updated` | `Signal(int, str)` | `(persen_0_100, pesan_status)` untuk *Bottom Status Bar*. |
| `ImportWorker` | `import_succeeded` | `Signal(object)` | Mengirimkan instance `LoadedDataset` ke `MainWindow`. |
| `ImportWorker` | `import_failed` | `Signal(str, str)` | `(error_code, user_friendly_message)`. |
| `AnalysisWorker` | `progress_updated` | `Signal(int, str)` | `(persen_0_100, pesan_soal_aktif)`. |
| `AnalysisWorker` | `analysis_succeeded` | `Signal(object)` | Mengirimkan `dict[str, AnalysisResult]` ke `MainWindow`. |
| `AnalysisWorker` | `analysis_failed` | `Signal(str, str)` | `(error_code, user_friendly_message)`. |

### 3.2 Sinyal Navigasi Drill-Down Bukti (`ui/pages/*` $\rightarrow$ `MainWindow` $\rightarrow$ `CaseExplorerPage`)
Setiap halaman soal (`Ex11_7Page`, `Ex11_15_18Page`, `Ex11_22Page`) wajib mengekspos sinyal:
```python
request_case_drilldown = Signal(str, str, object)
# Payload: (case_id: str, exercise_code: str, evidence_orig_indices: list[int])
```
Ketika sinyal ini dipancarkan, `MainWindow` otomatis mengalihkan `QStackedWidget` ke indeks halaman **Case Explorer** dan memanggil `case_explorer_page.load_case_with_evidence(case_id, exercise_code, set(evidence_orig_indices))`.

---

## 4. Taksonomi Kode Error & Hierarki Exception (`core/models.py`)

Semua error domain mewarisi `BPICAnalyzerError(Exception)` yang memiliki atribut `code: str` dan `user_message: str`:

| Kode Error | Nama Kelas Exception | Pemicu | Tindakan Pemulihan UI |
| :--- | :--- | :--- | :--- |
| `ERR_XES_NOT_FOUND` | `XESFileNotFoundError` | File `.xes`/`.xes.gz` tidak ditemukan atau berukuran $0\text{ byte}$. | Tampilkan dialog error; pertahankan state sebelumnya. |
| `ERR_XES_INVALID_FORMAT` | `InvalidXESFormatError` | File rusak (*corrupt*), XML/gzip tidak valid, atau gagal di-*parse* oleh `pm4py.read_xes()`. | Tampilkan dialog error ramah pengguna tanpa *stack trace* mentah. |
| `ERR_XES_EMPTY_LOG` | `EmptyEventLogError` | File XES valid namun menghasilkan DataFrame dengan $0$ baris *event*. | Batalkan pemuatan dan beri tahu pengguna bahwa log kosong. |
| `ERR_XES_MISSING_REQ_COLS` | `MissingRequiredColumnsError` | Salah satu dari `case:concept:name`, `concept:name`, atau `time:timestamp` tidak ditemukan. | Tampilkan daftar spesifik nama kolom wajib yang hilang. |
| `ERR_ANALYZER_MISSING_OPT_COL` | `MissingOptionalAttributeError` | Menjalankan 11.15/11.18 saat `lifecycle:transition` atau `org:resource` tidak ada di dataset. | Tangkap di `AnalysisWorker`; tandai soal terkait sebagai *Skipped/Unavailable* dengan penjelasan di UI, sedangkan soal lain (11.7 & 11.22) tetap disajikan. |
| `ERR_EXPORT_PREREQUISITE` | `ExportPrerequisiteError` | Fungsi ekspor dipanggil saat hasil analisis belum tersedia. | Tampilkan peringatan untuk menekan **Run Analysis** terlebih dahulu. |
| `ERR_EXPORT_IO_PERMISSION` | `CSVExportIOError` | `PermissionError` atau `OSError` saat menulis/mengganti file CSV tujuan. | Bersihkan file `.tmp`, tampilkan pesan agar memilih folder lain atau menutup file CSV yang terbuka di Excel. |
