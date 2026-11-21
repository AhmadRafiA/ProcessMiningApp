"""CLI Verification Tool & Fluxicon Disco Benchmarking script for BPIC17 Event Log Analyzer.

Pure Python domain engine — Zero Qt/GUI imports!
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from core.analyzers import run_all_required_analyses
from core.exporter import (
    export_exercise_cases_csv,
    export_summary_csv,
    get_canonical_exercise_csv_filename,
)
from core.metrics import build_loaded_dataset
from core.models import EXERCISE_CODES, AnalysisResult, BPICAnalyzerError, LoadedDataset


def print_banner() -> None:
    """Print top CLI banner."""
    print("=" * 80)
    print("  BPIC17 EVENT LOG ANALYZER — CLI VERIFICATION & DISCO BENCHMARK")
    print("  Chapter 11 Analytics (Ex 11.7 A–E, 11.15, 11.18, 11.22) & Trace Audit")
    print("=" * 80)


def print_overview(dataset: LoadedDataset) -> None:
    """Print dataset overview and statistics."""
    ov = dataset.overview
    print("\n--- [1] LOG OVERVIEW & METRICS ---")
    print(f"File Name        : {ov.dataset_filename}")
    print(f"Total Cases      : {ov.total_cases:,} cases")
    print(f"Total Events     : {ov.total_events:,} events")
    start_str = ov.start_time_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    end_str = ov.end_time_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Time Range       : {start_str}  -->  {end_str}")
    print(
        f"Mean Cycle Time  : {ov.mean_cycle_time_days:.2f} hari "
        f"(Median: {ov.median_cycle_time_days:.2f} hari)"
    )
    life_status = "Available (OK)" if ov.has_lifecycle else "NOT AVAILABLE"
    res_status = "Available (OK)" if ov.has_resource else "NOT AVAILABLE"
    print(f"Attributes       : lifecycle:transition: {life_status} | org:resource: {res_status}")
    if ov.warnings:
        for w in ov.warnings:
            print(f"  [!] Peringatan: {w}")

    # Top 5 activities
    print("\nTop Activities by Frequency:")
    top_act = dataset.activity_freq_df.head(5)
    for idx, row in top_act.iterrows():
        act_name = str(row["activity_name"])
        ev_cnt = int(row["event_count"])
        cov_pct = float(row["case_coverage_pct"])
        print(f"  {idx + 1}. {act_name:<38} : {ev_cnt:>8,} events ({cov_pct:>6.2f}% cases)")


def print_results_table(results: dict[str, AnalysisResult]) -> None:
    """Print formatted summary table for all 8 Chapter 11 exercises."""
    print("\n--- [2] CHAPTER 11 ANALYTICAL RESULTS TABLE ---")
    header_fmt = "{:<8} | {:<42} | {:>14} | {:>10} | {:>16}"
    row_fmt = "{:<8} | {:<42} | {:>14} | {:>10} | {:>16}"

    sep_line = "-" * 100
    print(sep_line)
    print(
        header_fmt.format(
            "Code",
            "Exercise Title",
            "Matched / Total",
            "Pct (%)",
            "Mean Cycle Time",
        )
    )
    print(sep_line)

    for code in EXERCISE_CODES:
        if code not in results:
            continue
        res = results[code]
        pct_str = f"{res.percentage:.2f}%" if res.percentage is not None else "-"
        dur_str = (
            f"{res.mean_cycle_time_days:.2f} hari"
            if res.mean_cycle_time_days is not None
            else "-"
        )
        ratio_str = f"{res.case_count:,} / {res.total_cases:,}"

        # Truncate title if too long for terminal display
        disp_title = res.title if len(res.title) <= 42 else res.title[:39] + "..."

        print(row_fmt.format(res.exercise_code, disp_title, ratio_str, pct_str, dur_str))

    print(sep_line)


def print_sample_cases(results: dict[str, AnalysisResult], sample_limit: int = 5) -> None:
    """Print sample matching Case IDs for cross-verification vs Fluxicon Disco."""
    print(
        f"\n--- [3] SAMPLE MATCHING CASE IDs FOR DISCO BENCHMARK (Max {sample_limit} per soal) ---"
    )

    for code in EXERCISE_CODES:
        if code not in results:
            continue
        res = results[code]
        df = res.matched_cases_df

        if df.empty:
            print(f"\n[{code}] {res.title} — 0 matching cases")
            continue

        sample_df = df.head(sample_limit)
        count_str = f"{len(sample_df)} of {res.case_count:,}"
        print(f"\n[{code}] {res.title} (Sampel {count_str}):")

        for _, row in sample_df.iterrows():
            cid = str(row["case_id"])
            details: list[str] = []
            if "cycle_time_days" in row and pd.notna(row["cycle_time_days"]):
                details.append(f"CT: {float(row['cycle_time_days']):.2f} hari")
            if "event_count" in row and pd.notna(row["event_count"]):
                details.append(f"Events: {int(row['event_count'])}")
            if "last_activity" in row and pd.notna(row["last_activity"]):
                details.append(f"Last: {row['last_activity']}")
            if "complete_count" in row and pd.notna(row["complete_count"]):
                details.append(f"Complete: {int(row['complete_count'])}")
            if "matching_resources" in row and pd.notna(row["matching_resources"]):
                details.append(f"Resource: {row['matching_resources']}")

            detail_str = f" ({', '.join(details)})" if details else ""
            print(f"   • {cid}{detail_str}")


def export_all_to_dir(
    results: dict[str, AnalysisResult],
    dataset_filename: str,
    export_dir: Path,
) -> None:
    """Export summary results and per-exercise matched cases to target directory."""
    export_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n--- [4] EXPORTING CSV ARTIFACTS TO '{export_dir}' ---")

    # 1. Summary results CSV
    summary_path = export_dir / "summary_results.csv"
    export_summary_csv(results, dataset_filename, summary_path)
    print("  [✓] summary_results.csv (8 canonical exercises)")

    # 2. Per-exercise matched cases CSVs
    for code, res in results.items():
        if res.matched_cases_df is not None:
            filename = get_canonical_exercise_csv_filename(code)
            cases_path = export_dir / filename
            export_exercise_cases_csv(res, cases_path)
            print(f"  [✓] {filename:<22} ({res.case_count:,} cases)")

    print("Seluruh file CSV berhasil diekspor secara atomik.\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="python main_cli.py",
        description=(
            "BPIC17 Event Log Analyzer — CLI Verification & Fluxicon Disco Benchmarking Tool.\n"
            "Evaluates Chapter 11 process mining questions (Ex 11.7 A–E, 11.15, 11.18, 11.22) "
            "completely offline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default=None,
        help="Path ke file log .xes atau .xes.gz BPIC17.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file_opt",
        default=None,
        help="Path alternatif ke file .xes/.xes.gz.",
    )
    parser.add_argument(
        "-e",
        "--export-dir",
        dest="export_dir",
        default=None,
        help="Direktori output untuk ekspor summary_results.csv dan cases_*.csv.",
    )
    parser.add_argument(
        "-s",
        "--samples",
        dest="samples",
        type=int,
        default=5,
        help="Jumlah sampel Case ID yang dicetak per soal untuk pencocokan Disco (default: 5).",
    )
    return parser.parse_args(argv)


def run_cli(argv: Sequence[str] | None = None) -> int:
    """Execute main CLI routine. Returns status exit code (0 for success, 1 for error)."""
    args = parse_args(argv)

    target_file = args.file_path or args.file_opt
    if not target_file:
        print("Error: Harap tentukan path file .xes atau .xes.gz yang akan dianalisis.")
        print("Contoh: python main_cli.py /path/to/BPI_Challenge_2017.xes.gz\n")
        return 1

    file_path = Path(target_file)

    try:
        print_banner()
        print(f"Memuat dan menganalisis event log: '{file_path}'...")
        print("Menjalankan Single-Parse In-Memory Loader & Deterministic Mergesort...")

        # 1. Load and prepare dataset (Single-Parse)
        dataset = build_loaded_dataset(file_path)
        print_overview(dataset)

        # 2. Run all Chapter 11 required analyses
        print("\nMenghitung analisis 8 soal Bab 11 secara deterministik di memori...")
        results = run_all_required_analyses(dataset)

        # 3. Print Results Table
        print_results_table(results)

        # 4. Print Sample Case IDs for Disco Verification
        print_sample_cases(results, sample_limit=args.samples)

        # 5. Optional CSV export
        if args.export_dir:
            export_all_to_dir(results, dataset.overview.dataset_filename, Path(args.export_dir))

        print("\n" + "=" * 80)
        print("  PROSES VERIFIKASI SELESAI DENGAN SUKSES [STATUS: OK]")
        print("=" * 80 + "\n")
        return 0

    except BPICAnalyzerError as err:
        print(f"\n[ERROR DOMAIN ({err.code})]: {err.user_message}")
        if err.detail:
            print(f"Detail Teknis: {err.detail}")
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR]: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
