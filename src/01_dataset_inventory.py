import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    FINAL_DATASET,
    DFIR_TIMELINE,
    TABLES_DIR,
    REPORTS_DIR,
    PROJECT_TITLE,
    PROJECT_DATASET,
)


def inspect_files(directory):
    """Collect file names, extensions and sizes recursively."""
    records = []

    if not directory.exists():
        return records

    for path in directory.rglob("*"):
        if path.is_file():
            records.append({
                "file_name": path.name,
                "relative_path": str(path.relative_to(PROJECT_ROOT)),
                "extension": path.suffix.lower(),
                "size_mb": round(path.stat().st_size / (1024 ** 2), 3),
            })

    return records


def main():
    print("=" * 75)
    print("M.TECH INSIDER-THREAT DETECTION PROJECT")
    print("STEP 01: DATASET INVENTORY AND VALIDATION")
    print("=" * 75)

    print(f"\nProject: {PROJECT_TITLE}")
    print(f"Dataset: {PROJECT_DATASET}")
    print(f"Project root: {PROJECT_ROOT}")

    # Check important paths
    print("\n[1] PATH VALIDATION")

    paths = {
        "Raw data directory": RAW_DATA_DIR,
        "Processed data directory": PROCESSED_DATA_DIR,
        "Final processed dataset": FINAL_DATASET,
        "DFIR investigation timeline": DFIR_TIMELINE,
    }

    for label, path in paths.items():
        print(f"{label}: {'FOUND' if path.exists() else 'NOT FOUND'}")

    if not FINAL_DATASET.exists():
        raise FileNotFoundError(
            f"Required dataset not found: {FINAL_DATASET}"
        )

    # Inventory raw and processed files
    print("\n[2] FILE INVENTORY")

    raw_records = inspect_files(RAW_DATA_DIR)
    processed_records = inspect_files(PROCESSED_DATA_DIR)

    inventory = pd.DataFrame(raw_records + processed_records)

    if not inventory.empty:
        inventory.to_csv(
            TABLES_DIR / "dataset_file_inventory.csv",
            index=False
        )

    print(f"Raw files found: {len(raw_records)}")
    print(f"Processed files found: {len(processed_records)}")

    # Read final dataset
    print("\n[3] FINAL DATASET VALIDATION")

    df = pd.read_csv(FINAL_DATASET, low_memory=False)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Unique users: {df['user'].nunique():,}")

    df["date_only"] = pd.to_datetime(
        df["date_only"],
        errors="coerce"
    )

    print(f"Date range: {df['date_only'].min()} to "
          f"{df['date_only'].max()}")

    duplicate_rows = int(df.duplicated().sum())
    duplicate_user_days = int(
        df.duplicated(subset=["user", "date_only"]).sum()
    )

    print(f"Duplicate rows: {duplicate_rows:,}")
    print(f"Duplicate user-days: {duplicate_user_days:,}")

    # Missing-value analysis
    missing = df.isna().sum()
    missing = missing[missing > 0]

    print("\n[4] MISSING VALUE ANALYSIS")

    if missing.empty:
        print("No missing values found.")
    else:
        print(missing.to_string())

    # Column inventory
    column_inventory = pd.DataFrame({
        "column": df.columns,
        "data_type": [str(df[c].dtype) for c in df.columns],
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "missing_percentage": [
            round(float(df[c].isna().mean() * 100), 4)
            for c in df.columns
        ],
        "unique_values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })

    column_inventory.to_csv(
        TABLES_DIR / "dataset_column_inventory.csv",
        index=False
    )

    # Summary
    summary = {
        "project_title": PROJECT_TITLE,
        "dataset": PROJECT_DATASET,
        "inspection_time": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": str(FINAL_DATASET),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "unique_users": int(df["user"].nunique()),
        "start_date": str(df["date_only"].min().date()),
        "end_date": str(df["date_only"].max().date()),
        "duplicate_rows": duplicate_rows,
        "duplicate_user_days": duplicate_user_days,
        "columns_with_missing_values": {
            str(k): int(v) for k, v in missing.items()
        },
        "raw_file_count": len(raw_records),
        "processed_file_count": len(processed_records),
    }

    summary_path = TABLES_DIR / "dataset_summary.json"

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    report_path = REPORTS_DIR / "dataset_inventory.txt"

    with open(report_path, "w", encoding="utf-8") as file:
        file.write("M.TECH INSIDER-THREAT DETECTION\n")
        file.write("DATASET INVENTORY REPORT\n")
        file.write("=" * 60 + "\n\n")

        for key, value in summary.items():
            file.write(f"{key}: {value}\n")

    print("\n[5] OUTPUT FILES")

    print(f"File inventory: {TABLES_DIR / 'dataset_file_inventory.csv'}")
    print(f"Column inventory: {TABLES_DIR / 'dataset_column_inventory.csv'}")
    print(f"Dataset summary: {summary_path}")
    print(f"Text report: {report_path}")

    print("\nSTEP 01 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
