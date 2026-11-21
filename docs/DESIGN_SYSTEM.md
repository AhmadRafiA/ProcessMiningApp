# DESIGN_SYSTEM.md — Ergonomi UI/UX, Wireframe, & Kontrak Visual

Dokumen ini menetapkan aturan antarmuka pengguna (PySide6), tata letak jendela, format angka/satuan, serta pemetaan *state* komponen ke indikator visual yang konkret.

---

## 1. Prinsip Utama UX & Ergonomi Pengguna

1. **Alur Kerja Linear & Fleksibel (*Core User Flow*):**
   Antarmuka membimbing pengguna melalui alur:
   `Impor XES` $\rightarrow$ `Lihat Overview` $\rightarrow$ `Pilih Latihan` $\rightarrow$ `Jalankan Analisis` $\rightarrow$ `Lihat Jawaban & Aturan` $\rightarrow$ `Periksa Bukti di Case Explorer` $\rightarrow$ `Ekspor CSV`.
2. **Responsivitas Tanpa Beku (*Non-Blocking UI*):**
   * Target *frame rate* *scrolling* pada tabel $>30.000$ baris (`QTableView` + `QAbstractTableModel`) adalah $< 16\text{ ms}$ per *frame* ($60\text{ FPS}$).
   * Selama `QThread` menjalankan impor atau analisis, tampilkan perubahan status dan *progress bar* di *Bottom Status Bar*, ubah kursor atau nonaktifkan tombol pemicu untuk mencegah klik ganda.
3. **Keterlacakan Bukti 1-Klik (*1-Click Evidence Drill-Down*):**
   * Setiap baris di tabel daftar *case* terpilih pada halaman **Exercise 11.7**, **Exercise 11.15 & 11.18**, dan **Exercise 11.22** dapat dibuka langsung di **Case Explorer** dengan **klik ganda (*double-click*)** pada baris atau menekan tombol **"Lihat Rincian Case"**.
   * Saat berpindah ke **Case Explorer**, aplikasi otomatis mengisi kotak pencarian `case_id`, memuat seluruh *event* kronologis *case* tersebut, memberi warna sorotan (*highlight*) pada baris *event* yang menjadi bukti (`_orig_idx` bukti), dan melakukan *auto-scroll* ke baris bukti pertama.
4. **Standar Format Angka, Satuan, & Denominator Eksplisit:**
   * **Bilangan Bulat (Jumlah Case / Event):** Wajib memakai pemisah ribuan koma (`31,509 cases`, `1,202,267 events`).
   * **Durasi (*Cycle Time*):** Wajib diformat **2 angka di belakang koma** disertai satuan eksplisit `hari` (contoh: `21.90 hari`, `0.00 hari`). Dilarang menampilkan angka tanpa satuan.
   * **Persentase (Exercise 11.22 & metrik proporsi):** Wajib diformat **2 angka di belakang koma** beserta **denominator eksplisit** dalam format: `X / Y cases (Z.ZZ%)` — contoh: `1,420 / 31,509 cases (4.51%)`.
   * **Timestamp:** Ditampilkan dalam format ISO-8601 UTC yang bersih: `YYYY-MM-DD HH:MM:SS.fff UTC`.

---

## 2. Tata Letak Utama (*ASCII Wireframe* & *Grid Proportions*)

Ukuran jendela minimum (`minimumSize`): `1200 x 760 px` (default saat dibuka: `1366 x 840 px`). Menggunakan struktur **Top Dataset Bar + Left Sidebar + Main Content Area (`QStackedWidget`) + Bottom Status Bar**.

```text
+--------------------------------------------------------------------------------------------------+
| [Import XES] | File: BPI_Challenge_2017.xes.gz [Badge: READY] | [Reset/Re-run All] [Export CSV] [About] | <- Top Header (Height: 56px)
+----------------------+---------------------------------------------------------------------------+
| NAVIGASI (Width:230px)| AREA KONTEN UTAMA (QStackedWidget - Flex 100%)                           |
|                      |                                                                           |
| (1) Overview         | +-----------------------------------------------------------------------+ |
| (2) Exercise 11.7    | | HEADER HALAMAN & KOTAK ATURAN FILTER (Filter Rule Box)                | |
| (3) Ex 11.15 & 11.18 | +-----------------------------------------------------------------------+ |
| (4) Exercise 11.22   | | KARTU METRIK RINGKASAN (Metric Cards Grid: 2 s/d 5 Kartu)             | |
| (5) Case Explorer    | +-----------------------------------------------------------------------+ |
|                      | | TOOLBAR TABEL: [Filter/Search Case ID...]        [Lihat Rincian Case] | |
|                      | | +-------------------------------------------------------------------+ | |
|                      | | | QTableView (Virtualized via QAbstractTableModel)                  | | |
|                      | | | _orig_idx | case_id | cycle_time_days | ...                       | | |
|                      | | +-------------------------------------------------------------------+ | |
|                      | +-----------------------------------------------------------------------+ |
+----------------------+---------------------------------------------------------------------------+
| Status: Ready        | [==================== 100% ====================] | Cases: 31,509 | Events: 1,202,267 | <- Bottom Status Bar (Height: 32px)
+--------------------------------------------------------------------------------------------------+
```

### Tipografi & Skala Ukuran (ramah proyektor & rekaman layar)
* **Font UI Utama:** Sistem native (`SF Pro Text` / `Segoe UI` / `Inter`), ukuran dasar `13px` (`10pt`).
* **Font Angka Metrik Utama (Kartu Jawaban):** `22px` (`16.5pt`), `Bold`.
* **Font Tabel (`Case ID`, `Timestamp`, `_orig_idx`):** Monospace (`JetBrains Mono` / `SF Mono` / `Consolas`), `12.5px`, agar angka dan *timestamp* sejajar vertikal.

---

## 3. Matriks Indikator Visual, Palet Warna, & *Component States*

Gunakan tema terang berkontras tinggi (*High-Contrast Light Theme*) agar nyaman dibaca saat demonstrasi proyektor.

### 3.1 Palet Warna & Status Badge
| Kondisi / Elemen Visual | Warna Latar (Hex) | Warna Teks / Border (Hex) | Teks Badge / Indikator | Aturan Penggunaan |
| :--- | :--- | :--- | :--- | :--- |
| **Background Utama / Card** | `#F8FAFC` / `#FFFFFF` | Teks: `#0F172A`<br>Border: `#E2E8F0` | — | Latar jendela `#F8FAFC`, kartu metrik & tabel `#FFFFFF`. |
| **Primary Action Button** | `#2563EB` (Hover: `#1D4ED8`) | Teks: `#FFFFFF` | `Import XES`, `Run Analysis` | Tombol aksi utama di tiap halaman. |
| **State: Empty / Idle** | `#F1F5F9` | `#475569` | `NO DATASET` | Saat aplikasi baru dibuka sebelum impor XES. |
| **State: Loading / Running** | `#EFF6FF` | `#1D4ED8` | `LOADING XES...` / `RUNNING...` | Ditampilkan saat `QThread` aktif; *progress bar* bergerak. |
| **State: Ready / Success** | `#DCFCE7` | `#15803D` | `READY` / `COMPLETED` | Dataset valid & analisis selesai tanpa peringatan. |
| **State: Warning (Missing Optional Col)** | `#FEF3C7` | `#B45309` | `WARNING: PARTIAL ATTRIBUTES` | Ketika `lifecycle:transition` atau `org:resource` tidak ada. |
| **State: Error / Failed** | `#FEE2E2` | `#B91C1C` | `ERROR` | Gagal baca file XES, kolom wajib hilang, atau gagal tulis CSV. |
| **State: Disabled Control** | `#E2E8F0` | `#94A3B8` (Opacity `55%`) | — | Tombol `Run Analysis` / `Export CSV` saat *state* belum memenuhi syarat. |
| **Kotak Aturan Filter (*Rule Box*)** | `#F0FDF4` (atau `#EFF6FF`) | Border Kiri `4px`: `#0284C7`<br>Teks: `#0C4A6E` | `Aturan Filter & Rumus:` | Kotak wajib di atas tabel hasil yang menjelaskan logika filter soal. |
| **Highlight Baris Bukti (Case Explorer)** | `#FEF08A` (Kuning Lembut) | Teks: `#713F12` (`Bold`) | Badge Kolom Bukti: `[EVIDENCE]` | Menyorot baris *event* di Case Explorer yang cocok dengan `_orig_idx` bukti. |

### 3.2 Matriks State Komponen per Halaman
| Komponen | State `EMPTY_IDLE` | State `LOADING_XES` / `RUNNING_ANALYSIS` | State `DATASET_READY` | State `RESULTS_READY` |
| :--- | :--- | :--- | :--- | :--- |
| **Tombol `Import XES`** | Aktif (`Enabled`) | Nonaktif (`Disabled`) | Aktif (`Enabled`) | Aktif (`Enabled`) |
| **Tombol `Run Analysis`** | Nonaktif (`Disabled`) | Nonaktif (`Disabled`) | Aktif (`Enabled`) | Aktif (`Enabled`) |
| **Tombol `Reset / Re-run All`** | Nonaktif (`Disabled`) | Nonaktif (`Disabled`) | Aktif (`Enabled`) | Aktif (`Enabled`) |
| **Tombol `Export Summary CSV`** | Nonaktif (`Disabled`) | Nonaktif (`Disabled`) | Nonaktif (`Disabled`) | Aktif (`Enabled`) |
| **Area Tabel Halaman Soal** | Placeholder: *"Silakan impor file .xes/.xes.gz terlebih dahulu."* | Indikator *Loading* + *Progress Bar* aktif di Status Bar. | Placeholder: *"Klik 'Run Analysis' untuk menghitung jawaban."* | Menampilkan kartu jawaban, aturan filter, & tabel *case* terpilih. |

---

## 4. Spesifikasi Halaman & Komponen Khusus

### 4.1 Halaman 1: `Overview` (F01 & F02)
* **Baris Kartu Metrik (5 Kartu):** Total Unique Cases, Total Events, Time Range (`Start UTC` s/d `End UTC`), Mean Cycle Time (`XX.XX hari`), dan Atribut Terdeteksi (menampilkan centang hijau untuk `case:concept:name`, `concept:name`, `time:timestamp`, serta status tersedia/tidaknya `lifecycle:transition` dan `org:resource`).
* **Split View Bawah (`40%` Kiri / `60%` Kanan):**
  * **Kiri (`40%`):** Tabel **Distribusi Frekuensi Aktivitas** (`activity_name`, `event_count`, `case_coverage_pct`) terurut menurun berdasarkan `event_count`.
  * **Kanan (`60%`):** Tabel **Daftar Seluruh Case (`CaseSummaryTable`)** lengkap dengan kotak pencarian *real-time* berdasarkan `case_id` (`QSortFilterProxyModel`).

### 4.2 Halaman 2: `Exercise 11.7 (A–E)` (F03)
* **Tombol Aksi Atas:** `Run Exercise 11.7 Analysis` dan `Export Selected Category CSV`.
* **5 Kartu/Baris Hasil Interaktif (11.7 A, 11.7 B, 11.7 C, 11.7 D, 11.7 E):**
  * Setiap kartu menampilkan: Kode Soal, Judul, Jumlah Case (`X cases`), Rata-rata Cycle Time (`YY.YY hari`), dan ringkasan **Aturan Filter**.
  * Kartu **11.7 C**, **11.7 D**, dan **11.7 E** berfungsi sebagai pemilih tab tabel di bawahnya: saat pengguna mengklik kartu C, D, atau E, tabel di bagian bawah menampilkan daftar `case_id`, `cycle_time_days`, `event_count`, `last_activity`, serta tombol/aksi *double-click* **"Lihat Rincian Case"** menuju Case Explorer.

### 4.3 Halaman 3: `Exercise 11.15 & 11.18` (F04 & F05)
* **Kotak Aturan Filter Ketat:** Menampilkan keterangan eksplisit bahwa hanya aktivitas `W_Assess Potential Fraud` dengan `lifecycle:transition == "complete"` yang dihitung, dan untuk 11.18 nilai `org:resource` kosong (`NaN`/`""`) telah dieliminasi.
* **Tab / Panel Ganda Berdampingan atau Bertingkat:**
  * **Panel 11.15:** Kartu total *case* lolos 11.15 + tabel (`case_id`, `complete_count`, `cycle_time_days`) + tombol `Export 11.15 Cases CSV`.
  * **Panel 11.18:** Kartu total *case* lolos 11.18 + tabel (`case_id`, `matching_resources`, `max_resource_complete_count`, `cycle_time_days`) + tombol `Export 11.18 Cases CSV`.
  * Klik ganda pada baris di salah satu tabel langsung membuka *case* tersebut di **Case Explorer** dengan menyorot *event* `W_Assess Potential Fraud` (`complete`) yang menjadi bukti.

### 4.4 Halaman 4: `Exercise 11.22` (F06)
* **Kartu Metrik Utama:** Menampilkan Jumlah Case Lolos, Total Case Aktif (Denominator), dan **Persentase Eksplisit** (`X / Y cases (Z.ZZ%)`).
* **Kotak Aturan Filter:** Menjelaskan semantik *Eventually Follows* level *Case* ($\text{indeks } i < j$ di mana $\text{event}_i = \text{O\_Cancelled}$ dan $\text{event}_j = \text{O\_Accepted}$ pada urutan deterministik `(time:timestamp, _orig_idx)`).
* **Tabel Bukti 11.22:** Kolom `case_id`, `first_cancelled_idx`, `first_cancelled_time`, `following_accepted_idx`, `following_accepted_time`, `cycle_time_days`, serta aksi *double-click* ke **Case Explorer** (menyorot pasangan *event* `O_Cancelled` dan `O_Accepted` tersebut).

### 4.5 Halaman 5: `Case Explorer` (F07) & Dialog `About`
* **Toolbar Pencarian Case Explorer:** Input pencarian `case_id` + *indicator badge* konteks bukti aktif (misal: *"Menampilkan bukti untuk Exercise 11.18 — 2 event disorot"* disertai tombol `Clear Highlight`).
* **Tabel Kronologis Trace (`QTableView`):** Menampilkan seluruh *event* dari `case_id` terpilih secara utuh, terurut berdasarkan `(time:timestamp, _orig_idx)`, dengan kolom: `step_no` ($1 \dots N$), `_orig_idx`, `time:timestamp`, `concept:name`, `lifecycle:transition`, `org:resource`, dan `is_evidence` (`[EVIDENCE]` dengan latar `#FEF08A` jika `_orig_idx` ada di dalam `highlight_indices`).
* **Dialog `About` (Reproduktibilitas):** Modal ringkas yang menampilkan versi aplikasi, versi Python (`sys.version`), versi `pm4py`, `pandas`, `numpy`, dan `PySide6`, lengkap dengan tombol `Copy Environment Info`.
