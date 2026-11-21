"""Unit and integration tests for Stage 5: CLI Verification Tool, Disco Benchmarking & Hardening."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pm4py
import pytest

from core.models import EXERCISE_CODES, LoadedDataset
from main_cli import run_cli


@pytest.fixture
def synthetic_xes_file(edge_cases_dataset: LoadedDataset, tmp_path: Path) -> Path:
    """Generate a real temporary XES file from edge_cases_dataset for CLI execution."""
    xes_path = tmp_path / "cli_test_dataset.xes"
    pm4py.write_xes(edge_cases_dataset.raw_df, str(xes_path))
    return xes_path


def test_cli_zero_pyside6_imports() -> None:
    """Invariant: main_cli.py must have zero PySide6 imports."""
    cli_file = Path(__file__).resolve().parent.parent / "main_cli.py"
    text = cli_file.read_text(encoding="utf-8")
    assert "PySide6" not in text, "Forbidden PySide6 import found in main_cli.py"


def test_cli_missing_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI execution without any arguments returns exit code 1."""
    code = run_cli([])
    assert code == 1
    captured = capsys.readouterr().out
    assert "Error: Harap tentukan path file .xes" in captured


def test_cli_file_not_found(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Test CLI execution with a non-existent file returns code 1 and error message."""
    missing = tmp_path / "ghost_file.xes"
    code = run_cli([str(missing)])
    assert code == 1
    captured = capsys.readouterr().out
    assert "ERR_XES_NOT_FOUND" in captured


def test_cli_happy_path(
    synthetic_xes_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test full CLI verification run against an XES file."""
    code = run_cli([str(synthetic_xes_file)])
    assert code == 0

    captured = capsys.readouterr().out

    # Verify banner and sections
    assert "BPIC17 EVENT LOG ANALYZER" in captured
    assert "LOG OVERVIEW & METRICS" in captured
    assert "CHAPTER 11 ANALYTICAL RESULTS TABLE" in captured
    assert "SAMPLE MATCHING CASE IDs FOR DISCO BENCHMARK" in captured
    assert "PROSES VERIFIKASI SELESAI DENGAN SUKSES" in captured

    # Verify all 8 canonical exercise codes are printed in table
    for exercise_code in EXERCISE_CODES:
        assert exercise_code in captured


def test_cli_samples_flag(
    synthetic_xes_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test CLI with customized sample limit flag (-s / --samples)."""
    code = run_cli([str(synthetic_xes_file), "-s", "2"])
    assert code == 0

    captured = capsys.readouterr().out
    assert "Max 2 per soal" in captured


def test_cli_export_dir(
    synthetic_xes_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test CLI automatic CSV export using --export-dir."""
    export_out = tmp_path / "cli_exported_csvs"
    code = run_cli([str(synthetic_xes_file), "--export-dir", str(export_out)])
    assert code == 0

    captured = capsys.readouterr().out
    assert "EXPORTING CSV ARTIFACTS" in captured
    assert "summary_results.csv" in captured

    # Check generated files on disk
    summary_csv = export_out / "summary_results.csv"
    assert summary_csv.exists()

    df_summary = pd.read_csv(summary_csv, encoding="utf-8-sig")
    assert len(df_summary) == 8
    assert list(df_summary["exercise_code"]) == list(EXERCISE_CODES)

    # Check per-exercise cases CSVs
    expected_case_files = [
        "cases_11_7_C.csv",
        "cases_11_7_D.csv",
        "cases_11_7_E.csv",
        "cases_11_15.csv",
        "cases_11_18.csv",
        "cases_11_22.csv",
    ]
    for fn in expected_case_files:
        p = export_out / fn
        assert p.exists(), f"Expected exported CSV {fn} was not found."


def test_main_gui_script_structure() -> None:
    """Verify main.py entry point imports and delegates to QApplication and MainWindow."""
    main_file = Path(__file__).resolve().parent.parent / "main.py"
    text = main_file.read_text(encoding="utf-8")
    assert "MainWindow" in text
    assert "QApplication" in text
    assert "main()" in text
