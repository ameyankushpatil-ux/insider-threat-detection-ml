import sys
import json
import pandas as pd
import numpy as np

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    FINAL_DATASET,
    TABLES_DIR,
    REPORTS_DIR,
)

# Original behavioural measurements.
BEHAVIOURAL_FEATURES = [
    "login_count",
    "logoff_count",
    "unique_pc_count",
    "after_hours_login_count",
    "after_hours_logoff_count",
    "device_activity_count",
    "device_connect_count",
    "device_disconnect_count",
    "after_hours_device_activity",
    "file_access_count",
    "unique_file_extensions",
    "after_hours_file_access",
    "zip_file_count",
    "exe_file_count",
    "pdf_file_count",
    "email_count",
    "attachment_count",
    "total_email_size",
    "after_hours_email_count",
    "after_hours_email_ratio",
    "unique_recipients",
    "web_activity_count",
    "unique_urls",
    "unique_domains",
    "after_hours_web_activity",
]

METADATA_COLUMNS = ["user", "date_only"]

# Outputs created by the previous modelling and evidence pipeline.
EXCLUDED_OUTPUTS = [
    "ocsvm_prediction",
    "ocsvm_anomaly_score",
    "ocsvm_anomaly",
    "iso_prediction",
    "iso_anomaly_score",
    "iso_anomaly",
    "model_agreement",
    "if_percentile",
    "ocsvm_percentile",
    "consensus_score",
    "consensus_rank",
    "dbscan_label",
    "dbscan_noise",
    "dbscan_anomaly",
    "models_agreeing",
    "consensus_category",
    "after_hours_login",
    "after_hours_logoff",
    "after_hours_device",
    "after_hours_file",
    "zip_activity",
    "exe_activity",
    "pdf_activity",
    "email_attachment",
    "after_hours_email",
    "after_hours_web",
    "evidence_score",
    "evidence_signal_count",
]


def main():
    print("=" * 75)
    print("STEP 02: DATA VALIDATION AND FEATURE SELECTION")
    print("=" * 75)

    if not FINAL_DATASET.exists():
        raise FileNotFoundError(FINAL_DATASET)

    df = pd.read_csv(FINAL_DATASET, low_memory=False)

    # Validate required columns.
    required = (
        METADATA_COLUMNS
        + BEHAVIOURAL_FEATURES
        + EXCLUDED_OUTPUTS
    )

    missing_columns = sorted(set(required) - set(df.columns))

    if missing_columns:
        raise ValueError(
            f"Expected columns missing from dataset: {missing_columns}"
        )

    print(f"\nDataset shape: {df.shape}")

    # Convert date and validate identifiers.
    df["date_only"] = pd.to_datetime(
        df["date_only"],
        errors="coerce"
    )

    invalid_dates = int(df["date_only"].isna().sum())
    missing_users = int(df["user"].isna().sum())

    # Check numerical behavioural features.
    numeric_df = df[BEHAVIOURAL_FEATURES].apply(
        pd.to_numeric,
        errors="coerce"
    )

    non_numeric_counts = numeric_df.isna().sum()
    negative_counts = (numeric_df < 0).sum()
    infinite_counts = pd.Series(
        np.isinf(numeric_df.to_numpy()).sum(axis=0),
        index=BEHAVIOURAL_FEATURES
    )

    # Check zero variance.
    constant_features = [
        col for col in BEHAVIOURAL_FEATURES
        if numeric_df[col].nunique(dropna=True) <= 1
    ]

    # Classify columns.
    classification = []

    for col in df.columns:
        if col in METADATA_COLUMNS:
            category = "Metadata"
            use_for_training = False
        elif col in BEHAVIOURAL_FEATURES:
            category = "Behavioural input"
            use_for_training = True
        else:
            category = "Previous model/evidence output"
            use_for_training = False

        classification.append({
            "column": col,
            "category": category,
            "use_for_training": use_for_training,
            "data_type": str(df[col].dtype),
            "missing_count": int(df[col].isna().sum()),
            "unique_values": int(df[col].nunique(dropna=True)),
        })

    classification_df = pd.DataFrame(classification)

    classification_path = (
        TABLES_DIR / "feature_classification.csv"
    )
    classification_df.to_csv(
        classification_path,
        index=False
    )

    # Feature-level quality report.
    feature_quality = pd.DataFrame({
        "feature": BEHAVIOURAL_FEATURES,
        "missing_count": [
            int(numeric_df[c].isna().sum())
            for c in BEHAVIOURAL_FEATURES
        ],
        "negative_count": [
            int(negative_counts[c])
            for c in BEHAVIOURAL_FEATURES
        ],
        "infinite_count": [
            int(infinite_counts[c])
            for c in BEHAVIOURAL_FEATURES
        ],
        "unique_values": [
            int(numeric_df[c].nunique(dropna=True))
            for c in BEHAVIOURAL_FEATURES
        ],
        "mean": [
            float(numeric_df[c].mean())
            if numeric_df[c].notna().any() else None
            for c in BEHAVIOURAL_FEATURES
        ],
        "std": [
            float(numeric_df[c].std())
            if numeric_df[c].notna().any() else None
            for c in BEHAVIOURAL_FEATURES
        ],
    })

    quality_path = TABLES_DIR / "behavioural_feature_quality.csv"
    feature_quality.to_csv(quality_path, index=False)

    # DBSCAN coverage check.
    dbscan_columns = [
        "dbscan_label",
        "dbscan_noise",
        "dbscan_anomaly",
    ]

    dbscan_coverage = {
        col: {
            "available": int(df[col].notna().sum()),
            "missing": int(df[col].isna().sum()),
        }
        for col in dbscan_columns
    }

    # Build validation summary.
    summary = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "behavioural_feature_count": len(BEHAVIOURAL_FEATURES),
        "metadata_column_count": len(METADATA_COLUMNS),
        "excluded_previous_output_count": len(EXCLUDED_OUTPUTS),
        "invalid_dates": invalid_dates,
        "missing_user_identifiers": missing_users,
        "duplicate_user_days": int(
            df.duplicated(subset=["user", "date_only"]).sum()
        ),
        "behavioural_missing_values": int(
            numeric_df.isna().sum().sum()
        ),
        "behavioural_negative_values": int(
            negative_counts.sum()
        ),
        "behavioural_infinite_values": int(
            infinite_counts.sum()
        ),
        "constant_features": constant_features,
        "dbscan_coverage": dbscan_coverage,
        "training_features": BEHAVIOURAL_FEATURES,
        "excluded_outputs": EXCLUDED_OUTPUTS,
    }

    summary_path = TABLES_DIR / "feature_validation_summary.json"

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    # Human-readable report.
    report_path = REPORTS_DIR / "feature_validation_report.txt"

    with open(report_path, "w", encoding="utf-8") as file:
        file.write("DATA VALIDATION AND FEATURE SELECTION REPORT\n")
        file.write("=" * 65 + "\n\n")

        for key, value in summary.items():
            file.write(f"{key}:\n{value}\n\n")

    # Console output.
    print("\n[1] FEATURE CLASSIFICATION")
    print(f"Behavioural inputs: {len(BEHAVIOURAL_FEATURES)}")
    print(f"Metadata columns: {len(METADATA_COLUMNS)}")
    print(f"Previous outputs excluded: {len(EXCLUDED_OUTPUTS)}")

    print("\n[2] DATA QUALITY")
    print(f"Invalid dates: {invalid_dates}")
    print(f"Missing user IDs: {missing_users}")
    print(f"Duplicate user-days: {summary['duplicate_user_days']}")
    print(
        "Missing behavioural values:",
        summary["behavioural_missing_values"]
    )
    print(
        "Negative behavioural values:",
        summary["behavioural_negative_values"]
    )
    print(
        "Infinite behavioural values:",
        summary["behavioural_infinite_values"]
    )

    print("\n[3] CONSTANT FEATURES")
    print(constant_features if constant_features else "None")

    print("\n[4] DBSCAN COVERAGE")
    for col, values in dbscan_coverage.items():
        print(
            f"{col}: {values['available']:,} available, "
            f"{values['missing']:,} missing"
        )

    print("\n[5] OUTPUT FILES")
    print(classification_path)
    print(quality_path)
    print(summary_path)
    print(report_path)

    print("\nSTEP 02 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
