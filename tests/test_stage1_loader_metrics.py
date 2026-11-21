"""Stage 1 unit & integration tests for core.models, core.loader, and core.metrics."""

from __future__ import annotations

import gzip
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from core.loader import load_xes_raw
from core.metrics import (
    build_loaded_dataset,
    compute_activity_frequency,
    compute_case_summary,
)
from core.models import (
    EXERCISE_CODES,
    EmptyEventLogError,
    InvalidXESFormatError,
    MissingRequiredColumnsError,
    XESFileNotFoundError,
)


def _write_xes(path: Path, traces_xml: str, compressed: bool = False) -> Path:
    """Helper to write a minimal valid XES 1.0 XML file (optionally gzipped)."""
    content = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<log xes.version="1.0" xes.features="nested-attributes" '
        'xmlns="http://www.xes-standard.org/">\n'
        f"{traces_xml}\n"
        "</log>\n"
    )
    if compressed:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _sample_traces_xml() -> str:
    return """
  <trace>
    <string key="concept:name" value="Case_A"/>
    <event>
      <string key="concept:name" value="A_Create Application"/>
      <string key="lifecycle:transition" value="complete"/>
      <string key="org:resource" value="User_1"/>
      <date key="time:timestamp" value="2024-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="O_Accepted"/>
      <string key="lifecycle:transition" value="complete"/>
      <string key="org:resource" value="User_2"/>
      <date key="time:timestamp" value="2024-01-03T12:00:00.000+00:00"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="Case_B"/>
    <event>
      <string key="concept:name" value="A_Create Application"/>
      <string key="lifecycle:transition" value="complete"/>
      <string key="org:resource" value="User_1"/>
      <date key="time:timestamp" value="2024-01-02T00:00:00.000+00:00"/>
    </event>
  </trace>
"""


def test_core_has_zero_pyside6_imports() -> None:
    """Invariant: core/ must never import PySide6."""
    core_dir = Path(__file__).resolve().parent.parent / "core"
    for py_file in core_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        assert "PySide6" not in text, f"Forbidden PySide6 import found in {py_file.name}"


def test_exercise_codes_canonical() -> None:
    """Verify EXERCISE_CODES contains all 8 required Chapter 11 exercises."""
    assert EXERCISE_CODES == (
        "11.7 A",
        "11.7 B",
        "11.7 C",
        "11.7 D",
        "11.7 E",
        "11.15",
        "11.18",
        "11.22",
    )


@pytest.mark.parametrize("compressed", [False, True])
def test_happy_path_xes_and_xes_gz(tmp_path: Path, compressed: bool) -> None:
    """Happy path: load .xes and .xes.gz, verify schemas, UTC, and pre-computed tables."""
    ext = ".xes.gz" if compressed else ".xes"
    xes_path = _write_xes(tmp_path / f"sample{ext}", _sample_traces_xml(), compressed=compressed)

    dataset = build_loaded_dataset(xes_path)

    assert dataset.overview.dataset_filename == f"sample{ext}"
    assert dataset.overview.total_cases == 2
    assert dataset.overview.total_events == 3
    assert dataset.overview.has_lifecycle is True
    assert dataset.overview.has_resource is True
    assert dataset.overview.warnings == ()

    # RawEventLogTable checks
    assert "_orig_idx" in dataset.raw_df.columns
    assert str(dataset.raw_df["_orig_idx"].dtype) == "int64"
    assert str(dataset.raw_df["time:timestamp"].dtype) == "datetime64[ns, UTC]"

    # CaseSummaryTable checks
    cs = dataset.case_summary_df.set_index("case_id")
    assert cs.loc["Case_A", "event_count"] == 2
    assert cs.loc["Case_A", "cycle_time_days"] == pytest.approx(2.5)
    assert cs.loc["Case_A", "first_activity"] == "A_Create Application"
    assert cs.loc["Case_A", "last_activity"] == "O_Accepted"

    # EC-02.1: single-event case cycle_time_days == 0.0
    assert cs.loc["Case_B", "event_count"] == 1
    assert cs.loc["Case_B", "cycle_time_days"] == pytest.approx(0.0)
    assert not pd.isna(cs.loc["Case_B", "cycle_time_days"])

    # Overview mean/median cycle time
    assert dataset.overview.mean_cycle_time_days == pytest.approx(1.25)
    assert dataset.overview.median_cycle_time_days == pytest.approx(1.25)

    # ActivityFrequencyTable checks
    af = dataset.activity_freq_df.set_index("activity_name")
    assert af.loc["A_Create Application", "event_count"] == 2
    assert af.loc["A_Create Application", "case_count"] == 2
    assert af.loc["A_Create Application", "case_coverage_pct"] == pytest.approx(100.0)
    assert af.loc["O_Accepted", "event_count"] == 1
    assert af.loc["O_Accepted", "case_count"] == 1
    assert af.loc["O_Accepted", "case_coverage_pct"] == pytest.approx(50.0)


def test_ec_01_1_missing_empty_and_corrupt_files(tmp_path: Path) -> None:
    """EC-01.1: Non-existent, 0-byte, unsupported ext, and corrupt XES raise domain errors."""
    with pytest.raises(XESFileNotFoundError) as exc_missing:
        load_xes_raw(tmp_path / "does_not_exist.xes")
    assert exc_missing.value.code == "ERR_XES_NOT_FOUND"

    empty_file = tmp_path / "zero.xes"
    empty_file.write_bytes(b"")
    with pytest.raises(XESFileNotFoundError) as exc_zero:
        load_xes_raw(empty_file)
    assert exc_zero.value.code == "ERR_XES_NOT_FOUND"

    wrong_ext = tmp_path / "data.csv"
    wrong_ext.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(InvalidXESFormatError) as exc_ext:
        load_xes_raw(wrong_ext)
    assert exc_ext.value.code == "ERR_XES_INVALID_FORMAT"

    corrupt_xes = tmp_path / "corrupt.xes"
    corrupt_xes.write_text("<not-valid-xml", encoding="utf-8")
    with pytest.raises(InvalidXESFormatError) as exc_corrupt:
        load_xes_raw(corrupt_xes)
    assert exc_corrupt.value.code == "ERR_XES_INVALID_FORMAT"


def test_ec_01_2_missing_required_columns(tmp_path: Path) -> None:
    """EC-01.2: Missing required column raises MissingRequiredColumnsError."""
    dummy_xes = _write_xes(tmp_path / "dummy.xes", _sample_traces_xml())
    incomplete_df = pd.DataFrame(
        {
            "case:concept:name": ["C1"],
            "time:timestamp": ["2024-01-01T00:00:00Z"],
            # missing 'concept:name'
        }
    )
    with patch("core.loader.pm4py.read_xes", return_value=incomplete_df):
        with pytest.raises(MissingRequiredColumnsError) as exc_info:
            load_xes_raw(dummy_xes)
    assert exc_info.value.code == "ERR_XES_MISSING_REQ_COLS"
    assert exc_info.value.missing_columns == ("concept:name",)


def test_ec_01_3_empty_event_log(tmp_path: Path) -> None:
    """EC-01.3: Valid XES with 0 events raises EmptyEventLogError."""
    empty_log_xes = _write_xes(tmp_path / "empty_log.xes", "")
    with pytest.raises(EmptyEventLogError) as exc_info:
        load_xes_raw(empty_log_xes)
    assert exc_info.value.code == "ERR_XES_EMPTY_LOG"


def test_ec_01_4_missing_optional_attributes_graceful_degradation(tmp_path: Path) -> None:
    """EC-01.4: Missing lifecycle:transition and org:resource still loads with warnings."""
    traces_no_opt = """
  <trace>
    <string key="concept:name" value="C1"/>
    <event>
      <string key="concept:name" value="Start"/>
      <date key="time:timestamp" value="2024-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="End"/>
      <date key="time:timestamp" value="2024-01-02T00:00:00.000+00:00"/>
    </event>
  </trace>
"""
    xes_path = _write_xes(tmp_path / "no_opt.xes", traces_no_opt)
    dataset = build_loaded_dataset(xes_path)

    assert dataset.overview.has_lifecycle is False
    assert dataset.overview.has_resource is False
    assert len(dataset.overview.warnings) == 2
    assert "lifecycle:transition" in dataset.raw_df.columns
    assert "org:resource" in dataset.raw_df.columns
    assert dataset.raw_df["lifecycle:transition"].isna().all()
    assert dataset.raw_df["org:resource"].isna().all()


def test_ec_02_2_mixed_timezones_normalized_to_utc(tmp_path: Path) -> None:
    """EC-02.2: Mixed timezone offsets (+01:00 and +02:00) normalize to UTC accurately."""
    # 10:00+01:00 == 09:00 UTC; 11:00+02:00 == 09:00 UTC -> 0.0 days!
    # 12:00+02:00 == 10:00 UTC -> 1 hour = 1/24 days.
    traces_tz = """
  <trace>
    <string key="concept:name" value="C_TZ"/>
    <event>
      <string key="concept:name" value="E1"/>
      <date key="time:timestamp" value="2024-06-01T10:00:00.000+01:00"/>
    </event>
    <event>
      <string key="concept:name" value="E2"/>
      <date key="time:timestamp" value="2024-06-01T12:00:00.000+02:00"/>
    </event>
  </trace>
"""
    xes_path = _write_xes(tmp_path / "tz.xes", traces_tz)
    dataset = build_loaded_dataset(xes_path)
    cs = dataset.case_summary_df.set_index("case_id")
    assert cs.loc["C_TZ", "cycle_time_days"] == pytest.approx(1.0 / 24.0)


def test_ec_02_3_identical_timestamps_resolved_by_orig_idx(tmp_path: Path) -> None:
    """EC-02.3: Identical timestamps at trace end preserve original XES order via _orig_idx."""
    traces_tie = """
  <trace>
    <string key="concept:name" value="C_TIE_1"/>
    <event>
      <string key="concept:name" value="Start"/>
      <date key="time:timestamp" value="2024-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="O_Accepted"/>
      <date key="time:timestamp" value="2024-01-02T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="O_Cancelled"/>
      <date key="time:timestamp" value="2024-01-02T00:00:00.000+00:00"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="C_TIE_2"/>
    <event>
      <string key="concept:name" value="Start"/>
      <date key="time:timestamp" value="2024-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="O_Cancelled"/>
      <date key="time:timestamp" value="2024-01-02T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="O_Accepted"/>
      <date key="time:timestamp" value="2024-01-02T00:00:00.000+00:00"/>
    </event>
  </trace>
"""
    xes_path = _write_xes(tmp_path / "tie.xes", traces_tie)
    dataset = build_loaded_dataset(xes_path)
    cs = dataset.case_summary_df.set_index("case_id")

    assert cs.loc["C_TIE_1", "last_activity"] == "O_Cancelled"
    assert cs.loc["C_TIE_2", "last_activity"] == "O_Accepted"


def test_resource_empty_whitespace_nan_normalized_to_na(tmp_path: Path) -> None:
    """Empty, whitespace-only, or literal 'nan'/'None' org:resource must become pd.NA."""
    dummy_xes = _write_xes(tmp_path / "res.xes", _sample_traces_xml())
    raw_input = pd.DataFrame(
        {
            "case:concept:name": ["C1", "C1", "C1", "C1", "C1"],
            "concept:name": ["A", "B", "C", "D", "E"],
            "time:timestamp": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
            "lifecycle:transition": ["complete"] * 5,
            "org:resource": ["", "   ", "nan", "None", "User_1"],
        }
    )
    with patch("core.loader.pm4py.read_xes", return_value=raw_input):
        df, has_life, has_res, _ = load_xes_raw(dummy_xes)

    assert has_life is True
    assert has_res is True
    assert df["org:resource"].iloc[:4].isna().all()
    assert df["org:resource"].iloc[4] == "User_1"


def test_compute_case_summary_and_activity_freq_empty_df() -> None:
    """Boundary check: empty DataFrames return properly structured empty tables."""
    empty_raw = pd.DataFrame(
        columns=[
            "_orig_idx",
            "case:concept:name",
            "concept:name",
            "time:timestamp",
            "lifecycle:transition",
            "org:resource",
        ]
    )
    cs = compute_case_summary(empty_raw)
    af = compute_activity_frequency(empty_raw, total_cases=0)
    assert cs.empty
    assert list(cs.columns) == [
        "case_id",
        "event_count",
        "start_time",
        "end_time",
        "cycle_time_days",
        "first_activity",
        "last_activity",
    ]
    assert af.empty
    assert list(af.columns) == [
        "activity_name",
        "event_count",
        "case_count",
        "case_coverage_pct",
    ]
