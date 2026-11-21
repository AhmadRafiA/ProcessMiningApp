# 02 — Mesin Analitik Inti: Exercise 11.7, 11.15, 11.18, & 11.22 (F03–F06)

Dokumen ini mendefinisikan spesifikasi matematis, algoritma vektorisasi/deterministik di `core/analyzers.py`, struktur tabel `matched_cases_df`, pencatatan indeks bukti (`evidence_event_indices`), serta skenario pengujian wajib (`pytest`) untuk kedelapan soal Bab 11.

---

## 1. Notasi Formal & Ketentuan Umum

Misalkan $C$ adalah himpunan seluruh *case* unik dalam dataset aktif, dengan total kasus $N_{\text{total}} = |C|$.  
Untuk setiap kasus $c \in C$, barisan *event*-nya yang telah diurutkan secara deterministik berdasarkan `(time:timestamp, _orig_idx)` adalah:

$$E_c = \langle e_1, e_2, \dots, e_{k_c} \rangle, \quad k_c \ge 1$$

di mana setiap *event* $e_m$ ($1 \le m \le k_c$) memiliki atribut:
* $\text{idx}(e_m) \in \mathbb{Z}_{\ge 0}$: indeks baris asli `_orig_idx` dari file XES.
* $t(e_m)$: waktu kejadian `time:timestamp` dalam UTC.
* $\text{act}(e_m)$: nama aktivitas `concept:name`.
* $\text{life}(e_m)$: status siklus hidup yang dinormalisasi (`str(lifecycle:transition).strip().lower()`).
* $\text{res}(e_m)$: pelaku aktivitas `org:resource` yang telah dibersihkan (bernilai $\varnothing$ jika `NaN`/`None`/`""`/spasi).
* $\text{CT}(c)$: durasi *trace* utuh `cycle_time_days` milik kasus $c$ yang diambil langsung dari `CaseSummaryTable`:
  $$\text{CT}(c) = \frac{t(e_{k_c}) - t(e_1)}{86400.0}$$

> **ATURAN MUTLAK RATA-RATA CYCLE TIME & PERSENTASE:**
> * Untuk himpunan bagian kasus terpilih $S \subseteq C$:
>   $$\overline{\text{CT}}(S) = \begin{cases} \frac{1}{|S|} \sum_{c \in S} \text{CT}(c) & \text{jika } |S| > 0 \\ 0.0 & \text{jika } |S| = 0 \end{cases}$$
> * Persentase terhadap total kasus aktif:
>   $$\text{Pct}(S) = \begin{cases} \frac{|S|}{N_{\text{total}}} \times 100.0 & \text{jika } N_{\text{total}} > 0 \\ 0.0 & \text{jika } N_{\text{total}} = 0 \end{cases}$$

---

## 2. Spesifikasi Exercise 11.7 (A–E) — F03

Kelima subsoal 11.7 dievaluasi pada level *case* dengan mengambil `CT(c)` dari `CaseSummaryTable` (*trace* utuh):

### 2.1 Definisi Matematis & Aturan Filter (11.7 A s/d 11.7 E)

1. **Exercise 11.7 A — Total Unique Cases:**
   * **Rumus:** $S_{\text{11.7A}} = C$, $\quad \text{case\_count} = |C| = N_{\text{total}}$.
   * **`mean_cycle_time_days`:** `None` (atau disertakan sebagai referensi).
   * **`filter_rule`:** `"Seluruh unique cases di dalam event log aktif (tanpa filter)."`.
2. **Exercise 11.7 B — Mean Cycle Time (All Cases):**
   * **Rumus:** $S_{\text{11.7B}} = C$, $\quad \text{mean\_cycle\_time\_days} = \overline{\text{CT}}(C)$.
   * **`filter_rule`:** `"Rata-rata cycle time (hari) dari seluruh unique cases, dihitung dari selisih timestamp akhir dan awal pada trace utuh."`.
3. **Exercise 11.7 C — Successful Cases (`contains O_Accepted`):**
   * **Himpunan Kasus:**
     $$S_{\text{11.7C}} = \{ c \in C \mid \exists e_m \in E_c,\; \text{act}(e_m) = \text{"O\_Accepted"} \}$$
   * **Indeks Bukti (`evidence_event_indices[c]`):** Daftar seluruh $\text{idx}(e_m)$ dalam $E_c$ di mana $\text{act}(e_m) = \text{"O\_Accepted"}$.
   * **`mean_cycle_time_days`:** $\overline{\text{CT}}(S_{\text{11.7C}})$ (dari *trace* utuh!).
   * **`filter_rule`:** `"Case memiliki minimal 1 event dengan concept:name == 'O_Accepted' (level case, non-eksklusif; cycle time dari trace utuh)."`.
4. **Exercise 11.7 D — Unsuccessful Cases (`contains O_Refused`):**
   * **Himpunan Kasus:**
     $$S_{\text{11.7D}} = \{ c \in C \mid \exists e_m \in E_c,\; \text{act}(e_m) = \text{"O\_Refused"} \}$$
   * **Indeks Bukti (`evidence_event_indices[c]`):** Daftar seluruh $\text{idx}(e_m)$ dalam $E_c$ di mana $\text{act}(e_m) = \text{"O\_Refused"}$.
   * **`mean_cycle_time_days`:** $\overline{\text{CT}}(S_{\text{11.7D}})$ (dari *trace* utuh!).
   * **`filter_rule`:** `"Case memiliki minimal 1 event dengan concept:name == 'O_Refused' (level case, non-eksklusif terhadap 11.7 C; cycle time dari trace utuh)."`.
5. **Exercise 11.7 E — Canceled Cases (`endpoint O_Cancelled`):**
   * **Himpunan Kasus:**
     $$S_{\text{11.7E}} = \{ c \in C \mid \text{act}(e_{k_c}) = \text{"O\_Cancelled"} \}$$
   * **Indeks Bukti (`evidence_event_indices[c]`):** $[\text{idx}(e_{k_c})]$ (hanya *event* paling akhir pada *trace* utuh).
   * **`mean_cycle_time_days`:** $\overline{\text{CT}}(S_{\text{11.7E}})$ (dari *trace* utuh!).
   * **`filter_rule`:** `"Event paling akhir pada trace utuh (berdasarkan urutan time:timestamp dan _orig_idx) adalah 'O_Cancelled'."`.

### 2.2 Skema `matched_cases_df` untuk Exercise 11.7 (C, D, E)
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `case_id` | `string` | ID kasus yang lolos filter kategori terkait. |
| `cycle_time_days` | `float64` | Durasi kasus dari *trace* utuh (`CaseSummaryTable`). |
| `event_count` | `int32` | Total seluruh *event* pada *trace* utuh. |
| `last_activity` | `string` | Aktivitas terakhir pada *trace* utuh. |
| `matching_event_count` | `int32` | Jumlah *event* bukti (`O_Accepted` di C, `O_Refused` di D, `1` di E). |

---

## 3. Spesifikasi Exercise 11.15 — Pengulangan Aktivitas Fraud (`complete`) — F04

### 3.1 Definisi Matematis & Aturan Filter
Definisikan himpunan *event* penyelesaian *fraud assessment* pada kasus $c$:

$$F_c = \{ e_m \in E_c \mid \text{act}(e_m) = \text{"W\_Assess Potential Fraud"} \;\land\; \text{life}(e_m) = \text{"complete"} \}$$

Kasus $c$ lolos **Exercise 11.15** jika dan hanya jika kardinalitas $F_c$ minimal 2:

$$S_{\text{11.15}} = \{ c \in C \mid |F_c| \ge 2 \}$$

* **Indeks Bukti (`evidence_event_indices[c]`):** $[\text{idx}(e) \text{ untuk setiap } e \in F_c]$.
* **`filter_rule`:** `"Case memiliki >= 2 event dengan concept:name == 'W_Assess Potential Fraud' DAN lifecycle:transition (normalized lower/strip) == 'complete'."`.
* **Prasyarat Kolom:** Jika `dataset.has_lifecycle == False`, lempar `MissingOptionalAttributeError("lifecycle:transition", "11.15")`.

### 3.2 Skema `matched_cases_df` untuk Exercise 11.15
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `case_id` | `string` | ID kasus yang lolos 11.15. |
| `complete_count` | `int32` | Nilai $|F_c|$ (jumlah *complete occurrence* `W_Assess Potential Fraud`, $\ge 2$). |
| `cycle_time_days` | `float64` | Durasi *trace* utuh dari `CaseSummaryTable`. |
| `event_count` | `int32` | Total *event* pada *trace* utuh. |

---

## 4. Spesifikasi Exercise 11.18 — Pengulangan oleh *Resource* Sama — F05

### 4.1 Definisi Matematis & Aturan Filter
Dari himpunan $F_c$ (yang sudah disaring hanya untuk `W_Assess Potential Fraud` berstatus `complete`), buang seluruh *event* yang memiliki `org:resource` kosong ($\text{res}(e) = \varnothing$):

$$F_c^{\text{valid}} = \{ e \in F_c \mid \text{res}(e) \neq \varnothing \}$$

Untuk setiap *resource* valid $r$ yang muncul di $F_c^{\text{valid}}$, definisikan sub-himpunan *event*-nya:

$$F_{c, r} = \{ e \in F_c^{\text{valid}} \mid \text{res}(e) = r \}$$

Kasus $c$ lolos **Exercise 11.18** jika terdapat minimal satu *resource* valid $r$ yang menyelesaikan aktivitas tersebut $\ge 2$ kali dalam kasus $c$:

$$S_{\text{11.18}} = \{ c \in C \mid \exists r \neq \varnothing,\; |F_{c, r}| \ge 2 \}$$

* **Daftar Resource Bukti per Kasus:** $R_c^{*} = \{ r \neq \varnothing \mid |F_{c, r}| \ge 2 \}$ (diurutkan sesuai abjad dan digabung dengan `", "` untuk kolom `matching_resources`).
* **Indeks Bukti (`evidence_event_indices[c]`):** $[\text{idx}(e) \text{ untuk setiap } e \in F_{c, r} \text{ dengan } r \in R_c^{*}]$.
* **Konsistensi Level Case:** Jika $|R_c^{*}| \ge 2$ (ada 2 *resource* berbeda yang masing-masing menyelesaikan $\ge 2$ kali pada *case* yang sama), kasus $c$ **tetap dihitung 1 kali** di `case_count`, namun seluruh *resource* di $R_c^{*}$ ditampilkan di `matching_resources`.
* **`filter_rule`:** `"Case memiliki >= 2 event 'W_Assess Potential Fraud' berstatus 'complete' yang dikerjakan oleh org:resource valid (tidak kosong/NaN) yang SAMA."`.
* **Prasyarat Kolom:** Jika `not dataset.has_lifecycle` atau `not dataset.has_resource`, lempar `MissingOptionalAttributeError`.

### 4.2 Skema `matched_cases_df` untuk Exercise 11.18
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `case_id` | `string` | ID kasus yang lolos 11.18. |
| `matching_resources` | `string` | Nama `org:resource` yang mencapai $\ge 2$ `complete` (dipisahkan `", "` jika $>1$). |
| `max_resource_complete_count` | `int32` | $\max_{r \in R_c^{*}} |F_{c, r}|$ ($\ge 2$). |
| `total_fraud_complete_count` | `int32` | Total $|F_c|$ pada kasus tersebut. |
| `cycle_time_days` | `float64` | Durasi *trace* utuh dari `CaseSummaryTable`. |
| `event_count` | `int32` | Total *event* pada *trace* utuh. |

---

## 5. Spesifikasi Exercise 11.22 — Urutan *Eventually Follows* (`O_Cancelled` $\rightarrow$ `O_Accepted`) — F06

### 5.1 Definisi Matematis & Algoritma Deterministik $O(|E_c|)$
Pada barisan *event* terurut $E_c = \langle e_1, e_2, \dots, e_{k_c} \rangle$, kasus $c$ lolos **Exercise 11.22** jika terdapat pasangan posisi indeks urutan $(i, j)$ dalam *trace* yang sama sedemikian sehingga:

$$1 \le i < j \le k_c \quad \land \quad \text{act}(e_i) = \text{"O\_Cancelled"} \quad \land \quad \text{act}(e_j) = \text{"O\_Accepted"}$$

**Algoritma Vektorisasi / Linear per Trace (KanoniK):**
1. Cari posisi kemunculan **pertama** `O_Cancelled` dalam $E_c$:
   $$i^{*} = \min \{ m \in \{1, \dots, k_c\} \mid \text{act}(e_m) = \text{"O\_Cancelled"} \}$$
2. Cari posisi kemunculan **pertama** `O_Accepted` yang berada **setelah** $i^{*}$ ($m > i^{*}$):
   $$j^{*} = \min \{ m \in \{i^{*} + 1, \dots, k_c\} \mid \text{act}(e_m) = \text{"O\_Accepted"} \}$$
3. Jika $i^{*}$ dan $j^{*}$ keduanya ada ($i^{*} < j^{*}$), maka $c \in S_{\text{11.22}}$.
4. **Indeks Bukti (`evidence_event_indices[c]`):** $[\text{idx}(e_{i^{*}}),\; \text{idx}(e_{j^{*}})]$.
5. **Persentase:** $\text{percentage} = \frac{|S_{\text{11.22}}|}{N_{\text{total}}} \times 100.0$.
6. **`filter_rule`:** `"Case memiliki event 'O_Cancelled' pada posisi i yang diikuti oleh 'O_Accepted' pada posisi j > i (Eventually Follows level case berdasarkan time:timestamp dan _orig_idx)."`.

### 5.2 Skema `matched_cases_df` untuk Exercise 11.22
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `case_id` | `string` | ID kasus yang lolos 11.22. |
| `first_cancelled_idx` | `int64` | Nilai `_orig_idx` dari $e_{i^{*}}$ (`O_Cancelled` pertama). |
| `first_cancelled_time` | `datetime64[ns, UTC]` | Timestamp $t(e_{i^{*}})$. |
| `following_accepted_idx` | `int64` | Nilai `_orig_idx` dari $e_{j^{*}}$ (`O_Accepted` pertama sesudah $e_{i^{*}}$). |
| `following_accepted_time` | `datetime64[ns, UTC]` | Timestamp $t(e_{j^{*}})$. |
| `cycle_time_days` | `float64` | Durasi *trace* utuh dari `CaseSummaryTable`. |
| `event_count` | `int32` | Total *event* pada *trace* utuh. |

---

## 6. Matriks 10 Skenario *Edge Cases* Wajib di `tests/test_analyzers.py`

| ID Test | Soal Target | Susunan Trace Sintetis | Hasil Wajib (*Assertion*) |
| :--- | :--- | :--- | :--- |
| **T-01** | **11.7 C** | 1 *case* berisi `O_Accepted` sebanyak 2 kali pada hari ke-1 dan ke-5 (total durasi *trace* 10 hari). | Dihitung tepat **1 *case*** di 11.7 C; `cycle_time_days == 10.0` (dari *trace* utuh, bukan 4 hari). |
| **T-02** | **11.7 E** | 1 *case* memiliki `O_Cancelled` di tengah *trace*, lalu diikuti `W_Call after offers`. | **Tidak lolos** 11.7 E (`case_count == 0`). |
| **T-03** | **11.7 C & D** | 1 *case* memiliki `O_Accepted` dan juga `O_Refused`. | **Lolos keduanya**: masuk ke 11.7 C (`1`) dan masuk ke 11.7 D (`1`). |
| **T-04** | **11.7 E** | 2 *event* terakhir memiliki *timestamp* identik: `_orig_idx=10` (`O_Accepted`) dan `_orig_idx=11` (`O_Cancelled`). | **Lolos** 11.7 E karena `_orig_idx=11` adalah *event* terakhir; jika urutan `_orig_idx` dibalik, **gagal** 11.7 E. |
| **T-05** | **11.15** | `W_Assess Potential Fraud` muncul 2x `schedule`, 1x `start`, dan hanya 1x `complete`. | **Tidak lolos** 11.15 (`case_count == 0`). |
| **T-06** | **11.15** | `W_Assess Potential Fraud` memiliki `lifecycle:transition` bernilai `"COMPLETE "` dan `" complete"`. | **Lolos** 11.15 (`complete_count == 2`) berkat normalisasi `.str.strip().str.lower()`. |
| **T-07** | **11.15 & 18** | 2 `complete` `W_Assess Potential Fraud` dikerjakan oleh `User_1` dan `User_2`. | **Lolos 11.15** (`1`), tetapi **Gagal 11.18** (`0`). |
| **T-08** | **11.18** | 2 `complete` `W_Assess Potential Fraud` sama-sama memiliki `org:resource` kosong (`NaN`, `""`, atau `"  "`). | **Gagal 11.18** (`case_count == 0`). |
| **T-09** | **11.18** | 1 *case* memiliki `User_1` (2x `complete`) dan `User_2` (2x `complete`). | `case_count == 1` (dihitung 1 *case*), `matching_resources == "User_1, User_2"`. |
| **T-10** | **11.22** | (a) `O_Cancelled` $\rightarrow$ `A_Validating` $\rightarrow$ `O_Accepted`; (b) `O_Accepted` $\rightarrow$ `O_Cancelled` tanpa `O_Accepted` lagi; (c) `O_Cancelled` dan `O_Accepted` ber-*timestamp* sama (`_orig_idx` 5 dan 6). | (a) **Lolos** 11.22; (b) **Gagal** 11.22; (c) **Lolos** 11.22 karena `_orig_idx` $5 < 6$. |
