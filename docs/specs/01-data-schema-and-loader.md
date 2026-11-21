# 01 — Skema Data In-Memory, Parsing XES, & Pre-Kalkulasi Metrik (F01 & F02)

Dokumen ini mendefinisikan struktur tabel in-memory (`RawEventLogTable`, `CaseSummaryTable`, `ActivityFrequencyTable`), algoritma pemuatan dan validasi file `.xes`/`.xes.gz` (`core/loader.py`), serta perhitungan metrik dasar dari *trace* utuh (`core/metrics.py`).

---

## 1. Skema Tabel In-Memory (`pandas.DataFrame`)

Aplikasi tidak menggunakan database eksternal. Begitu file `.xes` atau `.xes.gz` dimuat, data distandardisasi menjadi tiga struktur `pandas.DataFrame` bersifat **Read-Only** di dalam objek `LoadedDataset`.

### 1.1 `RawEventLogTable` (`raw_df: pd.DataFrame`)
Hasil konversi langsung dari `pm4py.read_xes()`, telah dinormalisasi dan diurutkan secara deterministik:

| Nama Kolom Kanonik | Tipe Data (`dtype`) | Sifat | Aturan Normalisasi & Constraint |
| :--- | :--- | :--- | :--- |
| `_orig_idx` | `int64` | **Wajib (PK)** | Indeks baris urutan asli dari file XES ($0, 1, \dots, N-1$) sebelum pengurutan apa pun. Wajib menjadi *tie-breaker* saat `time:timestamp` kembar. *(Catatan Rekonsiliasi: Nama kanonik adalah `_orig_idx`, menggantikan referensi `_event_idx`)*. |
| `case:concept:name` | `string` (`object`/`str`) | **Wajib** | Identifier unik kasus (*Case ID*). Wajib di-*cast* ke `str` dan di-*strip* spasinya. Baris dengan `case:concept:name` kosong/`NaN` ditolak saat validasi. |
| `concept:name` | `string` (`object`/`str`) | **Wajib** | Nama aktivitas (contoh: `O_Accepted`, `O_Refused`, `O_Cancelled`, `W_Assess Potential Fraud`). Wajib di-*cast* ke `str` dan di-*strip*. |
| `time:timestamp` | `datetime64[ns, UTC]` | **Wajib** | Waktu kejadian yang telah dikonversi dengan `pd.to_datetime(..., utc=True)`. Tidak boleh mengandung `NaT`. |
| `lifecycle:transition` | `string` (Nullable) | Opsional | Status siklus hidup (`complete`, `schedule`, `start`, dll.). Jika kolom tidak ada di file XES, buat kolom bernilai `pd.NA` dan catat peringatan. |
| `org:resource` | `string` (Nullable) | Opsional | Pelaku aktivitas (`User_1`, dll.). Nilai kosong (`""`, spasi `"   "`, `"nan"`, `"None"`, `None`) wajib dinormalisasi menjadi `pd.NA` / `np.nan`. |

### 1.2 `CaseSummaryTable` (`case_summary_df: pd.DataFrame` — *Pre-computed*)
Dihitung **satu kali** tepat setelah `RawEventLogTable` selesai diurutkan, menggunakan **seluruh *event* pada *trace* utuh** (sebelum filter soal apa pun dijalankan):

| Nama Kolom Kanonik | Tipe Data (`dtype`) | Sifat | Rumus / Aturan Pembentukan |
| :--- | :--- | :--- | :--- |
| `case_id` | `string` | **Wajib (PK)** | Nilai unik dari `case:concept:name` (diurutkan menaik atau sesuai kemunculan awal). |
| `event_count` | `int32` | **Wajib** | Jumlah seluruh *event* di dalam *case* tersebut ($\ge 1$). |
| `start_time` | `datetime64[ns, UTC]` | **Wajib** | `time:timestamp` dari *event* pertama pada *trace* utuh. |
| `end_time` | `datetime64[ns, UTC]` | **Wajib** | `time:timestamp` dari *event* terakhir pada *trace* utuh. |
| `cycle_time_days` | `float64` | **Wajib** | Durasi kasus dalam satuan hari (lihat Rumus 2.2). Bernilai $0.0$ jika `event_count == 1`. |
| `first_activity` | `string` | **Wajib** | `concept:name` dari *event* paling awal berdasarkan urutan `(time:timestamp, _orig_idx)`. |
| `last_activity` | `string` | **Wajib** | `concept:name` dari *event* paling akhir berdasarkan urutan `(time:timestamp, _orig_idx)`. |

### 1.3 `ActivityFrequencyTable` (`activity_freq_df: pd.DataFrame`)
Tabel ringkasan distribusi aktivitas untuk halaman **Overview (F02)**:

| Nama Kolom Kanonik | Tipe Data (`dtype`) | Rumus / Aturan Pembentukan |
| :--- | :--- | :--- |
| `activity_name` | `string` | Nilai unik `concept:name`, diurutkan menurun berdasarkan `event_count` (tie-breaker: abjad `activity_name`). |
| `event_count` | `int64` | Total kemunculan *event* aktivitas tersebut di seluruh log. |
| `case_count` | `int64` | Jumlah *case* unik yang mengandung minimal 1 *event* aktivitas tersebut. |
| `case_coverage_pct` | `float64` | $\frac{\text{case\_count}}{\text{total\_cases}} \times 100.0$. |

---

## 2. Algoritma Pemuatan, Normalisasi, & Rumus Pre-Kalkulasi

### 2.1 Langkah Pemuatan & Pengurutan Deterministik (`core/loader.py`)
1. **Validasi File Fisik:**
   * Pastikan path file ada, bukan direktori, berukuran $> 0\text{ byte}$, dan berekstensi `.xes` atau `.xes.gz`.
2. **Parsing via PM4Py:**
   * Panggil `log = pm4py.read_xes(str(file_path))`. Jika keluaran belum berupa `pd.DataFrame`, konversi dengan `pm4py.convert_to_dataframe(log)`.
   * Tangkap segala `Exception` dari parser XML/gzip (`etree.XMLSyntaxError`, `EOFError`, `gzip.BadGzipFile`, `ValueError`) dan bungkus menjadi `InvalidXESFormatError`.
3. **Penyematan `_orig_idx` Sebelum Manipulasi:**
   * Segera setelah `DataFrame` mentah terbentuk, sematkan indeks urutan asli:
     ```python
     df["_orig_idx"] = np.arange(len(df), dtype=np.int64)
     ```
4. **Validasi Kolom Wajib & Deteksi Kolom Opsional:**
   * Periksa keberadaan `REQUIRED_COLUMNS = {"case:concept:name", "concept:name", "time:timestamp"}`. Jika ada yang hilang, lempar `MissingRequiredColumnsError(missing_cols)`.
   * Periksa keberadaan `OPTIONAL_COLUMNS = {"lifecycle:transition", "org:resource"}`. Jika tidak ditemukan:
     * Tambahkan kolom tersebut ke `df` dengan nilai `pd.NA`.
     * Tambahkan pesan peringatan ke `warnings: list[str]` pada `LoadedDataset`.
5. **Normalisasi Tipe Data & Pembersihan Resource Kosong:**
   * Konversi `time:timestamp` ke UTC: `df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True, errors="raise")`.
   * Normalisasi `org:resource`: ubah nilai `None`, `np.nan`, string kosong `""`, string hanya spasi (`^\s+$`), atau string literal `"nan"`/`"None"` (case-insensitive) menjadi `pd.NA`.
6. **Pengurutan Deterministik (*Stable Sort*):**
   * Urutkan `df` menggunakan algoritma *mergesort* agar urutan asli `_orig_idx` terjaga mutlak saat `time:timestamp` kembar:
     ```python
     df = df.sort_values(
         by=["case:concept:name", "time:timestamp", "_orig_idx"],
         ascending=[True, True, True],
         kind="mergesort",
     ).reset_index(drop=True)
     ```

### 2.2 Rumus Pre-Kalkulasi `CaseSummaryTable` (`core/metrics.py`)
Untuk setiap kasus $c \in C$ yang memiliki barisan *event* terurut $E_c = \langle e_1, e_2, \dots, e_k \rangle$ ($k \ge 1$):

$$\text{start\_time}(c) = \min_{e \in E_c} t(e) = t(e_1)$$

$$\text{end\_time}(c) = \max_{e \in E_c} t(e) = t(e_k)$$

$$\text{cycle\_time\_days}(c) = \frac{\text{end\_time}(c) - \text{start\_time}(c)}{86.400\text{ detik}} = \frac{\Delta t_{\text{seconds}}(c)}{86400.0}$$

$$\text{last\_activity}(c) = \text{activity}(e_k)$$

* **Rata-rata *Cycle Time* Global (Overview & Exercise 11.7 B):**
  $$\overline{\text{CT}}_{\text{all}} = \frac{1}{|C|} \sum_{c \in C} \text{cycle\_time\_days}(c)$$

---

## 3. Penanganan *Edge Cases* & Skenario Kegagalan (F01 & F02)

| ID Skenario | Kondisi Input (*Edge Case*) | Perilaku Sistem yang Diwajibkan (*Expected Output*) |
| :--- | :--- | :--- |
| **EC-01.1** | File `.xes` / `.xes.gz` rusak (*corrupt*) atau bukan XML/XES valid. | Melempar `InvalidXESFormatError` dengan pesan ramah pengguna; aplikasi tidak *crash* dan kembali ke state `EMPTY_IDLE` (atau mempertahankan dataset sebelumnya). |
| **EC-01.2** | Salah satu kolom wajib (`case:concept:name`, `concept:name`, `time:timestamp`) tidak ada. | Melempar `MissingRequiredColumnsError` yang mencantumkan daftar nama kolom yang hilang; pemuatan dibatalkan. |
| **EC-01.3** | File XES valid tetapi memiliki $0$ baris *event* (log kosong). | Melempar `EmptyEventLogError("File XES tidak memiliki baris event.")`; pemuatan dibatalkan. |
| **EC-01.4** | Kolom `lifecycle:transition` atau `org:resource` tidak ada pada dataset. | Pemuatan **tetap sukses**; kolom dibuat dengan nilai `pd.NA`, flag `has_lifecycle` / `has_resource` bernilai `False`, dan daftar `warnings` diisi untuk ditampilkan di UI. |
| **EC-02.1** | Sebuah *case* hanya memiliki **1 *event*** ($k = 1$, sehingga $\text{start\_time} == \text{end\_time}$). | `cycle_time_days` wajib bernilai `0.0` (`float64`), tidak boleh menghasilkan `NaN`, `None`, atau `ZeroDivisionError`. |
| **EC-02.2** | Baris-baris *event* di file XES memiliki zona waktu (*timezone offset*) yang berbeda-beda (mis. `+01:00` dan `+02:00` akibat *Daylight Saving Time*). | Seluruh *timestamp* dinormalisasi ke `UTC` (`datetime64[ns, UTC]`) sebelum pengurutan dan pengurangan `end_time - start_time`. |
| **EC-02.3** | Dua *event* terakhir dalam satu *case* memiliki `time:timestamp` yang sama persis hingga nanodetik. | Karena diurutkan dengan `by=["case:concept:name", "time:timestamp", "_orig_idx"]` (`kind="mergesort"`), `last_activity` wajib mengambil aktivitas dengan `_orig_idx` yang lebih besar (muncul lebih akhir di file XES). |
