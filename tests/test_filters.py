"""Unit tests for generic Disco-style filtering engine (core/filters.py)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from core.exporter import export_filtered_cases_csv
from core.filters import (
    AttributeFilterRule,
    EndpointsFilterRule,
    FilterMode,
    FollowerFilterRule,
    FollowerType,
    PerformanceFilterRule,
    TimeframeFilterRule,
    TimeframeMode,
    apply_filter_stack,
    evaluate_rule,
)
from core.models import LoadedDataset
from tests.conftest import make_dataset_from_records, make_record


def test_filters_zero_pyside6_imports() -> None:
    """Verify that core/filters.py is 100% free of Qt/PySide6 imports."""
    filters_path = Path(__file__).resolve().parent.parent / "core" / "filters.py"
    content = filters_path.read_text(encoding="utf-8")
    lower_content = content.lower()

    for forbidden in ["pyside6", "pyqt", "qwidget", "qapplication"]:
        msg = f"Forbidden import '{forbidden}' found in core/filters.py!"
        assert forbidden not in lower_content, msg


def test_attribute_filter_keep_and_drop(edge_cases_dataset: LoadedDataset) -> None:
    """Test AttributeFilterRule for both KEEP_CASES and DROP_CASES modes."""
    # 1. Keep cases containing O_Accepted
    rule_keep = AttributeFilterRule(
        attribute_name="concept:name",
        selected_values=["O_Accepted"],
        mode=FilterMode.KEEP_CASES,
    )
    matching = evaluate_rule(
        edge_cases_dataset.raw_df, edge_cases_dataset.case_summary_df, rule_keep
    )
    assert "Case_T01" in matching
    assert "Case_T03" in matching
    assert "Case_T02" not in matching  # Only has O_Cancelled

    # Apply as stack
    filtered_ds, summaries = apply_filter_stack(edge_cases_dataset, [rule_keep])
    assert len(filtered_ds.case_summary_df) == len(matching)
    assert summaries[0].cases_after == len(matching)
    assert summaries[0].case_retention_pct > 0.0

    # 2. Drop cases containing O_Accepted
    rule_drop = AttributeFilterRule(
        attribute_name="concept:name",
        selected_values=["O_Accepted"],
        mode=FilterMode.DROP_CASES,
    )
    filtered_drop, _ = apply_filter_stack(edge_cases_dataset, [rule_drop])
    assert "Case_T01" not in filtered_drop.case_summary_df["case_id"].values
    assert "Case_T02" in filtered_drop.case_summary_df["case_id"].values


def test_attribute_filter_resource(edge_cases_dataset: LoadedDataset) -> None:
    """Test AttributeFilterRule on org:resource column."""
    rule_res = AttributeFilterRule(
        attribute_name="org:resource",
        selected_values=["User_1"],
        mode=FilterMode.KEEP_CASES,
    )
    matching = evaluate_rule(
        edge_cases_dataset.raw_df, edge_cases_dataset.case_summary_df, rule_res
    )
    assert "Case_T07" in matching
    assert "Case_T08" not in matching  # Has no resource


def test_endpoints_filter(edge_cases_dataset: LoadedDataset) -> None:
    """Test EndpointsFilterRule for start and end activities."""
    # Start with A_Create
    rule_start = EndpointsFilterRule(start_activities=["A_Create"])
    matching_start = evaluate_rule(
        edge_cases_dataset.raw_df, edge_cases_dataset.case_summary_df, rule_start
    )
    assert "Case_T01" in matching_start

    # End with O_Cancelled (Case_T04 and Case_T10b end with O_Cancelled; Case_T02 ends with W_Call)
    rule_end = EndpointsFilterRule(end_activities=["O_Cancelled"])
    matching_end = evaluate_rule(
        edge_cases_dataset.raw_df, edge_cases_dataset.case_summary_df, rule_end
    )
    assert "Case_T04" in matching_end
    assert "Case_T10b" in matching_end
    assert "Case_T02" not in matching_end

    # Both Start with O_Accepted AND End with O_Cancelled
    rule_both = EndpointsFilterRule(
        start_activities=["O_Accepted"],
        end_activities=["O_Cancelled"],
    )
    filtered_both, _ = apply_filter_stack(edge_cases_dataset, [rule_both])
    assert "Case_T04" in filtered_both.case_summary_df["case_id"].values
    for _, row in filtered_both.case_summary_df.iterrows():
        assert row["first_activity"] == "O_Accepted"
        assert row["last_activity"] == "O_Cancelled"


def test_performance_filter(edge_cases_dataset: LoadedDataset) -> None:
    """Test PerformanceFilterRule for duration thresholds."""
    # Min days >= 9.0 (Case_T01 duration is 10.0 days)
    rule_slow = PerformanceFilterRule(min_days=9.0)
    matching = evaluate_rule(
        edge_cases_dataset.raw_df, edge_cases_dataset.case_summary_df, rule_slow
    )
    assert "Case_T01" in matching

    # Max days <= 1.0 day
    rule_fast = PerformanceFilterRule(min_days=0.0, max_days=1.0)
    matching_fast = evaluate_rule(
        edge_cases_dataset.raw_df, edge_cases_dataset.case_summary_df, rule_fast
    )
    assert "Case_T01" not in matching_fast


def test_follower_filter_directly_and_eventually() -> None:
    """Test FollowerFilterRule for DIRECTLY_FOLLOWS and EVENTUALLY_FOLLOWS."""
    records = [
        # Case 1: A -> B -> C (A is directly followed by B; A eventually followed by C)
        make_record(1, "Case_1", "A", "2024-01-01T01:00:00Z"),
        make_record(2, "Case_1", "B", "2024-01-01T02:00:00Z"),
        make_record(3, "Case_1", "C", "2024-01-01T03:00:00Z"),
        # Case 2: A -> X -> B (A is NOT directly followed by B; but A eventually followed by B)
        make_record(4, "Case_2", "A", "2024-01-01T01:00:00Z"),
        make_record(5, "Case_2", "X", "2024-01-01T02:00:00Z"),
        make_record(6, "Case_2", "B", "2024-01-01T03:00:00Z"),
    ]
    ds = make_dataset_from_records(records, "test_follower.xes")

    # Directly Follows: A -> B
    rule_direct = FollowerFilterRule(
        source_activity="A",
        target_activity="B",
        follower_type=FollowerType.DIRECTLY_FOLLOWS,
    )
    direct_matches = evaluate_rule(ds.raw_df, ds.case_summary_df, rule_direct)
    assert "Case_1" in direct_matches
    assert "Case_2" not in direct_matches

    # Eventually Follows: A -> B
    rule_eventual = FollowerFilterRule(
        source_activity="A",
        target_activity="B",
        follower_type=FollowerType.EVENTUALLY_FOLLOWS,
    )
    eventual_matches = evaluate_rule(ds.raw_df, ds.case_summary_df, rule_eventual)
    assert "Case_1" in eventual_matches
    assert "Case_2" in eventual_matches


def test_timeframe_filter() -> None:
    """Test TimeframeFilterRule across start, end, and active modes."""
    records = [
        # Case Jan: 2024-01-01 to 2024-01-10
        make_record(1, "Case_Jan", "A", "2024-01-01T00:00:00Z"),
        make_record(2, "Case_Jan", "B", "2024-01-10T00:00:00Z"),
        # Case Feb: 2024-02-01 to 2024-02-10
        make_record(3, "Case_Feb", "A", "2024-02-01T00:00:00Z"),
        make_record(4, "Case_Feb", "B", "2024-02-10T00:00:00Z"),
    ]
    ds = make_dataset_from_records(records, "timeframe.xes")

    rule_jan = TimeframeFilterRule(
        start_time_utc=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        end_time_utc=datetime(2024, 1, 15, 0, 0, tzinfo=UTC),
        timeframe_mode=TimeframeMode.STARTED_IN_TIMEFRAME,
    )
    matching = evaluate_rule(ds.raw_df, ds.case_summary_df, rule_jan)
    assert "Case_Jan" in matching
    assert "Case_Feb" not in matching


def test_filter_stacking_and_toggle(edge_cases_dataset: LoadedDataset) -> None:
    """Test combining multiple filters in a stack and toggling is_enabled."""
    rule1 = AttributeFilterRule(
        attribute_name="concept:name",
        selected_values=["O_Accepted"],
        mode=FilterMode.KEEP_CASES,
        is_enabled=True,
    )
    rule2 = PerformanceFilterRule(
        min_days=5.0,
        mode=FilterMode.KEEP_CASES,
        is_enabled=True,
    )

    filtered_ds, summaries = apply_filter_stack(edge_cases_dataset, [rule1, rule2])
    assert len(summaries) == 2
    assert summaries[0].cases_after >= summaries[1].cases_after
    assert "Case_T01" in filtered_ds.case_summary_df["case_id"].values

    # Disable rule2
    rule2.is_enabled = False
    filtered_disabled, summaries_disabled = apply_filter_stack(edge_cases_dataset, [rule1, rule2])
    assert summaries_disabled[1].is_enabled is False
    assert summaries_disabled[1].cases_after == summaries_disabled[0].cases_after


def test_filter_empty_result(edge_cases_dataset: LoadedDataset) -> None:
    """Test that a filter matching 0 cases produces a valid, clean empty LoadedDataset."""
    rule_empty = AttributeFilterRule(
        attribute_name="concept:name",
        selected_values=["Non_Existent_Activity"],
        mode=FilterMode.KEEP_CASES,
    )
    filtered_ds, summaries = apply_filter_stack(edge_cases_dataset, [rule_empty])
    assert len(filtered_ds.case_summary_df) == 0
    assert len(filtered_ds.raw_df) == 0
    assert filtered_ds.overview.total_cases == 0
    assert filtered_ds.overview.total_events == 0
    assert summaries[0].cases_after == 0


def test_export_filtered_cases_csv(edge_cases_dataset: LoadedDataset, tmp_path: Path) -> None:
    """Test exporting filtered cases summary to CSV."""
    out_file = tmp_path / "filtered_export.csv"
    exported_path = export_filtered_cases_csv(edge_cases_dataset.case_summary_df, out_file)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 0
    read_df = pd.read_csv(exported_path, encoding="utf-8-sig")
    assert "case_id" in read_df.columns
    assert len(read_df) == len(edge_cases_dataset.case_summary_df)


def test_filter_builder_page_and_main_window_integration(
    edge_cases_dataset: LoadedDataset,
) -> None:
    """Test FilterBuilderPage UI rendering, rule stack management, and MainWindow routing."""
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication

    from ui.main_window import MainWindow
    from ui.pages.filter_page import FilterBuilderPage

    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])

    page = FilterBuilderPage()
    page.set_dataset(edge_cases_dataset)

    # Initial state: 0 filters, full dataset in table
    assert page.table_model.rowCount() == len(edge_cases_dataset.case_summary_df)
    assert len(page._rules) == 0

    # Add rule programmatically
    rule = AttributeFilterRule(
        attribute_name="concept:name",
        selected_values=["O_Accepted"],
        mode=FilterMode.KEEP_CASES,
    )
    page._rules.append(rule)
    page._reapply_filters()

    assert page.table_model.rowCount() < len(edge_cases_dataset.case_summary_df)
    assert page.table_model.rowCount() > 0

    # Toggle rule off
    page._on_rule_toggled(0, False)
    assert page.table_model.rowCount() == len(edge_cases_dataset.case_summary_df)

    # Toggle rule back on
    page._on_rule_toggled(0, True)
    assert page.table_model.rowCount() < len(edge_cases_dataset.case_summary_df)

    # Delete rule
    page._on_rule_deleted(0)
    assert len(page._rules) == 0
    assert page.table_model.rowCount() == len(edge_cases_dataset.case_summary_df)

    # MainWindow navigation integration
    win = MainWindow()
    win._on_import_succeeded(edge_cases_dataset)
    assert len(win.nav_buttons) == 6
    assert win.stacked_widget.count() == 6

    # Navigate to Filter Builder
    win._navigate_to_page(5)
    assert win.stacked_widget.currentIndex() == 5

    # Test drilldown routing from FilterBuilderPage to Case Explorer (index 4)
    first_case = edge_cases_dataset.case_summary_df["case_id"].iloc[0]
    win.page_filter_builder.request_case_drilldown.emit(first_case, "Disco Filter", None)
    assert win.stacked_widget.currentIndex() == 4
    assert win.page_case_explorer._current_case_id == first_case

    win.close()
    page.close()

