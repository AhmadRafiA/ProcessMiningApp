"""AddFilterDialog for configuring Disco-style filtering rules."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.filters import (
    AttributeFilterRule,
    BaseFilterRule,
    EndpointsFilterRule,
    FilterMode,
    FollowerFilterRule,
    FollowerType,
    PerformanceFilterRule,
    TimeframeFilterRule,
    TimeframeMode,
)
from core.models import LoadedDataset


class AddFilterDialog(QDialog):
    """Modal dialog allowing users to create any of the 5 Disco filter rules."""

    def __init__(self, dataset: LoadedDataset, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tambah Filter ala Fluxicon Disco")
        self.setMinimumSize(560, 520)
        self.resize(600, 560)

        self._dataset = dataset
        self._created_rule: BaseFilterRule | None = None

        self._init_ui()

    def get_rule(self) -> BaseFilterRule | None:
        """Return the created rule after dialog accepted, or None if cancelled."""
        return self._created_rule

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title
        title = QLabel("Tambah Filter Baru")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        layout.addWidget(title)

        subtitle = QLabel("Pilih tipe filter Disco dan tentukan kriteria penyaringan kasus.")
        subtitle.setStyleSheet("font-size: 12px; color: #475569;")
        layout.addWidget(subtitle)

        # Top Control: Filter Type & Mode
        top_form = QFormLayout()
        top_form.setSpacing(10)

        self.combo_type = QComboBox()
        self.combo_type.addItems(
            [
                "Attribute Filter (Aktivitas / Resource / Lifecycle)",
                "Endpoints Filter (Aktivitas Awal & Akhir)",
                "Performance Filter (Durasi Kasus / Cycle Time)",
                "Follower Filter (Urutan Pasangan Kejadian)",
                "Timeframe Filter (Batas Waktu / Tanggal)",
            ]
        )
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        top_form.addRow("Tipe Filter:", self.combo_type)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(
            [
                "Simpan Kasus yang Cocok (Keep Cases)",
                "Buang Kasus yang Cocok (Drop Cases)",
            ]
        )
        top_form.addRow("Mode Aksi:", self.combo_mode)
        layout.addLayout(top_form)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(sep)

        # Stacked Widget for Forms
        self.stack = QStackedWidget()

        self.page_attr = self._create_attribute_form()
        self.page_endpoints = self._create_endpoints_form()
        self.page_perf = self._create_performance_form()
        self.page_follower = self._create_follower_form()
        self.page_timeframe = self._create_timeframe_form()

        self.stack.addWidget(self.page_attr)       # Index 0
        self.stack.addWidget(self.page_endpoints)  # Index 1
        self.stack.addWidget(self.page_perf)       # Index 2
        self.stack.addWidget(self.page_follower)   # Index 3
        self.stack.addWidget(self.page_timeframe)  # Index 4

        layout.addWidget(self.stack, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setStyleSheet(
            "background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; "
            "padding: 6px 16px; border-radius: 6px; font-weight: 500;"
        )
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Terapkan Filter")
        self.btn_apply.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; border: none; "
            "padding: 6px 18px; border-radius: 6px; font-weight: bold;"
        )
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)

    def _on_type_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    # --------------------------------------------------------------------------
    # Form 1: Attribute Filter
    # --------------------------------------------------------------------------
    def _create_attribute_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        attr_row = QHBoxLayout()
        attr_lbl = QLabel("Pilih Atribut:")
        attr_lbl.setStyleSheet("font-weight: bold; color: #1E293B;")
        attr_row.addWidget(attr_lbl)

        self.combo_attr_name = QComboBox()
        self.combo_attr_name.addItem("Aktivitas (concept:name)", "concept:name")
        if self._dataset.overview.has_resource:
            self.combo_attr_name.addItem("Resource (org:resource)", "org:resource")
        if self._dataset.overview.has_lifecycle:
            self.combo_attr_name.addItem("Lifecycle (lifecycle:transition)", "lifecycle:transition")
        self.combo_attr_name.currentIndexChanged.connect(self._populate_attribute_values)
        attr_row.addWidget(self.combo_attr_name, stretch=1)
        layout.addLayout(attr_row)

        desc = QLabel("Centang satu atau lebih nilai yang ingin difilter:")
        desc.setStyleSheet("font-size: 11.5px; color: #64748B;")
        layout.addWidget(desc)

        self.list_attr_values = QListWidget()
        self.list_attr_values.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 4px; padding: 4px;"
        )
        layout.addWidget(self.list_attr_values, stretch=1)

        # Quick select buttons
        btn_row = QHBoxLayout()
        btn_all = QPushButton("Pilih Semua")
        btn_all.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        btn_all.clicked.connect(lambda: self._set_list_check_all(self.list_attr_values, True))
        btn_none = QPushButton("Hapus Pilihan")
        btn_none.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        btn_none.clicked.connect(lambda: self._set_list_check_all(self.list_attr_values, False))
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._populate_attribute_values()
        return widget

    def _populate_attribute_values(self) -> None:
        self.list_attr_values.clear()
        col = self.combo_attr_name.currentData()
        if col not in self._dataset.raw_df.columns:
            return

        counts = self._dataset.raw_df[col].dropna().value_counts()
        for val, count in counts.items():
            str_val = str(val).strip()
            item = QListWidgetItem(f"{str_val}  ({count:,} events)")
            item.setData(Qt.ItemDataRole.UserRole, str_val)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_attr_values.addItem(item)

    # --------------------------------------------------------------------------
    # Form 2: Endpoints Filter
    # --------------------------------------------------------------------------
    def _create_endpoints_form(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Start Activities Column
        col_start = QVBoxLayout()
        lbl_start = QLabel("Aktivitas Awal (Start Activity):")
        lbl_start.setStyleSheet("font-weight: bold; color: #1E293B;")
        col_start.addWidget(lbl_start)

        self.list_start_acts = QListWidget()
        self.list_start_acts.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 4px;"
        )
        col_start.addWidget(self.list_start_acts, stretch=1)
        layout.addLayout(col_start)

        # End Activities Column
        col_end = QVBoxLayout()
        lbl_end = QLabel("Aktivitas Akhir (End Activity):")
        lbl_end.setStyleSheet("font-weight: bold; color: #1E293B;")
        col_end.addWidget(lbl_end)

        self.list_end_acts = QListWidget()
        self.list_end_acts.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 4px;"
        )
        col_end.addWidget(self.list_end_acts, stretch=1)
        layout.addLayout(col_end)

        # Populate start and end activities
        if "first_activity" in self._dataset.case_summary_df.columns:
            start_counts = self._dataset.case_summary_df["first_activity"].value_counts()
            for act, cnt in start_counts.items():
                item = QListWidgetItem(f"{act} ({cnt:,})")
                item.setData(Qt.ItemDataRole.UserRole, str(act))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.list_start_acts.addItem(item)

        if "last_activity" in self._dataset.case_summary_df.columns:
            end_counts = self._dataset.case_summary_df["last_activity"].value_counts()
            for act, cnt in end_counts.items():
                item = QListWidgetItem(f"{act} ({cnt:,})")
                item.setData(Qt.ItemDataRole.UserRole, str(act))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.list_end_acts.addItem(item)

        return widget

    # --------------------------------------------------------------------------
    # Form 3: Performance Filter
    # --------------------------------------------------------------------------
    def _create_performance_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        desc = QLabel(
            "Saring kasus berdasarkan total waktu siklus (cycle time) dalam satuan hari.\n"
            f"Rentang dataset saat ini: 0.00 s/d "
            f"{self._dataset.overview.mean_cycle_time_days * 3:.2f}+ hari "
            f"(Rata-rata: {self._dataset.overview.mean_cycle_time_days:.2f} hari)."
        )
        desc.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)

        self.spin_min_days = QDoubleSpinBox()
        self.spin_min_days.setRange(0.0, 99999.0)
        self.spin_min_days.setDecimals(2)
        self.spin_min_days.setValue(0.0)
        self.spin_min_days.setSuffix(" hari")
        form.addRow("Durasi Minimum:", self.spin_min_days)

        self.spin_max_days = QDoubleSpinBox()
        self.spin_max_days.setRange(0.0, 99999.0)
        self.spin_max_days.setDecimals(2)
        self.spin_max_days.setValue(30.0)
        self.spin_max_days.setSuffix(" hari")
        form.addRow("Durasi Maksimum:", self.spin_max_days)

        self.chk_no_max = QCheckBox("Tanpa Batas Maksimum (>= Durasi Minimum)")
        self.chk_no_max.toggled.connect(
            lambda checked: self.spin_max_days.setEnabled(not checked)
        )
        form.addRow("", self.chk_no_max)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    # --------------------------------------------------------------------------
    # Form 4: Follower Filter
    # --------------------------------------------------------------------------
    def _create_follower_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        desc = QLabel(
            "Saring kasus berdasarkan keberadaan pasangan urutan sekuensial dua aktivitas."
        )
        desc.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)

        self.combo_source_act = QComboBox()
        self.combo_target_act = QComboBox()

        acts = sorted(self._dataset.raw_df["concept:name"].dropna().unique())
        for a in acts:
            self.combo_source_act.addItem(str(a))
            self.combo_target_act.addItem(str(a))

        if len(acts) > 1:
            self.combo_target_act.setCurrentIndex(1)

        form.addRow("Aktivitas Sumber (Awal):", self.combo_source_act)

        self.combo_rel_type = QComboBox()
        self.combo_rel_type.addItem(
            "Eventually Follows (kemudian diikuti di mana saja dalam trace)",
            FollowerType.EVENTUALLY_FOLLOWS,
        )
        self.combo_rel_type.addItem(
            "Directly Follows (langsung diikuti persis pada event berikutnya)",
            FollowerType.DIRECTLY_FOLLOWS,
        )
        form.addRow("Hubungan Relasi:", self.combo_rel_type)

        form.addRow("Aktivitas Target (Pengikut):", self.combo_target_act)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    # --------------------------------------------------------------------------
    # Form 5: Timeframe Filter
    # --------------------------------------------------------------------------
    def _create_timeframe_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        desc = QLabel(
            "Saring kasus berdasarkan jendela rentang waktu kejadian (UTC)."
        )
        desc.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)

        min_dt = self._dataset.overview.start_time_utc
        max_dt = self._dataset.overview.end_time_utc

        min_qdt = QDateTime(
            min_dt.year, min_dt.month, min_dt.day, min_dt.hour, min_dt.minute, min_dt.second
        )
        max_qdt = QDateTime(
            max_dt.year, max_dt.month, max_dt.day, max_dt.hour, max_dt.minute, max_dt.second
        )

        self.dt_start = QDateTimeEdit(min_qdt)
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_start.setCalendarPopup(True)
        form.addRow("Waktu Mulai (UTC):", self.dt_start)

        self.dt_end = QDateTimeEdit(max_qdt)
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_end.setCalendarPopup(True)
        form.addRow("Waktu Selesai (UTC):", self.dt_end)

        self.combo_time_mode = QComboBox()
        self.combo_time_mode.addItem(
            "Kasus Aktif dalam Periode (Active in timeframe)",
            TimeframeMode.ACTIVE_IN_TIMEFRAME,
        )
        self.combo_time_mode.addItem(
            "Kasus Dimulai dalam Periode (Started in timeframe)",
            TimeframeMode.STARTED_IN_TIMEFRAME,
        )
        self.combo_time_mode.addItem(
            "Kasus Selesai dalam Periode (Completed in timeframe)",
            TimeframeMode.COMPLETED_IN_TIMEFRAME,
        )
        form.addRow("Mode Evaluasi Waktu:", self.combo_time_mode)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    # --------------------------------------------------------------------------
    # Helper Methods & Apply
    # --------------------------------------------------------------------------
    def _set_list_check_all(self, list_widget: QListWidget, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for idx in range(list_widget.count()):
            item = list_widget.item(idx)
            item.setCheckState(state)

    def _get_checked_values(self, list_widget: QListWidget) -> list[str]:
        vals: list[str] = []
        for idx in range(list_widget.count()):
            item = list_widget.item(idx)
            if item.checkState() == Qt.CheckState.Checked:
                data = item.data(Qt.ItemDataRole.UserRole)
                vals.append(str(data) if data is not None else item.text())
        return vals

    def _on_apply_clicked(self) -> None:
        mode = (
            FilterMode.KEEP_CASES
            if self.combo_mode.currentIndex() == 0
            else FilterMode.DROP_CASES
        )
        type_idx = self.stack.currentIndex()

        if type_idx == 0:  # Attribute Filter
            vals = self._get_checked_values(self.list_attr_values)
            if not vals:
                QMessageBox.warning(
                    self, "Validasi Filter", "Silakan pilih minimal satu nilai atribut."
                )
                return
            attr_col = str(self.combo_attr_name.currentData())
            self._created_rule = AttributeFilterRule(
                attribute_name=attr_col,
                selected_values=vals,
                mode=mode,
            )

        elif type_idx == 1:  # Endpoints Filter
            starts = self._get_checked_values(self.list_start_acts)
            ends = self._get_checked_values(self.list_end_acts)
            if not starts and not ends:
                QMessageBox.warning(
                    self,
                    "Validasi Filter",
                    "Silakan pilih minimal satu aktivitas awal atau aktivitas akhir.",
                )
                return
            self._created_rule = EndpointsFilterRule(
                start_activities=starts,
                end_activities=ends,
                mode=mode,
            )

        elif type_idx == 2:  # Performance Filter
            min_days = self.spin_min_days.value()
            max_days = float("inf") if self.chk_no_max.isChecked() else self.spin_max_days.value()
            if not self.chk_no_max.isChecked() and min_days > max_days:
                QMessageBox.warning(
                    self,
                    "Validasi Filter",
                    "Durasi minimum tidak boleh lebih besar dari durasi maksimum.",
                )
                return
            self._created_rule = PerformanceFilterRule(
                min_days=min_days,
                max_days=max_days,
                mode=mode,
            )

        elif type_idx == 3:  # Follower Filter
            src = self.combo_source_act.currentText()
            tgt = self.combo_target_act.currentText()
            rel_type = self.combo_rel_type.currentData()
            self._created_rule = FollowerFilterRule(
                source_activity=src,
                target_activity=tgt,
                follower_type=rel_type,
                mode=mode,
            )

        elif type_idx == 4:  # Timeframe Filter
            st = datetime.fromtimestamp(self.dt_start.dateTime().toSecsSinceEpoch(), tz=UTC)
            et = datetime.fromtimestamp(self.dt_end.dateTime().toSecsSinceEpoch(), tz=UTC)
            if st > et:
                QMessageBox.warning(
                    self,
                    "Validasi Filter",
                    "Waktu mulai tidak boleh lebih besar dari waktu selesai.",
                )
                return
            time_mode = self.combo_time_mode.currentData()
            self._created_rule = TimeframeFilterRule(
                start_time_utc=st,
                end_time_utc=et,
                timeframe_mode=time_mode,
                mode=mode,
            )

        self.accept()
